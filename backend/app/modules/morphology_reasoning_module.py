from typing import Any


def run_morphology_reasoning_module(
    selected_word: dict[str, Any],
    root: dict[str, Any],
    pattern: dict[str, Any] | None = None,
) -> dict[str, Any]:
    segments = get_breakdown_segments(selected_word)

    root_letters = extract_letters_by_role(
        segments=segments,
        role="root",
    )

    pattern_letters = extract_letters_by_role(
        segments=segments,
        role="pattern",
    )

    reasoning_summary = build_reasoning_summary(
        selected_word=selected_word,
        root=root,
        pattern=pattern,
        root_letters=root_letters,
        pattern_letters=pattern_letters,
    )

    morphology_trace = {
        "selected_word_id": selected_word.get("id"),
        "root_id": selected_word.get("root_id"),
        "pattern_id": selected_word.get("pattern_id"),
        "has_breakdown": bool(selected_word.get("breakdown")),
        "segment_count": len(segments),
        "root_letter_count": len(root_letters),
        "pattern_letter_count": len(pattern_letters),
        "root_letters_detected": root_letters,
        "pattern_letters_detected": pattern_letters,
    }

    return {
        "root_letters": root_letters,
        "pattern_letters": pattern_letters,
        "reasoning_summary": reasoning_summary,
        "pipeline_trace": {
            "morphology": morphology_trace,
        },
    }


def build_morphology_output(morphology_result: dict[str, Any]) -> dict[str, Any]:
    """
    The module's three learner-facing outputs, without the trace.

    Every consumer wants the same three keys and nothing else: /api/analyze
    surfaces them under a top-level `morphology`, and the agent evidence state
    carries them under the same name. Defined once here so the shape cannot
    drift between the request path and the prompt lab.
    """
    return {
        "root_letters": morphology_result.get("root_letters", []),
        "pattern_letters": morphology_result.get("pattern_letters", []),
        "reasoning_summary": morphology_result.get("reasoning_summary", ""),
    }


def empty_morphology_output() -> dict[str, Any]:
    """The same three keys, for a word that did not resolve — never `None`."""
    return build_morphology_output({})


def get_breakdown_segments(selected_word: dict[str, Any]) -> list[dict[str, Any]]:
    breakdown = selected_word.get("breakdown", {})

    if not isinstance(breakdown, dict):
        return []

    segments = breakdown.get("segments", [])

    if not isinstance(segments, list):
        return []

    valid_segments: list[dict[str, Any]] = []

    for segment in segments:
        if isinstance(segment, dict):
            valid_segments.append(segment)

    return valid_segments


def extract_letters_by_role(
    segments: list[dict[str, Any]],
    role: str,
) -> list[str]:
    letters: list[str] = []

    for segment in segments:
        segment_role = segment.get("type") or segment.get("role")
        segment_text = segment.get("text") or segment.get("letter") or ""

        if segment_role != role:
            continue

        if not isinstance(segment_text, str):
            continue

        cleaned_text = segment_text.strip()

        if cleaned_text:
            letters.append(cleaned_text)

    return letters


def build_reasoning_summary(
    selected_word: dict[str, Any],
    root: dict[str, Any],
    pattern: dict[str, Any] | None,
    root_letters: list[str],
    pattern_letters: list[str],
) -> str:
    word_arabic = selected_word.get("arabic", "This word")
    root_arabic = root.get("arabic", "its root")
    root_meaning = root.get("meaning", "the root meaning")

    pattern_name = None

    if pattern:
        pattern_name = (
            pattern.get("name")
            or pattern.get("arabic")
            or pattern.get("id")
        )

    if pattern_name:
        return (
            f"{word_arabic} is connected to the root {root_arabic}, "
            f"which carries the core meaning of {root_meaning}. "
            f"The root letters are {format_letter_list(root_letters)}, "
            f"and the pattern letters are {format_letter_list(pattern_letters)}. "
            f"Together, the root and pattern form the word through the pattern {pattern_name}."
        )

    return (
        f"{word_arabic} is connected to the root {root_arabic}, "
        f"which carries the core meaning of {root_meaning}. "
        f"The root letters are {format_letter_list(root_letters)}, "
        f"and the pattern letters are {format_letter_list(pattern_letters)}."
    )


def format_letter_list(letters: list[str]) -> str:
    if not letters:
        return "not explicitly marked in the current breakdown"

    return " + ".join(letters)