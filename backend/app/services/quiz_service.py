from typing import Any

from app.data_loader import kb


MAX_CHOICES = 4
DEFAULT_QUIZ_LIMIT = 3


def build_quiz_for_word(
    selected_word: dict[str, Any],
    root: dict[str, Any],
    limit: int = DEFAULT_QUIZ_LIMIT,
) -> list[dict[str, Any]]:
    quiz: list[dict[str, Any]] = []

    for template in kb.quiz_templates.values():
        if not template.get("enabled", True):
            continue

        if not template.get("demo_safe", True):
            continue

        question = build_question_from_template(
            template=template,
            selected_word=selected_word,
            root=root,
        )

        if question:
            quiz.append(question)

        if len(quiz) == limit:
            break

    return quiz


def build_question_from_template(
    template: dict[str, Any],
    selected_word: dict[str, Any],
    root: dict[str, Any],
) -> dict[str, Any] | None:
    category = template.get("category")

    if category == "meaning":
        return build_meaning_question(
            template=template,
            selected_word=selected_word,
            root=root,
        )

    if category == "root":
        return build_root_question(
            template=template,
            selected_word=selected_word,
            root=root,
        )

    if category == "pattern":
        return build_pattern_question(
            template=template,
            selected_word=selected_word,
        )

    return None


def build_meaning_question(
    template: dict[str, Any],
    selected_word: dict[str, Any],
    root: dict[str, Any],
) -> dict[str, Any] | None:
    selected_word_id = selected_word["id"]
    correct_answer = selected_word.get("short_meaning") or selected_word.get("meaning")

    if not correct_answer:
        return None

    distractors = get_meaning_distractors(
        selected_word_id=selected_word_id,
        root_id=root["id"],
    )

    return build_multiple_choice_question(
        template=template,
        selected_word=selected_word,
        correct_answer=correct_answer,
        distractors=distractors,
    )


def build_root_question(
    template: dict[str, Any],
    selected_word: dict[str, Any],
    root: dict[str, Any],
) -> dict[str, Any] | None:
    correct_answer = root.get("arabic")

    if not correct_answer:
        return None

    distractors = get_root_distractors(
        correct_root_id=root["id"],
    )

    return build_multiple_choice_question(
        template=template,
        selected_word=selected_word,
        correct_answer=correct_answer,
        distractors=distractors,
    )


def build_pattern_question(
    template: dict[str, Any],
    selected_word: dict[str, Any],
) -> dict[str, Any] | None:
    pattern_id = selected_word.get("pattern_id")

    if not pattern_id:
        return None

    pattern = kb.get_pattern(pattern_id)

    if not pattern:
        return None

    correct_answer = pattern.get("arabic")

    if not correct_answer:
        return None

    distractors = get_pattern_distractors(
        correct_pattern_id=pattern_id,
    )

    return build_multiple_choice_question(
        template=template,
        selected_word=selected_word,
        correct_answer=correct_answer,
        distractors=distractors,
    )


def build_multiple_choice_question(
    template: dict[str, Any],
    selected_word: dict[str, Any],
    correct_answer: str,
    distractors: list[str],
) -> dict[str, Any]:
    selected_word_id = selected_word["id"]
    template_id = template["id"]

    choices = build_choices(
        correct_answer=correct_answer,
        distractors=distractors,
    )

    return {
        "id": f"{selected_word_id}_{template_id}",
        "type": template.get("type", "multiple_choice"),
        "category": template.get("category"),
        "question": fill_template(
            template_text=template.get("question_template", ""),
            selected_word=selected_word,
            correct_answer=correct_answer,
        ),
        "choices": choices,
        "answer_id": "a",
        "explanation": fill_template(
            template_text=template.get("explanation_template", ""),
            selected_word=selected_word,
            correct_answer=correct_answer,
        ),
        "source": "template",
    }


def fill_template(
    template_text: str,
    selected_word: dict[str, Any],
    correct_answer: str,
) -> str:
    return template_text.format(
        word_arabic=selected_word.get("arabic", ""),
        word_transliteration=selected_word.get("transliteration", ""),
        word_meaning=selected_word.get("meaning", ""),
        correct_answer=correct_answer,
    )


def get_meaning_distractors(
    selected_word_id: str,
    root_id: str,
    limit: int = 3,
) -> list[str]:
    distractors: list[str] = []

    root_words = kb.words_by_root.get(root_id, [])

    for word in root_words:
        if word.get("id") == selected_word_id:
            continue

        meaning = word.get("short_meaning") or word.get("meaning")

        if meaning and meaning not in distractors:
            distractors.append(meaning)

        if len(distractors) == limit:
            break

    return distractors


def get_root_distractors(
    correct_root_id: str,
    limit: int = 3,
) -> list[str]:
    distractors: list[str] = []

    for root_id, root in kb.roots.items():
        if root_id == correct_root_id:
            continue

        root_arabic = root.get("arabic")

        if root_arabic and root_arabic not in distractors:
            distractors.append(root_arabic)

        if len(distractors) == limit:
            break

    fallback_roots = ["ق ر أ", "د ر س", "ع ل م"]

    for fallback_root in fallback_roots:
        if len(distractors) == limit:
            break

        if fallback_root not in distractors:
            distractors.append(fallback_root)

    return distractors


def get_pattern_distractors(
    correct_pattern_id: str,
    limit: int = 3,
) -> list[str]:
    distractors: list[str] = []

    for pattern_id, pattern in kb.patterns.items():
        if pattern_id == correct_pattern_id:
            continue

        pattern_arabic = pattern.get("arabic")

        if pattern_arabic and pattern_arabic not in distractors:
            distractors.append(pattern_arabic)

        if len(distractors) == limit:
            break

    return distractors


def build_choices(
    correct_answer: str,
    distractors: list[str],
) -> list[dict[str, str]]:
    choice_ids = ["a", "b", "c", "d"]
    unique_choices = [correct_answer]

    for distractor in distractors:
        if distractor not in unique_choices:
            unique_choices.append(distractor)

        if len(unique_choices) == MAX_CHOICES:
            break

    choices: list[dict[str, str]] = []

    for index, choice_text in enumerate(unique_choices):
        choices.append(
            {
                "id": choice_ids[index],
                "text": choice_text,
            }
        )

    return choices