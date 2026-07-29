# app/prompt_lab/shared/validators/common_validator.py

# 1. Output is valid JSON
# 2. Output JSON is an object/dict
# 3. Output has no markdown/code fences
# 4. Output has no text before or after JSON
# 5. No Arabic words appear unless grounded in the input evidence
# 6. No empty required string fields

from dataclasses import dataclass, field
import json
import re
from typing import Any, Callable


@dataclass
class ValidationResult:
    passed: bool = True
    violations: list[str] = field(default_factory=list)
    parsed_json: dict[str, Any] | None = None

    def add(self, message: str) -> None:
        self.violations.append(message)
        self.passed = False


# Matches contiguous Arabic-script runs, INCLUDING internal spaces,
# so "ع ل م" is treated as one run instead of three isolated letters.
# We trim leading/trailing whitespace after matching.
_ARABIC_RUN = re.compile(r"[\u0600-\u06FF][\u0600-\u06FF\s]*[\u0600-\u06FF]|[\u0600-\u06FF]")

_CODE_FENCE_RE = re.compile(r"```")

# Harakat (short vowels/tashkeel) + tatweel (kashida) + other diacritic marks.
# Stripped before comparison so "تَفْعِيل" and "تفعيل" are treated as equal.
_TASHKEEL_RE = re.compile(r"[\u0610-\u061A\u064B-\u065F\u0670\u06D6-\u06DC\u06DF-\u06E8\u06EA-\u06ED\u0640]")


def get_llm_input(evidence_packet: dict[str, Any]) -> dict[str, Any]:
    """
    Prompt-lab evidence packets wrap the actual model input under llm_input.

    Validators should validate against the same evidence the model saw.
    If no llm_input wrapper exists, fall back to the original packet so this
    helper also works with direct/non-prompt-lab evidence dictionaries.
    """

    if isinstance(evidence_packet.get("llm_input"), dict):
        return evidence_packet["llm_input"]

    return evidence_packet


def parse_json_output(raw_output: str) -> ValidationResult:
    """
    Validates that the model output is clean JSON only.

    This catches:
    - markdown/code fences
    - text before JSON
    - text after JSON
    - invalid JSON
    - non-object JSON
    """

    result = ValidationResult()

    if not isinstance(raw_output, str) or not raw_output.strip():
        result.add("json: output is empty")
        return result

    text = raw_output.strip()

    if _CODE_FENCE_RE.search(text):
        result.add("json: output must not contain markdown code fences")

    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        result.add(f"json: output is not valid JSON: {exc}")
        return result

    if not isinstance(parsed, dict):
        result.add("json: output JSON must be an object")
        return result

    result.parsed_json = parsed
    return result


def word_count(text: str) -> int:
    return len(text.split())


def sentence_count(text: str) -> int:
    parts = re.split(r"[.!؟?]+", text.strip())
    return len([part for part in parts if part.strip()])


def normalize_arabic(text: str) -> str:
    """
    Strips diacritics (tashkeel) and tatweel so that grounding comparisons
    are insensitive to whether harakat were included.

    e.g. "تَفْعِيل" -> "تفعيل"
    """

    if not isinstance(text, str):
        return ""

    stripped = _TASHKEEL_RE.sub("", text)
    return re.sub(r"\s+", " ", stripped).strip()


def extract_arabic_runs(text: str) -> list[str]:
    if not isinstance(text, str):
        return []

    return [run.strip() for run in _ARABIC_RUN.findall(text) if run.strip()]


def replace_arabic_runs(text: str, replace: Callable[[str], str]) -> str:
    """
    Rewrite each maximal Arabic run through `replace`, leaving all other text
    untouched. Returns non-strings unchanged.

    Whole runs only, which is the point: replacing a run by `str.replace` of its
    text would also rewrite that same sequence where it sits *inside* a longer
    Arabic word elsewhere in the string. Callers that canonicalize spelling need
    the run boundaries the grounding check already uses, so the definition of "a
    run" stays here rather than being restated per caller.
    """
    if not isinstance(text, str):
        return text

    return _ARABIC_RUN.sub(lambda match: replace(match.group(0)), text)


def check_no_unknown_arabic(
    text: str,
    allowed_arabic: set[str],
    field_name: str,
    result: ValidationResult,
) -> None:
    """
    Flags Arabic text that is not grounded in the evidence packet.

    Matching is diacritic-insensitive and intentionally loose:
    - normalized run in normalized allowed item
    - normalized allowed item in normalized run

    This helps avoid false failures from prefixes, diacritics, or
    spaced-letter root notation (e.g. "ع ل م").
    """

    # Spaces are also dropped: root notation is spaced ("د ر س"), and a model
    # mis-spacing a copy ("در س") is a typography slip, not invented Arabic.
    normalized_allowed = {
        normalize_arabic(item).replace(" ", "") for item in allowed_arabic if item
    }
    normalized_allowed = {item for item in normalized_allowed if item}

    for run in extract_arabic_runs(text):
        normalized_run = normalize_arabic(run).replace(" ", "")

        if not normalized_run:
            continue

        is_allowed = any(
            normalized_run in allowed_item or allowed_item in normalized_run
            for allowed_item in normalized_allowed
        )

        if not is_allowed:
            result.add(
                f"{field_name}: contains Arabic text not present in input evidence: '{run}'"
            )


def require_exact_keys(
    actual: dict[str, Any],
    expected_keys: set[str],
    label: str,
    result: ValidationResult,
) -> None:
    actual_keys = set(actual.keys())

    if actual_keys != expected_keys:
        result.add(
            f"{label}: expected exactly keys {sorted(expected_keys)}, got {sorted(actual_keys)}"
        )


def require_non_empty_string(
    value: Any,
    field_name: str,
    result: ValidationResult,
) -> None:
    if not isinstance(value, str) or not value.strip():
        result.add(f"{field_name}: must be a non-empty string")


def add_arabic_value(values: set[str], value: Any) -> None:
    """
    Adds a value or each item of a list of values to an allowed-Arabic set.

    Handles evidence fields that may be stored as either a plain string
    ("تفعيل") or a list of strings/letters (["ع", "ل", "م"]).
    """

    if isinstance(value, str) and value.strip():
        values.add(value.strip())
    elif isinstance(value, list):
        for item in value:
            if isinstance(item, str) and item.strip():
                values.add(item.strip())