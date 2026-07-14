from typing import Any

from app.core.normalizer import normalize_arabic
from app.data_loader import kb


def run_lookup_module(query: str) -> dict[str, Any]:
    normalized_query = normalize_arabic(query)

    lookup_trace: dict[str, Any] = {
        "input_received": bool(query),
        "normalized_query": normalized_query,
        "alias_match": False,
        "normalized_word_match": False,
        "selected_word_found": False,
        "root_found": False,
        "pattern_found": False,
        "family_word_count": 0,
        "same_pattern_word_count": 0,
    }

    if not normalized_query:
        return {
            "found": False,
            "query": query,
            "normalized_query": normalized_query,
            "reason": "empty_query",
            "message": "Empty query.",
            "pipeline_trace": {
                "lookup": lookup_trace,
            },
        }

    selected_word_id = find_word_id(
        raw_query=query,
        normalized_query=normalized_query,
        lookup_trace=lookup_trace,
    )

    if not selected_word_id:
        return {
            "found": False,
            "query": query,
            "normalized_query": normalized_query,
            "reason": "word_not_found",
            "message": "Word not found in the knowledge base.",
            "pipeline_trace": {
                "lookup": lookup_trace,
            },
        }

    selected_word = kb.get_word(selected_word_id)

    if not selected_word:
        lookup_trace["selected_word_id"] = selected_word_id

        return {
            "found": False,
            "query": query,
            "normalized_query": normalized_query,
            "selected_word_id": selected_word_id,
            "reason": "missing_word_for_alias",
            "message": "Alias points to a missing word ID.",
            "pipeline_trace": {
                "lookup": lookup_trace,
            },
        }

    lookup_trace["selected_word_found"] = True

    root_id = selected_word.get("root_id")
    root = kb.get_root(root_id) if root_id else None

    if not root:
        lookup_trace["selected_word_id"] = selected_word_id
        lookup_trace["root_id"] = root_id

        return {
            "found": False,
            "query": query,
            "normalized_query": normalized_query,
            "selected_word_id": selected_word_id,
            "selected_word": selected_word,
            "reason": "missing_root_for_word",
            "message": "Selected word points to a missing root.",
            "pipeline_trace": {
                "lookup": lookup_trace,
            },
        }

    lookup_trace["root_found"] = True

    pattern_id = selected_word.get("pattern_id")
    pattern = get_pattern(pattern_id)

    if pattern:
        lookup_trace["pattern_found"] = True

    family_words = get_family_words(root_id=root_id)
    same_pattern_words = get_same_pattern_words(pattern_id=pattern_id)

    lookup_trace.update(
        {
            "selected_word_id": selected_word_id,
            "root_id": root_id,
            "pattern_id": pattern_id,
            "family_word_count": len(family_words),
            "same_pattern_word_count": len(same_pattern_words),
        }
    )

    return {
        "found": True,
        "query": query,
        "normalized_query": normalized_query,
        "selected_word_id": selected_word_id,
        "selected_word": selected_word,
        "root": root,
        "pattern": pattern,
        "family_words": family_words,
        "same_pattern_words": same_pattern_words,
        "pipeline_trace": {
            "lookup": lookup_trace,
        },
    }


def find_word_id(
    raw_query: str,
    normalized_query: str,
    lookup_trace: dict[str, Any],
) -> str | None:
    raw_alias_match = kb.aliases.get(raw_query)

    if raw_alias_match:
        lookup_trace["alias_match"] = True
        lookup_trace["alias_match_type"] = "raw_query"
        return raw_alias_match

    normalized_alias_match = kb.aliases.get(normalized_query)

    if normalized_alias_match:
        lookup_trace["alias_match"] = True
        lookup_trace["alias_match_type"] = "normalized_query"
        return normalized_alias_match

    normalized_word_match = find_by_word_normalized(normalized_query)

    if normalized_word_match:
        lookup_trace["normalized_word_match"] = True
        return normalized_word_match

    return None


def find_by_word_normalized(normalized_query: str) -> str | None:
    for word_id, word in kb.words.items():
        if word.get("normalized") == normalized_query:
            return word_id

    return None


def get_pattern(pattern_id: str | None) -> dict[str, Any] | None:
    if not pattern_id:
        return None

    patterns = getattr(kb, "patterns", {})

    if not isinstance(patterns, dict):
        return None

    return patterns.get(pattern_id)


def get_family_words(root_id: str | None) -> list[dict[str, Any]]:
    if not root_id:
        return []

    family_words: list[dict[str, Any]] = []

    for word in kb.words.values():
        if word.get("root_id") == root_id:
            family_words.append(word)

    return family_words


def get_same_pattern_words(pattern_id: str | None) -> list[dict[str, Any]]:
    if not pattern_id:
        return []

    same_pattern_words: list[dict[str, Any]] = []

    for word in kb.words.values():
        if word.get("pattern_id") == pattern_id:
            same_pattern_words.append(word)

    return same_pattern_words