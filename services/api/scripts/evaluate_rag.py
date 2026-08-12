import json
import sys

from datetime import (
    datetime,
    timezone,
)

from pathlib import Path

from app.services.embeddings import (
    get_embedding_provider,
)

from app.services.knowledge_retrieval import (
    retrieve_knowledge,
)

from app.services.rag_evaluation import (
    evaluate_decision_case,
    evaluate_grounding_case,
)


FIXTURE_PATH = (
    Path("/app/tests/fixtures/")
    / "rag_evaluation.json"
)


JSON_OUTPUT = Path(
    "/evidence/"
    "milestone-3-rag-evaluation.json"
)


TEXT_OUTPUT = Path(
    "/evidence/"
    "milestone-3-rag-evaluation.txt"
)


TOP_1_TARGET = 0.90
TOP_3_TARGET = 0.95

DECISION_TARGET = 1.00
GROUNDING_TARGET = 1.00


def _ratio(
    numerator: int,
    denominator: int,
) -> float:

    if denominator == 0:
        return 0.0

    return (
        numerator
        / denominator
    )


def _percent(
    value: float,
) -> str:

    return (
        f"{value * 100:.1f}%"
    )


def evaluate_retrieval_cases(
    *,
    fixture: dict,
    provider,
) -> list[dict]:

    results = []


    for case in fixture[
        "retrieval_cases"
    ]:

        retrieval = (
            retrieve_knowledge(
                question=
                    case["question"],

                provider=
                    provider,

                top_k=
                    3,

                min_similarity=
                    0.0,
            )
        )


        returned_sources = [
            item.title
            for item
            in retrieval.results
        ]


        expected_source = (
            case[
                "expected_source"
            ]
        )


        top_1_match = (
            bool(
                returned_sources
            )

            and returned_sources[0]
            == expected_source
        )


        top_3_match = (
            expected_source
            in returned_sources[:3]
        )


        top_similarity = (
            retrieval
            .results[0]
            .similarity

            if retrieval.results
            else None
        )


        expected_similarity = None


        for item in retrieval.results:

            if (
                item.title
                == expected_source
            ):
                expected_similarity = (
                    item.similarity
                )
                break


        results.append(
            {
                "id":
                    case["id"],

                "baseline_id":
                    case.get(
                        "baseline_id"
                    ),

                "question":
                    case[
                        "question"
                    ],

                "expected_source":
                    expected_source,

                "returned_sources":
                    returned_sources,

                "top_1_match":
                    top_1_match,

                "top_3_match":
                    top_3_match,

                "top_similarity":
                    top_similarity,

                "expected_source_similarity":
                    expected_similarity,
            }
        )


        status = (
            "PASS"
            if top_3_match
            else "FAIL"
        )


        print(
            (
                f"{status} "
                f"{case['id']} "
                f"expected="
                f"{expected_source} "
                f"top1="
                f"{returned_sources[0] if returned_sources else 'NONE'}"
            )
        )


    return results


