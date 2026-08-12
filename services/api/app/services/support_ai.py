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


PROMPT_VERSION = (
    "grounded-v1+evidence-decision-v1"
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
        connection.row_factory = dict_row

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


            row = (
                cursor.fetchone()
            )


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
        connection.row_factory = dict_row


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


                for rank, evidence in enumerate(
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
                    )
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
        ticket_id=ticket_id,
        message_id=message_id,
    ).strip()


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


    if (
        assessment
        .generation_allowed
    ):
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
                        assessment.confidence,

                        (
                            settings
                            .evidence_medium_similarity
                            - 0.0001
                        ),
                    ),

                    confidence_band="LOW",

                    generation_allowed=False,

                    contradiction_detected=
                        assessment
                        .contradiction_detected,

                    ambiguity_detected=
                        assessment
                        .ambiguity_detected,

                    reasons=[
                        *assessment.reasons,
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


    # --------------------------------------------------------
    # IMPORTANT:
    #
    # M3E may judge the knowledge evidence as HIGH, but M4 has
    # not yet evaluated restricted actions or commerce safety.
    #
    # Therefore M3E NEVER authorizes AUTO_RESPOND.
    # --------------------------------------------------------

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
            user=user,

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