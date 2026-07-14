import json
from typing import Any


EXPECTED_TOP_LEVEL_KEYS = {
    "groundedness",
    "quiz_quality",
    "clarity",
    "overall_score",
}

EXPECTED_METRIC_KEYS = {
    "score",
    "justification",
}


def validate_evaluation_output(
    evidence_packet: dict[str, Any],
    answer: str,
) -> dict[str, Any]:
    violations: list[str] = []

    parsed_answer = parse_answer_json(answer)

    if parsed_answer is None:
        return {
            "passed": False,
            "violations": ["Answer must be a valid JSON object."],
        }

    actual_top_level_keys = set(parsed_answer.keys())

    missing_keys = EXPECTED_TOP_LEVEL_KEYS - actual_top_level_keys
    extra_keys = actual_top_level_keys - EXPECTED_TOP_LEVEL_KEYS

    if missing_keys:
        violations.append(f"Missing top-level keys: {sorted(missing_keys)}")

    if extra_keys:
        violations.append(f"Unexpected top-level keys: {sorted(extra_keys)}")

    for metric_name in [
        "groundedness",
        "quiz_quality",
        "clarity",
        "overall_score",
    ]:
        metric = parsed_answer.get(metric_name)

        if not isinstance(metric, dict):
            violations.append(f"{metric_name} must be an object.")
            continue

        validate_metric(
            metric_name=metric_name,
            metric=metric,
            violations=violations,
        )

    return {
        "passed": len(violations) == 0,
        "violations": violations,
    }


def parse_answer_json(answer: str) -> dict[str, Any] | None:
    try:
        parsed = json.loads(answer)
    except json.JSONDecodeError:
        return None

    if not isinstance(parsed, dict):
        return None

    return parsed


def validate_metric(
    metric_name: str,
    metric: dict[str, Any],
    violations: list[str],
) -> None:
    actual_keys = set(metric.keys())

    missing_keys = EXPECTED_METRIC_KEYS - actual_keys
    extra_keys = actual_keys - EXPECTED_METRIC_KEYS

    if missing_keys:
        violations.append(
            f"{metric_name} missing keys: {sorted(missing_keys)}"
        )

    if extra_keys:
        violations.append(
            f"{metric_name} has unexpected keys: {sorted(extra_keys)}"
        )

    score = metric.get("score")
    justification = metric.get("justification")

    if metric_name == "quiz_quality":
        if score is not None and not is_valid_score(score):
            violations.append(
                "quiz_quality.score must be an integer or float from 1 to 10, or null."
            )

        if score is None and justification != "quiz_output not provided":
            violations.append(
                "When quiz_quality.score is null, justification must be 'quiz_output not provided'."
            )
    else:
        if not is_valid_score(score):
            violations.append(
                f"{metric_name}.score must be an integer or float from 1 to 10."
            )

    if not isinstance(justification, str):
        violations.append(f"{metric_name}.justification must be a string.")
    elif not justification.strip():
        violations.append(f"{metric_name}.justification must not be empty.")


def is_valid_score(value: Any) -> bool:
    if not isinstance(value, int | float):
        return False

    return 1 <= value <= 10