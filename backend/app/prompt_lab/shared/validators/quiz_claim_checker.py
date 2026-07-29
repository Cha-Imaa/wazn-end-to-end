# app/prompt_lab/shared/validators/quiz_claim_checker.py

"""
Checks what a quiz's prose *asserts*, not just which tokens it reuses.

Grounding (§1.4) proves every Arabic token came from the evidence, and
`derive_correct_choice_id` proves the answer key points at the right choice.
Neither reads the sentences. Observed live on قَاسِم, 2026-07-29: a quiz served
`k2_live` — every token grounded, every answer key correct — carrying two
distractor explanations that were simply false:

    "فَعَلَ is a noun pattern forming abstract nouns like قَسَمَ"
    "قَسَمَ follows the فَعَلَ pattern, not فَعَلَ"

فَعَلَ is a verb pattern, قَسَمَ does not mean "section, department", and the
second sentence contradicts itself. The live guardrail flagged both — *after*
the quiz was served. That was the third defect the guardrail alone caught, and
the argument for checking here: the claims are about pattern function, word
meaning, and word-to-pattern assignment, all of which are knowledge-base facts.

Four claim shapes are checked, and every one is skipped rather than guessed at
when the sentence is not unambiguous — the same conservatism as
`derive_correct_choice_id`. A false rejection costs the learner a live quiz and
serves the deterministic one; a false pass teaches something wrong.
"""

import re
from typing import Any

from app.prompt_lab.shared.validators.common_validator import (
    arabic_identity,
    extract_arabic_runs,
    normalize_arabic,
    unambiguous_by_grounding_key,
)

# The same run definition `common_validator` uses, as a fragment so claim
# patterns can put prose around it.
_RUN = r"[؀-ۿ][؀-ۿ\s]*[؀-ۿ]|[؀-ۿ]"

WORD_CLASSES = ("noun", "verb", "adjective")

_SENTENCE_SPLIT_RE = re.compile(r"[.!?؟\n]+")

# Any negation in the sentence disables the positive-claim checks: "قَاسِم is
# not on the مَفْعُول pattern" is a *correct* statement whose surface form is
# indistinguishable from a false attribution without parsing scope.
_NEGATION_RE = re.compile(
    r"\b(?:not|never|isn't|doesn't|does not|is not|rather than|instead of|unlike|"
    r"n't)\b",
    re.IGNORECASE,
)

# "<word> follows the <pattern> pattern" and its close variants, directional so
# the word being described comes first.
_ATTRIBUTION_RE = re.compile(
    rf"({_RUN})"
    r"\s*(?:\([^)]*\)\s*)?"
    r"(?:follows|follow|is formed on|is formed using|is built on|is based on|"
    r"is on|uses)\s+"
    r"(?:the\s+)?"
    rf"({_RUN})",
    re.IGNORECASE,
)

# "the <pattern> pattern, not <pattern>" — a self-contradiction when both runs
# name the same item.
_CONTRADICTION_RE = re.compile(
    rf"({_RUN})\s*(?:pattern)?\s*,?\s+not\s+(?:the\s+)?({_RUN})",
    re.IGNORECASE,
)

_CLASS_CLAIM_RE = re.compile(
    rf"\b({'|'.join(WORD_CLASSES)})\s+pattern\b",
    re.IGNORECASE,
)

# "<word> means ..." — the claim text runs to the end of the sentence or to a
# contrasting clause, because knowledge-base meanings contain commas
# ("section, department").
_MEANING_CLAIM_RE = re.compile(
    rf"({_RUN})"
    r"\s*(?:\([^)]*\)\s*)?"
    r"(?:means|meaning is|refers to|translates as)\s+"
    r"(.+)",
    re.IGNORECASE,
)

_MEANING_CLAUSE_END_RE = re.compile(
    r"\b(?:while|whereas|but|and then|which)\b|[;:]",
    re.IGNORECASE,
)

_PROSE_FIELDS = ("question", "correct_feedback", "wrong_feedback", "explanation")

# How a per-choice feedback string opens: affirming the pick, or rejecting it.
_AFFIRMS_RE = re.compile(
    r"^\W*(?:correct|right|yes|exactly|that's right|well done)\b",
    re.IGNORECASE,
)
_REJECTS_RE = re.compile(
    r"^\W*(?:not quite|no\b|nope|incorrect|wrong)\b",
    re.IGNORECASE,
)