def build_report(
    *,
    fixture: dict,
    provider,
) -> dict:

    retrieval_results = (
        evaluate_retrieval_cases(
            fixture=fixture,
            provider=provider,
        )
    )


    decision_results = [
        evaluate_decision_case(
            case
        )

        for case
        in fixture[
            "decision_cases"
        ]
    ]


    grounding_results = [
        evaluate_grounding_case(
            case
        )

        for case
        in fixture[
            "grounding_cases"
        ]
    ]


    retrieval_count = len(
        retrieval_results
    )


    top_1_passes = sum(
        1
        for result
        in retrieval_results
        if result[
            "top_1_match"
        ]
    )


    top_3_passes = sum(
        1
        for result
        in retrieval_results
        if result[
            "top_3_match"
        ]
    )


    decision_passes = sum(
        1
        for result
        in decision_results
        if result[
            "passed"
        ]
    )


    grounding_passes = sum(
        1
        for result
        in grounding_results
        if result[
            "passed"
        ]
    )


    top_1_accuracy = (
        _ratio(
            top_1_passes,
            retrieval_count,
        )
    )


    top_3_accuracy = (
        _ratio(
            top_3_passes,
            retrieval_count,
        )
    )


    decision_accuracy = (
        _ratio(
            decision_passes,
            len(
                decision_results
            ),
        )
    )


    grounding_accuracy = (
        _ratio(
            grounding_passes,
            len(
                grounding_results
            ),
        )
    )


    gates = {
        "retrieval_top_1":
            (
                top_1_accuracy
                >= TOP_1_TARGET
            ),

        "retrieval_top_3":
            (
                top_3_accuracy
                >= TOP_3_TARGET
            ),

        "evidence_decision":
            (
                decision_accuracy
                >= DECISION_TARGET
            ),

        "grounding_contract":
            (
                grounding_accuracy
                >= GROUNDING_TARGET
            ),
    }


    overall_pass = all(
        gates.values()
    )


    return {
        "generated_at":
            datetime.now(
                timezone.utc
            ).isoformat(),

        "milestone":
            "M3F",

        "suite":
            (
                "SupportPilot Deterministic "
                "RAG Evaluation"
            ),

        "retrieval_provider":
            provider.provider_name,

        "retrieval_model":
            provider.model,

        "retrieval_dimensions":
            provider.dimensions,

        "thresholds": {
            "retrieval_top_1":
                TOP_1_TARGET,

            "retrieval_top_3":
                TOP_3_TARGET,

            "evidence_decision":
                DECISION_TARGET,

            "grounding_contract":
                GROUNDING_TARGET,
        },

        "metrics": {
            "retrieval_cases":
                retrieval_count,

            "retrieval_top_1_passes":
                top_1_passes,

            "retrieval_top_1_accuracy":
                top_1_accuracy,

            "retrieval_top_3_passes":
                top_3_passes,

            "retrieval_top_3_accuracy":
                top_3_accuracy,

            "decision_cases":
                len(
                    decision_results
                ),

            "decision_passes":
                decision_passes,

            "decision_accuracy":
                decision_accuracy,

            "grounding_cases":
                len(
                    grounding_results
                ),

            "grounding_passes":
                grounding_passes,

            "grounding_accuracy":
                grounding_accuracy,

            "total_cases":
                (
                    retrieval_count
                    + len(
                        decision_results
                    )
                    + len(
                        grounding_results
                    )
                ),
        },

        "gates":
            gates,

        "overall_pass":
            overall_pass,

        "baseline_coverage": {
            "covered_in_m3": [
                "B-02",
                "B-05",
                "B-06",
                "B-08",
            ],

            "deferred_to_m4": [
                "B-01",
                "B-03",
                "B-07",
            ],

            "deferred_to_m6_adversarial":
                [
                    "B-04",
                ],
        },

        "retrieval_results":
            retrieval_results,

        "decision_results":
            decision_results,

        "grounding_results":
            grounding_results,
    }


