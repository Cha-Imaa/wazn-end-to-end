# app/prompt_lab/shared/validators/quiz_validator.py

# 1. Output is valid JSON
# 2. Output is a JSON object
# 3. Output has exactly one top-level key:
#    - quiz
# 4. quiz is a list
# 5. quiz contains exactly 5 questions
# 6. Each question has exactly these keys:
#    - id
#    - type
#    - question
#    - choices
#    - answer_id
#    - correct_feedback
#    - wrong_feedback
#    - choice_feedback
#    - explanation
# 7. Question ids are:
#    - q1
#    - q2
#    - q3
#    - q4
#    - q5
# 8. type must be one of:
#    - root_meaning
#    - leaf_meaning
#    - meaning_to_leaf
#    - pattern_recognition
#    - pattern_meaning_effect
#    - pattern_application
# 9. The 5 question types must be distinct
# 10. choices must contain exactly 4 items
# 11. choice ids must be exactly:
#    - a
#    - b
#    - c
#    - d
# 12. answer_id must be one of:
#    - a
#    - b
#    - c
#    - d
# 13. answer_id must match one of the choice ids
# 14. choice_feedback must contain exactly:
#    - a
#    - b
#    - c
#    - d
# 15. All required text fields must be non-empty strings:
#    - question
#    - correct_feedback
#    - wrong_feedback
#    - explanation
#    - each choice.text
#    - each choice_feedback value
# 16. Correct answer position should not repeat more than twice.
# 17. No invented Arabic:
#    Arabic text in question, choices, feedback, or explanation must come from:
#    - root.arabic
#    - leaf.arabic
#    - pattern.arabic
# 18. For meaning questions:
#    choice texts should come from leaf meanings or root meaning, depending on question type
# 19. For Arabic word choices:
#    choice texts must come from real leaf words in the input
# 20. For pattern choices:
#    choice texts must come from real patterns in the input
# 21. For pattern_application:
#    every choice must be a real leaf word from the input
# 22. wrong_feedback should start with:
#    "Not quite"

from typing import Any

from app.prompt_lab.shared.validators.common_validator import (
    ValidationResult,
    add_arabic_value,
    check_no_unknown_arabic,
    get_llm_input,
    normalize_arabic,
    parse_json_output,
    require_exact_keys,
    require_non_empty_string,
)

REQUIRED_TOP_LEVEL_KEYS = {"quiz"}

REQUIRED_QUESTION_KEYS = {
    "id",
    "type",
    "question",
    "choices",
    "answer_id",
    "correct_feedback",
    "wrong_feedback",
    "choice_feedback",
    "explanation",
}

VALID_QUESTION_TYPES = {
    "root_meaning",
    "leaf_meaning",
    "meaning_to_leaf",
    "pattern_recognition",
    "pattern_meaning_effect",
    "pattern_application",
}

EXPECTED_QUESTION_IDS = ["q1", "q2", "q3", "q4", "q5"]

CHOICE_IDS = {"a", "b", "c", "d"}


