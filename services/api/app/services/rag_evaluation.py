from dataclasses import dataclass
from datetime import (
    datetime,
    timezone,
)
from uuid import (
    NAMESPACE_URL,
    uuid5,
)

from app.schemas.grounded_generation import (
    GroundedModelOutput,
)

from app.schemas.knowledge_retrieval import (
    KnowledgeRetrievalResponse,
    KnowledgeRetrievalResult,
)

from app.services.evidence_decision import (
    assess_evidence,
)

from app.services.generation import (
    GenerationResult,
)

from app.services.grounded_answer import (
    GroundedGenerationConsistencyError,
    generate_grounded_answer,
)


def _stable_uuid(
    value: str,
):
    return uuid5(
        NAMESPACE_URL,
        (
            "supportpilot-rag-eval:"
            + value
        ),
    )


def build_synthetic_retrieval(
    case: dict,
) -> KnowledgeRetrievalResponse:

    results = []


    for index, item in enumerate(
        case.get(
            "results",
            [],
        ),
        start=1,
    ):
        source_key = item.get(
            "source_key",
            f"source-{index}",
        )


        chunk_metadata = {}

        if "claim_key" in item:
            chunk_metadata[
                "claim_key"
            ] = item[
                "claim_key"
            ]

        if "claim_value" in item:
            chunk_metadata[
                "claim_value"
            ] = item[
                "claim_value"
            ]


        results.append(
            KnowledgeRetrievalResult(
                chunk_id=
                    _stable_uuid(
                        (
                            case["id"]
                            + ":chunk:"
                            + str(index)
                        )
                    ),

                source_id=
                    _stable_uuid(
                        (
                            "source:"
                            + source_key
                        )
                    ),

                title=
                    (
                        "Synthetic "
                        + source_key
                    ),

                type=
                    "POLICY",

                version=
                    "1.0",

                section=
                    "Synthetic Evidence",

                content=
                    item.get(
                        "content",
                        (
                            "Synthetic approved "
                            "evaluation evidence."
                        ),
                    ),

                similarity=
                    float(
                        item["similarity"]
                    ),

                effective_at=
                    datetime(
                        2026,
                        8,
                        1,
                        tzinfo=timezone.utc,
                    ),

                source_metadata={},

                chunk_metadata=
                    chunk_metadata,
            )
        )


    results.sort(
        key=lambda result:
            result.similarity,
        reverse=True,
    )


    return KnowledgeRetrievalResponse(
        question=
            (
                "Synthetic evaluation "
                + case["id"]
            ),

        provider=
            "evaluation",

        model=
            "deterministic-v1",

        dimensions=
            1536,

        top_k=
            5,

        min_similarity=
            0.0,

        results=
            results,
    )


def evaluate_decision_case(
    case: dict,
) -> dict:

    retrieval = (
        build_synthetic_retrieval(
            case
        )
    )

    assessment = (
        assess_evidence(
            retrieval
        )
    )


    checks = {
        "confidence_band":
            (
                assessment
                .confidence_band
                ==
                case[
                    "expected_band"
                ]
            ),

        "generation_allowed":
            (
                assessment
                .generation_allowed
                ==
                case[
                    "expected_generation_allowed"
                ]
            ),

        "contradiction":
            (
                assessment
                .contradiction_detected
                ==
                case[
                    "expected_contradiction"
                ]
            ),

        "reason":
            (
                case[
                    "expected_reason"
                ]
                in assessment.reasons
            ),
    }


    return {
        "id":
            case["id"],

        "name":
            case.get(
                "name"
            ),

        "baseline_id":
            case.get(
                "baseline_id"
            ),

        "passed":
            all(
                checks.values()
            ),

        "checks":
            checks,

        "actual": {
            "confidence":
                assessment
                .confidence,

            "confidence_band":
                assessment
                .confidence_band,

            "generation_allowed":
                assessment
                .generation_allowed,

            "contradiction_detected":
                assessment
                .contradiction_detected,

            "ambiguity_detected":
                assessment
                .ambiguity_detected,

            "reasons":
                assessment.reasons,
        },
    }


