from datetime import (
    datetime,
    timezone,
)

from app.services.evidence_decision import (
    EvidenceAssessment,
)

from app.services.request_classification import (
    classify_support_request,
)

from app.services.restricted_actions import (
    detect_restricted_action,
)

from app.services.support_decision import (
    decide_support_action,
)


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


def evaluate_restricted_action_case(
    case: dict,
) -> dict:

    detection = (
        detect_restricted_action(
            case[
                "text"
            ]
        )
    )


    expected_categories = tuple(
        case.get(
            "expected_categories",
            [],
        )
    )


    checks = {
        "restricted":
            (
                detection.restricted
                ==
                case[
                    "expected_restricted"
                ]
            ),

        "categories":
            (
                detection.categories
                ==
                expected_categories
            ),
    }


    return {
        "id":
            case[
                "id"
            ],

        "baseline_id":
            case.get(
                "baseline_id"
            ),

        "text":
            case[
                "text"
            ],

        "passed":
            all(
                checks.values()
            ),

        "checks":
            checks,

        "expected": {
            "restricted":
                case[
                    "expected_restricted"
                ],

            "categories":
                list(
                    expected_categories
                ),
        },

        "actual": {
            "restricted":
                detection.restricted,

            "categories":
                list(
                    detection.categories
                ),

            "matched_rules":
                list(
                    detection.matched_rules
                ),
        },
    }


def evaluate_classification_case(
    case: dict,
) -> dict:

    classification = (
        classify_support_request(
            case[
                "text"
            ]
        )
    )


    checks = {
        "intent":
            (
                classification.intent
                ==
                case[
                    "expected_intent"
                ]
            ),

        "commerce_required":
            (
                classification
                .commerce_required
                ==
                case[
                    "expected_commerce_required"
                ]
            ),

        "order_number":
            (
                classification.order_number
                ==
                case[
                    "expected_order_number"
                ]
            ),
    }


    return {
        "id":
            case[
                "id"
            ],

        "baseline_id":
            case.get(
                "baseline_id"
            ),

        "text":
            case[
                "text"
            ],

        "passed":
            all(
                checks.values()
            ),

        "checks":
            checks,

        "expected": {
            "intent":
                case[
                    "expected_intent"
                ],

            "commerce_required":
                case[
                    "expected_commerce_required"
                ],

            "order_number":
                case[
                    "expected_order_number"
                ],
        },

        "actual": {
            "intent":
                classification.intent,

            "commerce_required":
                classification
                .commerce_required,

            "order_number":
                classification
                .order_number,

            "reasons":
                list(
                    classification.reasons
                ),
        },
    }


def _build_evidence_assessment(
    case: dict,
) -> EvidenceAssessment:

    evidence = (
        case[
            "evidence"
        ]
    )


    return EvidenceAssessment(
        confidence=
            float(
                evidence[
                    "confidence"
                ]
            ),

        confidence_band=
            evidence[
                "confidence_band"
            ],

        generation_allowed=
            evidence[
                "generation_allowed"
            ],

        contradiction_detected=
            evidence[
                "contradiction_detected"
            ],

        ambiguity_detected=
            evidence[
                "ambiguity_detected"
            ],

        reasons=
            list(
                evidence[
                    "reasons"
                ]
            ),
    )


def _evaluate_decision(
    case: dict,
):

    kind = (
        case[
            "kind"
        ]
    )


    intent = (
        case.get(
            "intent"
        )
    )


    if kind == "restricted":

        return decide_support_action(
            intent=
                intent,

            restricted_categories=
                tuple(
                    case[
                        "restricted_categories"
                    ]
                ),
        )


    if kind == "existing_restricted":

        return decide_support_action(
            intent=
                intent,

            existing_restricted_action=
                True,
        )


    if kind == "commerce":

        kwargs = {
            "intent":
                intent,

            "commerce_required":
                True,

            "order_number":
                case.get(
                    "order_number"
                ),
        }


        if (
            "identity_verified_for_order"
            in case
        ):

            kwargs[
                "identity_verified_for_order"
            ] = (
                case[
                    "identity_verified_for_order"
                ]
            )


        if (
            "commerce_succeeded"
            in case
        ):

            kwargs[
                "commerce_succeeded"
            ] = (
                case[
                    "commerce_succeeded"
                ]
            )


        return decide_support_action(
            **kwargs
        )


    if kind == "knowledge":

        assessment = (
            _build_evidence_assessment(
                case
            )
        )


        return decide_support_action(
            intent=
                intent,

            evidence_assessment=
                assessment,

            answer_status=
                case[
                    "answer_status"
                ],
        )


    raise ValueError(
        (
            "Unsupported M4F decision "
            f"case kind: {kind}"
        )
    )


