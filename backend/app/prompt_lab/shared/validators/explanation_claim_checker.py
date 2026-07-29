# app/prompt_lab/shared/validators/explanation_claim_checker.py

"""
Checks what explanation prose *asserts about the same-pattern cards*.

The defect class (observed live 2026-07-29, the sixth guardrail-only catch and
the last one moved pre-serve): the evidence tells the model two true facts —
"مَحْصَلَة shares the selected word's pattern مَفْعَلَة" and "مَفْعَلَة often
means a place connected to the root action" — and the model stitches them into
a third statement, "مَحْصَلَة is a place where…". The KB said *often*; the
card's own meaning ("outcome, net result") says nothing about a place. Every
token is grounded, so the grounding check passes it, and only the live
guardrail flagged it — after the learner saw it.

The claim is mechanically decidable, and only in one narrow shape, so the
checker judges exactly that shape and declines everything else (the same
conservatism as `quiz_claim_checker` — a false rejection costs a live
explanation, a false pass teaches something wrong):

    rejected   an *unhedged* sentence naming *exactly one* card that asserts
               the selected pattern's own category term about it ("place",
               "person", …, read off the pattern's `name`/`meaning_effect`),
               where the card's own meaning does not state that category

    declined   any hedged sentence ("often", "usually", … — that is the
               pattern's general tendency, which the evidence does support);
               any sentence naming no card or several ("words such as X, Y, Z"
               enumerations are membership statements, not per-card claims);
               any negated sentence; any category term the pattern's own
               function statement does not use; the selected word itself —
               connecting the pattern's function to *its* meaning is the
               explanation's whole mandate, and its meaning is fully in
               evidence for the guardrail and evaluation agents to review

Note the deliberate asymmetry: a category assertion about a card whose meaning
*does* state it ("اِقْرَأْ is a command" when the KB meaning is "read!
(command)") passes, and an unhedged assertion the evidence cannot support is
rejected even when it happens to be true in the world ("مَزْرَعَة is a place"
— its KB meaning just says "farm"). The evidence says "often"; the unhedged
specific claim is the model's invention either way.
"""

import re
from typing import Any

from app.prompt_lab.shared.validators.common_validator import (
    arabic_identity,
    extract_arabic_runs,
    normalize_arabic,
    unambiguous_by_grounding_key,
)

_SENTENCE_SPLIT_RE = re.compile(r"[.!?؟\n]+")

_NEGATION_RE = re.compile(
    r"\b(?:not|never|isn't|doesn't|does not|is not|rather than|instead of|unlike|"
    r"n't)\b",
    re.IGNORECASE,
)

# A hedge marks the sentence as stating the pattern's tendency, which the
# meaning_effect ("often …") genuinely supports.
_HEDGE_RE = re.compile(
    r"\b(?:often|usually|typically|commonly|generally|frequently|sometimes|"
    r"tends?\s+to|may|might|can)\b",
    re.IGNORECASE,
)

# The categories a pattern's KB function statement can name about a word.
# Deliberately concrete nouns only: "action"/"process"/"result" appear in
# nearly every meaning_effect and in ordinary true prose, so matching them
# would judge sentences this module has no business judging.
_CATEGORY_TERMS = (
    "place",
    "person",
    "people",
    "tool",
    "instrument",
    "substance",
    "profession",
    "command",
)


def card_claim_violations(
    fields: dict[str, str],
    evidence: dict[str, Any],
) -> list[str]:
    """
    Violations for unsupported pattern-category claims about specific cards.

    `fields` maps field name → prose (the three explanation output fields).
    `evidence` is the explanation `llm_input`: selected_word, root, pattern
    (with name/meaning_effect), same_pattern_cards (with meanings).
    """
    pattern_terms = _pattern_category_terms(evidence.get("pattern"))

    if not pattern_terms:
        return []

    cards = _cards_by_form(evidence.get("same_pattern_cards"))

    if not cards["by_form"]:
        return []

    violations: list[str] = []

    for field_name, text in fields.items():
        if not isinstance(text, str):
            continue
        for sentence in _sentences(text):
            violations.extend(
                _sentence_violations(sentence, field_name, pattern_terms, cards)
            )

    return violations


def _sentence_violations(
    sentence: str,
    field_name: str,
    pattern_terms: set[str],
    cards: dict[str, Any],
) -> list[str]:
    if _NEGATION_RE.search(sentence) or _HEDGE_RE.search(sentence):
        return []

    asserted = {
        term for term in pattern_terms if _term_in(term, sentence)
    }

    if not asserted:
        return []

    # Which card the claim is about has to be unambiguous: an enumeration
    # ("words such as X, Y, Z use the same pattern") is a membership statement
    # about the group, not a checkable claim about one word.
    named = {
        form
        for form in (
            _resolve(cards["by_form"], cards["folded"], run)
            for run in extract_arabic_runs(sentence)
        )
        if form is not None
    }

    if len(named) != 1:
        return []

    card = cards["by_form"][next(iter(named))]
    meaning_text = _english_fold(card.get("meaning") or "")

    unsupported = {
        term for term in asserted if not _term_in(term, meaning_text)
    }

    if not unsupported:
        return []

    return [
        f"{field_name}: asserts the pattern's category"
        f" ({', '.join(sorted(unsupported))}) about {card.get('arabic')}, whose"
        f" meaning in the evidence is '{card.get('meaning')}' — the pattern's"
        f" function is a tendency ('often'), not a fact about this word:"
        f" \"{_clip(sentence)}\""
    ]


def _pattern_category_terms(pattern: Any) -> set[str]:
    """The category terms the pattern's own KB function statement uses."""
    if not isinstance(pattern, dict):
        return set()

    stated = _english_fold(
        f"{pattern.get('name') or ''} {pattern.get('meaning_effect') or ''}"
    )

    return {term for term in _CATEGORY_TERMS if _term_in(term, stated)}


def _cards_by_form(cards: Any) -> dict[str, Any]:
    by_form: dict[str, dict[str, Any]] = {}

    if isinstance(cards, list):
        for card in cards:
            if not isinstance(card, dict):
                continue
            form = arabic_identity(card.get("arabic") or "")
            if form:
                by_form[form] = card

    return {
        "by_form": by_form,
        "folded": unambiguous_by_grounding_key(by_form),
    }


def _resolve(
    by_form: dict[str, dict[str, Any]],
    by_folded: dict[str, str],
    run: str,
) -> str | None:
    form = arabic_identity(run)

    if form in by_form:
        return form

    return by_folded.get(normalize_arabic(run).replace(" ", ""))


def _sentences(text: str) -> list[str]:
    return [part.strip() for part in _SENTENCE_SPLIT_RE.split(text) if part.strip()]


def _term_in(term: str, text: str) -> bool:
    return re.search(rf"\b{re.escape(term)}\b", text) is not None


def _english_fold(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().casefold()


def _clip(sentence: str, limit: int = 120) -> str:
    collapsed = re.sub(r"\s+", " ", sentence).strip()

    return collapsed if len(collapsed) <= limit else collapsed[: limit - 1] + "…"