def feedback_claim_violations(
    question: dict[str, Any],
    evidence: dict[str, Any],
) -> list[str]:
    """
    Violations for every checkable false claim in one question's prose.

    `evidence` is the quiz `llm_input`: root, leaves, and each leaf's pattern.
    Returns an empty list when nothing checkable is wrong — which includes the
    common case of prose that makes no claim this module can decide.
    """
    lookup = _build_lookup(evidence)

    if not lookup["leaves"] and not lookup["patterns"]:
        return []

    violations = _check_affirmation_placement(question)

    for field_name, text in _prose_fields(question):
        for sentence in _sentences(text):
            violations.extend(_sentence_violations(sentence, field_name, lookup))

    return violations


def affirmed_choice_id(question: dict[str, Any]) -> str | None:
    """
    The choice whose feedback affirms it ("Correct. …"), or None.

    Which choice the model itself believes is right, read off prose rather than
    off `answer_id`. The two disagreeing is the signal that separates a clerical
    key slip — repairable, because the feedback proves what was meant — from the
    model actually believing a wrong answer, which nothing should repair.
    """
    choice_feedback = question.get("choice_feedback")

    if not isinstance(choice_feedback, dict):
        return None

    affirmed = [
        choice_id
        for choice_id in sorted(choice_feedback, key=str)
        if isinstance(choice_feedback[choice_id], str)
        and _AFFIRMS_RE.match(choice_feedback[choice_id])
    ]

    return affirmed[0] if len(affirmed) == 1 else None


def _check_affirmation_placement(question: dict[str, Any]) -> list[str]:
    """
    "Correct." must sit on the choice the answer key points at.

    A per-choice feedback string opens by either affirming or rejecting the
    pick, so the two must agree with `answer_id`. Observed live on عِلْم,
    2026-07-29: a meaning_to_leaf question keyed correctly at c (مُعَلِّم,
    "teacher") carried "Correct. مُعَلِّم has the meaning 'teacher'" on choice d,
    whose text is مَعْلُوم — so a learner picking the right answer is told what
    a different word means, and one picking d is congratulated. Every token is
    grounded and the key is right, which is why nothing else sees it.

    Cheap and prose-shape only: it says nothing about whether the sentence is
    *true*, which is what the checks above are for.
    """
    answer_id = question.get("answer_id")
    choice_feedback = question.get("choice_feedback")

    if not isinstance(choice_feedback, dict) or not isinstance(answer_id, str):
        return []

    violations: list[str] = []

    for choice_id in sorted(choice_feedback, key=str):
        feedback = choice_feedback[choice_id]

        if not isinstance(feedback, str) or not feedback.strip():
            continue

        if choice_id == answer_id and _REJECTS_RE.match(feedback):
            violations.append(
                f"choice_feedback.{choice_id}: rejects the choice the answer key"
                f" points at: \"{_clip(feedback)}\""
            )
        elif choice_id != answer_id and _AFFIRMS_RE.match(feedback):
            violations.append(
                f"choice_feedback.{choice_id}: affirms a choice that is not the"
                f" answer ('{answer_id}' is): \"{_clip(feedback)}\""
            )

    return violations


def _prose_fields(question: dict[str, Any]) -> list[tuple[str, str]]:
    fields: list[tuple[str, str]] = []

    for field_name in _PROSE_FIELDS:
        value = question.get(field_name)
        if isinstance(value, str):
            fields.append((field_name, value))

    choice_feedback = question.get("choice_feedback")

    if isinstance(choice_feedback, dict):
        for choice_id in sorted(choice_feedback, key=str):
            value = choice_feedback[choice_id]
            if isinstance(value, str):
                fields.append((f"choice_feedback.{choice_id}", value))

    return fields


def _sentences(text: str) -> list[str]:
    return [part.strip() for part in _SENTENCE_SPLIT_RE.split(text) if part.strip()]


def _sentence_violations(
    sentence: str,
    field_name: str,
    lookup: dict[str, Any],
) -> list[str]:
    violations: list[str] = []

    # Contradictions are checked first and are the one check a negation does not
    # disable: "not" is the contradiction.
    violations.extend(_check_contradiction(sentence, field_name, lookup))

    if _NEGATION_RE.search(sentence):
        return violations

    violations.extend(_check_word_pattern_attribution(sentence, field_name, lookup))
    violations.extend(_check_pattern_word_class(sentence, field_name, lookup))
    violations.extend(_check_word_meaning(sentence, field_name, lookup))

    return violations


def _check_contradiction(
    sentence: str,
    field_name: str,
    lookup: dict[str, Any],
) -> list[str]:
    violations: list[str] = []

    for match in _CONTRADICTION_RE.finditer(sentence):
        first = _resolve_any(lookup, match.group(1))
        second = _resolve_any(lookup, match.group(2))

        # Only a claim about a knowledge-base item is ours to reject; an
        # unresolvable run is the grounding check's business.
        if first is None or second is None or first != second:
            continue

        violations.append(
            f"{field_name}: contradicts itself — asserts and denies the same item"
            f" '{match.group(1).strip()}': \"{_clip(sentence)}\""
        )

    return violations


