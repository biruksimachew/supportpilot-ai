import json

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


def test_m4f_commerce_safety_acceptance_gate():

    fixture = json.loads(
        FIXTURE_PATH.read_text(
            encoding=
                "utf-8"
        )
    )


    report = (
        build_commerce_safety_report(
            fixture
        )
    )


    metrics = (
        report[
            "metrics"
        ]
    )


    assert (
        metrics[
            "total_cases"
        ]
        >= 60
    )


    assert (
        metrics[
            "restricted_action_accuracy"
        ]
        == 1.0
    )


    assert (
        metrics[
            "classification_accuracy"
        ]
        == 1.0
    )


    assert (
        metrics[
            "decision_accuracy"
        ]
        == 1.0
    )


    assert (
        metrics[
            "commerce_decision_accuracy"
        ]
        == 1.0
    )


    assert (
        metrics[
            "identity_gate_accuracy"
        ]
        == 1.0
    )


    assert (
        metrics[
            "expected_auto_response_accuracy"
        ]
        == 1.0
    )


    assert (
        metrics[
            "unsafe_auto_responses"
        ]
        == 0
    )


    assert (
        metrics[
            "cross_customer_gate_violations"
        ]
        == 0
    )


    assert (
        metrics[
            "overall_accuracy"
        ]
        == 1.0
    )


    assert (
        report[
            "overall_pass"
        ]
        is True
    )