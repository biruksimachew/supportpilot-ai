from time import perf_counter
from uuid import UUID

from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from app.core.config import settings

from app.core.database import (
    get_database_connection,
)

from app.schemas.auth import (
    InternalUser,
)

from app.schemas.evidence_decision import (
    TicketAIDraftResponse,
)

from app.schemas.grounded_generation import (
    GroundedAnswerResponse,
)

from app.services.embeddings import (
    EmbeddingProvider,
)

from app.services.evidence_decision import (
    EvidenceAssessment,
    assess_evidence,
)

from app.services.generation import (
    GenerationProvider,
)

from app.services.grounded_answer import (
    generate_grounded_answer,
)

from app.services.knowledge_retrieval import (
    retrieve_knowledge,
)

from app.services.restricted_actions import (
    RestrictedActionDetection,
    detect_restricted_action,
)


PROMPT_VERSION = (
    "grounded-v1+evidence-decision-v1"
)


RESTRICTED_ACTION_VERSION = (
    "restricted-action-v1"
)


class TicketMessageNotFoundError(
    LookupError
):
    pass


def _load_message(
    *,
    ticket_id: UUID,
    message_id: UUID,
) -> str:

    with get_database_connection() as connection:

        connection.row_factory = (
            dict_row
        )


        with connection.cursor() as cursor:

            cursor.execute(
                """
                select
                    m.body

                from public.messages m

                join public.tickets t
                    on t.id = m.ticket_id

                where t.id = %s
                  and m.id = %s

                limit 1;
                """,
                (
                    ticket_id,
                    message_id,
                ),
            )


            row = cursor.fetchone()


    if row is None:

        raise TicketMessageNotFoundError(
            (
                "Message was not found "
                "for this ticket."
            )
        )


    return row[
        "body"
    ]


def _insufficient_answer(
    *,
    question: str,

    retrieval_provider: str,
    retrieval_model: str,
) -> GroundedAnswerResponse:

    return GroundedAnswerResponse(
        status=
            "INSUFFICIENT_EVIDENCE",

        question=
            question,

        answer=(
            "I don't have enough approved "
            "evidence to answer that reliably."
        ),

        citations=[],

        generation_provider=None,
        generation_model=None,

        retrieval_provider=
            retrieval_provider,

        retrieval_model=
            retrieval_model,

        input_tokens=None,
        output_tokens=None,
        generation_ms=None,
    )


def _restricted_action_answer(
    *,
    question: str,
) -> GroundedAnswerResponse:

    return GroundedAnswerResponse(
        status=
            "INSUFFICIENT_EVIDENCE",

        question=
            question,

        answer=(
            "This request requires human "
            "review. No refund, cancellation, "
            "order change, payment action, "
            "policy exception, or replacement "
            "action has been performed."
        ),

        citations=[],

        generation_provider=None,
        generation_model=None,

        retrieval_provider=
            "not-run",

        retrieval_model=
            RESTRICTED_ACTION_VERSION,

        input_tokens=None,
        output_tokens=None,
        generation_ms=None,
    )


