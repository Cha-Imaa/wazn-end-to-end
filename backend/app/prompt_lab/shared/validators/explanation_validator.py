# app/prompt_lab/shared/validators/explanation_validator.py

# 1. Output is valid JSON
# 2. Output is a JSON object
# 3. Output has exactly these keys:
#    - explanation
#    - pattern_explanation
#    - same_pattern_explanation
# 4. No extra keys are allowed
# 5. Each value is a non-empty string
# 6. explanation:
#    - maximum 3 sentences
#    - maximum 60 words
# 7. pattern_explanation:
#    - maximum 1 sentence
#    - maximum 20 words
#    - must not mention same-pattern cards
# 8. same_pattern_explanation:
#    - maximum 2 sentences
#    - maximum 45 words
# 9. If no same-pattern cards are provided:
#    same_pattern_explanation must be exactly:
#    "No same-pattern comparison is available in the current data."
# 10. No invented Arabic:
#    Any Arabic text in explanation fields must come from:
#    - selected word
#    - root
#    - pattern
#    - same-pattern cards

from typing import Any

from app.prompt_lab.shared.validators.explanation_claim_checker import (
    card_claim_violations,
)
from app.prompt_lab.shared.validators.common_validator import (
    ValidationResult,
    add_arabic_value,
    check_no_unknown_arabic,
    get_llm_input,
    parse_json_output,
    require_exact_keys,
    require_non_empty_string,
    sentence_count,
    word_count,
)

REQUIRED_EXPLANATION_KEYS = {
    "explanation",
    "pattern_explanation",
    "same_pattern_explanation",
}

NO_SAME_PATTERN_FALLBACK = (
    "No same-pattern comparison is available in the current data."
)


def validate_explanation_output(
    evidence_packet: dict[str, Any],
    raw_output: str,
) -> ValidationResult:
    """
    Deterministic validator for Explanation Agent raw output.

    This validates:
    1. valid JSON
    2. JSON object
    3. exact keys
    4. non-empty strings
    5. length limits
    6. no invented Arabic
    7. no same-pattern cards mentioned in pattern_explanation
    8. exact fallback when no same-pattern cards exist
    """

    result = parse_json_output(raw_output)

    if not result.passed or result.parsed_json is None:
        return result

    output = result.parsed_json

    require_exact_keys(
        actual=output,
        expected_keys=REQUIRED_EXPLANATION_KEYS,
        label="explanation_output",
        result=result,
    )

    if not result.passed:
        return result

    for key in REQUIRED_EXPLANATION_KEYS:
        require_non_empty_string(output.get(key), key, result)

    if not result.passed:
        return result

    evidence = get_llm_input(evidence_packet)

    explanation = output["explanation"]
    pattern_explanation = output["pattern_explanation"]
    same_pattern_explanation = output["same_pattern_explanation"]

    if sentence_count(explanation) > 3:
        result.add("explanation: exceeds 3 sentence limit")

    if word_count(explanation) > 60:
        result.add("explanation: exceeds 60 word limit")

    if sentence_count(pattern_explanation) > 1:
        result.add("pattern_explanation: exceeds 1 sentence limit")

    if word_count(pattern_explanation) > 20:
        result.add("pattern_explanation: exceeds 20 word limit")

    if sentence_count(same_pattern_explanation) > 2:
        result.add("same_pattern_explanation: exceeds 2 sentence limit")

    if word_count(same_pattern_explanation) > 45:
        result.add("same_pattern_explanation: exceeds 45 word limit")

    allowed_arabic = _collect_allowed_arabic_for_explanation(evidence)

    check_no_unknown_arabic(
        explanation,
        allowed_arabic,
        "explanation",
        result,
    )

    check_no_unknown_arabic(
        pattern_explanation,
        allowed_arabic,
        "pattern_explanation",
        result,
    )

    check_no_unknown_arabic(
        same_pattern_explanation,
        allowed_arabic,
        "same_pattern_explanation",
        result,
    )

    # What the prose *asserts* about the cards, not just which tokens it
    # reuses — the مَحْصَلَة-called-a-place defect passed every check above.
    # See `explanation_claim_checker` for what is and is not judged.
    for violation in card_claim_violations(
        {
            "explanation": explanation,
            "pattern_explanation": pattern_explanation,
            "same_pattern_explanation": same_pattern_explanation,
        },
        evidence,
    ):
        result.add(violation)

    same_pattern_cards = evidence.get("same_pattern_cards", [])

    for card in same_pattern_cards:
        if not isinstance(card, dict):
            continue

        card_arabic = card.get("arabic", "")

        if card_arabic and card_arabic in pattern_explanation:
            result.add(
                "pattern_explanation: must not mention same-pattern cards"
            )

    if not same_pattern_cards:
        if same_pattern_explanation.strip() != NO_SAME_PATTERN_FALLBACK:
            result.add(
                "same_pattern_explanation: must use the exact fallback string when no same-pattern cards exist"
            )

    return result


def _collect_allowed_arabic_for_explanation(
    evidence_packet: dict[str, Any],
) -> set[str]:
    allowed: set[str] = set()

    selected_word = evidence_packet.get("selected_word", {})
    root = evidence_packet.get("root", {})
    pattern = evidence_packet.get("pattern", {})

    if isinstance(selected_word, dict):
        add_arabic_value(allowed, selected_word.get("arabic"))

    if isinstance(root, dict):
        add_arabic_value(allowed, root.get("arabic"))
        add_arabic_value(allowed, root.get("letters"))

    if isinstance(pattern, dict):
        add_arabic_value(allowed, pattern.get("arabic"))

    for card in evidence_packet.get("same_pattern_cards", []):
        if isinstance(card, dict):
            add_arabic_value(allowed, card.get("arabic"))

    return {item for item in allowed if item}