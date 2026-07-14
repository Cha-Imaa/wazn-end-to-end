from typing import Any

from app.data_loader import kb


MAX_TREE_LEAVES = 8


def build_tree_response(
    selected_word: dict[str, Any],
    root: dict[str, Any],
) -> dict[str, Any]:
    root_id = root["id"]
    selected_word_id = selected_word["id"]

    root_word_ids = root.get("word_ids", [])

    leaf_word_ids = _choose_leaf_word_ids(
        root_word_ids=root_word_ids,
        selected_word_id=selected_word_id,
    )

    leaves = []

    for word_id in leaf_word_ids:
        word = kb.get_word(word_id)

        if not word:
            continue

        leaves.append(
            {
                "id": word["id"],
                "arabic": word.get("arabic"),
                "normalized": word.get("normalized"),
                "transliteration": word.get("transliteration"),
                "meaning": word.get("meaning"),
                "short_meaning": word.get("short_meaning", word.get("meaning")),
                "is_selected": word["id"] == selected_word_id,
            }
        )

    return {
        "trunk": {
            "root_id": root_id,
            "arabic": root.get("arabic"),
            "transliteration": root.get("transliteration"),
            "meaning": root.get("meaning"),
            "description": root.get("description"),
        },
        "leaves": leaves,
    }


def _choose_leaf_word_ids(
    root_word_ids: list[str],
    selected_word_id: str,
) -> list[str]:
    cleaned_ids = []

    for word_id in root_word_ids:
        if word_id not in cleaned_ids:
            cleaned_ids.append(word_id)

    if selected_word_id not in cleaned_ids:
        cleaned_ids.insert(0, selected_word_id)

    if len(cleaned_ids) <= MAX_TREE_LEAVES:
        return cleaned_ids

    selected_plus_others = [selected_word_id]

    for word_id in cleaned_ids:
        if word_id != selected_word_id:
            selected_plus_others.append(word_id)

        if len(selected_plus_others) == MAX_TREE_LEAVES:
            break

    return selected_plus_others