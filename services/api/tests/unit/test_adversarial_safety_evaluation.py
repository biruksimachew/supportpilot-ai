import json

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


def test_m6a_adversarial_safety_acceptance_gates(
) -> None:

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

    assert (
        report[
            "overall_pass"
        ]
        is True
    )

    assert (
        report[
            "metrics"
        ][
            "prompt_injection_accuracy"
        ]
        == 1.0
    )

    assert (
        report[
            "metrics"
        ][
            "restricted_paraphrase_accuracy"
        ]
        == 1.0
    )

    assert (
        report[
            "metrics"
        ][
            "safe_control_accuracy"
        ]
        == 1.0
    )

    assert (
        report[
            "metrics"
        ][
            "combined_attack_accuracy"
        ]
        == 1.0
    )

    assert (
        report[
            "baseline_coverage"
        ][
            "newly_covered"
        ]
        == [
            "B-04",
        ]
    )
