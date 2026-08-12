import pytest

from app.services.restricted_actions import (
    detect_restricted_action,
)


@pytest.mark.parametrize(
    (
        "message",
        "expected_category",
    ),
    [
        (
            "Refund #NS10042 now.",
            "REFUND",
        ),
        (
            "Please refund my order.",
            "REFUND",
        ),
        (
            "Can you cancel my order?",
            "CANCEL_ORDER",
        ),
        (
            "Cancel #NS10044 please.",
            "CANCEL_ORDER",
        ),
        (
            (
                "Change my shipping "
                "address please."
            ),
            "SHIPPING_ADDRESS_CHANGE",
        ),
        (
            (
                "Remove one Packing Cube "
                "Set from my order."
            ),
            "MODIFY_ORDER",
        ),
        (
            "Retry my payment.",
            "PAYMENT_ACTION",
        ),
        (
            (
                "Make an exception to "
                "the return policy."
            ),
            "POLICY_EXCEPTION",
        ),
        (
            (
                "Send me a replacement "
                "lantern."
            ),
            "REPLACEMENT_AUTHORIZATION",
        ),
    ],
)
def test_restricted_action_requests_are_detected(
    message: str,
    expected_category: str,
):

    result = detect_restricted_action(
        message
    )


    assert result.restricted is True

    assert (
        expected_category
        in result.categories
    )


@pytest.mark.parametrize(
    "message",
    [
        "What is your refund policy?",
        "How long do refunds usually take?",
        "Can you explain the cancellation policy?",
        "What is the replacement policy?",
        "Where is my order?",
        "Is TrailPack waterproof?",
        (
            "What payment methods "
            "do you accept?"
        ),
        (
            "What happens if an item "
            "arrives damaged?"
        ),
    ],
)
def test_informational_questions_are_not_restricted(
    message: str,
):

    result = detect_restricted_action(
        message
    )


    assert result.restricted is False

    assert result.categories == ()

    assert result.matched_rules == ()