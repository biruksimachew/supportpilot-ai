import json

from pathlib import Path

from app.services.rag_evaluation import (
    evaluate_decision_case,
    evaluate_grounding_case,
)


FIXTURE_PATH = (
    Path(__file__)
    .resolve()
    .parents[1]
    / "fixtures"
    / "rag_evaluation.json"
)


def load_fixture() -> dict:

    return json.loads(
        FIXTURE_PATH.read_text(
            encoding="utf-8"
        )
    )


def test_all_evidence_decision_evaluation_cases_pass():

    fixture = load_fixture()

    results = [
        evaluate_decision_case(
            case
        )
        for case
        in fixture[
            "decision_cases"
        ]
    ]


    failures = [
        result
        for result in results
        if not result[
            "passed"
        ]
    ]


    assert failures == []


def test_all_grounding_contract_evaluation_cases_pass():

    fixture = load_fixture()

    results = [
        evaluate_grounding_case(
            case
        )
        for case
        in fixture[
            "grounding_cases"
        ]
    ]


    failures = [
        result
        for result in results
        if not result[
            "passed"
        ]
    ]


    assert failures == []