"""Deterministic guardrail stage: real checks over the content /api/analyze serves.

Descends from the stranded `backend/deterministic_guardrail.py` ("Layer 1:
fast, deterministic, non-LLM checks"), which validated prompt-lab agent output
against evidence packets and was imported by nothing. This module keeps its
idea — mechanical grounding and shape checks, cheap and zero-false-negative on
what they cover — but runs it over the pipeline's own outputs, replacing the
four trivially-true predicates `k2_think_service._build_guardrails` used to
emit (§1.7). "All Checks Passed" now means the served content was checked, not
that the lookup returned a dict.

The KB has no schema validation at load time, so these checks are also where a
malformed entry surfaces as a failed guardrail instead of a silently broken
tree.

Grounding reuses `common_validator` — the same Arabic-run extraction and
tashkeel-insensitive comparison the live K2 validators use — so "grounded"
means one thing across the deterministic and live paths.
"""

from typing import Any

from app.data_loader import kb
from app.prompt_lab.shared.validators.common_validator import (
    ValidationResult,
    add_arabic_value,
    check_no_unknown_arabic_keys,
    grounding_keys,
    normalize_arabic,
)


ENGINE_STATUS_DETERMINISTIC = "deterministic"

SUMMARY_PASSED = "All Checks Passed"
SUMMARY_FAILED = "Some Checks Need Review"

# Hamza seats vary with vowel environment (ء أ إ ؤ ئ آ are one letter written
# six ways — §2.2c's substitution findings), so a root-letter comparison must
# fold them: قَرَأَ's breakdown carries أ while the root is spelled ق ر ء.
_HAMZA_FOLD = str.maketrans({"أ": "ء", "إ": "ء", "ؤ": "ء", "ئ": "ء", "آ": "ء"})

_LEAF_PROSE_FIELDS = (
    "explanation",
    "pattern_explanation",
    "same_pattern_explanation",
    "tutor_note",
)

_QUIZ_CHOICE_IDS = ["a", "b", "c", "d"]


def run_guardrail_validator_module(
    selected_word: dict[str, Any],
    root: dict[str, Any],
    pattern: dict[str, Any] | None,
    quiz: list[dict[str, Any]],
    selected_leaf: dict[str, Any] | None,
) -> dict[str, Any]:
    """
    Run the deterministic checks and return the guardrails block plus a trace.

    Shape mirrors the other modules: learner-facing output under its own key,
    diagnostics under `pipeline_trace`.
    """
    check_results = [
        _check_verified_words(selected_word, root),
        _check_root_pattern_matched(selected_word, root, pattern),
        _check_meanings_verified(selected_word, selected_leaf),
        _check_quiz_one_answer(quiz),
        _check_no_invented_arabic(selected_leaf, quiz, root),
    ]

    checks = [
        {"id": check_id, "label": label, "passed": result.passed}
        for check_id, label, result in check_results
    ]
    violations = [
        violation
        for _, _, result in check_results
        for violation in result.violations
    ]
    passed = all(check["passed"] for check in checks)

    return {
        "guardrails": {
            "passed": passed,
            "summary": SUMMARY_PASSED if passed else SUMMARY_FAILED,
            "checks": checks,
            # Mechanical checks over KB-derived content, not a model review.
            # /api/insights swaps this block for the live 12-check verdict when
            # the guardrail agent is k2_live; the panel labels which kind ran.
            "engine_status": ENGINE_STATUS_DETERMINISTIC,
        },
        "pipeline_trace": {
            "guardrail_validator": {
                "source": ENGINE_STATUS_DETERMINISTIC,
                "checks_run": len(checks),
                "checks_passed": sum(1 for check in checks if check["passed"]),
                "violations": violations,
            },
        },
    }


# --- the checks ----------------------------------------------------------------


