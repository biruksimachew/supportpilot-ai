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

from app.schemas.commerce import (
    CommerceOrder,
)

from app.schemas.evidence_decision import (
    TicketAIDraftResponse,
)

from app.schemas.grounded_generation import (
    GroundedAnswerResponse,
)

from app.services.commerce import (
    CommerceProviderError,
    get_commerce_provider,
)

from app.services.commerce_lookup import (
    CommerceOrderNotFoundError,
    lookup_customer_order,
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

from app.services.request_classification import (
    SupportRequestClassification,
    classify_support_request,
)

from app.services.restricted_actions import (
    RestrictedActionDetection,
    detect_restricted_action,
)

from app.services.support_decision import (
    UnifiedSafetyDecision,
    decide_support_action,
)


PROMPT_VERSION = (
    "grounded-v1+unified-decision-v2"
)

RESTRICTED_ACTION_VERSION = (
    "restricted-action-v1"
)


UNIFIED_DECISION_VERSION = (
    "unified-decision-v2"
)


COMMERCE_DECISION_MODEL = (
    "verified-order-status-v1"
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


def _load_ticket_context(
    *,
    ticket_id: UUID,
) -> dict:

    with get_database_connection() as connection:

        connection.row_factory = dict_row

        with connection.cursor() as cursor:

            cursor.execute(
                """
                select
                    id,
                    customer_ref,

                    restricted_action,

                    identity_verification_status,
                    identity_verified_order_number

                from public.tickets

                where id = %s

                limit 1;
                """,
                (
                    ticket_id,
                ),
            )


            row = cursor.fetchone()


    if row is None:

        raise TicketMessageNotFoundError(
            "Ticket was not found."
        )


    return row


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


def _clarification_answer(
    *,
    question: str,
    order_number: str | None,
) -> GroundedAnswerResponse:

    if order_number is None:

        text = (
            "I need the Northstar order number "
            "before order details can be checked. "
            "Customer identity must also be verified "
            "before any order information is disclosed."
        )

    else:

        text = (
            f"Identity verification is required for "
            f"order {order_number} before order details "
            "can be disclosed. Please complete the "
            "customer verification step."
        )


    return GroundedAnswerResponse(
        status=
            "INSUFFICIENT_EVIDENCE",

        question=
            question,

        answer=
            text,

        citations=[],

        generation_provider=None,
        generation_model=None,

        retrieval_provider=
            "not-run",

        retrieval_model=
            UNIFIED_DECISION_VERSION,

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
            "This request requires human review. "
            "No refund, cancellation, order change, "
            "payment action, policy exception, or "
            "replacement action has been performed."
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


def _commerce_answer(
    *,
    question: str,
    order: CommerceOrder,
    provider_name: str,
) -> GroundedAnswerResponse:

    status_text = (
        order.status
        .replace(
            "_",
            " ",
        )
        .lower()
    )


    parts = [
        (
            f"Order {order.order_number} "
            f"is currently {status_text}."
        )
    ]


    if order.delivered_at is not None:

        parts.append(
            (
                "It was delivered on "
                f"{order.delivered_at.isoformat()}."
            )
        )


    item_statuses = [
        (
            f"{item.name}: "
            + item.status
            .replace(
                "_",
                " ",
            )
            .lower()
        )

        for item
        in order.items

        if item.status
    ]


    if item_statuses:

        parts.append(
            (
                "Fulfillment details: "
                + "; ".join(
                    item_statuses
                )
                + "."
            )
        )


    if order.tracking_number:

        parts.append(
            (
                "Tracking number: "
                f"{order.tracking_number}."
            )
        )


    return GroundedAnswerResponse(
        status=
            "ANSWERED",

        question=
            question,

        answer=
            " ".join(
                parts
            ),

        citations=[],

        generation_provider=None,
        generation_model=None,

        retrieval_provider=
            "commerce-tool",

        retrieval_model=
            provider_name,

        input_tokens=None,
        output_tokens=None,
        generation_ms=None,
    )


def _insert_decision_audit(
    cursor,
    *,
    ai_run_id: UUID,
    ticket_id: UUID,
    message_id: UUID,
    user: InternalUser,

    decision:
        UnifiedSafetyDecision,

    intent: str,

    commerce_required: bool,
) -> None:

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

            'SUPPORT_DECISION_EVALUATED',

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

                    "intent":
                        intent,

                    "commerce_required":
                        commerce_required,

                    "decision":
                        decision.decision,

                    "ticket_status":
                        decision.ticket_status,

                    "safe_draft_ready":
                        decision.safe_draft_ready,

                    "auto_response_eligible":
                        (
                            decision.decision
                            == "AUTO_RESPOND"
                        ),

                    "reasons":
                        list(
                            decision.reasons
                        ),
                }
            ),
        ),
    )