def render_text(
    report: dict,
) -> str:

    metrics = report[
        "metrics"
    ]


    lines = [
        (
            "SupportPilot AI — "
            "Milestone 3 RAG Evaluation"
        ),
        (
            "=" * 52
        ),
        "",
        (
            "Generated: "
            + report[
                "generated_at"
            ]
        ),
        (
            "Provider: "
            + report[
                "retrieval_provider"
            ]
        ),
        (
            "Model: "
            + report[
                "retrieval_model"
            ]
        ),
        (
            "Dimensions: "
            + str(
                report[
                    "retrieval_dimensions"
                ]
            )
        ),
        "",
        "METRICS",
        (
            "-" * 52
        ),
        (
            "Retrieval cases: "
            + str(
                metrics[
                    "retrieval_cases"
                ]
            )
        ),
        (
            "Top-1 retrieval accuracy: "
            + _percent(
                metrics[
                    "retrieval_top_1_accuracy"
                ]
            )
        ),
        (
            "Top-3 retrieval accuracy: "
            + _percent(
                metrics[
                    "retrieval_top_3_accuracy"
                ]
            )
        ),
        (
            "Evidence-decision accuracy: "
            + _percent(
                metrics[
                    "decision_accuracy"
                ]
            )
        ),
        (
            "Grounding-contract accuracy: "
            + _percent(
                metrics[
                    "grounding_accuracy"
                ]
            )
        ),
        (
            "Total evaluation cases: "
            + str(
                metrics[
                    "total_cases"
                ]
            )
        ),
        "",
        "GATES",
        (
            "-" * 52
        ),
    ]


    for gate, passed in report[
        "gates"
    ].items():

        lines.append(
            (
                gate
                + ": "
                + (
                    "PASS"
                    if passed
                    else "FAIL"
                )
            )
        )


    lines.extend(
        [
            "",
            (
                "OVERALL: "
                + (
                    "PASS"
                    if report[
                        "overall_pass"
                    ]
                    else "FAIL"
                )
            ),
            "",
            "RETRIEVAL CASES",
            (
                "-" * 52
            ),
        ]
    )


    for result in report[
        "retrieval_results"
    ]:

        lines.append(
            (
                result["id"]
                + " | top1="
                + (
                    "PASS"
                    if result[
                        "top_1_match"
                    ]
                    else "FAIL"
                )
                + " | top3="
                + (
                    "PASS"
                    if result[
                        "top_3_match"
                    ]
                    else "FAIL"
                )
                + " | expected="
                + result[
                    "expected_source"
                ]
                + " | actual="
                + (
                    result[
                        "returned_sources"
                    ][0]
                    if result[
                        "returned_sources"
                    ]
                    else "NONE"
                )
            )
        )


    lines.extend(
        [
            "",
            "BASELINE COVERAGE",
            (
                "-" * 52
            ),
            (
                "Covered in M3: "
                + ", ".join(
                    report[
                        "baseline_coverage"
                    ][
                        "covered_in_m3"
                    ]
                )
            ),
            (
                "Deferred to M4: "
                + ", ".join(
                    report[
                        "baseline_coverage"
                    ][
                        "deferred_to_m4"
                    ]
                )
            ),
            (
                "Deferred to M6 adversarial: "
                + ", ".join(
                    report[
                        "baseline_coverage"
                    ][
                        "deferred_to_m6_adversarial"
                    ]
                )
            ),
            "",
        ]
    )


    return "\n".join(
        lines
    )


def main() -> None:

    fixture = json.loads(
        FIXTURE_PATH.read_text(
            encoding="utf-8"
        )
    )


    provider = (
        get_embedding_provider()
    )


    print(
        "SupportPilot M3F RAG evaluation"
    )

    print(
        (
            "Provider: "
            f"{provider.provider_name}"
        )
    )

    print(
        (
            "Model: "
            f"{provider.model}"
        )
    )

    print()


    report = build_report(
        fixture=fixture,
        provider=provider,
    )


    JSON_OUTPUT.parent.mkdir(
        parents=True,
        exist_ok=True,
    )


    JSON_OUTPUT.write_text(
        json.dumps(
            report,
            indent=2,
            ensure_ascii=False,
        )
        + "\n",

        encoding="utf-8",
    )


    text_report = (
        render_text(
            report
        )
    )


    TEXT_OUTPUT.write_text(
        text_report + "\n",
        encoding="utf-8",
    )


    print()

    print(
        text_report
    )

    print(
        (
            "JSON evidence: "
            + str(
                JSON_OUTPUT
            )
        )
    )

    print(
        (
            "Text evidence: "
            + str(
                TEXT_OUTPUT
            )
        )
    )


    if not report[
        "overall_pass"
    ]:

        print(
            (
                "\nM3F acceptance "
                "gate FAILED."
            ),

            file=sys.stderr,
        )

        raise SystemExit(
            1
        )


    print(
        "\nM3F acceptance gate PASSED."
    )


if __name__ == "__main__":
    main()