def evaluate_decision_case(
    case: dict,
) -> dict:

    decision = (
        _evaluate_decision(
            case
        )
    )


    required_reasons = (
        case.get(
            "required_reasons",
            [],
        )
    )


    checks = {
        "decision":
            (
                decision.decision
                ==
                case[
                    "expected_decision"
                ]
            ),

        "ticket_status":
            (
                decision.ticket_status
                ==
                case[
                    "expected_ticket_status"
                ]
            ),

        "safe_draft_ready":
            (
                decision.safe_draft_ready
                ==
                case[
                    "expected_safe_draft_ready"
                ]
            ),

        "required_reasons":
            all(
                reason
                in decision.reasons

                for reason
                in required_reasons
            ),
    }


    unsafe_auto_response = (
        decision.decision
        == "AUTO_RESPOND"

        and case[
            "expected_decision"
        ]
        != "AUTO_RESPOND"
    )


    cross_customer_gate_violation = (
        bool(
            case.get(
                "cross_customer_gate",
                False,
            )
        )

        and decision.decision
        == "AUTO_RESPOND"
    )


    return {
        "id":
            case[
                "id"
            ],

        "kind":
            case[
                "kind"
            ],

        "baseline_id":
            case.get(
                "baseline_id"
            ),

        "identity_gate":
            bool(
                case.get(
                    "identity_gate",
                    False,
                )
            ),

        "cross_customer_gate":
            bool(
                case.get(
                    "cross_customer_gate",
                    False,
                )
            ),

        "passed":
            all(
                checks.values()
            ),

        "checks":
            checks,

        "unsafe_auto_response":
            unsafe_auto_response,

        "cross_customer_gate_violation":
            cross_customer_gate_violation,

        "expected": {
            "decision":
                case[
                    "expected_decision"
                ],

            "ticket_status":
                case[
                    "expected_ticket_status"
                ],

            "safe_draft_ready":
                case[
                    "expected_safe_draft_ready"
                ],

            "required_reasons":
                required_reasons,
        },

        "actual": {
            "decision":
                decision.decision,

            "ticket_status":
                decision.ticket_status,

            "safe_draft_ready":
                decision.safe_draft_ready,

            "reasons":
                list(
                    decision.reasons
                ),

            "escalation_reason":
                decision.escalation_reason,
        },
    }


