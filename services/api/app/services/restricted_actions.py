import re

from dataclasses import dataclass

from app.services.prompt_injection import (
    detect_prompt_injection,
)


@dataclass(frozen=True)
class RestrictedActionDetection:
    restricted: bool

    categories: tuple[str, ...]

    matched_rules: tuple[str, ...]


# ----------------------------------------------------------
# IMPORTANT:
#
# Most rules below target OPERATIONAL ACTION REQUESTS rather
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
# M6 also feeds deterministic prompt-injection detection into
# the same pre-provider fail-closed channel. That gives the
# existing support decision path one security category:
#
#   PROMPT_INJECTION
#
# It is handled specially by support_decision.py so it cannot
# become an automatic response and cannot proceed to RAG or
# generation.
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
            r"(?:return|send|give|pay|credit)"
            r"\s+(?:me\s+)?"
            r"(?:my\s+)?money\s+back\b"
        ),
    ),

    (
        "REFUND",
        "reimburse_customer",

        re.compile(
            r"\b"
            r"(?:reimburse|repay)"
            r"\s+(?:me|us|my\s+card|my\s+account)\b"
        ),
    ),

    (
        "REFUND",
        "credit_customer_back",

        re.compile(
            r"\bcredit\s+"
            r"(?:me|my\s+(?:card|account))"
            r"\s+back\b"
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

    (
        "CANCEL_ORDER",
        "stop_order",

        re.compile(
            r"\b(?:stop|halt)\s+"
            r"(?:(?:my|this|the)\s+)?"
            r"order(?:\s+#?ns[0-9]{5})?\b"
        ),
    ),

    (
        "CANCEL_ORDER",
        "stop_order_number",

        re.compile(
            r"\b(?:stop|halt)\s+"
            r"(?:order\s+)?#ns[0-9]{5}\b"
        ),
    ),

    (
        "CANCEL_ORDER",
        "do_not_ship_order",

        re.compile(
            r"\b(?:do\s+not|don't)\s+"
            r"(?:ship|send|dispatch)\s+"
            r"(?:(?:my|this|the)\s+)?order\b"
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
        "put_item_on_order",

        re.compile(
            r"\b"
            r"(?:put|place)"
            r"\s+.+?"
            r"\s+(?:on|into)"
            r"\s+(?:my|this|the)"
            r"\s+order\b"
        ),
    ),

    (
        "MODIFY_ORDER",
        "take_item_off_order",

        re.compile(
            r"\b"
            r"(?:take|remove)"
            r"\s+.+?"
            r"\s+(?:off|from)"
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

    (
        "SHIPPING_ADDRESS_CHANGE",
        "change_order_address",

        re.compile(
            r"\b"
            r"(?:change|switch|swap|update|edit)"
            r"\s+(?:the\s+)?address"
            r"\s+(?:for|on|used\s+for)"
            r"\s+(?:my|this|the)"
            r"\s+order\b"
        ),
    ),

    (
        "SHIPPING_ADDRESS_CHANGE",
        "send_order_to_new_address",

        re.compile(
            r"\b"
            r"(?:ship|send|deliver)"
            r"\s+(?:it|the\s+order|my\s+order)"
            r"\s+to\s+"
            r"(?:a\s+)?"
            r"(?:different|new|another)?"
            r"\s*address\b"
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
        "run_payment_again",

        re.compile(
            r"\b"
            r"(?:run|try|charge|take)"
            r"\s+(?:(?:my|the)\s+)?"
            r"(?:card|payment)"
            r"\s+again\b"
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
        "bypass_policy",

        re.compile(
            r"\b"
            r"(?:bypass|ignore|bend|break)"
            r"\s+(?:the\s+)?"
            r"(?:policy|rules?|return\s+window|"
            r"[0-9]+\s*day\s+rule)\b"
        ),
    ),

    (
        "POLICY_EXCEPTION",
        "allow_late_return",

        re.compile(
            r"\b"
            r"(?:let|allow)\s+me\s+"
            r"(?:to\s+)?return\b"
            r".{0,35}\b"
            r"(?:late|after|outside)\b"
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

    (
        "REPLACEMENT_AUTHORIZATION",
        "send_another_item",

        re.compile(
            r"\b"
            r"(?:send|ship)"
            r"\s+(?:me\s+)?"
            r"(?:another|a\s+new|one\s+more)"
            r"\s+(?:one|item|product|unit)\b"
        ),
    ),

    (
        "REPLACEMENT_AUTHORIZATION",
        "replace_for_free",

        re.compile(
            r"\breplace\s+"
            r"(?:this|it|the\s+item)"
            r"\s+(?:for\s+free|free\s+of\s+charge|"
            r"at\s+no\s+charge)\b"
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
            "â€™",
            "'",
        )
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


    injection = (
        detect_prompt_injection(
            text
        )
    )

    if injection.detected:

        categories.append(
            "PROMPT_INJECTION"
        )

        matched_rules.extend(
            (
                "prompt_injection:"
                + rule_name
            )

            for rule_name
            in injection.matched_rules
        )


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