def _check_word_pattern_attribution(
    sentence: str,
    field_name: str,
    lookup: dict[str, Any],
) -> list[str]:
    violations: list[str] = []

    for match in _ATTRIBUTION_RE.finditer(sentence):
        leaf_form = _resolve(lookup["leaves"], lookup["leaves_folded"], match.group(1))
        claimed = _resolve(
            lookup["patterns"], lookup["patterns_folded"], match.group(2)
        )

        if leaf_form is None or claimed is None:
            continue

        actual = lookup["pattern_form_by_leaf_form"].get(leaf_form)

        if not actual or actual == claimed:
            continue

        violations.append(
            f"{field_name}: says {match.group(1).strip()} follows"
            f" {match.group(2).strip()}, but the evidence gives it"
            f" {lookup['patterns'][actual].get('arabic')}"
        )

    return violations


def _check_pattern_word_class(
    sentence: str,
    field_name: str,
    lookup: dict[str, Any],
) -> list[str]:
    claimed = {match.group(1).lower() for match in _CLASS_CLAIM_RE.finditer(sentence)}

    if len(claimed) != 1:
        return []

    # Which pattern the claim is about has to be unambiguous, so a sentence
    # naming two patterns ("فَاعِل is a noun pattern, فَعَلَ a verb pattern")
    # is left alone.
    pattern_forms = {
        form
        for form in (
            _resolve(lookup["patterns"], lookup["patterns_folded"], run)
            for run in extract_arabic_runs(sentence)
        )
        if form is not None
    }

    if len(pattern_forms) != 1:
        return []

    pattern = lookup["patterns"][next(iter(pattern_forms))]
    actual = _word_class_of(pattern)

    if actual is None:
        # The knowledge base does not state a class for this pattern (the
        # participle patterns are named "active participle pattern (Form I)"),
        # so the claim is not checkable here.
        return []

    claimed_class = next(iter(claimed))

    if claimed_class == actual:
        return []

    return [
        f"{field_name}: calls {pattern.get('arabic')} a {claimed_class} pattern,"
        f" but the evidence names it a {actual} pattern"
        f" ('{pattern.get('name')}')"
    ]


def _check_word_meaning(
    sentence: str,
    field_name: str,
    lookup: dict[str, Any],
) -> list[str]:
    violations: list[str] = []

    for match in _MEANING_CLAIM_RE.finditer(sentence):
        leaf_form = _resolve(lookup["leaves"], lookup["leaves_folded"], match.group(1))

        if leaf_form is None:
            continue

        claim = _meaning_claim_text(match.group(2))
        claim_key = _english_key(claim)

        if not claim_key:
            continue

        own_key = _english_key(lookup["leaves"][leaf_form].get("meaning") or "")

        if _states_own_meaning(claim_key, own_key):
            continue

        # Only an exact restatement of a *different* item's meaning is rejected.
        # Anything else is paraphrase, and paraphrase is not this module's call
        # to make — the live guardrail reviews prose quality.
        owner = lookup["meaning_owner"].get(claim_key)

        if owner is None or owner == leaf_form:
            continue

        violations.append(
            f"{field_name}: gives {match.group(1).strip()} the meaning"
            f" '{claim}', which the evidence assigns to"
            f" {lookup['labels'].get(owner, owner)} —"
            f" {match.group(1).strip()} means"
            f" '{lookup['leaves'][leaf_form].get('meaning')}'"
        )

    return violations


def _states_own_meaning(claim_key: str, own_key: str) -> bool:
    """
    Whether a meaning claim is the item's own meaning, allowing for prose that
    shortens or extends it at a clause boundary.

    Knowledge-base meanings are often two glosses ("earning, income", "read!
    (command)"), and prose that quotes the first one is telling the truth. Found
    by sweeping the deterministic quizzes: 4 of 464 words explain a word using
    the leading gloss of its own meaning, which the earlier exact comparison
    read as attributing another item's meaning to it. Extension is allowed the
    same way, for "means divided into shares".
    """
    if not claim_key or not own_key:
        return False

    if claim_key == own_key:
        return True

    longer, shorter = (
        (claim_key, own_key) if len(claim_key) > len(own_key) else (own_key, claim_key)
    )

    return longer.startswith(shorter) and not longer[len(shorter)].isalnum()