def _persist_restricted_ai_run(
    *,
    user: InternalUser,

    ticket_id: UUID,
    message_id: UUID,

    detection:
        RestrictedActionDetection,

    reasons: list[str],

    latency_ms: int,

) -> UUID:

    escalation_reason = (
        "RESTRICTED_ACTION:"
        + ",".join(
            detection.categories
        )
    )


    with get_database_connection() as connection:

        connection.row_factory = (
            dict_row
        )


        with connection.transaction():

            with connection.cursor() as cursor:

                # ------------------------------------------
                # Persist the deterministic policy decision.
                # ------------------------------------------

                cursor.execute(
                    """
                    insert into public.ai_runs (
                        ticket_id,
                        message_id,

                        provider,
                        model,

                        prompt_version,

                        intent,

                        confidence,
                        confidence_band,

                        decision,
                        decision_reasons,

                        latency_ms,
                        error_code
                    )

                    values (
                        %s,
                        %s,

                        'deterministic-policy',
                        %s,

                        %s,

                        null,

                        0.0,
                        'LOW',

                        'REVIEW_REQUIRED',
                        %s,

                        %s,
                        null
                    )

                    returning id;
                    """,
                    (
                        ticket_id,
                        message_id,

                        RESTRICTED_ACTION_VERSION,

                        RESTRICTED_ACTION_VERSION,

                        Jsonb(
                            reasons
                        ),

                        latency_ms,
                    ),
                )


                ai_run_id = (
                    cursor.fetchone()[
                        "id"
                    ]
                )


                # ------------------------------------------
                # Mark the ticket itself as restricted and
                # force it into the human-review queue.
                # ------------------------------------------

                cursor.execute(
                    """
                    update public.tickets

                    set
                        restricted_action =
                            true,

                        status =
                            'REVIEW_REQUIRED',

                        escalation_reason =
                            %s

                    where id = %s;
                    """,
                    (
                        escalation_reason,
                        ticket_id,
                    ),
                )


                # ------------------------------------------
                # Preserve the same general AI-run audit
                # event used by normal drafts.
                # ------------------------------------------

                cursor.execute(
                    """
                    insert into public.audit_events (
                        actor_type,
                        actor_id,

                        event_type,

                        entity_type,
                        entity_id,

                        metadata
                    )

                    values (
                        'AI',
                        %s,

                        'AI_DRAFT_EVALUATED',

                        'ai_run',
                        %s,

                        %s
                    );
                    """,
                    (
                        str(
                            ai_run_id
                        ),

                        str(
                            ai_run_id
                        ),

                        Jsonb(
                            {
                                "ticket_id":
                                    str(
                                        ticket_id
                                    ),

                                "message_id":
                                    str(
                                        message_id
                                    ),

                                "requested_by":
                                    str(
                                        user.id
                                    ),

                                "requested_by_role":
                                    user.role,

                                "decision":
                                    (
                                        "REVIEW_REQUIRED"
                                    ),

                                "restricted_action":
                                    True,

                                "restricted_categories":
                                    list(
                                        detection
                                        .categories
                                    ),

                                "evidence_count":
                                    0,

                                "generation_attempted":
                                    False,
                            }
                        ),
                    ),
                )


                # ------------------------------------------
                # Separate security-specific audit event.
                #
                # Deliberately does NOT persist the raw
                # customer message.
                # ------------------------------------------

                cursor.execute(
                    """
                    insert into public.audit_events (
                        actor_type,
                        actor_id,

                        event_type,

                        entity_type,
                        entity_id,

                        metadata
                    )

                    values (
                        'AI',
                        %s,

                        'RESTRICTED_ACTION_DETECTED',

                        'ticket',
                        %s,

                        %s
                    );
                    """,
                    (
                        str(
                            ai_run_id
                        ),

                        str(
                            ticket_id
                        ),

                        Jsonb(
                            {
                                "ticket_id":
                                    str(
                                        ticket_id
                                    ),

                                "message_id":
                                    str(
                                        message_id
                                    ),

                                "ai_run_id":
                                    str(
                                        ai_run_id
                                    ),

                                "categories":
                                    list(
                                        detection
                                        .categories
                                    ),

                                "matched_rules":
                                    list(
                                        detection
                                        .matched_rules
                                    ),
                            }
                        ),
                    ),
                )


    return ai_run_id


