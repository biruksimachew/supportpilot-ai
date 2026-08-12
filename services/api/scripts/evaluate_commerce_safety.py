import json
import sys

from pathlib import Path

from app.services.commerce_safety_evaluation import (
    build_commerce_safety_report,
)


FIXTURE_PATH = (
    Path(
        "/app/tests/fixtures"
    )
    / "commerce_safety_evaluation.json"
)


JSON_OUTPUT = Path(
    "/evidence/"
    "milestone-4-commerce-safety-evaluation.json"
)


TEXT_OUTPUT = Path(
    "/evidence/"
    "milestone-4-commerce-safety-evaluation.txt"
)


def _percent(
    value: float,
) -> str:

    return (
        f"{value * 100:.1f}%"
    )


def _status(
    passed: bool,
) -> str:

    if passed:
        return "PASS"

    return "FAIL"


def render_text(
    report: dict,
) -> str:

    metrics = (
        report[
            "metrics"
        ]
    )


    lines = [
        (
            "SupportPilot AI - "
            "Milestone 4 Commerce "
            "and Safety Evaluation"
        ),
        "=" * 64,
        "",
        (
            "Generated: "
            + report[
                "generated_at"
            ]
        ),
        (
            "Version: "
            + report[
                "version"
            ]
        ),
        "",
        "METRICS",
        "-" * 64,
        (
            "Restricted-action detection: "
            + _percent(
                metrics[
                    "restricted_action_accuracy"
                ]
            )
            + " ("
            + str(
                metrics[
                    "restricted_action_passes"
                ]
            )
            + "/"
            + str(
                metrics[
                    "restricted_action_cases"
                ]
            )
            + ")"
        ),
        (
            "Request classification:       "
            + _percent(
                metrics[
                    "classification_accuracy"
                ]
            )
            + " ("
            + str(
                metrics[
                    "classification_passes"
                ]
            )
            + "/"
            + str(
                metrics[
                    "classification_cases"
                ]
            )
            + ")"
        ),
        (
            "Safety-decision accuracy:     "
            + _percent(
                metrics[
                    "decision_accuracy"
                ]
            )
            + " ("
            + str(
                metrics[
                    "decision_passes"
                ]
            )
            + "/"
            + str(
                metrics[
                    "decision_cases"
                ]
            )
            + ")"
        ),
        (
            "Commerce-decision accuracy:   "
            + _percent(
                metrics[
                    "commerce_decision_accuracy"
                ]
            )
        ),
        (
            "Identity-gate accuracy:       "
            + _percent(
                metrics[
                    "identity_gate_accuracy"
                ]
            )
        ),
        (
            "Expected AUTO_RESPOND:        "
            + _percent(
                metrics[
                    "expected_auto_response_accuracy"
                ]
            )
        ),
        (
            "Unsafe AUTO_RESPOND cases:    "
            + str(
                metrics[
                    "unsafe_auto_responses"
                ]
            )
        ),
        (
            "Cross-customer gate violations: "
            + str(
                metrics[
                    "cross_customer_gate_violations"
                ]
            )
        ),
        (
            "Overall deterministic accuracy: "
            + _percent(
                metrics[
                    "overall_accuracy"
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
        "ACCEPTANCE GATES",
        "-" * 64,
    ]


    for (
        gate,
        passed,
    ) in report[
        "gates"
    ].items():

        lines.append(
            (
                gate
                + ": "
                + _status(
                    passed
                )
            )
        )


    lines.extend(
        [
            "",
            (
                "OVERALL: "
                + _status(
                    report[
                        "overall_pass"
                    ]
                )
            ),
            "",
            "RESTRICTED-ACTION CASES",
            "-" * 64,
        ]
    )


    for result in report[
        "restricted_action_results"
    ]:

        lines.append(
            (
                result[
                    "id"
                ]
                + " | "
                + _status(
                    result[
                        "passed"
                    ]
                )
                + " | restricted="
                + str(
                    result[
                        "actual"
                    ][
                        "restricted"
                    ]
                )
                + " | categories="
                + ",".join(
                    result[
                        "actual"
                    ][
                        "categories"
                    ]
                )
            )
        )


    lines.extend(
        [
            "",
            "CLASSIFICATION CASES",
            "-" * 64,
        ]
    )


    for result in report[
        "classification_results"
    ]:

        lines.append(
            (
                result[
                    "id"
                ]
                + " | "
                + _status(
                    result[
                        "passed"
                    ]
                )
                + " | intent="
                + result[
                    "actual"
                ][
                    "intent"
                ]
                + " | commerce="
                + str(
                    result[
                        "actual"
                    ][
                        "commerce_required"
                    ]
                )
                + " | order="
                + str(
                    result[
                        "actual"
                    ][
                        "order_number"
                    ]
                )
            )
        )


    lines.extend(
        [
            "",
            "SAFETY DECISION CASES",
            "-" * 64,
        ]
    )


    for result in report[
        "decision_results"
    ]:

        lines.append(
            (
                result[
                    "id"
                ]
                + " | "
                + _status(
                    result[
                        "passed"
                    ]
                )
                + " | expected="
                + result[
                    "expected"
                ][
                    "decision"
                ]
                + " | actual="
                + result[
                    "actual"
                ][
                    "decision"
                ]
                + " | ticket="
                + result[
                    "actual"
                ][
                    "ticket_status"
                ]
            )
        )


    coverage = report[
        "baseline_coverage"
    ]


    lines.extend(
        [
            "",
            "BASELINE COVERAGE",
            "-" * 64,
            (
                "Covered in M4F: "
                + ", ".join(
                    coverage.get(
                        "covered",
                        [],
                    )
                )
            ),
            (
                "Deferred to M6 adversarial: "
                + ", ".join(
                    coverage.get(
                        "deferred_to_m6_adversarial",
                        [],
                    )
                )
            ),
            "",
            (
                "NOTE: cross-customer results in this "
                "deterministic suite measure the policy "
                "gate. Database ownership enforcement is "
                "covered separately by integration tests."
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
            encoding=
                "utf-8"
        )
    )


    print(
        (
            "SupportPilot M4F "
            "commerce/safety evaluation"
        )
    )

    print()


    report = (
        build_commerce_safety_report(
            fixture
        )
    )


    JSON_OUTPUT.parent.mkdir(
        parents=
            True,

        exist_ok=
            True,
    )


    JSON_OUTPUT.write_text(
        (
            json.dumps(
                report,
                indent=2,
                ensure_ascii=False,
            )
            + "\n"
        ),

        encoding=
            "utf-8",
    )


    text_report = (
        render_text(
            report
        )
    )


    TEXT_OUTPUT.write_text(
        (
            text_report
            + "\n"
        ),

        encoding=
            "utf-8",
    )


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
                "\nM4F acceptance "
                "gate FAILED."
            ),

            file=
                sys.stderr,
        )


        raise SystemExit(
            1
        )


    print(
        (
            "\nM4F acceptance "
            "gate PASSED."
        )
    )


if __name__ == "__main__":

    main()