def _meaning_claim_text(text: str) -> str:
    clause = _MEANING_CLAUSE_END_RE.split(text, maxsplit=1)[0]
    stripped = clause.strip().strip("\"“”'")
    return stripped.strip().rstrip(".,").strip()


def _word_class_of(pattern: dict[str, Any]) -> str | None:
    """
    The word class the knowledge base states for a pattern, or None.

    Read off `name` — "abstract noun pattern", "Form VIII past-tense verb
    pattern". Names that state no class, or somehow more than one, return None
    so the claim is not judged.
    """
    name = pattern.get("name")

    if not isinstance(name, str):
        return None

    found = {word_class for word_class in WORD_CLASSES if word_class in name.lower()}

    return next(iter(found)) if len(found) == 1 else None


def _folded(text: str) -> str:
    """The grounding key: tashkeel- and spacing-insensitive."""
    return normalize_arabic(text).replace(" ", "")


def _resolve(
    by_form: dict[str, dict[str, Any]],
    by_folded: dict[str, str],
    run: str,
) -> str | None:
    """
    Which evidence item a run names, as its exact form, or None.

    Exact spelling first. An under-vocalized run falls back to the folded key,
    but only where that key belongs to a single item — otherwise there is no
    telling which of the family's near-identical items was meant, and an
    unresolved run means the claim about it simply is not judged.
    """
    form = arabic_identity(run)

    if form in by_form:
        return form

    return by_folded.get(_folded(run))


def _resolve_any(lookup: dict[str, Any], run: str) -> str | None:
    """A run naming any evidence item — leaf, root, or pattern."""
    return _resolve(lookup["leaves"], lookup["leaves_folded"], run) or _resolve(
        lookup["patterns"], lookup["patterns_folded"], run
    )


def _english_key(text: str) -> str:
    if not isinstance(text, str):
        return ""

    collapsed = re.sub(r"\s+", " ", text).strip().casefold()

    return re.sub(r"^(?:the|a|an)\s+", "", collapsed)


def _clip(sentence: str, limit: int = 120) -> str:
    collapsed = re.sub(r"\s+", " ", sentence).strip()

    return collapsed if len(collapsed) <= limit else collapsed[: limit - 1] + "…"


def _build_lookup(evidence: dict[str, Any]) -> dict[str, Any]:
    """
    Indexes over the quiz evidence, keyed by exact Arabic form.

    `leaves` holds the root under its own form too, so a claim about the root's
    meaning resolves like any other. `meaning_owner` maps an English meaning to
    the single item that owns it, dropping any meaning two items share so an
    ambiguous meaning can never produce a violation.
    """
    root = evidence.get("root") if isinstance(evidence, dict) else None
    leaves = evidence.get("leaves") if isinstance(evidence, dict) else None

    leaf_by_form: dict[str, dict[str, Any]] = {}
    pattern_by_form: dict[str, dict[str, Any]] = {}
    pattern_form_by_leaf_form: dict[str, str] = {}
    labels: dict[str, str] = {}
    owners_by_meaning: dict[str, set[str]] = {}

    def register_meaning(meaning: Any, owner_form: str) -> None:
        key = _english_key(meaning if isinstance(meaning, str) else "")
        if key:
            owners_by_meaning.setdefault(key, set()).add(owner_form)

    if isinstance(root, dict):
        root_form = arabic_identity(root.get("arabic") or "")
        if root_form:
            leaf_by_form[root_form] = root
            labels[root_form] = f"the root {root.get('arabic')}"
            register_meaning(root.get("meaning"), root_form)

    if isinstance(leaves, list):
        for leaf in leaves:
            if not isinstance(leaf, dict):
                continue

            leaf_form = arabic_identity(leaf.get("arabic") or "")

            if leaf_form:
                leaf_by_form[leaf_form] = leaf
                labels[leaf_form] = str(leaf.get("arabic"))
                register_meaning(leaf.get("meaning"), leaf_form)

            pattern = leaf.get("pattern")

            if isinstance(pattern, dict):
                pattern_form = arabic_identity(pattern.get("arabic") or "")
                if pattern_form:
                    pattern_by_form[pattern_form] = pattern
                    if leaf_form:
                        pattern_form_by_leaf_form[leaf_form] = pattern_form

    return {
        "leaves": leaf_by_form,
        "leaves_folded": unambiguous_by_grounding_key(leaf_by_form),
        "patterns": pattern_by_form,
        "patterns_folded": unambiguous_by_grounding_key(pattern_by_form),
        "pattern_form_by_leaf_form": pattern_form_by_leaf_form,
        "meaning_owner": {
            key: next(iter(owners))
            for key, owners in owners_by_meaning.items()
            if len(owners) == 1
        },
        "labels": labels,
    }