def _persist_ai_run(
    *,
    user: InternalUser,

    ticket_id: UUID,
    message_id: UUID,

    generation_provider:
        GenerationProvider,

    assessment:
        EvidenceAssessment,

    decision: str,

    reasons: list[str],

    retrieval,

    latency_ms: int,

) -> UUID:

    with get_database_connection() as connection:

        connection.row_factory = (
            dict_row
        )


        with connection.transaction():

            with connection.cursor() as cursor:

                cursor.execute(
                    """
                    insert into public.ai_runs (
                        ticket_id,
                        message_id,

                        provider,
                        model,

                        prompt_version,

                        intent,

                        confidence,
                        confidence_band,

                        decision,
                        decision_reasons,

                        latency_ms,
                        error_code
                    )

                    values (
                        %s,
                        %s,

                        %s,
                        %s,

                        %s,

                        null,

                        %s,
                        %s,

                        %s,
                        %s,

                        %s,
                        null
                    )

                    returning id;
                    """,
                    (
                        ticket_id,
                        message_id,

                        generation_provider
                        .provider_name,

                        generation_provider
                        .model,

                        PROMPT_VERSION,

                        assessment
                        .confidence,

                        assessment
                        .confidence_band,

                        decision,

                        Jsonb(
                            reasons
                        ),

                        latency_ms,
                    ),
                )


                ai_run_id = (
                    cursor.fetchone()[
                        "id"
                    ]
                )


                for (
                    rank,
                    evidence,
                ) in enumerate(
                    retrieval.results,
                    start=1,
                ):

                    cursor.execute(
                        """
                        insert into
                            public.retrieval_evidence (
                                ai_run_id,
                                chunk_id,
                                rank,
                                score
                            )

                        values (
                            %s,
                            %s,
                            %s,
                            %s
                        );
                        """,
                        (
                            ai_run_id,
                            evidence.chunk_id,
                            rank,
                            evidence.similarity,
                        ),
                    )


                cursor.execute(
                    """
                    insert into public.audit_events (
                        actor_type,
                        actor_id,

                        event_type,

                        entity_type,
                        entity_id,

                        metadata
                    )

                    values (
                        'AI',
                        %s,

                        'AI_DRAFT_EVALUATED',

                        'ai_run',
                        %s,

                        %s
                    );
                    """,
                    (
                        str(
                            ai_run_id
                        ),

                        str(
                            ai_run_id
                        ),

                        Jsonb(
                            {
                                "ticket_id":
                                    str(
                                        ticket_id
                                    ),

                                "message_id":
                                    str(
                                        message_id
                                    ),

                                "requested_by":
                                    str(
                                        user.id
                                    ),

                                "requested_by_role":
                                    user.role,

                                "confidence":
                                    assessment
                                    .confidence,

                                "confidence_band":
                                    assessment
                                    .confidence_band,

                                "decision":
                                    decision,

                                "evidence_count":
                                    len(
                                        retrieval
                                        .results
                                    ),

                                "contradiction_detected":
                                    assessment
                                    .contradiction_detected,
                            }
                        ),
                    ),
                )


    return ai_run_id