def validate_quiz_output(
    evidence_packet: dict[str, Any],
    raw_output: str,
) -> ValidationResult:
    """
    Deterministic validator for Quiz Agent raw output.

    This validates:
    1. valid JSON
    2. JSON object
    3. top-level quiz key only
    4. exactly 5 questions
    5. exact question keys
    6. q1-q5 ids
    7. valid distinct question types
    8. exactly 4 choices with a/b/c/d
    9. valid answer_id
    10. choice_feedback keys a/b/c/d
    11. non-empty text fields
    12. answer position not repeated more than twice
    13. no invented Arabic
    14. type-specific grounded choices
    15. wrong_feedback starts with "Not quite"
    """

    result = parse_json_output(raw_output)

    if not result.passed or result.parsed_json is None:
        return result

    output = result.parsed_json

    require_exact_keys(
        actual=output,
        expected_keys=REQUIRED_TOP_LEVEL_KEYS,
        label="quiz_output",
        result=result,
    )

    if not result.passed:
        return result

    quiz = output.get("quiz")

    if not isinstance(quiz, list):
        result.add("quiz: must be a list")
        return result

    if len(quiz) != 5:
        result.add(f"quiz: must contain exactly 5 questions, got {len(quiz)}")
        return result

    evidence = get_llm_input(evidence_packet)
    evidence_sets = _collect_quiz_evidence_sets(evidence)

    seen_types: list[str] = []
    answer_positions: list[str] = []

    for index, question in enumerate(quiz):
        label = f"quiz[{index}]"

        if not isinstance(question, dict):
            result.add(f"{label}: must be an object")
            continue

        _validate_question_shape(question, index, label, result)

        if not result.passed:
            continue

        question_type = question["type"]
        seen_types.append(question_type)

        answer_positions.append(question["answer_id"])

        _validate_question_text_fields(question, label, result)
        _validate_choices(question, label, result)
        _validate_choice_feedback(question, label, result)
        _validate_wrong_feedback(question, label, result)
        _validate_no_invented_arabic(
            question,
            label,
            evidence_sets["allowed_arabic"],
            result,
        )
        _validate_type_specific_grounding(
            question,
            label,
            evidence_sets,
            result,
        )

    _validate_distinct_question_types(seen_types, result)
    _validate_answer_position_distribution(answer_positions, result)

    return result


def _validate_question_shape(
    question: dict[str, Any],
    index: int,
    label: str,
    result: ValidationResult,
) -> None:
    require_exact_keys(
        actual=question,
        expected_keys=REQUIRED_QUESTION_KEYS,
        label=label,
        result=result,
    )

    expected_id = EXPECTED_QUESTION_IDS[index]

    if question.get("id") != expected_id:
        result.add(f"{label}.id: expected '{expected_id}', got '{question.get('id')}'")

    question_type = question.get("type")

    if question_type not in VALID_QUESTION_TYPES:
        result.add(f"{label}.type: invalid question type '{question_type}'")


def _validate_question_text_fields(
    question: dict[str, Any],
    label: str,
    result: ValidationResult,
) -> None:
    for field_name in [
        "question",
        "correct_feedback",
        "wrong_feedback",
        "explanation",
    ]:
        require_non_empty_string(
            question.get(field_name),
            f"{label}.{field_name}",
            result,
        )


def _validate_choices(
    question: dict[str, Any],
    label: str,
    result: ValidationResult,
) -> None:
    choices = question.get("choices")

    if not isinstance(choices, list):
        result.add(f"{label}.choices: must be a list")
        return

    if len(choices) != 4:
        result.add(f"{label}.choices: must contain exactly 4 choices")
        return

    actual_choice_ids = set()

    for choice_index, choice in enumerate(choices):
        choice_label = f"{label}.choices[{choice_index}]"

        if not isinstance(choice, dict):
            result.add(f"{choice_label}: must be an object")
            continue

        require_exact_keys(
            actual=choice,
            expected_keys={"id", "text"},
            label=choice_label,
            result=result,
        )

        choice_id = choice.get("id")

        if isinstance(choice_id, str):
            actual_choice_ids.add(choice_id)

        require_non_empty_string(choice.get("id"), f"{choice_label}.id", result)
        require_non_empty_string(choice.get("text"), f"{choice_label}.text", result)

    if actual_choice_ids != CHOICE_IDS:
        result.add(
            f"{label}.choices: choice ids must be exactly {sorted(CHOICE_IDS)}, got {sorted(actual_choice_ids)}"
        )

    answer_id = question.get("answer_id")

    if answer_id not in CHOICE_IDS:
        result.add(f"{label}.answer_id: must be one of {sorted(CHOICE_IDS)}")

    if answer_id not in actual_choice_ids:
        result.add(f"{label}.answer_id: must match one of the choice ids")


