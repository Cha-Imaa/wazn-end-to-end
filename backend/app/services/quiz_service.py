import random
from typing import Any

from app.data_loader import kb


MAX_CHOICES = 4
DEFAULT_QUIZ_LIMIT = 5
DISTRACTOR_LIMIT = MAX_CHOICES - 1


def question_seed(
    selected_word: dict[str, Any],
    template: dict[str, Any],
) -> str:
    """Stable per-question seed, so a given word always yields the same quiz."""
    return f"{selected_word.get('id', '')}_{template.get('id', '')}"


def sample_distractors(
    pool: list[str],
    correct_answer: str,
    seed: str,
    limit: int = DISTRACTOR_LIMIT,
) -> list[str]:
    candidates: list[str] = []

    for value in pool:
        if not value or value == correct_answer or value in candidates:
            continue

        candidates.append(value)

    if len(candidates) <= limit:
        return candidates

    return random.Random(seed).sample(candidates, limit)


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

    if category == "root_meaning":
        return build_root_meaning_question(
            template=template,
            selected_word=selected_word,
            root=root,
        )

    if category == "transliteration":
        return build_transliteration_question(
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
        correct_answer=correct_answer,
        seed=question_seed(selected_word, template),
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
        correct_answer=correct_answer,
        seed=question_seed(selected_word, template),
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
        correct_answer=correct_answer,
        seed=question_seed(selected_word, template),
    )

    return build_multiple_choice_question(
        template=template,
        selected_word=selected_word,
        correct_answer=correct_answer,
        distractors=distractors,
    )


def build_root_meaning_question(
    template: dict[str, Any],
    selected_word: dict[str, Any],
    root: dict[str, Any],
) -> dict[str, Any] | None:
    correct_answer = root.get("meaning")

    if not correct_answer:
        return None

    distractors = get_root_meaning_distractors(
        correct_root_id=root["id"],
        correct_answer=correct_answer,
        seed=question_seed(selected_word, template),
    )

    return build_multiple_choice_question(
        template=template,
        selected_word=selected_word,
        correct_answer=correct_answer,
        distractors=distractors,
    )


def build_transliteration_question(
    template: dict[str, Any],
    selected_word: dict[str, Any],
) -> dict[str, Any] | None:
    correct_answer = selected_word.get("transliteration")

    if not correct_answer:
        return None

    distractors = get_transliteration_distractors(
        selected_word_id=selected_word["id"],
        correct_answer=correct_answer,
        seed=question_seed(selected_word, template),
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
) -> dict[str, Any] | None:
    selected_word_id = selected_word["id"]
    template_id = template["id"]

    choices, answer_id = build_choices(
        correct_answer=correct_answer,
        distractors=distractors,
        seed=question_seed(selected_word, template),
    )

    # De-duplication can leave fewer than four choices; a short question is
    # dropped like any other unbuildable one rather than served malformed.
    if len(choices) < MAX_CHOICES:
        return None

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
        "answer_id": answer_id,
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
    correct_answer: str,
    seed: str,
) -> list[str]:
    pool = [
        word.get("short_meaning") or word.get("meaning")
        for word in kb.words_by_root.get(root_id, [])
        if word.get("id") != selected_word_id
    ]

    return sample_distractors(
        pool=pool,
        correct_answer=correct_answer,
        seed=seed,
    )


def get_root_distractors(
    correct_root_id: str,
    correct_answer: str,
    seed: str,
) -> list[str]:
    pool = [
        root.get("arabic")
        for root_id, root in kb.roots.items()
        if root_id != correct_root_id
    ]

    return sample_distractors(
        pool=pool,
        correct_answer=correct_answer,
        seed=seed,
    )


def get_pattern_distractors(
    correct_pattern_id: str,
    correct_answer: str,
    seed: str,
) -> list[str]:
    pool = [
        pattern.get("arabic")
        for pattern_id, pattern in kb.patterns.items()
        if pattern_id != correct_pattern_id
    ]

    return sample_distractors(
        pool=pool,
        correct_answer=correct_answer,
        seed=seed,
    )


def get_root_meaning_distractors(
    correct_root_id: str,
    correct_answer: str,
    seed: str,
) -> list[str]:
    pool = [
        root.get("meaning")
        for root_id, root in kb.roots.items()
        if root_id != correct_root_id
    ]

    return sample_distractors(
        pool=pool,
        correct_answer=correct_answer,
        seed=seed,
    )


def get_transliteration_distractors(
    selected_word_id: str,
    correct_answer: str,
    seed: str,
) -> list[str]:
    pool = [
        word.get("transliteration")
        for word in kb.words.values()
        if word.get("id") != selected_word_id
    ]

    return sample_distractors(
        pool=pool,
        correct_answer=correct_answer,
        seed=seed,
    )


def build_choices(
    correct_answer: str,
    distractors: list[str],
    seed: str,
) -> tuple[list[dict[str, str]], str]:
    choice_ids = ["a", "b", "c", "d"]
    unique_choices = [correct_answer]

    for distractor in distractors:
        if distractor not in unique_choices:
            unique_choices.append(distractor)

        if len(unique_choices) == MAX_CHOICES:
            break

    random.Random(f"{seed}_order").shuffle(unique_choices)

    choices: list[dict[str, str]] = []
    answer_id = choice_ids[0]

    for index, choice_text in enumerate(unique_choices):
        choice_id = choice_ids[index]

        if choice_text == correct_answer:
            answer_id = choice_id

        choices.append(
            {
                "id": choice_id,
                "text": choice_text,
            }
        )

    return choices, answer_id