def run_ticket_ai_draft(
    *,
    user: InternalUser,

    ticket_id: UUID,
    message_id: UUID,

    embedding_provider:
        EmbeddingProvider,

    generation_provider:
        GenerationProvider,

) -> TicketAIDraftResponse:

    started_at = (
        perf_counter()
    )


    question = _load_message(
        ticket_id=
            ticket_id,

        message_id=
            message_id,
    ).strip()


    # ======================================================
    # M4C PRE-GENERATION SAFETY GATE
    #
    # This runs BEFORE:
    # - semantic retrieval
    # - Ollama generation
    # - any future commerce operation
    # ======================================================

    restricted_detection = (
        detect_restricted_action(
            question
        )
    )


    if restricted_detection.restricted:

        reasons = [
            "RESTRICTED_ACTION_DETECTED",

            *[
                (
                    "RESTRICTED_ACTION:"
                    + category
                )

                for category
                in restricted_detection
                .categories
            ],

            "HUMAN_ACTION_REQUIRED",
            "AUTO_RESPONSE_BLOCKED",
        ]


        latency_ms = max(
            0,

            round(
                (
                    perf_counter()
                    - started_at
                )
                * 1000
            ),
        )


        ai_run_id = (
            _persist_restricted_ai_run(
                user=
                    user,

                ticket_id=
                    ticket_id,

                message_id=
                    message_id,

                detection=
                    restricted_detection,

                reasons=
                    reasons,

                latency_ms=
                    latency_ms,
            )
        )


        return TicketAIDraftResponse(
            ai_run_id=
                ai_run_id,

            ticket_id=
                ticket_id,

            message_id=
                message_id,

            confidence=
                0.0,

            confidence_band=
                "LOW",

            decision=
                "REVIEW_REQUIRED",

            decision_reasons=
                reasons,

            evidence_count=
                0,

            contradiction_detected=
                False,

            generation_attempted=
                False,

            answer=
                _restricted_action_answer(
                    question=
                        question
                ),
        )


    # ======================================================
    # NORMAL NON-RESTRICTED RAG PIPELINE
    # ======================================================

    retrieval = retrieve_knowledge(
        question=
            question,

        provider=
            embedding_provider,

        top_k=5,

        min_similarity=0.0,
    )


    assessment = (
        assess_evidence(
            retrieval
        )
    )


    generation_attempted = False


    if assessment.generation_allowed:

        generation_attempted = True


        answer = (
            generate_grounded_answer(
                question=
                    question,

                retrieval=
                    retrieval,

                provider=
                    generation_provider,
            )
        )


        if (
            answer.status
            ==
            "INSUFFICIENT_EVIDENCE"
        ):

            assessment = (
                EvidenceAssessment(
                    confidence=min(
                        assessment
                        .confidence,

                        (
                            settings
                            .evidence_medium_similarity
                            - 0.0001
                        ),
                    ),

                    confidence_band=
                        "LOW",

                    generation_allowed=
                        False,

                    contradiction_detected=
                        assessment
                        .contradiction_detected,

                    ambiguity_detected=
                        assessment
                        .ambiguity_detected,

                    reasons=[
                        *assessment
                        .reasons,

                        (
                            "GENERATION_DECLARED_"
                            "INSUFFICIENT_EVIDENCE"
                        ),
                    ],
                )
            )


    else:

        answer = _insufficient_answer(
            question=
                question,

            retrieval_provider=
                retrieval.provider,

            retrieval_model=
                retrieval.model,
        )


    # ------------------------------------------------------
    # M4C now evaluates restricted actions, but full commerce
    # safety and controlled AUTO_RESPOND eligibility are still
    # implemented in later M4 checkpoints.
    #
    # Therefore normal answers remain REVIEW_REQUIRED here.
    # ------------------------------------------------------

    reasons = [
        *assessment.reasons,
        "COMMERCE_SAFETY_NOT_EVALUATED",
    ]


    decision = (
        "REVIEW_REQUIRED"
    )


    latency_ms = max(
        0,

        round(
            (
                perf_counter()
                - started_at
            )
            * 1000
        ),
    )


    ai_run_id = (
        _persist_ai_run(
            user=
                user,

            ticket_id=
                ticket_id,

            message_id=
                message_id,

            generation_provider=
                generation_provider,

            assessment=
                assessment,

            decision=
                decision,

            reasons=
                reasons,

            retrieval=
                retrieval,

            latency_ms=
                latency_ms,
        )
    )


    return TicketAIDraftResponse(
        ai_run_id=
            ai_run_id,

        ticket_id=
            ticket_id,

        message_id=
            message_id,

        confidence=
            assessment
            .confidence,

        confidence_band=
            assessment
            .confidence_band,

        decision=
            decision,

        decision_reasons=
            reasons,

        evidence_count=
            len(
                retrieval.results
            ),

        contradiction_detected=
            assessment
            .contradiction_detected,

        generation_attempted=
            generation_attempted,

        answer=
            answer,
    )