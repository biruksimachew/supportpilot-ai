import json
import sys

from pathlib import Path

from app.services.adversarial_safety_evaluation import (
    build_adversarial_safety_report,
)


FIXTURE_PATH = (
    Path(
        "/app/tests/fixtures"
    )
    / "adversarial_safety_evaluation.json"
)


JSON_OUTPUT = Path(
    "/evidence/"
    "milestone-6a-adversarial-safety-evaluation.json"
)


TEXT_OUTPUT = Path(
    "/evidence/"
    "milestone-6a-adversarial-safety-evaluation.txt"
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

    return (
        "PASS"
        if passed
        else "FAIL"
    )


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
            "Milestone 6A "
            "Adversarial Safety Evaluation"
        ),
        "=" * 72,
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
        "-" * 72,
        (
            "Prompt-injection detection:       "
            + _percent(
                metrics[
                    "prompt_injection_accuracy"
                ]
            )
            + " ("
            + str(
                metrics[
                    "prompt_injection_passes"
                ]
            )
            + "/"
            + str(
                metrics[
                    "prompt_injection_cases"
                ]
            )
            + ")"
        ),
        (
            "Restricted paraphrase detection: "
            + _percent(
                metrics[
                    "restricted_paraphrase_accuracy"
                ]
            )
            + " ("
            + str(
                metrics[
                    "restricted_paraphrase_passes"
                ]
            )
            + "/"
            + str(
                metrics[
                    "restricted_paraphrase_cases"
                ]
            )
            + ")"
        ),
        (
            "Safe-control protection:          "
            + _percent(
                metrics[
                    "safe_control_accuracy"
                ]
            )
            + " ("
            + str(
                metrics[
                    "safe_control_passes"
                ]
            )
            + "/"
            + str(
                metrics[
                    "safe_control_cases"
                ]
            )
            + ")"
        ),
        (
            "Combined attack fail-closed:      "
            + _percent(
                metrics[
                    "combined_attack_accuracy"
                ]
            )
            + " ("
            + str(
                metrics[
                    "combined_attack_passes"
                ]
            )
            + "/"
            + str(
                metrics[
                    "combined_attack_cases"
                ]
            )
            + ")"
        ),
        (
            "Overall deterministic accuracy:   "
            + _percent(
                metrics[
                    "overall_accuracy"
                ]
            )
        ),
        (
            "Total adversarial cases:          "
            + str(
                metrics[
                    "total_cases"
                ]
            )
        ),
        "",
        "ACCEPTANCE GATES",
        "-" * 72,
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
            "BASELINE COVERAGE",
            "-" * 72,
            (
                "Newly covered: "
                + ", ".join(
                    report[
                        "baseline_coverage"
                    ].get(
                        "newly_covered",
                        [],
                    )
                )
            ),
            "",
            (
                "NOTE: This deterministic suite validates "
                "prompt-injection and restricted-action "
                "policy gates. End-to-end pre-provider "
                "blocking is covered by the M6A integration "
                "test."
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

    report = (
        build_adversarial_safety_report(
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
        text_report + "\n",
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
                "\nM6A adversarial "
                "acceptance gate FAILED."
            ),
            file=
                sys.stderr,
        )

        raise SystemExit(
            1
        )

    print(
        (
            "\nM6A adversarial "
            "acceptance gate PASSED."
        )
    )


if __name__ == "__main__":

    main()
