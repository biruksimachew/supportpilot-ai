from app.services.evidence_decision import (
    EvidenceAssessment,
)

from app.services.support_decision import (
    decide_support_action,
)


def high_evidence() -> EvidenceAssessment:

    return EvidenceAssessment(
        confidence=
            0.90,

        confidence_band=
            "HIGH",

        generation_allowed=
            True,

        contradiction_detected=
            False,

        ambiguity_detected=
            False,

        reasons=[
            "EVIDENCE_HIGH",
        ],
    )


def medium_evidence() -> EvidenceAssessment:

    return EvidenceAssessment(
        confidence=
            0.65,

        confidence_band=
            "MEDIUM",

        generation_allowed=
            True,

        contradiction_detected=
            False,

        ambiguity_detected=
            False,

        reasons=[
            "EVIDENCE_MEDIUM",
        ],
    )


def ambiguous_evidence() -> EvidenceAssessment:

    return EvidenceAssessment(
        confidence=
            0.70,

        confidence_band=
            "MEDIUM",

        generation_allowed=
            True,

        contradiction_detected=
            False,

        ambiguity_detected=
            True,

        reasons=[
            "EVIDENCE_AMBIGUOUS",
            "EVIDENCE_MEDIUM",
        ],
    )


def low_evidence() -> EvidenceAssessment:

    return EvidenceAssessment(
        confidence=
            0.40,

        confidence_band=
            "LOW",

        generation_allowed=
            False,

        contradiction_detected=
            False,

        ambiguity_detected=
            False,

        reasons=[
            "EVIDENCE_WEAK",
        ],
    )


def test_unverified_commerce_requests_clarification():

    decision = decide_support_action(
        intent=
            "order_status",

        commerce_required=
            True,

        order_number=
            "#NS10041",

        identity_verified_for_order=
            False,
    )


    assert (
        decision.decision
        == "REQUEST_CLARIFICATION"
    )


    assert (
        decision.ticket_status
        == "WAITING_CUSTOMER"
    )


    assert (
        decision.safe_draft_ready
        is False
    )


    assert (
        "IDENTITY_VERIFICATION_REQUIRED"
        in decision.reasons
    )


def test_verified_order_status_is_auto_respond_eligible():

    decision = decide_support_action(
        intent=
            "order_status",

        commerce_required=
            True,

        order_number=
            "#NS10041",

        identity_verified_for_order=
            True,

        commerce_succeeded=
            True,
    )


    assert (
        decision.decision
        == "AUTO_RESPOND"
    )


    # No outbound transport has sent the response yet.
    assert (
        decision.ticket_status
        == "DRAFTED"
    )


    assert (
        decision.safe_draft_ready
        is True
    )


    assert (
        "AUTO_RESPONSE_ELIGIBLE"
        in decision.reasons
    )


    assert (
        "AUTO_RESPONSE:VERIFIED_ORDER_STATUS"
        in decision.reasons
    )


def test_unapproved_commerce_intent_does_not_auto_respond():

    decision = decide_support_action(
        intent=
            "other",

        commerce_required=
            True,

        order_number=
            "#NS10041",

        identity_verified_for_order=
            True,

        commerce_succeeded=
            True,
    )


    assert (
        decision.decision
        == "REVIEW_REQUIRED"
    )


    assert (
        decision.safe_draft_ready
        is True
    )


    assert (
        "AUTO_RESPONSE_INTENT_NOT_ALLOWED"
        in decision.reasons
    )


def test_low_evidence_requires_review():

    decision = decide_support_action(
        intent=
            "product",

        evidence_assessment=
            low_evidence(),

        answer_status=
            "INSUFFICIENT_EVIDENCE",
    )


    assert (
        decision.decision
        == "REVIEW_REQUIRED"
    )


    assert (
        decision.ticket_status
        == "REVIEW_REQUIRED"
    )


    assert (
        decision.safe_draft_ready
        is False
    )


def test_medium_evidence_can_be_draft_but_not_auto_response():

    decision = decide_support_action(
        intent=
            "product",

        evidence_assessment=
            medium_evidence(),

        answer_status=
            "ANSWERED",
    )


    assert (
        decision.decision
        == "REVIEW_REQUIRED"
    )


    assert (
        decision.ticket_status
        == "DRAFTED"
    )


    assert (
        decision.safe_draft_ready
        is True
    )


    assert (
        "AUTO_RESPONSE_CONFIDENCE_NOT_HIGH"
        in decision.reasons
    )


def test_ambiguous_evidence_never_auto_responds():

    decision = decide_support_action(
        intent=
            "product",

        evidence_assessment=
            ambiguous_evidence(),

        answer_status=
            "ANSWERED",
    )


    assert (
        decision.decision
        == "REVIEW_REQUIRED"
    )


    assert (
        decision.safe_draft_ready
        is True
    )


    assert (
        "AUTO_RESPONSE_AMBIGUOUS_EVIDENCE"
        in decision.reasons
    )


def test_high_product_evidence_is_auto_respond_eligible():

    decision = decide_support_action(
        intent=
            "product",

        evidence_assessment=
            high_evidence(),

        answer_status=
            "ANSWERED",
    )


    assert (
        decision.decision
        == "AUTO_RESPOND"
    )


    assert (
        decision.ticket_status
        == "DRAFTED"
    )


    assert (
        decision.safe_draft_ready
        is True
    )


    assert (
        "AUTO_RESPONSE_ELIGIBLE"
        in decision.reasons
    )


    assert (
        "AUTO_RESPONSE:KNOWLEDGE_PRODUCT"
        in decision.reasons
    )


def test_high_return_policy_evidence_is_auto_respond_eligible():

    decision = decide_support_action(
        intent=
            "return",

        evidence_assessment=
            high_evidence(),

        answer_status=
            "ANSWERED",
    )


    assert (
        decision.decision
        == "AUTO_RESPOND"
    )


    assert (
        "AUTO_RESPONSE:KNOWLEDGE_RETURN"
        in decision.reasons
    )


def test_high_shipping_evidence_is_auto_respond_eligible():

    decision = decide_support_action(
        intent=
            "shipping",

        evidence_assessment=
            high_evidence(),

        answer_status=
            "ANSWERED",
    )


    assert (
        decision.decision
        == "AUTO_RESPOND"
    )


    assert (
        "AUTO_RESPONSE:KNOWLEDGE_SHIPPING"
        in decision.reasons
    )


def test_high_evidence_complaint_still_requires_review():

    decision = decide_support_action(
        intent=
            "complaint",

        evidence_assessment=
            high_evidence(),

        answer_status=
            "ANSWERED",
    )


    assert (
        decision.decision
        == "REVIEW_REQUIRED"
    )


    assert (
        decision.safe_draft_ready
        is True
    )


    assert (
        "AUTO_RESPONSE_INTENT_NOT_ALLOWED"
        in decision.reasons
    )


def test_existing_restricted_ticket_remains_review_required():

    decision = decide_support_action(
        intent=
            "product",

        existing_restricted_action=
            True,
    )


    assert (
        decision.decision
        == "REVIEW_REQUIRED"
    )


    assert (
        decision.ticket_status
        == "REVIEW_REQUIRED"
    )


    assert (
        decision.safe_draft_ready
        is False
    )


def test_new_restricted_action_never_auto_responds():

    decision = decide_support_action(
        intent=
            "return",

        restricted_categories=(
            "REFUND",
        ),
    )


    assert (
        decision.decision
        == "REVIEW_REQUIRED"
    )


    assert (
        decision.safe_draft_ready
        is False
    )


    assert (
        "AUTO_RESPONSE_BLOCKED"
        in decision.reasons
    )