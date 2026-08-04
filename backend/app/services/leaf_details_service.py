from typing import Any

from app.data_loader import kb
import random


def build_leaf_details_for_tree(
    tree: dict[str, Any],
    root: dict[str, Any],
) -> dict[str, Any]:
    details: dict[str, Any] = {}

    for leaf in tree.get("leaves", []):
        word_id = leaf["id"]
        word = kb.get_word(word_id)

        if not word:
            continue

        details[word_id] = build_single_leaf_detail(
            word=word,
            root=root,
        )

    return details


def build_single_leaf_detail(
    word: dict[str, Any],
    root: dict[str, Any],
) -> dict[str, Any]:
    pattern_id = word.get("pattern_id")
    pattern = kb.get_pattern(pattern_id) if pattern_id else None

    same_pattern_words = get_same_pattern_words(
        pattern_id=pattern_id,
        selected_word_id=word["id"],
    )

    explanation = build_template_explanation(
        word=word,
        root=root,
        pattern=pattern,
    )

    pattern_explanation = build_pattern_explanation(
        word=word,
        pattern=pattern,
    )

    same_pattern_explanation = build_same_pattern_explanation(
        word=word,
        pattern=pattern,
        same_pattern_words=same_pattern_words,
    )

    tutor_note = build_tutor_note(
        word=word,
        root=root,
        pattern=pattern,
    )

    return {
        "word": {
            "id": word.get("id"),
            "arabic": word.get("arabic"),
            "normalized": word.get("normalized"),
            "transliteration": word.get("transliteration"),
            "meaning": word.get("meaning"),
            "short_meaning": word.get("short_meaning", word.get("meaning")),
            "word_type": word.get("word_type"),
            "pos": word.get("pos"),
            "level": word.get("level"),
        },
        "root": {
            "id": root.get("id"),
            "arabic": root.get("arabic"),
            "transliteration": root.get("transliteration"),
            "meaning": root.get("meaning"),
            "description": root.get("description"),
        },
        "pattern": pattern,
        "breakdown": word.get("breakdown"),
        "explanation": explanation,
        "pattern_explanation": pattern_explanation,
        "same_pattern_words": same_pattern_words,
        "same_pattern_explanation": same_pattern_explanation,
        "tutor_note": tutor_note,
    }


def get_same_pattern_words(
    pattern_id: str | None,
    selected_word_id: str,
    limit: int = 3,
) -> list[dict[str, Any]]:
    if not pattern_id:
        return []

    candidates = [
        word
        for word in kb.words_by_pattern.get(pattern_id, [])
        if word.get("id") != selected_word_id
    ]

    if not candidates:
        return []

    # Seeded per word, the way quiz_service seeds its own sampling. Unseeded,
    # this re-drew the related cards on every request: two identical searches
    # showed different words, `same_pattern_explanation` named different
    # examples, and prompt-lab runs of one word were not reproducible. It also
    # broke review — cached insights would describe a card set that a later
    # /api/analyze no longer sends.
    sampled_words = random.Random(f"{pattern_id}_{selected_word_id}").sample(
        candidates,
        k=min(limit, len(candidates)),
    )

    results = []

    for word in sampled_words:
        results.append(
            {
                "id": word.get("id"),
                "arabic": word.get("arabic"),
                "transliteration": word.get("transliteration"),
                "meaning": word.get("meaning"),
                "short_meaning": word.get("short_meaning", word.get("meaning")),
            }
        )

    return results


def build_template_explanation(
    word: dict[str, Any],
    root: dict[str, Any],
    pattern: dict[str, Any] | None,
) -> str:
    word_arabic = word.get("arabic", "")
    word_meaning = word.get("meaning", "")
    root_arabic = root.get("arabic", "")
    root_meaning = root.get("meaning", "")

    if pattern:
        pattern_arabic = pattern.get("arabic", "")
        pattern_effect = (
            pattern.get("meaning_effect")
            or pattern.get("short_explanation", "")
        )

        return (
            f"The root {root_arabic} carries the idea of {root_meaning}. "
            f"The pattern {pattern_arabic} {pattern_effect}. "
            f"{word_arabic} therefore means “{word_meaning}”."
        )

    return (
        f"The root {root_arabic} carries the idea of {root_meaning}. "
        f"{word_arabic} means “{word_meaning}”."
    )


def build_pattern_explanation(
    word: dict[str, Any],
    pattern: dict[str, Any] | None,
) -> str:
    word_arabic = word.get("arabic", "")
    word_meaning = word.get("meaning", "")

    if not pattern:
        return (
            f"No pattern explanation is available yet for {word_arabic}. "
            f"The known meaning from the knowledge base is {word_meaning}."
        )

    pattern_arabic = pattern.get("arabic", "")
    pattern_name = pattern.get("name") or pattern.get("id") or "this pattern"
    pattern_effect = (
        pattern.get("meaning_effect")
        or pattern.get("short_explanation")
        or pattern.get("description")
        or "adds a specific meaning to the root"
    )

    return (
        f"{word_arabic} uses the pattern {pattern_arabic} "
        f"({pattern_name}). This pattern {pattern_effect}."
    )


def build_same_pattern_explanation(
    word: dict[str, Any],
    pattern: dict[str, Any] | None,
    same_pattern_words: list[dict[str, Any]],
) -> str:
    word_arabic = word.get("arabic", "")

    if not pattern:
        return (
            f"No same-pattern explanation is available yet for {word_arabic} "
            f"because no pattern is linked to this word."
        )

    pattern_arabic = pattern.get("arabic", "")
    pattern_label = pattern_arabic or pattern.get("name") or pattern.get("id")

    if not same_pattern_words:
        return (
            f"{word_arabic} follows the pattern {pattern_label}. "
            f"No additional same-pattern examples are currently available."
        )

    example_words = [
        same_pattern_word.get("arabic", "")
        for same_pattern_word in same_pattern_words
        if same_pattern_word.get("arabic")
    ]

    if not example_words:
        return (
            f"{word_arabic} follows the pattern {pattern_label}. "
            f"Other same-pattern examples are available in the knowledge base."
        )

    return (
        f"{word_arabic} follows the pattern {pattern_label}. "
        f"Words such as {', '.join(example_words)} use the same pattern, "
        f"so learners can compare how one pattern works across different roots."
    )


def build_tutor_note(
    word: dict[str, Any],
    root: dict[str, Any],
    pattern: dict[str, Any] | None,
) -> str:
    word_arabic = word.get("arabic", "")
    word_meaning = word.get("meaning", "")
    root_arabic = root.get("arabic", "")
    root_meaning = root.get("meaning", "")

    if pattern:
        pattern_arabic = pattern.get("arabic", "")

        return (
            f"Beginner hint: first notice the root {root_arabic}, "
            f"which points to {root_meaning}. Then notice the pattern "
            f"{pattern_arabic}. Together, they help you understand why "
            f"{word_arabic} means {word_meaning}."
        )

    return (
        f"Beginner hint: connect {word_arabic} back to the root "
        f"{root_arabic}, which points to {root_meaning}. "
        f"This helps you remember the meaning: {word_meaning}."
    )