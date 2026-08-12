import re

from dataclasses import dataclass


ORDER_NUMBER_PATTERN = re.compile(
    r"(?<![A-Z0-9])#?NS[0-9]{5}\b",
    re.IGNORECASE,
)


ORDER_STATUS_PATTERNS = (
    re.compile(
        r"\bwhere\s+is\s+(?:(?:my|the)\s+)?order\b"
    ),

    re.compile(
        r"\btrack(?:ing)?\s+(?:(?:my|the)\s+)?order\b"
    ),

    re.compile(
        r"\border\s+status\b"
    ),

    re.compile(
        r"\bstatus\s+of\s+(?:(?:my|the)\s+)?order\b"
    ),

    re.compile(
        r"\bhas\s+(?:(?:my|the)\s+)?order\s+shipped\b"
    ),

    re.compile(
        r"\bwhen\s+will\s+(?:(?:my|the)\s+)?order\s+"
        r"(?:arrive|be\s+delivered)\b"
    ),

    re.compile(
        r"\border\b.*\b(?:status|tracking|shipped)\b"
    ),
)


@dataclass(frozen=True)
class SupportRequestClassification:
    intent: str

    commerce_required: bool

    order_number: str | None

    reasons: tuple[str, ...]


def normalize_order_number(
    value: str,
) -> str:

    normalized = (
        value
        .strip()
        .upper()
    )


    if not normalized.startswith(
        "#"
    ):
        normalized = (
            "#"
            + normalized
        )


    return normalized


def extract_order_number(
    text: str,
) -> str | None:

    match = (
        ORDER_NUMBER_PATTERN
        .search(
            text
        )
    )


    if match is None:
        return None


    return normalize_order_number(
        match.group(
            0
        )
    )


def _normalize_text(
    text: str,
) -> str:

    return " ".join(
        text
        .casefold()
        .replace(
            "’",
            "'",
        )
        .split()
    )


def classify_support_request(
    text: str,
) -> SupportRequestClassification:

    normalized = (
        _normalize_text(
            text
        )
    )


    order_number = (
        extract_order_number(
            text
        )
    )


    if any(
        pattern.search(
            normalized
        )
        for pattern
        in ORDER_STATUS_PATTERNS
    ):

        return SupportRequestClassification(
            intent=
                "order_status",

            commerce_required=
                True,

            order_number=
                order_number,

            reasons=(
                "ORDER_STATUS_REQUEST",
                "COMMERCE_REQUIRED",
            ),
        )


    if re.search(
        r"\b"
        r"(?:damaged|broken|cracked|defective)"
        r"\b",
        normalized,
    ):

        return SupportRequestClassification(
            intent=
                "damaged_item",

            commerce_required=
                False,

            order_number=
                order_number,

            reasons=(
                "DAMAGED_ITEM_REQUEST",
            ),
        )


    if re.search(
        r"\b"
        r"(?:return|returns|exchange|exchanges)"
        r"\b",
        normalized,
    ):

        return SupportRequestClassification(
            intent=
                "return",

            commerce_required=
                False,

            order_number=
                order_number,

            reasons=(
                "RETURN_REQUEST",
            ),
        )


    if re.search(
        r"\b"
        r"(?:shipping|delivery|deliveries)"
        r"\b",
        normalized,
    ):

        return SupportRequestClassification(
            intent=
                "shipping",

            commerce_required=
                False,

            order_number=
                order_number,

            reasons=(
                "SHIPPING_INFORMATION_REQUEST",
            ),
        )


    if re.search(
        r"\b"
        r"(?:trailpack|summit\s+flask|campglow|"
        r"packing\s+cube|waterproof|water-resistant|"
        r"dishwasher|battery|warranty|wash)"
        r"\b",
        normalized,
    ):

        return SupportRequestClassification(
            intent=
                "product",

            commerce_required=
                False,

            order_number=
                order_number,

            reasons=(
                "PRODUCT_INFORMATION_REQUEST",
            ),
        )


    if re.search(
        r"\b"
        r"(?:account|login|password|sign\s+in)"
        r"\b",
        normalized,
    ):

        return SupportRequestClassification(
            intent=
                "account",

            commerce_required=
                False,

            order_number=
                order_number,

            reasons=(
                "ACCOUNT_REQUEST",
            ),
        )


    if re.search(
        r"\b"
        r"(?:complaint|complain|unacceptable)"
        r"\b",
        normalized,
    ):

        return SupportRequestClassification(
            intent=
                "complaint",

            commerce_required=
                False,

            order_number=
                order_number,

            reasons=(
                "COMPLAINT_REQUEST",
            ),
        )


    return SupportRequestClassification(
        intent=
            "other",

        commerce_required=
            False,

        order_number=
            order_number,

        reasons=(
            "OTHER_REQUEST",
        ),
    )