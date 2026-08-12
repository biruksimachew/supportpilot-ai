import re

from dataclasses import dataclass


@dataclass(frozen=True)
class RestrictedActionDetection:
    restricted: bool

    categories: tuple[str, ...]

    matched_rules: tuple[str, ...]


# ----------------------------------------------------------
# IMPORTANT:
#
# These rules intentionally target ACTION REQUESTS rather
# than mere mentions of refunds/cancellations/etc.
#
# Examples:
#
#   "Refund my order."              -> restricted
#   "What is your refund policy?"   -> not restricted
#
#   "Cancel #NS10044."              -> restricted
#   "What is your cancellation
#    policy?"                        -> not restricted
#
# This keeps informational support questions eligible for
# normal grounded RAG while blocking operational requests.
# ----------------------------------------------------------


RULES: tuple[
    tuple[
        str,
        str,
        re.Pattern[str],
    ],
    ...,
] = (

    # ======================================================
    # REFUNDS
    # ======================================================

    (
        "REFUND",
        "refund_order",

        re.compile(
            r"\brefund\s+"
            r"(?:my|this|the|order)\b"
        ),
    ),

    (
        "REFUND",
        "refund_order_number",

        re.compile(
            r"(?:^|\s)"
            r"refund\s+#ns[0-9]{5}\b"
        ),
    ),

    (
        "REFUND",
        "issue_refund",

        re.compile(
            r"\b"
            r"(?:issue|process|send|give)"
            r"\s+(?:me\s+)?"
            r"(?:a\s+)?refund\b"
        ),
    ),

    (
        "REFUND",
        "want_refund",

        re.compile(
            r"\bi\s+"
            r"(?:want|need)"
            r"\s+(?:a\s+)?refund\b"
        ),
    ),

    (
        "REFUND",
        "return_money",

        re.compile(
            r"\b"
            r"(?:return|send|give)"
            r"\s+(?:me\s+)?"
            r"(?:my\s+)?money\s+back\b"
        ),
    ),


    # ======================================================
    # ORDER CANCELLATION
    # ======================================================

    (
        "CANCEL_ORDER",
        "cancel_order",

        re.compile(
            r"\bcancel\s+"
            r"(?:my|this|the|order)\b"
        ),
    ),

    (
        "CANCEL_ORDER",
        "cancel_order_number",

        re.compile(
            r"(?:^|\s)"
            r"cancel\s+#ns[0-9]{5}\b"
        ),
    ),


    # ======================================================
    # ORDER MODIFICATION
    # ======================================================

    (
        "MODIFY_ORDER",
        "modify_order",

        re.compile(
            r"\b"
            r"(?:change|modify|update)"
            r"\s+(?:my|this|the)"
            r"\s+order\b"
        ),
    ),

    (
        "MODIFY_ORDER",
        "add_remove_order_item",

        re.compile(
            r"\b"
            r"(?:add|remove)"
            r"\s+.+?"
            r"\s+(?:to|from)"
            r"\s+(?:my|this|the)"
            r"\s+order\b"
        ),
    ),

    (
        "MODIFY_ORDER",
        "change_order_quantity",

        re.compile(
            r"\b"
            r"(?:change|update)"
            r"\s+(?:the\s+)?quantity"
            r"\s+(?:on|in|for)"
            r"\s+(?:my|this|the)"
            r"\s+order\b"
        ),
    ),


    # ======================================================
    # SHIPPING ADDRESS CHANGE
    # ======================================================

    (
        "SHIPPING_ADDRESS_CHANGE",
        "change_shipping_address",

        re.compile(
            r"\b"
            r"(?:change|update|edit)"
            r"\s+(?:(?:my|the)\s+)?"
            r"(?:shipping|delivery)"
            r"\s+address\b"
        ),
    ),


    # ======================================================
    # PAYMENT ACTIONS / DISPUTES
    # ======================================================

    (
        "PAYMENT_ACTION",
        "process_payment",

        re.compile(
            r"\b"
            r"(?:charge|retry|rerun|process)"
            r"\s+(?:(?:my|the)\s+)?"
            r"(?:card|payment)\b"
        ),
    ),

    (
        "PAYMENT_ACTION",
        "change_payment_method",

        re.compile(
            r"\b"
            r"(?:change|update|replace)"
            r"\s+(?:(?:my|the)\s+)?"
            r"payment\s+method\b"
        ),
    ),

    
    (
        "PAYMENT_ACTION",
        "reverse_payment",

        re.compile(
            r"\b"
            r"(?:reverse|void)"
            r"\s+(?:(?:my|the)\s+)?"
            r"(?:charge|payment)\b"
        ),
    ),
    (
        "PAYMENT_ACTION",
        "dispute_charge",

        re.compile(
            r"\b"
            r"(?:dispute)"
            r"\s+(?:this|the|my)"
            r"\s+(?:charge|payment)\b"
        ),
    ),

    (
        "PAYMENT_ACTION",
        "chargeback",

        re.compile(
            r"\b"
            r"(?:file|start|open)"
            r"\s+(?:a\s+)?chargeback\b"
        ),
    ),


    # ======================================================
    # POLICY EXCEPTIONS
    # ======================================================

    (
        "POLICY_EXCEPTION",
        "make_exception",

        re.compile(
            r"\b"
            r"(?:make|grant|allow)"
            r"\s+(?:me\s+)?"
            r"(?:an?\s+)?exception\b"
        ),
    ),

    (
        "POLICY_EXCEPTION",
        "override_policy",

        re.compile(
            r"\boverride\s+"
            r"(?:the\s+)?"
            r"(?:policy|rule|return\s+window)\b"
        ),
    ),

    (
        "POLICY_EXCEPTION",
        "waive_fee",

        re.compile(
            r"\bwaive\s+"
            r"(?:the\s+)?"
            r"(?:fee|charge|restocking\s+fee)\b"
        ),
    ),


    # ======================================================
    # REPLACEMENT AUTHORIZATION
    # ======================================================

    (
        "REPLACEMENT_AUTHORIZATION",
        "send_replacement",

        re.compile(
            r"\b"
            r"(?:send|ship|issue|authorize)"
            r"\s+(?:me\s+)?"
            r"(?:a\s+)?replacement\b"
        ),
    ),

    (
        "REPLACEMENT_AUTHORIZATION",
        "replace_item",

        re.compile(
            r"\breplace\s+"
            r"(?:my|this|the)"
            r"\s+(?:item|product|order)\b"
        ),
    ),

    (
        "REPLACEMENT_AUTHORIZATION",
        "want_replacement",

        re.compile(
            r"\bi\s+"
            r"(?:want|need)"
            r"\s+(?:a\s+)?replacement\b"
        ),
    ),
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


def detect_restricted_action(
    text: str,
) -> RestrictedActionDetection:

    normalized = (
        _normalize_text(
            text
        )
    )


    categories: list[str] = []

    matched_rules: list[str] = []


    for (
        category,
        rule_name,
        pattern,
    ) in RULES:

        if not pattern.search(
            normalized
        ):
            continue


        if category not in categories:

            categories.append(
                category
            )


        matched_rules.append(
            rule_name
        )


    return RestrictedActionDetection(
        restricted=
            bool(
                categories
            ),

        categories=
            tuple(
                categories
            ),

        matched_rules=
            tuple(
                matched_rules
            ),
    )