def _validate_choice_feedback(
    question: dict[str, Any],
    label: str,
    result: ValidationResult,
) -> None:
    choice_feedback = question.get("choice_feedback")

    if not isinstance(choice_feedback, dict):
        result.add(f"{label}.choice_feedback: must be an object")
        return

    actual_keys = set(choice_feedback.keys())

    if actual_keys != CHOICE_IDS:
        result.add(
            f"{label}.choice_feedback: keys must be exactly {sorted(CHOICE_IDS)}, got {sorted(actual_keys)}"
        )

    for choice_id in CHOICE_IDS:
        require_non_empty_string(
            choice_feedback.get(choice_id),
            f"{label}.choice_feedback.{choice_id}",
            result,
        )


def _validate_wrong_feedback(
    question: dict[str, Any],
    label: str,
    result: ValidationResult,
) -> None:
    wrong_feedback = question.get("wrong_feedback")

    if not isinstance(wrong_feedback, str):
        return

    if not wrong_feedback.strip().startswith("Not quite"):
        result.add(f"{label}.wrong_feedback: must start with 'Not quite'")


def _validate_no_invented_arabic(
    question: dict[str, Any],
    label: str,
    allowed_arabic: set[str],
    result: ValidationResult,
) -> None:
    for field_name in [
        "question",
        "correct_feedback",
        "wrong_feedback",
        "explanation",
    ]:
        check_no_unknown_arabic(
            question.get(field_name, ""),
            allowed_arabic,
            f"{label}.{field_name}",
            result,
        )

    choices = question.get("choices", [])

    if isinstance(choices, list):
        for choice_index, choice in enumerate(choices):
            if isinstance(choice, dict):
                check_no_unknown_arabic(
                    choice.get("text", ""),
                    allowed_arabic,
                    f"{label}.choices[{choice_index}].text",
                    result,
                )

    choice_feedback = question.get("choice_feedback", {})

    if isinstance(choice_feedback, dict):
        for choice_id, feedback in choice_feedback.items():
            check_no_unknown_arabic(
                feedback,
                allowed_arabic,
                f"{label}.choice_feedback.{choice_id}",
                result,
            )


def _comparison_key(text: str) -> str:
    """Tashkeel-, spacing-, and case-insensitive form for grounding comparison."""
    return normalize_arabic(text).replace(" ", "").casefold()


def _is_grounded_in(text: str, evidence_set: set[str]) -> bool:
    """
    Membership check insensitive to tashkeel, spacing, and (English) case.

    §1.4 requires stripping tashkeel before comparison. Without this, a model
    emitting فاعِل where the KB has فَاعِل — the same pattern, one fatha short —
    rejected entire otherwise-valid quizzes (observed live on تجارة). Likewise
    "Often expresses..." vs the evidence's "often expresses..." (observed live
    on نظر) is capitalization, not an ungrounded meaning.
    """
    if text in evidence_set:
        return True

    key = _comparison_key(text)

    return any(key == _comparison_key(item) for item in evidence_set)


