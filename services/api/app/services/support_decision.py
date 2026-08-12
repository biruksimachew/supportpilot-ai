from dataclasses import dataclass

from app.services.evidence_decision import (
    EvidenceAssessment,
)


# ----------------------------------------------------------
# AUTO_RESPOND POLICY
#
# Only explicitly approved intents may be automatically
# answered.
#
# Anything not present here fails closed to human review.
# ----------------------------------------------------------

AUTO_RESPOND_KNOWLEDGE_INTENTS = frozenset(
    {
        "product",
        "return",
        "shipping",
    }
)


AUTO_RESPOND_COMMERCE_INTENTS = frozenset(
    {
        "order_status",
    }
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
    intent:
        str | None = None,

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

    # ======================================================
    # GATE 1
    # Restricted operations always require human review.
    # ======================================================

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
                    (
                        "RESTRICTED_ACTION:"
                        + category
                    )

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


    # ======================================================
    # GATE 2
    # Once a ticket contains a restricted action it remains
    # under human control until an agent workflow explicitly
    # resolves that state.
    # ======================================================

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


    # ======================================================
    # COMMERCE PATH
    # ======================================================

    if commerce_required:

        # --------------------------------------------------
        # Order-specific commerce requests require an order
        # number.
        # --------------------------------------------------

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


        # --------------------------------------------------
        # Exact-order identity verification is mandatory
        # before order facts may be disclosed.
        # --------------------------------------------------

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


        # --------------------------------------------------
        # Verification succeeded, but commerce lookup did
        # not.
        # --------------------------------------------------

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


        # --------------------------------------------------
        # Verified read-only commerce facts are available.
        # --------------------------------------------------

        if commerce_succeeded is True:

            # Fail closed if the intent is not explicitly
            # approved for automated commerce responses.

            if (
                intent
                not in AUTO_RESPOND_COMMERCE_INTENTS
            ):

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
                        "AUTO_RESPONSE_INTENT_NOT_ALLOWED",
                        "AUTO_RESPONSE_BLOCKED",
                    ),

                    escalation_reason=
                        None,
                )


            return UnifiedSafetyDecision(
                decision=
                    "AUTO_RESPOND",

                # IMPORTANT:
                #
                # The decision authorizes automatic delivery,
                # but this endpoint has not actually sent the
                # customer message yet.
                #
                # AUTO_RESPONDED should only be written after
                # outbound delivery succeeds.
                ticket_status=
                    "DRAFTED",

                safe_draft_ready=
                    True,

                reasons=(
                    "COMMERCE_FACTS_VERIFIED",
                    "SAFE_COMMERCE_DRAFT",
                    "AUTO_RESPONSE_ELIGIBLE",
                    "AUTO_RESPONSE:VERIFIED_ORDER_STATUS",
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


    # ======================================================
    # KNOWLEDGE / RAG PATH
    # ======================================================

    if evidence_assessment is None:

        raise ValueError(
            (
                "Evidence assessment is required "
                "for non-commerce requests."
            )
        )


    # ------------------------------------------------------
    # Weak, missing, contradictory, or generation-rejected
    # evidence must never auto-respond.
    # ------------------------------------------------------

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


    # ------------------------------------------------------
    # The answer may be usable as an agent draft, but
    # ambiguous evidence is not safe enough for automation.
    # ------------------------------------------------------

    if evidence_assessment.ambiguity_detected:

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
                "AUTO_RESPONSE_AMBIGUOUS_EVIDENCE",
                "AUTO_RESPONSE_BLOCKED",
            ),

            escalation_reason=
                None,
        )


    # ------------------------------------------------------
    # AUTO_RESPOND requires HIGH evidence confidence.
    #
    # MEDIUM evidence can still be useful to an agent as a
    # draft, but does not cross the automatic-send boundary.
    # ------------------------------------------------------

    if (
        evidence_assessment
        .confidence_band
        != "HIGH"
    ):

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
                "AUTO_RESPONSE_CONFIDENCE_NOT_HIGH",
                "AUTO_RESPONSE_BLOCKED",
            ),

            escalation_reason=
                None,
        )


    # ------------------------------------------------------
    # Even HIGH evidence is not enough by itself.
    #
    # Only explicitly approved intent classes may cross the
    # automatic-response boundary.
    # ------------------------------------------------------

    if (
        intent
        not in AUTO_RESPOND_KNOWLEDGE_INTENTS
    ):

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
                "AUTO_RESPONSE_INTENT_NOT_ALLOWED",
                "AUTO_RESPONSE_BLOCKED",
            ),

            escalation_reason=
                None,
        )


    # ======================================================
    # CONTROLLED AUTO_RESPOND
    #
    # Conditions already proven:
    #
    # - not restricted
    # - no previous restricted state
    # - non-commerce knowledge path
    # - evidence supports generation
    # - answer status ANSWERED
    # - no ambiguity
    # - HIGH confidence
    # - intent explicitly allowlisted
    # ======================================================

    return UnifiedSafetyDecision(
        decision=
            "AUTO_RESPOND",

        # Authorization has been granted, but no outbound
        # transport has confirmed delivery yet.
        ticket_status=
            "DRAFTED",

        safe_draft_ready=
            True,

        reasons=(
            *evidence_assessment.reasons,

            "SAFE_KNOWLEDGE_DRAFT",
            "AUTO_RESPONSE_ELIGIBLE",

            (
                "AUTO_RESPONSE:KNOWLEDGE_"
                + str(
                    intent
                ).upper()
            ),
        ),

        escalation_reason=
            None,
    )