def build_commerce_safety_report(
    fixture: dict,
) -> dict:

    restricted_results = [
        evaluate_restricted_action_case(
            case
        )

        for case
        in fixture[
            "restricted_action_cases"
        ]
    ]


    classification_results = [
        evaluate_classification_case(
            case
        )

        for case
        in fixture[
            "classification_cases"
        ]
    ]


    decision_results = [
        evaluate_decision_case(
            case
        )

        for case
        in fixture[
            "decision_cases"
        ]
    ]


    restricted_passes = sum(
        1
        for result
        in restricted_results
        if result[
            "passed"
        ]
    )


    classification_passes = sum(
        1
        for result
        in classification_results
        if result[
            "passed"
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


    commerce_results = [
        result
        for result
        in decision_results
        if result[
            "kind"
        ]
        == "commerce"
    ]


    commerce_passes = sum(
        1
        for result
        in commerce_results
        if result[
            "passed"
        ]
    )


    identity_results = [
        result
        for result
        in decision_results
        if result[
            "identity_gate"
        ]
    ]


    identity_passes = sum(
        1
        for result
        in identity_results
        if result[
            "passed"
        ]
    )


    cross_customer_results = [
        result
        for result
        in decision_results
        if result[
            "cross_customer_gate"
        ]
    ]


    cross_customer_gate_violations = sum(
        1
        for result
        in cross_customer_results
        if result[
            "cross_customer_gate_violation"
        ]
    )


    unsafe_auto_responses = sum(
        1
        for result
        in decision_results
        if result[
            "unsafe_auto_response"
        ]
    )


    expected_auto_response_results = [
        result
        for result
        in decision_results

        if result[
            "expected"
        ][
            "decision"
        ]
        == "AUTO_RESPOND"
    ]


    expected_auto_response_passes = sum(
        1
        for result
        in expected_auto_response_results

        if result[
            "actual"
        ][
            "decision"
        ]
        == "AUTO_RESPOND"

        and result[
            "passed"
        ]
    )


    restricted_accuracy = (
        _ratio(
            restricted_passes,
            len(
                restricted_results
            ),
        )
    )


    classification_accuracy = (
        _ratio(
            classification_passes,
            len(
                classification_results
            ),
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


    commerce_accuracy = (
        _ratio(
            commerce_passes,
            len(
                commerce_results
            ),
        )
    )


    identity_accuracy = (
        _ratio(
            identity_passes,
            len(
                identity_results
            ),
        )
    )


    auto_response_expected_accuracy = (
        _ratio(
            expected_auto_response_passes,
            len(
                expected_auto_response_results
            ),
        )
    )


    total_cases = (
        len(
            restricted_results
        )
        + len(
            classification_results
        )
        + len(
            decision_results
        )
    )


    total_passes = (
        restricted_passes
        + classification_passes
        + decision_passes
    )


    overall_accuracy = (
        _ratio(
            total_passes,
            total_cases,
        )
    )


    gates = {
        "restricted_action_detection_100_percent":
            (
                restricted_accuracy
                == 1.0
            ),

        "classification_100_percent":
            (
                classification_accuracy
                == 1.0
            ),

        "safety_decision_100_percent":
            (
                decision_accuracy
                == 1.0
            ),

        "commerce_decision_100_percent":
            (
                commerce_accuracy
                == 1.0
            ),

        "identity_gate_100_percent":
            (
                identity_accuracy
                == 1.0
            ),

        "expected_auto_response_100_percent":
            (
                auto_response_expected_accuracy
                == 1.0
            ),

        "unsafe_auto_responses_zero":
            (
                unsafe_auto_responses
                == 0
            ),

        "cross_customer_gate_violations_zero":
            (
                cross_customer_gate_violations
                == 0
            ),

        "overall_100_percent":
            (
                overall_accuracy
                == 1.0
            ),
    }


    return {
        "generated_at":
            datetime.now(
                timezone.utc
            ).isoformat(),

        "milestone":
            "M4F",

        "suite":
            fixture.get(
                "suite",
                (
                    "SupportPilot Commerce "
                    "and Safety Evaluation"
                ),
            ),

        "version":
            fixture.get(
                "version",
                "m4f-v1",
            ),

        "metrics": {
            "restricted_action_cases":
                len(
                    restricted_results
                ),

            "restricted_action_passes":
                restricted_passes,

            "restricted_action_accuracy":
                restricted_accuracy,

            "classification_cases":
                len(
                    classification_results
                ),

            "classification_passes":
                classification_passes,

            "classification_accuracy":
                classification_accuracy,

            "decision_cases":
                len(
                    decision_results
                ),

            "decision_passes":
                decision_passes,

            "decision_accuracy":
                decision_accuracy,

            "commerce_decision_cases":
                len(
                    commerce_results
                ),

            "commerce_decision_passes":
                commerce_passes,

            "commerce_decision_accuracy":
                commerce_accuracy,

            "identity_gate_cases":
                len(
                    identity_results
                ),

            "identity_gate_passes":
                identity_passes,

            "identity_gate_accuracy":
                identity_accuracy,

            "expected_auto_response_cases":
                len(
                    expected_auto_response_results
                ),

            "expected_auto_response_passes":
                expected_auto_response_passes,

            "expected_auto_response_accuracy":
                auto_response_expected_accuracy,

            "unsafe_auto_responses":
                unsafe_auto_responses,

            "cross_customer_gate_cases":
                len(
                    cross_customer_results
                ),

            "cross_customer_gate_violations":
                cross_customer_gate_violations,

            "total_cases":
                total_cases,

            "total_passes":
                total_passes,

            "overall_accuracy":
                overall_accuracy,
        },

        "gates":
            gates,

        "overall_pass":
            all(
                gates.values()
            ),

        "baseline_coverage":
            fixture.get(
                "baseline_coverage",
                {},
            ),

        "restricted_action_results":
            restricted_results,

        "classification_results":
            classification_results,

        "decision_results":
            decision_results,
    }