def _check_verified_words(
    selected_word: dict[str, Any],
    root: dict[str, Any],
) -> tuple[str, str, ValidationResult]:
    """
    Every word shown resolves to a knowledge-base entry by id.

    This asserts provenance (the family came out of the KB, not thin air), not
    the per-entry `verified` flag — what that flag should mean across 464 words
    is the open §1.7 decision, and reading it before it is set anywhere would
    turn this check into a permanent fail. When that lands, this is the check
    that starts reading `word.get("verified")`.
    """
    result = ValidationResult(passed=True)

    selected_id = selected_word.get("id")
    if not selected_id or not kb.get_word(selected_id):
        result.add(f"verified_words: selected word id '{selected_id}' not in KB")

    for word in kb.words_by_root.get(root.get("id"), []):
        if not word.get("id") or not kb.get_word(word["id"]):
            result.add(
                f"verified_words: family word id '{word.get('id')}' not in KB"
            )

    return ("verified_words", "Only verified words used", result)


def _check_root_pattern_matched(
    selected_word: dict[str, Any],
    root: dict[str, Any],
    pattern: dict[str, Any] | None,
) -> tuple[str, str, ValidationResult]:
    """The root and pattern shown actually belong to this word."""
    result = ValidationResult(passed=True)

    root_id = root.get("id")
    if not root_id or root_id not in kb.roots:
        result.add(f"root_pattern_matched: root '{root_id}' not in KB")
    if selected_word.get("root_id") != root_id:
        result.add(
            f"root_pattern_matched: word carries root_id "
            f"'{selected_word.get('root_id')}', shown root is '{root_id}'"
        )

    pattern_id = selected_word.get("pattern_id")
    if pattern_id:
        if not pattern or pattern.get("id") != pattern_id:
            result.add(
                f"root_pattern_matched: word's pattern_id '{pattern_id}' "
                f"does not match the shown pattern"
            )
        if not kb.get_pattern(pattern_id):
            result.add(f"root_pattern_matched: pattern '{pattern_id}' not in KB")

    breakdown = selected_word.get("breakdown") or {}
    root_letters = breakdown.get("root_letters") or []
    if root_letters:
        built = _root_key("".join(root_letters))
        expected = _root_key(root.get("arabic", ""))
        if built != expected:
            result.add(
                f"root_pattern_matched: breakdown root letters "
                f"{root_letters} do not spell the root '{root.get('arabic')}'"
            )
    else:
        result.add("root_pattern_matched: breakdown has no root letters")

    return ("root_pattern_matched", "Root & pattern matched", result)


def _check_meanings_verified(
    selected_word: dict[str, Any],
    selected_leaf: dict[str, Any] | None,
) -> tuple[str, str, ValidationResult]:
    """Every meaning on screen is the KB's meaning for that entry, verbatim."""
    result = ValidationResult(passed=True)

    if not selected_word.get("meaning"):
        result.add("meanings_verified: selected word has no meaning")

    leaf = selected_leaf or {}

    leaf_word = leaf.get("word") or {}
    _require_kb_meaning(leaf_word, "leaf word", result)

    for card in leaf.get("same_pattern_words") or []:
        _require_kb_meaning(card, "same-pattern card", result)

    return ("meanings_verified", "Meanings from verified KB", result)


def _check_quiz_one_answer(
    quiz: list[dict[str, Any]],
) -> tuple[str, str, ValidationResult]:
    """Each question is well-formed with exactly one correct choice."""
    result = ValidationResult(passed=True)

    if not quiz:
        result.add("quiz_one_answer: quiz is empty")

    for index, question in enumerate(quiz):
        label = f"quiz_one_answer: q[{index}]"

        if not isinstance(question, dict):
            result.add(f"{label} is not an object")
            continue

        choices = question.get("choices")
        if not isinstance(choices, list) or len(choices) < 2:
            result.add(f"{label} needs at least 2 choices")
            continue

        choice_ids = [choice.get("id") for choice in choices]
        if choice_ids != _QUIZ_CHOICE_IDS[: len(choices)]:
            result.add(f"{label} choice ids are {choice_ids}, expected a/b/c/d order")

        texts = [choice.get("text") for choice in choices]
        if any(not text for text in texts):
            result.add(f"{label} has an empty choice")
        if len(set(texts)) != len(texts):
            # Duplicate texts mean two indistinguishable choices — the learner
            # cannot tell the correct one from its copy.
            result.add(f"{label} has duplicate choices: {texts}")

        if question.get("answer_id") not in choice_ids:
            result.add(
                f"{label} answer_id '{question.get('answer_id')}' "
                f"is not a choice"
            )

        if not question.get("question"):
            result.add(f"{label} has no question text")

    return ("quiz_one_answer", "Quiz has one correct answer", result)