def _validate_type_specific_grounding(
    question: dict[str, Any],
    label: str,
    evidence_sets: dict[str, set[str]],
    result: ValidationResult,
) -> None:
    question_type = question.get("type")
    choices = question.get("choices", [])

    if not isinstance(choices, list):
        return

    choice_texts = [
        choice.get("text")
        for choice in choices
        if isinstance(choice, dict) and isinstance(choice.get("text"), str)
    ]

    if question_type == "root_meaning":
        correct_choice_text = _get_correct_choice_text(question)

        if not _is_grounded_in(correct_choice_text, evidence_sets["root_meanings"]):
            result.add(
                f"{label}: root_meaning correct answer must come from root meanings: '{correct_choice_text}'"
            )

    elif question_type == "leaf_meaning":
        for text in choice_texts:
            if not _is_grounded_in(text, evidence_sets["leaf_meanings"]):
                result.add(
                    f"{label}: leaf_meaning choices must come from leaf meanings: '{text}'"
                )

    elif question_type == "meaning_to_leaf":
        for text in choice_texts:
            if not _is_grounded_in(text, evidence_sets["leaf_words"]):
                result.add(
                    f"{label}: meaning_to_leaf choices must be real leaf words: '{text}'"
                )

    elif question_type == "pattern_recognition":
        for text in choice_texts:
            if not _is_grounded_in(text, evidence_sets["patterns"]):
                result.add(
                    f"{label}: pattern_recognition choices must be real patterns: '{text}'"
                )

    elif question_type == "pattern_meaning_effect":
        for text in choice_texts:
            if not _is_grounded_in(text, evidence_sets["pattern_meaning_effects"]):
                result.add(
                    f"{label}: pattern_meaning_effect choices must come from pattern meaning_effect values: '{text}'"
                )

    elif question_type == "pattern_application":
        for text in choice_texts:
            if not _is_grounded_in(text, evidence_sets["leaf_words"]):
                result.add(
                    f"{label}: pattern_application choices must be real leaf words: '{text}'"
                )


def _get_correct_choice_text(question: dict[str, Any]) -> str:
    answer_id = question.get("answer_id")
    choices = question.get("choices", [])

    if not isinstance(answer_id, str) or not isinstance(choices, list):
        return ""

    for choice in choices:
        if not isinstance(choice, dict):
            continue

        if choice.get("id") == answer_id:
            text = choice.get("text")
            return text if isinstance(text, str) else ""

    return ""

def _validate_distinct_question_types(
    seen_types: list[str],
    result: ValidationResult,
) -> None:
    if len(seen_types) != 5:
        return

    if len(set(seen_types)) != 5:
        result.add(f"quiz.types: expected 5 distinct question types, got {seen_types}")


def _validate_answer_position_distribution(
    answer_positions: list[str],
    result: ValidationResult,
) -> None:
    for choice_id in CHOICE_IDS:
        count = answer_positions.count(choice_id)

        if count > 2:
            result.add(
                f"quiz.answer_positions: answer_id '{choice_id}' appears {count} times; maximum allowed is 2"
            )


def _collect_quiz_evidence_sets(
    evidence_packet: dict[str, Any],
) -> dict[str, set[str]]:
    root = evidence_packet.get("root", {})
    leaves = evidence_packet.get("leaves", [])

    root_arabic: set[str] = set()
    root_meanings: set[str] = set()
    leaf_words: set[str] = set()
    leaf_meanings: set[str] = set()
    patterns: set[str] = set()
    pattern_meaning_effects: set[str] = set()

    if isinstance(root, dict):
        add_arabic_value(root_arabic, root.get("arabic"))
        add_arabic_value(root_meanings, root.get("meaning"))

    if isinstance(leaves, list):
        for leaf in leaves:
            if not isinstance(leaf, dict):
                continue

            add_arabic_value(leaf_words, leaf.get("arabic"))
            add_arabic_value(leaf_meanings, leaf.get("meaning"))

            pattern = leaf.get("pattern", {})

            if isinstance(pattern, dict):
                add_arabic_value(patterns, pattern.get("arabic"))
                add_arabic_value(
                    pattern_meaning_effects,
                    pattern.get("meaning_effect"),
                )

    allowed_arabic: set[str] = set()
    allowed_arabic.update(root_arabic)
    allowed_arabic.update(leaf_words)
    allowed_arabic.update(patterns)

    all_meanings: set[str] = set()
    all_meanings.update(root_meanings)
    all_meanings.update(leaf_meanings)
    all_meanings.update(pattern_meaning_effects)

    return {
        "allowed_arabic": allowed_arabic,
        "root_meanings": root_meanings,
        "leaf_words": leaf_words,
        "leaf_meanings": leaf_meanings,
        "patterns": patterns,
        "pattern_meaning_effects": pattern_meaning_effects,
        "all_meanings": all_meanings,
    }