def _persist_non_rag_ai_run(
    *,
    user: InternalUser,

    ticket_id: UUID,
    message_id: UUID,

    classification:
        SupportRequestClassification,

    decision:
        UnifiedSafetyDecision,

    provider: str,
    model: str,

    confidence: float,
    confidence_band: str,

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

                        %s,

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

                        provider,
                        model,

                        UNIFIED_DECISION_VERSION,

                        classification.intent,

                        confidence,
                        confidence_band,

                        decision.decision,

                        Jsonb(
                            list(
                                decision.reasons
                            )
                        ),

                        latency_ms,
                    ),
                )


                ai_run_id = (
                    cursor.fetchone()[
                        "id"
                    ]
                )


                cursor.execute(
                    """
                    update public.tickets

                    set
                        intent = %s,
                        confidence_band = %s,
                        status = %s,
                        escalation_reason = %s

                    where id = %s;
                    """,
                    (
                        classification.intent,

                        confidence_band,

                        decision.ticket_status,

                        decision.escalation_reason,

                        ticket_id,
                    ),
                )


                _insert_decision_audit(
                    cursor,

                    ai_run_id=
                        ai_run_id,

                    ticket_id=
                        ticket_id,

                    message_id=
                        message_id,

                    user=
                        user,

                    decision=
                        decision,

                    intent=
                        classification.intent,

                    commerce_required=
                        classification
                        .commerce_required,
                )


    return ai_run_id


def _create_commerce_ai_run(
    *,
    ticket_id: UUID,
    message_id: UUID,

    provider_name: str,

) -> UUID:

    with get_database_connection() as connection:

        connection.row_factory = dict_row


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

                    'commerce-tool',
                    %s,

                    %s,

                    'order_status',

                    0.0,
                    'LOW',

                    'REVIEW_REQUIRED',
                    '["COMMERCE_LOOKUP_PENDING"]'::jsonb,

                    null,
                    null
                )

                returning id;
                """,
                (
                    ticket_id,
                    message_id,

                    provider_name,

                    UNIFIED_DECISION_VERSION,
                ),
            )


            return cursor.fetchone()[
                "id"
            ]


def _finalize_commerce_ai_run(
    *,
    user: InternalUser,

    ai_run_id: UUID,

    ticket_id: UUID,
    message_id: UUID,

    decision:
        UnifiedSafetyDecision,

    confidence: float,
    confidence_band: str,

    latency_ms: int,

    error_code:
        str | None = None,

) -> None:

    with get_database_connection() as connection:

        connection.row_factory = dict_row


        with connection.transaction():

            with connection.cursor() as cursor:

                cursor.execute(
                    """
                    update public.ai_runs

                    set
                        confidence = %s,
                        confidence_band = %s,

                        decision = %s,
                        decision_reasons = %s,

                        latency_ms = %s,
                        error_code = %s

                    where id = %s;
                    """,
                    (
                        confidence,
                        confidence_band,

                        decision.decision,

                        Jsonb(
                            list(
                                decision.reasons
                            )
                        ),

                        latency_ms,
                        error_code,

                        ai_run_id,
                    ),
                )


                cursor.execute(
                    """
                    update public.tickets

                    set
                        intent =
                            'order_status',

                        confidence_band =
                            %s,

                        status =
                            %s,

                        escalation_reason =
                            %s

                    where id = %s;
                    """,
                    (
                        confidence_band,

                        decision.ticket_status,

                        decision.escalation_reason,

                        ticket_id,
                    ),
                )


                _insert_decision_audit(
                    cursor,

                    ai_run_id=
                        ai_run_id,

                    ticket_id=
                        ticket_id,

                    message_id=
                        message_id,

                    user=
                        user,

                    decision=
                        decision,

                    intent=
                        "order_status",

                    commerce_required=
                        True,
                )


def _persist_restricted_ai_run(
    *,
    user: InternalUser,

    ticket_id: UUID,
    message_id: UUID,

    detection:
        RestrictedActionDetection,

    decision:
        UnifiedSafetyDecision,

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

                        confidence,
                        confidence_band,

                        decision,
                        decision_reasons,

                        latency_ms
                    )

                    values (
                        %s,
                        %s,

                        'deterministic-policy',
                        %s,

                        %s,

                        0.0,
                        'LOW',

                        %s,
                        %s,

                        %s
                    )

                    returning id;
                    """,
                    (
                        ticket_id,
                        message_id,

                        RESTRICTED_ACTION_VERSION,

                        RESTRICTED_ACTION_VERSION,

                        decision.decision,

                        Jsonb(
                            list(
                                decision.reasons
                            )
                        ),

                        latency_ms,
                    ),
                )


                ai_run_id = (
                    cursor.fetchone()[
                        "id"
                    ]
                )


                cursor.execute(
                    """
                    update public.tickets

                    set
                        restricted_action =
                            true,

                        status =
                            %s,

                        confidence_band =
                            'LOW',

                        escalation_reason =
                            %s

                    where id = %s;
                    """,
                    (
                        decision.ticket_status,

                        decision.escalation_reason,

                        ticket_id,
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
                                        detection.categories
                                    ),

                                "matched_rules":
                                    list(
                                        detection.matched_rules
                                    ),
                            }
                        ),
                    ),
                )


    return ai_run_id


