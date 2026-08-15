import re
import unicodedata

from dataclasses import dataclass


@dataclass(frozen=True)
class PromptInjectionDetection:
    detected: bool

    matched_rules: tuple[str, ...]


# ----------------------------------------------------------
# SupportPilot treats prompt-injection detection as a
# deterministic security control.
#
# The detector is intentionally conservative and only targets
# attempts to:
#
# - override higher-priority instructions,
# - reveal hidden/system/developer instructions,
# - impersonate privileged instruction roles,
# - claim that user-provided text supersedes policy.
#
# Ordinary questions about AI/system prompts are not blocked.
# ----------------------------------------------------------

RULES: tuple[
    tuple[
        str,
        re.Pattern[str],
    ],
    ...,
] = (
    (
        "override_higher_priority_instructions",
        re.compile(
            r"\b"
            r"(?:ignore|disregard|forget|override|bypass)"
            r"\b.{0,60}\b"
            r"(?:previous|prior|earlier|system|developer|"
            r"hidden|internal|safety|policy|rules?|"
            r"instructions?|prompt)"
            r"\b"
        ),
    ),
    (
        "reveal_internal_instructions",
        re.compile(
            r"\b"
            r"(?:show|reveal|print|display|dump|expose|"
            r"repeat|quote|return|tell)"
            r"\b.{0,60}\b"
            r"(?:system|developer|hidden|internal)"
            r"\b.{0,35}\b"
            r"(?:prompt|message|instructions?|rules?)"
            r"\b"
        ),
    ),
    (
        "reveal_your_prompt",
        re.compile(
            r"\b"
            r"(?:show|reveal|print|display|dump|expose|"
            r"repeat|quote|tell)"
            r"\b.{0,60}\b"
            r"your\s+"
            r"(?:system|developer|hidden|internal)"
            r"\s+"
            r"(?:prompt|message|instructions?|rules?)"
            r"\b"
        ),
    ),
    (
        "privileged_role_impersonation",
        re.compile(
            r"\b"
            r"(?:act|pretend|behave|respond)"
            r"\s+as\s+(?:the\s+)?"
            r"(?:system|developer|administrator|admin|root)"
            r"\b"
        ),
    ),
    (
        "user_text_claims_precedence",
        re.compile(
            r"\b"
            r"(?:following|next|these|this)"
            r"\s+(?:instruction|instructions|message|text)"
            r"\b.{0,60}\b"
            r"(?:override|supersede|replace|outrank|"
            r"take\s+precedence\s+over)"
            r"\b"
        ),
    ),
    (
        "debug_internal_disclosure",
        re.compile(
            r"\b"
            r"(?:debug|debugging|diagnostic|maintenance)"
            r"\b.{0,70}\b"
            r"(?:dump|show|reveal|print|expose)"
            r"\b.{0,45}\b"
            r"(?:system\s+prompt|developer\s+message|"
            r"internal\s+instructions?|hidden\s+instructions?)"
            r"\b"
        ),
    ),
)


def _normalize_text(
    text: str,
) -> str:

    normalized = (
        unicodedata.normalize(
            "NFKC",
            text,
        )
        .casefold()
    )

    normalized = re.sub(
        r"[\W_]+",
        " ",
        normalized,
        flags=re.UNICODE,
    )

    return " ".join(
        normalized.split()
    )


def detect_prompt_injection(
    text: str,
) -> PromptInjectionDetection:

    normalized = (
        _normalize_text(
            text
        )
    )

    matched_rules = tuple(
        rule_name

        for (
            rule_name,
            pattern,
        )
        in RULES

        if pattern.search(
            normalized
        )
    )

    return PromptInjectionDetection(
        detected=
            bool(
                matched_rules
            ),

        matched_rules=
            matched_rules,
    )
