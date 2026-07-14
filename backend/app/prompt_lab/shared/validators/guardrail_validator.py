from typing import Any


EXPECTED_CHECK_NAMES = [
    "tutor_selected_explanation_incorrect",
    "tutor_pattern_explanation_incorrect",
    "tutor_same_pattern_explanation_incorrect",
    "tutor_introduced_incorrect_meaning",
    "tutor_introduced_unsupported_pattern",
    "tutor_introduced_unsupported_card",
    "quiz_introduced_unsupported_content",
    "quiz_answer_incorrect",
    "quiz_feedback_incorrect",
    "quiz_question_target_mismatch",
    "quiz_ambiguous_correct_answer",
    "quiz_pattern_or_card_not_in_tree",
]


def validate_guardrail_output(
    evidence_packet: dict[str, Any],
    answer: dict[str, Any] | None,
) -> dict[str, Any]:
    violations: list[str] = []

    if not isinstance(answer, dict):
        return {
            "passed": False,
            "violations": ["Answer must be a JSON object."],
        }

    required_top_level_keys = {
        "passed",
        "checks",
    }

    actual_top_level_keys = set(answer.keys())

    missing_top_level_keys = required_top_level_keys - actual_top_level_keys
    extra_top_level_keys = actual_top_level_keys - required_top_level_keys

    if missing_top_level_keys:
        violations.append(
            f"Missing top-level keys: {sorted(missing_top_level_keys)}"
        )

    if extra_top_level_keys:
        violations.append(
            f"Unexpected top-level keys: {sorted(extra_top_level_keys)}"
        )

    if not isinstance(answer.get("passed"), bool):
        violations.append("passed must be a boolean.")

    checks = answer.get("checks")

    if not isinstance(checks, list):
        violations.append("checks must be a list.")
        return {
            "passed": False,
            "violations": violations,
        }

    if len(checks) != len(EXPECTED_CHECK_NAMES):
        violations.append(
            f"checks must contain exactly {len(EXPECTED_CHECK_NAMES)} items."
        )

    observed_names: list[str] = []

    for index, check in enumerate(checks):
        if not isinstance(check, dict):
            violations.append(f"checks[{index}] must be an object.")
            continue

        validate_single_check(
            index=index,
            check=check,
            violations=violations,
        )

        name = check.get("name")
        if isinstance(name, str):
            observed_names.append(name)

        if index < len(EXPECTED_CHECK_NAMES):
            expected_name = EXPECTED_CHECK_NAMES[index]
            if name != expected_name:
                violations.append(
                    f"checks[{index}].name must be {expected_name!r}."
                )

    if observed_names != EXPECTED_CHECK_NAMES:
        violations.append(
            "checks must appear in the exact required order."
        )

    any_flagged = any(
        isinstance(check, dict) and check.get("flagged") is True
        for check in checks
    )

    expected_passed = not any_flagged

    if isinstance(answer.get("passed"), bool) and answer["passed"] != expected_passed:
        violations.append(
            "passed must be true only when every check has flagged=false."
        )

    return {
        "passed": len(violations) == 0,
        "violations": violations,
    }


def validate_single_check(
    index: int,
    check: dict[str, Any],
    violations: list[str],
) -> None:
    required_keys = {
        "name",
        "flagged",
        "reason",
        "evidence_quote",
    }

    actual_keys = set(check.keys())

    missing_keys = required_keys - actual_keys
    extra_keys = actual_keys - required_keys

    if missing_keys:
        violations.append(
            f"checks[{index}] missing keys: {sorted(missing_keys)}"
        )

    if extra_keys:
        violations.append(
            f"checks[{index}] has unexpected keys: {sorted(extra_keys)}"
        )

    if not isinstance(check.get("name"), str):
        violations.append(f"checks[{index}].name must be a string.")

    if not isinstance(check.get("flagged"), bool):
        violations.append(f"checks[{index}].flagged must be a boolean.")

    if not isinstance(check.get("reason"), str):
        violations.append(f"checks[{index}].reason must be a string.")

    evidence_quote = check.get("evidence_quote")

    if not isinstance(evidence_quote, dict):
        violations.append(f"checks[{index}].evidence_quote must be an object.")
        return

    expected_quote_keys = {
        "evidence",
        "output",
    }

    actual_quote_keys = set(evidence_quote.keys())

    missing_quote_keys = expected_quote_keys - actual_quote_keys
    extra_quote_keys = actual_quote_keys - expected_quote_keys

    if missing_quote_keys:
        violations.append(
            f"checks[{index}].evidence_quote missing keys: {sorted(missing_quote_keys)}"
        )

    if extra_quote_keys:
        violations.append(
            f"checks[{index}].evidence_quote has unexpected keys: {sorted(extra_quote_keys)}"
        )

    flagged = check.get("flagged")

    evidence_value = evidence_quote.get("evidence")
    output_value = evidence_quote.get("output")

    if flagged is True:
        if not isinstance(evidence_value, str) or not evidence_value.strip():
            violations.append(
                f"checks[{index}].evidence_quote.evidence must be a non-empty string when flagged=true."
            )

        if not isinstance(output_value, str) or not output_value.strip():
            violations.append(
                f"checks[{index}].evidence_quote.output must be a non-empty string when flagged=true."
            )

        if not check.get("reason", "").strip():
            violations.append(
                f"checks[{index}].reason must be non-empty when flagged=true."
            )

    if flagged is False:
        if evidence_value is not None:
            violations.append(
                f"checks[{index}].evidence_quote.evidence must be null when flagged=false."
            )

        if output_value is not None:
            violations.append(
                f"checks[{index}].evidence_quote.output must be null when flagged=false."
            )

        if check.get("reason") != "":
            violations.append(
                f"checks[{index}].reason must be an empty string when flagged=false."
            )