def _check_no_invented_arabic(
    selected_leaf: dict[str, Any] | None,
    quiz: list[dict[str, Any]],
    root: dict[str, Any],
) -> tuple[str, str, ValidationResult]:
    """
    Every Arabic run on screen is a knowledge-base form.

    Two scopes, matching how the content is built: the leaf's prose is templated
    from the word's own family and related cards, so it is checked against that
    family evidence; quiz distractors deliberately come from the whole KB (other
    roots' Arabic, other patterns — the same allowance §1.3's v5_combined
    guardrail prompt had to learn), so quiz text is checked KB-wide.
    """
    result = ValidationResult(passed=True)

    leaf = selected_leaf or {}
    family_keys = grounding_keys(_family_arabic_forms(leaf, root))
    for field in _LEAF_PROSE_FIELDS:
        check_no_unknown_arabic_keys(
            leaf.get(field) or "", family_keys, f"leaf.{field}", result
        )

    kb_keys = _kb_grounding_keys()
    for index, question in enumerate(quiz):
        if not isinstance(question, dict):
            continue
        label = f"quiz[{index}]"
        for field in ("question", "explanation"):
            check_no_unknown_arabic_keys(
                question.get(field) or "", kb_keys, f"{label}.{field}", result
            )
        for choice in question.get("choices") or []:
            check_no_unknown_arabic_keys(
                choice.get("text") or "",
                kb_keys,
                f"{label}.choice[{choice.get('id')}]",
                result,
            )

    return (
        "no_invented_arabic",
        "No Arabic outside the knowledge base",
        result,
    )


# --- helpers ---------------------------------------------------------------------


def _root_key(text: str) -> str:
    return normalize_arabic(text).replace(" ", "").translate(_HAMZA_FOLD)


def _require_kb_meaning(
    entry: dict[str, Any],
    what: str,
    result: ValidationResult,
) -> None:
    entry_id = entry.get("id")
    kb_word = kb.get_word(entry_id) if entry_id else None

    if not kb_word:
        result.add(f"meanings_verified: {what} '{entry_id}' not in KB")
        return

    if entry.get("meaning") != kb_word.get("meaning"):
        result.add(
            f"meanings_verified: {what} '{entry_id}' shows meaning "
            f"'{entry.get('meaning')}', KB says '{kb_word.get('meaning')}'"
        )


def _family_arabic_forms(
    leaf: dict[str, Any],
    root: dict[str, Any],
) -> set[str]:
    """The Arabic a leaf's prose may legitimately contain."""
    allowed: set[str] = set()

    add_arabic_value(allowed, root.get("arabic"))

    for word in kb.words_by_root.get(root.get("id"), []):
        add_arabic_value(allowed, word.get("arabic"))
        family_pattern = kb.get_pattern(word.get("pattern_id"))
        if family_pattern:
            add_arabic_value(allowed, family_pattern.get("arabic"))

    pattern = leaf.get("pattern")
    if pattern:
        add_arabic_value(allowed, pattern.get("arabic"))

    for card in leaf.get("same_pattern_words") or []:
        add_arabic_value(allowed, card.get("arabic"))

    return allowed


# Grounding keys for the whole KB, cached: the KB loads once at startup and
# never mutates afterwards, and re-keying ~560 forms on every request is what
# would put this stage's cost on /api/analyze. The cache key catches a reload.
_kb_keys_cache: tuple[tuple[int, int, int], set[str]] | None = None


def _kb_grounding_keys() -> set[str]:
    """Grounding keys for every Arabic form the KB holds — the distractor pool."""
    global _kb_keys_cache

    cache_key = (len(kb.words), len(kb.roots), len(kb.patterns))
    if _kb_keys_cache and _kb_keys_cache[0] == cache_key:
        return _kb_keys_cache[1]

    allowed: set[str] = set()
    for word in kb.words.values():
        add_arabic_value(allowed, word.get("arabic"))
    for kb_root in kb.roots.values():
        add_arabic_value(allowed, kb_root.get("arabic"))
    for kb_pattern in kb.patterns.values():
        add_arabic_value(allowed, kb_pattern.get("arabic"))

    keys = grounding_keys(allowed)
    _kb_keys_cache = (cache_key, keys)
    return keys