@dataclass
class StaticEvaluationGenerationProvider:
    output: GroundedModelOutput

    provider_name: str = (
        "evaluation"
    )

    model: str = (
        "grounding-contract-v1"
    )

    calls: int = 0


    def generate_grounded(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
    ) -> GenerationResult:

        self.calls += 1

        return GenerationResult(
            output=
                self.output,

            input_tokens=10,
            output_tokens=5,
            generation_ms=1.0,
        )


def _grounding_output_for_mode(
    mode: str,
) -> GroundedModelOutput:

    if mode == "valid_answer":
        return GroundedModelOutput(
            status=
                "ANSWERED",

            answer=
                (
                    "The approved policy "
                    "supports this answer."
                ),

            citation_refs=[
                "K1",
            ],
        )


    if (
        mode
        == "answered_without_citation"
    ):
        return GroundedModelOutput(
            status=
                "ANSWERED",

            answer=
                (
                    "This answer intentionally "
                    "has no citation."
                ),

            citation_refs=[],
        )


    if mode == "unknown_citation":
        return GroundedModelOutput(
            status=
                "ANSWERED",

            answer=
                (
                    "This answer intentionally "
                    "uses an unknown citation."
                ),

            citation_refs=[
                "K999",
            ],
        )


    if (
        mode
        ==
        "valid_insufficient_evidence"
    ):
        return GroundedModelOutput(
            status=
                "INSUFFICIENT_EVIDENCE",

            answer=
                (
                    "There is not enough "
                    "approved evidence."
                ),

            citation_refs=[],
        )


    raise ValueError(
        (
            "Unsupported grounding "
            f"evaluation mode: {mode}"
        )
    )


def evaluate_grounding_case(
    case: dict,
) -> dict:

    retrieval = (
        KnowledgeRetrievalResponse(
            question=
                (
                    "Grounding evaluation "
                    + case["id"]
                ),

            provider=
                "evaluation",

            model=
                "retrieval-contract-v1",

            dimensions=
                1536,

            top_k=
                1,

            min_similarity=
                0.0,

            results=[
                KnowledgeRetrievalResult(
                    chunk_id=
                        _stable_uuid(
                            case["id"]
                            + ":chunk"
                        ),

                    source_id=
                        _stable_uuid(
                            case["id"]
                            + ":source"
                        ),

                    title=
                        "Evaluation Policy",

                    type=
                        "POLICY",

                    version=
                        "1.0",

                    section=
                        "Evaluation",

                    content=
                        (
                            "This is approved "
                            "evaluation evidence."
                        ),

                    similarity=
                        0.90,

                    effective_at=
                        datetime(
                            2026,
                            8,
                            1,
                            tzinfo=
                                timezone.utc,
                        ),

                    source_metadata={},
                    chunk_metadata={},
                )
            ],
        )
    )


    provider = (
        StaticEvaluationGenerationProvider(
            output=
                _grounding_output_for_mode(
                    case["mode"]
                )
        )
    )


    observed_outcome = (
        "ACCEPTED"
    )

    error = None


    try:
        generate_grounded_answer(
            question=
                retrieval.question,

            retrieval=
                retrieval,

            provider=
                provider,
        )

    except (
        GroundedGenerationConsistencyError
    ) as exc:

        observed_outcome = (
            "REJECTED"
        )

        error = str(
            exc
        )


    return {
        "id":
            case["id"],

        "mode":
            case["mode"],

        "expected_outcome":
            case[
                "expected_outcome"
            ],

        "observed_outcome":
            observed_outcome,

        "provider_calls":
            provider.calls,

        "error":
            error,

        "passed":
            (
                observed_outcome
                ==
                case[
                    "expected_outcome"
                ]
            ),
    }