def _persist_rag_ai_run(
    *,
    user: InternalUser,

    ticket_id: UUID,
    message_id: UUID,

    classification:
        SupportRequestClassification,

    generation_provider:
        GenerationProvider,

    assessment:
        EvidenceAssessment,

    decision:
        UnifiedSafetyDecision,

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

                        %s,

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

                        classification.intent,

                        assessment.confidence,

                        assessment.confidence_band,

                        decision.decision,

                        Jsonb(
                            list(
                                decision.reasons
                            )
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
                        insert into public.retrieval_evidence (
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
                    update public.tickets

                    set
                        intent = %s,
                        confidence_band = %s,
                        status = %s,
                        escalation_reason = %s

                    where id = %s;
                    """,
                    (
                        classification.intent,

                        assessment.confidence_band,

                        decision.ticket_status,

                        decision.escalation_reason,

                        ticket_id,
                    ),
                )


                _insert_decision_audit(
                    cursor,

                    ai_run_id=
                        ai_run_id,

                    ticket_id=
                        ticket_id,

                    message_id=
                        message_id,

                    user=
                        user,

                    decision=
                        decision,

                    intent=
                        classification.intent,

                    commerce_required=
                        False,
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
    # Gate 1 — restricted action.
    # ======================================================

    restricted_detection = (
        detect_restricted_action(
            question
        )
    )


    if restricted_detection.restricted:

        decision = (
            decide_support_action(
                restricted_categories=
                    restricted_detection
                    .categories
            )
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
            _persist_restricted_ai_run(
                user=
                    user,

                ticket_id=
                    ticket_id,

                message_id=
                    message_id,

                detection=
                    restricted_detection,

                decision=
                    decision,

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
                decision.decision,

            decision_reasons=
                list(
                    decision.reasons
                ),

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

            safe_draft_ready=
                False,
        )


    classification = (
        classify_support_request(
            question
        )
    )


    ticket = (
        _load_ticket_context(
            ticket_id=
                ticket_id
        )
    )


    # ======================================================
    # Gate 2 — a ticket already carrying a restricted action
    # stays under human review.
    # ======================================================

    if ticket[
        "restricted_action"
    ]:

        decision = (
            decide_support_action(
                existing_restricted_action=
                    True
            )
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
            _persist_non_rag_ai_run(
                user=
                    user,

                ticket_id=
                    ticket_id,

                message_id=
                    message_id,

                classification=
                    classification,

                decision=
                    decision,

                provider=
                    "deterministic-policy",

                model=
                    UNIFIED_DECISION_VERSION,

                confidence=
                    0.0,

                confidence_band=
                    "LOW",

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
                decision.decision,

            decision_reasons=
                list(
                    decision.reasons
                ),

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

            intent=
                classification.intent,

            commerce_required=
                classification
                .commerce_required,

            order_number=
                classification
                .order_number,

            safe_draft_ready=
                False,
        )


    # ======================================================
    # Gate 3 — commerce path.
    # ======================================================

    if classification.commerce_required:

        order_number = (
            classification.order_number
        )


        if order_number is None:

            decision = (
                decide_support_action(
                    commerce_required=
                        True,

                    order_number=
                        None,
                )
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
                _persist_non_rag_ai_run(
                    user=
                        user,

                    ticket_id=
                        ticket_id,

                    message_id=
                        message_id,

                    classification=
                        classification,

                    decision=
                        decision,

                    provider=
                        "deterministic-policy",

                    model=
                        UNIFIED_DECISION_VERSION,

                    confidence=
                        0.0,

                    confidence_band=
                        "LOW",

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
                    decision.decision,

                decision_reasons=
                    list(
                        decision.reasons
                    ),

                evidence_count=
                    0,

                contradiction_detected=
                    False,

                generation_attempted=
                    False,

                answer=
                    _clarification_answer(
                        question=
                            question,

                        order_number=
                            None,
                    ),

                intent=
                    classification.intent,

                commerce_required=
                    True,

                order_number=
                    None,

                safe_draft_ready=
                    False,
            )


        identity_verified = (
            ticket[
                "identity_verification_status"
            ]
            == "VERIFIED"

            and ticket[
                "identity_verified_order_number"
            ]
            == order_number

            and ticket[
                "customer_ref"
            ]
            is not None
        )


        if not identity_verified:

            decision = (
                decide_support_action(
                    commerce_required=
                        True,

                    order_number=
                        order_number,

                    identity_verified_for_order=
                        False,
                )
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
                _persist_non_rag_ai_run(
                    user=
                        user,

                    ticket_id=
                        ticket_id,

                    message_id=
                        message_id,

                    classification=
                        classification,

                    decision=
                        decision,

                    provider=
                        "deterministic-policy",

                    model=
                        UNIFIED_DECISION_VERSION,

                    confidence=
                        0.0,

                    confidence_band=
                        "LOW",

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
                    decision.decision,

                decision_reasons=
                    list(
                        decision.reasons
                    ),

                evidence_count=
                    0,

                contradiction_detected=
                    False,

                generation_attempted=
                    False,

                answer=
                    _clarification_answer(
                        question=
                            question,

                        order_number=
                            order_number,
                    ),

                intent=
                    classification.intent,

                commerce_required=
                    True,

                order_number=
                    order_number,

                safe_draft_ready=
                    False,
            )


        commerce_provider = (
            get_commerce_provider()
        )


        ai_run_id = (
            _create_commerce_ai_run(
                ticket_id=
                    ticket_id,

                message_id=
                    message_id,

                provider_name=
                    commerce_provider
                    .provider_name,
            )
        )


        try:

            commerce_lookup = (
                lookup_customer_order(
                    user=
                        user,

                    customer_id=
                        ticket[
                            "customer_ref"
                        ],

                    order_number=
                        order_number,

                    provider=
                        commerce_provider,

                    ai_run_id=
                        ai_run_id,
                )
            )


        except CommerceOrderNotFoundError:

            decision = (
                decide_support_action(
                    commerce_required=
                        True,

                    order_number=
                        order_number,

                    identity_verified_for_order=
                        True,

                    commerce_succeeded=
                        False,
                )
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


            _finalize_commerce_ai_run(
                user=
                    user,

                ai_run_id=
                    ai_run_id,

                ticket_id=
                    ticket_id,

                message_id=
                    message_id,

                decision=
                    decision,

                confidence=
                    0.0,

                confidence_band=
                    "LOW",

                latency_ms=
                    latency_ms,

                error_code=
                    "COMMERCE_ORDER_UNAVAILABLE",
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
                    decision.decision,

                decision_reasons=
                    list(
                        decision.reasons
                    ),

                evidence_count=
                    0,

                contradiction_detected=
                    False,

                generation_attempted=
                    False,

                answer=
                    _insufficient_answer(
                        question=
                            question,

                        retrieval_provider=
                            "commerce-tool",

                        retrieval_model=
                            commerce_provider
                            .provider_name,
                    ),

                intent=
                    classification.intent,

                commerce_required=
                    True,

                order_number=
                    order_number,

                safe_draft_ready=
                    False,
            )


        except CommerceProviderError:

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


            failed_decision = (
                UnifiedSafetyDecision(
                    decision=
                        "FAILED",

                    ticket_status=
                        "FAILED",

                    safe_draft_ready=
                        False,

                    reasons=(
                        "COMMERCE_PROVIDER_ERROR",
                    ),

                    escalation_reason=
                        "COMMERCE_PROVIDER_ERROR",
                )
            )


            _finalize_commerce_ai_run(
                user=
                    user,

                ai_run_id=
                    ai_run_id,

                ticket_id=
                    ticket_id,

                message_id=
                    message_id,

                decision=
                    failed_decision,

                confidence=
                    0.0,

                confidence_band=
                    "LOW",

                latency_ms=
                    latency_ms,

                error_code=
                    "COMMERCE_PROVIDER_ERROR",
            )


            raise


        decision = (
            decide_support_action(
                intent=
                    classification.intent,

                commerce_required=
                    True,

                order_number=
                    order_number,

                identity_verified_for_order=
                    True,

                commerce_succeeded=
                    True,
            )
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


        _finalize_commerce_ai_run(
            user=
                user,

            ai_run_id=
                ai_run_id,

            ticket_id=
                ticket_id,

            message_id=
                message_id,

            decision=
                decision,

            confidence=
                1.0,

            confidence_band=
                "HIGH",

            latency_ms=
                latency_ms,
        )


        return TicketAIDraftResponse(
            ai_run_id=
                ai_run_id,

            ticket_id=
                ticket_id,

            message_id=
                message_id,

            confidence=
                1.0,

            confidence_band=
                "HIGH",

            decision=
                decision.decision,

            decision_reasons=
                list(
                    decision.reasons
                ),

            evidence_count=
                0,

            contradiction_detected=
                False,

            generation_attempted=
                False,

            answer=
                _commerce_answer(
                    question=
                        question,

                    order=
                        commerce_lookup.order,

                    provider_name=
                        commerce_provider
                        .provider_name,
                ),

            intent=
                "order_status",

            commerce_required=
                True,

            order_number=
                order_number,

            safe_draft_ready=
                decision.safe_draft_ready,

            commerce_order=
                commerce_lookup.order,

            commerce_tool_call_id=
                commerce_lookup
                .tool_call_id,
        )


    # ======================================================
    # Gate 4 — normal knowledge/RAG path.
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
                        assessment.confidence,

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
                        *assessment.reasons,

                        (
                            "GENERATION_DECLARED_"
                            "INSUFFICIENT_EVIDENCE"
                        ),
                    ],
                )
            )


    else:

        answer = (
            _insufficient_answer(
                question=
                    question,

                retrieval_provider=
                    retrieval.provider,

                retrieval_model=
                    retrieval.model,
            )
        )


    decision = (
        decide_support_action(
            intent=
                classification.intent,

            evidence_assessment=
                assessment,

            answer_status=
                answer.status,
        )
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
        _persist_rag_ai_run(
            user=
                user,

            ticket_id=
                ticket_id,

            message_id=
                message_id,

            classification=
                classification,

            generation_provider=
                generation_provider,

            assessment=
                assessment,

            decision=
                decision,

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
            assessment.confidence,

        confidence_band=
            assessment
            .confidence_band,

        decision=
            decision.decision,

        decision_reasons=
            list(
                decision.reasons
            ),

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

        intent=
            classification.intent,

        commerce_required=
            False,

        order_number=
            classification.order_number,

        safe_draft_ready=
            decision.safe_draft_ready,
    )