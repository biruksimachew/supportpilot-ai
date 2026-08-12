from app.services.evidence_decision import (
    EvidenceAssessment,
)

from app.services.support_decision import (
    decide_support_action,
)


def test_unverified_commerce_requests_clarification():

    decision = decide_support_action(
        commerce_required=True,

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


def test_verified_commerce_produces_safe_draft():

    decision = decide_support_action(
        commerce_required=True,

        order_number=
            "#NS10041",

        identity_verified_for_order=
            True,

        commerce_succeeded=
            True,
    )


    assert (
        decision.ticket_status
        == "DRAFTED"
    )

    assert (
        decision.safe_draft_ready
        is True
    )

    # AUTO_RESPOND remains M4E.
    assert (
        decision.decision
        == "REVIEW_REQUIRED"
    )


def test_low_evidence_requires_review():

    assessment = EvidenceAssessment(
        confidence=0.40,

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


    decision = decide_support_action(
        evidence_assessment=
            assessment,

        answer_status=
            "INSUFFICIENT_EVIDENCE",
    )


    assert (
        decision.ticket_status
        == "REVIEW_REQUIRED"
    )

    assert (
        decision.safe_draft_ready
        is False
    )


def test_high_grounded_evidence_produces_safe_draft():

    assessment = EvidenceAssessment(
        confidence=0.90,

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


    decision = decide_support_action(
        evidence_assessment=
            assessment,

        answer_status=
            "ANSWERED",
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
        decision.decision
        == "REVIEW_REQUIRED"
    )


def test_existing_restricted_ticket_remains_review_required():

    decision = decide_support_action(
        existing_restricted_action=True
    )


    assert (
        decision.ticket_status
        == "REVIEW_REQUIRED"
    )

    assert (
        decision.safe_draft_ready
        is False
    )