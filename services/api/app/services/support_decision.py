from dataclasses import dataclass

from app.services.evidence_decision import (
    EvidenceAssessment,
)


@dataclass(frozen=True)
class UnifiedSafetyDecision:
    decision: str

    ticket_status: str

    safe_draft_ready: bool

    reasons: tuple[str, ...]

    escalation_reason: str | None


def decide_support_action(
    *,
    restricted_categories:
        tuple[str, ...] = (),

    existing_restricted_action:
        bool = False,

    commerce_required:
        bool = False,

    order_number:
        str | None = None,

    identity_verified_for_order:
        bool | None = None,

    commerce_succeeded:
        bool | None = None,

    evidence_assessment:
        EvidenceAssessment | None = None,

    answer_status:
        str | None = None,

) -> UnifiedSafetyDecision:

    # ------------------------------------------------------
    # Restricted operations always fail closed.
    # ------------------------------------------------------

    if restricted_categories:

        return UnifiedSafetyDecision(
            decision=
                "REVIEW_REQUIRED",

            ticket_status=
                "REVIEW_REQUIRED",

            safe_draft_ready=
                False,

            reasons=(
                "RESTRICTED_ACTION_DETECTED",

                *(
                    "RESTRICTED_ACTION:"
                    + category

                    for category
                    in restricted_categories
                ),

                "HUMAN_ACTION_REQUIRED",
                "AUTO_RESPONSE_BLOCKED",
            ),

            escalation_reason=
                (
                    "RESTRICTED_ACTION:"
                    + ",".join(
                        restricted_categories
                    )
                ),
        )


    # A ticket that already contains a restricted operation
    # remains under human review until a later agent workflow
    # explicitly resolves it.

    if existing_restricted_action:

        return UnifiedSafetyDecision(
            decision=
                "REVIEW_REQUIRED",

            ticket_status=
                "REVIEW_REQUIRED",

            safe_draft_ready=
                False,

            reasons=(
                "EXISTING_RESTRICTED_ACTION",
                "HUMAN_ACTION_REQUIRED",
                "AUTO_RESPONSE_BLOCKED",
            ),

            escalation_reason=
                "EXISTING_RESTRICTED_ACTION",
        )


    # ------------------------------------------------------
    # Commerce path.
    # ------------------------------------------------------

    if commerce_required:

        if order_number is None:

            return UnifiedSafetyDecision(
                decision=
                    "REQUEST_CLARIFICATION",

                ticket_status=
                    "WAITING_CUSTOMER",

                safe_draft_ready=
                    False,

                reasons=(
                    "COMMERCE_REQUIRED",
                    "ORDER_NUMBER_REQUIRED",
                    "AUTO_RESPONSE_BLOCKED",
                ),

                escalation_reason=
                    None,
            )


        if identity_verified_for_order is not True:

            return UnifiedSafetyDecision(
                decision=
                    "REQUEST_CLARIFICATION",

                ticket_status=
                    "WAITING_CUSTOMER",

                safe_draft_ready=
                    False,

                reasons=(
                    "COMMERCE_REQUIRED",
                    "IDENTITY_VERIFICATION_REQUIRED",
                    "AUTO_RESPONSE_BLOCKED",
                ),

                escalation_reason=
                    None,
            )


        if commerce_succeeded is False:

            return UnifiedSafetyDecision(
                decision=
                    "REVIEW_REQUIRED",

                ticket_status=
                    "REVIEW_REQUIRED",

                safe_draft_ready=
                    False,

                reasons=(
                    "COMMERCE_LOOKUP_UNAVAILABLE",
                    "HUMAN_REVIEW_REQUIRED",
                    "AUTO_RESPONSE_BLOCKED",
                ),

                escalation_reason=
                    "COMMERCE_LOOKUP_UNAVAILABLE",
            )


        if commerce_succeeded is True:

            return UnifiedSafetyDecision(
                decision=
                    "REVIEW_REQUIRED",

                ticket_status=
                    "DRAFTED",

                safe_draft_ready=
                    True,

                reasons=(
                    "COMMERCE_FACTS_VERIFIED",
                    "SAFE_COMMERCE_DRAFT",
                    "AUTO_SEND_NOT_EVALUATED",
                ),

                escalation_reason=
                    None,
            )


        raise ValueError(
            (
                "commerce_succeeded must be supplied "
                "after verified commerce access."
            )
        )


    # ------------------------------------------------------
    # Knowledge/RAG path.
    # ------------------------------------------------------

    if evidence_assessment is None:

        raise ValueError(
            (
                "Evidence assessment is required "
                "for non-commerce requests."
            )
        )


    if (
        not evidence_assessment
        .generation_allowed

        or answer_status
        != "ANSWERED"
    ):

        return UnifiedSafetyDecision(
            decision=
                "REVIEW_REQUIRED",

            ticket_status=
                "REVIEW_REQUIRED",

            safe_draft_ready=
                False,

            reasons=(
                *evidence_assessment.reasons,

                "EVIDENCE_NOT_SUFFICIENT",
                "AUTO_RESPONSE_BLOCKED",
            ),

            escalation_reason=
                "EVIDENCE_NOT_SUFFICIENT",
        )


    return UnifiedSafetyDecision(
        decision=
            "REVIEW_REQUIRED",

        ticket_status=
            "DRAFTED",

        safe_draft_ready=
            True,

        reasons=(
            *evidence_assessment.reasons,

            "SAFE_KNOWLEDGE_DRAFT",
            "AUTO_SEND_NOT_EVALUATED",
        ),

        escalation_reason=
            None,
    )