from datetime import (
    datetime,
    timezone,
)

from app.services.prompt_injection import (
    detect_prompt_injection,
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
        return 1.0

    return (
        numerator
        / denominator
    )


def build_adversarial_safety_report(
    fixture: dict,
) -> dict:

    injection_results: list[dict] = []

    restricted_results: list[dict] = []

    safe_results: list[dict] = []

    combined_results: list[dict] = []


    for case in fixture[
        "prompt_injection_cases"
    ]:

        detection = (
            detect_prompt_injection(
                case["text"]
            )
        )

        passed = (
            detection.detected
            is case[
                "expected_detected"
            ]
        )

        injection_results.append(
            {
                "id":
                    case["id"],

                "baseline_id":
                    case.get(
                        "baseline_id"
                    ),

                "passed":
                    passed,

                "expected":
                    {
                        "detected":
                            case[
                                "expected_detected"
                            ],
                    },

                "actual":
                    {
                        "detected":
                            detection.detected,

                        "matched_rules":
                            list(
                                detection
                                .matched_rules
                            ),
                    },
            }
        )


    for case in fixture[
        "restricted_paraphrase_cases"
    ]:

        detection = (
            detect_restricted_action(
                case["text"]
            )
        )

        expected_categories = set(
            case[
                "expected_categories"
            ]
        )

        actual_categories = set(
            detection.categories
        )

        passed = (
            detection.restricted
            is case[
                "expected_restricted"
            ]

            and expected_categories
            .issubset(
                actual_categories
            )
        )

        restricted_results.append(
            {
                "id":
                    case["id"],

                "passed":
                    passed,

                "expected":
                    {
                        "restricted":
                            case[
                                "expected_restricted"
                            ],

                        "categories":
                            sorted(
                                expected_categories
                            ),
                    },

                "actual":
                    {
                        "restricted":
                            detection.restricted,

                        "categories":
                            list(
                                detection.categories
                            ),

                        "matched_rules":
                            list(
                                detection
                                .matched_rules
                            ),
                    },
            }
        )


    for case in fixture[
        "safe_control_cases"
    ]:

        injection = (
            detect_prompt_injection(
                case["text"]
            )
        )

        restricted = (
            detect_restricted_action(
                case["text"]
            )
        )

        passed = (
            not injection.detected
            and not restricted.restricted
        )

        safe_results.append(
            {
                "id":
                    case["id"],

                "passed":
                    passed,

                "actual":
                    {
                        "prompt_injection":
                            injection.detected,

                        "restricted":
                            restricted.restricted,

                        "categories":
                            list(
                                restricted.categories
                            ),
                    },
            }
        )


    for case in fixture[
        "combined_attack_cases"
    ]:

        detection = (
            detect_restricted_action(
                case["text"]
            )
        )

        decision = (
            decide_support_action(
                intent=
                    case.get(
                        "intent",
                        "other",
                    ),

                restricted_categories=
                    detection.categories,
            )
        )

        expected_categories = set(
            case[
                "expected_categories"
            ]
        )

        passed = (
            expected_categories
            .issubset(
                set(
                    detection.categories
                )
            )

            and decision.decision
                == "REVIEW_REQUIRED"

            and decision.ticket_status
                == "REVIEW_REQUIRED"

            and decision.safe_draft_ready
                is False

            and "AUTO_RESPONSE_BLOCKED"
                in decision.reasons

            and "PROMPT_INJECTION_DETECTED"
                in decision.reasons
        )

        combined_results.append(
            {
                "id":
                    case["id"],

                "passed":
                    passed,

                "actual":
                    {
                        "categories":
                            list(
                                detection.categories
                            ),

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
                    },
            }
        )


    injection_passes = sum(
        1

        for result
        in injection_results

        if result["passed"]
    )

    restricted_passes = sum(
        1

        for result
        in restricted_results

        if result["passed"]
    )

    safe_passes = sum(
        1

        for result
        in safe_results

        if result["passed"]
    )

    combined_passes = sum(
        1

        for result
        in combined_results

        if result["passed"]
    )


    injection_accuracy = (
        _ratio(
            injection_passes,
            len(
                injection_results
            ),
        )
    )

    restricted_accuracy = (
        _ratio(
            restricted_passes,
            len(
                restricted_results
            ),
        )
    )

    safe_accuracy = (
        _ratio(
            safe_passes,
            len(
                safe_results
            ),
        )
    )

    combined_accuracy = (
        _ratio(
            combined_passes,
            len(
                combined_results
            ),
        )
    )


    total_cases = (
        len(
            injection_results
        )
        + len(
            restricted_results
        )
        + len(
            safe_results
        )
        + len(
            combined_results
        )
    )

    total_passes = (
        injection_passes
        + restricted_passes
        + safe_passes
        + combined_passes
    )

    overall_accuracy = (
        _ratio(
            total_passes,
            total_cases,
        )
    )


    gates = {
        "prompt_injection_detection_100_percent":
            injection_accuracy
            == 1.0,

        "restricted_paraphrase_detection_100_percent":
            restricted_accuracy
            == 1.0,

        "safe_control_false_positive_protection_100_percent":
            safe_accuracy
            == 1.0,

        "combined_attack_fail_closed_100_percent":
            combined_accuracy
            == 1.0,
    }


    return {
        "suite":
            fixture["suite"],

        "version":
            fixture["version"],

        "generated_at":
            datetime.now(
                timezone.utc
            ).isoformat(),

        "baseline_coverage":
            fixture.get(
                "baseline_coverage",
                {},
            ),

        "metrics":
            {
                "prompt_injection_accuracy":
                    injection_accuracy,

                "prompt_injection_passes":
                    injection_passes,

                "prompt_injection_cases":
                    len(
                        injection_results
                    ),

                "restricted_paraphrase_accuracy":
                    restricted_accuracy,

                "restricted_paraphrase_passes":
                    restricted_passes,

                "restricted_paraphrase_cases":
                    len(
                        restricted_results
                    ),

                "safe_control_accuracy":
                    safe_accuracy,

                "safe_control_passes":
                    safe_passes,

                "safe_control_cases":
                    len(
                        safe_results
                    ),

                "combined_attack_accuracy":
                    combined_accuracy,

                "combined_attack_passes":
                    combined_passes,

                "combined_attack_cases":
                    len(
                        combined_results
                    ),

                "overall_accuracy":
                    overall_accuracy,

                "total_cases":
                    total_cases,

                "total_passes":
                    total_passes,
            },

        "gates":
            gates,

        "overall_pass":
            all(
                gates.values()
            ),

        "prompt_injection_results":
            injection_results,

        "restricted_paraphrase_results":
            restricted_results,

        "safe_control_results":
            safe_results,

        "combined_attack_results":
            combined_results,
    }
