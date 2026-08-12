import json

from dataclasses import dataclass

from app.core.config import settings

from app.schemas.knowledge_retrieval import (
    KnowledgeRetrievalResponse,
)


@dataclass(frozen=True)
class EvidenceAssessment:
    confidence: float
    confidence_band: str

    generation_allowed: bool

    contradiction_detected: bool
    ambiguity_detected: bool

    reasons: list[str]


def _clamp_confidence(
    value: float,
) -> float:
    return max(
        0.0,
        min(
            1.0,
            float(value),
        ),
    )


def _canonical_claim_value(
    value,
) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        ensure_ascii=False,
        default=str,
        separators=(
            ",",
            ":",
        ),
    )


def _detect_claim_conflicts(
    retrieval: KnowledgeRetrievalResponse,
) -> list[str]:

    claims: dict[
        str,
        set[str],
    ] = {}


    for result in retrieval.results:

        if (
            result.similarity
            <
            settings
            .evidence_conflict_min_similarity
        ):
            continue


        metadata = {
            **result.source_metadata,
            **result.chunk_metadata,
        }


        claim_key = (
            metadata.get(
                "claim_key"
            )
        )

        claim_value = (
            metadata.get(
                "claim_value"
            )
        )


        if (
            not claim_key
            or claim_value is None
        ):
            continue


        key = str(
            claim_key
        ).strip()


        if not key:
            continue


        claims.setdefault(
            key,
            set(),
        ).add(
            _canonical_claim_value(
                claim_value
            )
        )


    return [
        key
        for key, values
        in claims.items()
        if len(values) > 1
    ]


def assess_evidence(
    retrieval: KnowledgeRetrievalResponse,
) -> EvidenceAssessment:

    if not retrieval.results:
        return EvidenceAssessment(
            confidence=0.0,
            confidence_band="LOW",

            generation_allowed=False,

            contradiction_detected=False,
            ambiguity_detected=False,

            reasons=[
                "EVIDENCE_MISSING",
            ],
        )


    top = retrieval.results[0]

    confidence = (
        _clamp_confidence(
            top.similarity
        )
    )


    conflicting_claims = (
        _detect_claim_conflicts(
            retrieval
        )
    )


    if conflicting_claims:
        confidence = min(
            confidence,
            (
                settings
                .evidence_medium_similarity
                - 0.0001
            ),
        )

        return EvidenceAssessment(
            confidence=confidence,
            confidence_band="LOW",

            generation_allowed=False,

            contradiction_detected=True,
            ambiguity_detected=False,

            reasons=[
                "EVIDENCE_CONTRADICTORY",
                *[
                    (
                        "CONFLICTING_CLAIM:"
                        + key
                    )
                    for key
                    in sorted(
                        conflicting_claims
                    )
                ],
            ],
        )


    ambiguity_detected = False


    if len(
        retrieval.results
    ) >= 2:

        second = (
            retrieval.results[1]
        )

        score_gap = (
            top.similarity
            - second.similarity
        )


        if (
            top.source_id
            != second.source_id

            and second.similarity
            >=
            settings
            .evidence_medium_similarity

            and score_gap
            <
            settings
            .evidence_ambiguity_margin
        ):
            ambiguity_detected = True


    if (
        confidence
        <
        settings
        .evidence_medium_similarity
    ):
        return EvidenceAssessment(
            confidence=confidence,
            confidence_band="LOW",

            generation_allowed=False,

            contradiction_detected=False,

            ambiguity_detected=
                ambiguity_detected,

            reasons=[
                "EVIDENCE_WEAK",
            ],
        )


    if (
        confidence
        >=
        settings
        .evidence_high_similarity
    ):

        if ambiguity_detected:
            adjusted = min(
                confidence,

                (
                    settings
                    .evidence_high_similarity
                    - 0.0001
                ),
            )

            return EvidenceAssessment(
                confidence=adjusted,
                confidence_band="MEDIUM",

                generation_allowed=True,

                contradiction_detected=False,
                ambiguity_detected=True,

                reasons=[
                    "EVIDENCE_AMBIGUOUS",
                    "EVIDENCE_MEDIUM",
                ],
            )


        return EvidenceAssessment(
            confidence=confidence,
            confidence_band="HIGH",

            generation_allowed=True,

            contradiction_detected=False,
            ambiguity_detected=False,

            reasons=[
                "EVIDENCE_HIGH",
            ],
        )


    return EvidenceAssessment(
        confidence=confidence,
        confidence_band="MEDIUM",

        generation_allowed=True,

        contradiction_detected=False,

        ambiguity_detected=
            ambiguity_detected,

        reasons=(
            [
                "EVIDENCE_MEDIUM",
            ]
            + (
                [
                    "EVIDENCE_AMBIGUOUS",
                ]
                if ambiguity_detected
                else []
            )
        ),
    )