from app.services.request_classification import (
    classify_support_request,
)


def test_order_status_requires_commerce():

    result = classify_support_request(
        "Where is order #NS10041?"
    )

    assert result.intent == "order_status"

    assert result.commerce_required is True

    assert (
        result.order_number
        == "#NS10041"
    )


def test_order_status_without_number_still_requires_commerce():

    result = classify_support_request(
        "Where is my order?"
    )

    assert result.intent == "order_status"

    assert result.commerce_required is True

    assert result.order_number is None


def test_shipping_policy_does_not_require_commerce():

    result = classify_support_request(
        (
            "How long does standard "
            "shipping take?"
        )
    )

    assert result.intent == "shipping"

    assert result.commerce_required is False


def test_return_policy_does_not_require_commerce():

    result = classify_support_request(
        (
            "Can I return an unused "
            "item after 18 days?"
        )
    )

    assert result.intent == "return"

    assert result.commerce_required is False


def test_product_question_does_not_require_commerce():

    result = classify_support_request(
        "Is TrailPack waterproof?"
    )

    assert result.intent == "product"

    assert result.commerce_required is False