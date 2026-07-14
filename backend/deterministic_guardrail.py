# app/prompt_lab/shared/guardrail_layer1.py
"""
Layer 1 guardrail: fast, deterministic, non-LLM checks.

Runs BEFORE Layer 2. Catches schema violations and grounding violations
that can be verified mechanically. Cheap, fast, zero false negatives on
the checks it covers (if a word isn't a substring of the input, it is
definitely not grounded).

Both validators return a ValidationResult. If result.passed is False,
the caller should regenerate rather than pass to Layer 2 — no point
spending an LLM call semantically judging output that's already broken.
"""

from dataclasses import dataclass, field
import re


@dataclass
class ValidationResult:
    passed: bool
    violations: list[str] = field(default_factory=list)

    def add(self, msg: str) -> None:
        self.violations.append(msg)
        self.passed = False


# ---------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------

def _word_count(text: str) -> int:
    return len(text.split())


def _sentence_count(text: str) -> int:
    # Arabic text may use '.', '؟', '!' as terminators. Count non-empty
    # segments split on those. This is approximate — good enough for a
    # ceiling check, not meant to be linguistically exact.
    parts = re.split(r"[.!؟?]+", text.strip())
    return len([p for p in parts if p.strip()])


def _collect_grounded_arabic_strings(evidence: dict) -> set[str]:
    """
    Pulls every Arabic string that is legitimately allowed to appear in
    the output, based on the evidence packet given to the generator.

    ASSUMPTION: evidence packet shape matches the JSON examples used in
    the explanation_agent prompts:
        {
          "selected_word": {"arabic": ..., "meaning": ...},
          "root": {"arabic": ..., "meaning": ...},
          "pattern": {"arabic": ...},
          "same_pattern_cards": [{"arabic": ..., "meaning": ...}, ...]
        }
    Adjust the key paths below if build_explanation_evidence differs.
    """
    allowed = set()

    if "selected_word" in evidence:
        allowed.add(evidence["selected_word"].get("arabic", ""))
    if "root" in evidence:
        allowed.add(evidence["root"].get("arabic", ""))
    if "pattern" in evidence:
        allowed.add(evidence["pattern"].get("arabic", ""))
    for card in evidence.get("same_pattern_cards", []):
        allowed.add(card.get("arabic", ""))

    return {a for a in allowed if a}


def _collect_grounded_arabic_strings_quiz(evidence: dict) -> set[str]:
    """
    Same idea, for the quiz agent's evidence packet:
        {
          "root": {"arabic": ..., "meaning": ...},
          "leaves": [
            {"arabic": ..., "meaning": ...,
             "pattern": {"arabic": ..., "meaning_effect": ...}},
            ...
          ]
        }
    """
    allowed = set()

    if "root" in evidence:
        allowed.add(evidence["root"].get("arabic", ""))

    for leaf in evidence.get("leaves", []):
        allowed.add(leaf.get("arabic", ""))
        pattern = leaf.get("pattern", {})
        allowed.add(pattern.get("arabic", ""))

    return {a for a in allowed if a}


_ARABIC_RUN = re.compile(r"[\u0600-\u06FF]+")


def _extract_arabic_substrings(text: str) -> list[str]:
    """Pulls out contiguous Arabic-script runs from a text field."""
    return _ARABIC_RUN.findall(text)


def _check_no_unknown_arabic(text: str, allowed: set[str], field_name: str,
                              result: ValidationResult) -> None:
    """
    Flags any Arabic run in `text` that isn't a substring of, or doesn't
    contain, any allowed string. This is intentionally loose (substring
    match rather than exact token match) because diacritics and prefixes
    (e.g. ال) can cause exact matches to fail spuriously.
    """
    found_runs = _extract_arabic_substrings(text)
    for run in found_runs:
        # allowed if `run` is contained in an allowed string, or an
        # allowed string is contained in `run` (handles ال prefix, etc.)
        is_allowed = any(run in a or a in run for a in allowed if a)
        if not is_allowed:
            result.add(
                f"{field_name}: contains Arabic text not present in "
                f"input evidence: '{run}'"
            )


# ---------------------------------------------------------------------
# Explanation agent validator
# ---------------------------------------------------------------------

REQUIRED_EXPLANATION_KEYS = {
    "explanation", "pattern_explanation", "same_pattern_explanation"
}

BANNED_PHRASES = [
    "this shows that",
    "which allows you to predict",
    "allowing you to predict",
    "demonstrates that",
]


def validate_explanation_output(evidence: dict, output: dict) -> ValidationResult:
    result = ValidationResult(passed=True)

    # --- schema ---
    if set(output.keys()) != REQUIRED_EXPLANATION_KEYS:
        result.add(
            f"Unexpected key set. Expected {REQUIRED_EXPLANATION_KEYS}, "
            f"got {set(output.keys())}"
        )
        return result  # no point checking further if shape is wrong

    for key in REQUIRED_EXPLANATION_KEYS:
        if not isinstance(output[key], str) or not output[key].strip():
            result.add(f"{key}: must be a non-empty string")

    if not result.passed:
        return result

    explanation = output["explanation"]
    pattern_explanation = output["pattern_explanation"]
    same_pattern_explanation = output["same_pattern_explanation"]

    # --- length limits ---
    if _sentence_count(explanation) > 3:
        result.add("explanation: exceeds 3 sentence limit")
    if _word_count(explanation) > 60:
        result.add("explanation: exceeds 60 word limit")

    if _sentence_count(pattern_explanation) > 1:
        result.add("pattern_explanation: exceeds 1 sentence limit")
    if _word_count(pattern_explanation) > 20:
        result.add("pattern_explanation: exceeds 20 word limit")

    if _sentence_count(same_pattern_explanation) > 2:
        result.add("same_pattern_explanation: exceeds 2 sentence limit")
    if _word_count(same_pattern_explanation) > 45:
        result.add("same_pattern_explanation: exceeds 45 word limit")

    # --- grounding: no invented Arabic ---
    allowed_arabic = _collect_grounded_arabic_strings(evidence)
    _check_no_unknown_arabic(explanation, allowed_arabic, "explanation", result)
    _check_no_unknown_arabic(pattern_explanation, allowed_arabic,
                              "pattern_explanation", result)
    _check_no_unknown_arabic(same_pattern_explanation, allowed_arabic,
                              "same_pattern_explanation", result)

    # pattern_explanation must NOT reference same-pattern cards
    for card in evidence.get("same_pattern_cards", []):
        card_ar = card.get("arabic", "")
        if card_ar and card_ar in pattern_explanation:
            result.add(
                "pattern_explanation: must not mention same-pattern cards"
            )

    # --- no-same-pattern-cards case ---
    if not evidence.get("same_pattern_cards"):
        expected = "No same-pattern comparison is available in the current data."
        if same_pattern_explanation.strip() != expected:
            result.add(
                "same_pattern_explanation: must be the exact fallback "
                "string when no same-pattern cards are provided"
            )

    # --- banned phrases ---
    lower_same_pattern = same_pattern_explanation.lower()
    for phrase in BANNED_PHRASES:
        if phrase in lower_same_pattern:
            result.add(f"same_pattern_explanation: contains banned phrase '{phrase}'")

    return result


# ---------------------------------------------------------------------
# Quiz agent validator
# ---------------------------------------------------------------------

REQUIRED_QUESTION_KEYS = {
    "id", "type", "question", "choices", "answer_id",
    "correct_feedback", "wrong_feedback", "choice_feedback", "explanation",
}

VALID_TYPES = {
    "root_meaning", "leaf_meaning", "meaning_to_leaf",
    "pattern_recognition", "pattern_meaning_effect", "pattern_application",
}

CHOICE_IDS = {"a", "b", "c", "d"}


def validate_quiz_output(evidence: dict, output: dict) -> ValidationResult:
    result = ValidationResult(passed=True)

    quiz = output.get("quiz")
    if not isinstance(quiz, list) or len(quiz) != 5:
        result.add(f"quiz: must contain exactly 5 questions, got "
                    f"{len(quiz) if isinstance(quiz, list) else 'invalid type'}")
        return result

    seen_types = []
    answer_positions = []
    allowed_arabic = _collect_grounded_arabic_strings_quiz(evidence)

    for idx, q in enumerate(quiz):
        qlabel = f"q[{idx}] (id={q.get('id', '?')})"

        # --- key shape ---
        if set(q.keys()) != REQUIRED_QUESTION_KEYS:
            result.add(f"{qlabel}: unexpected keys, got {set(q.keys())}")
            continue

        # --- type validity ---
        qtype = q["type"]
        if qtype not in VALID_TYPES:
            result.add(f"{qlabel}: invalid type '{qtype}'")
        seen_types.append(qtype)

        # --- choices shape ---
        choices = q["choices"]
        if not isinstance(choices, list) or len(choices) != 4:
            result.add(f"{qlabel}: must have exactly 4 choices")
            continue

        choice_ids = {c.get("id") for c in choices}
        if choice_ids != CHOICE_IDS:
            result.add(f"{qlabel}: choice ids must be exactly a/b/c/d, "
                        f"got {choice_ids}")

        # --- answer_id validity ---
        answer_id = q["answer_id"]
        if answer_id not in choice_ids:
            result.add(f"{qlabel}: answer_id '{answer_id}' not among choice ids")
        answer_positions.append(answer_id)

        # --- choice_feedback shape ---
        choice_feedback = q["choice_feedback"]
        if set(choice_feedback.keys()) != CHOICE_IDS:
            result.add(f"{qlabel}: choice_feedback keys must be exactly a/b/c/d")

        # wrong_feedback must not be used as a stand-in in choice_feedback
        wrong_fb = q.get("wrong_feedback", "")
        for cid, fb in choice_feedback.items():
            if fb.strip() == wrong_fb.strip() and fb.strip():
                result.add(
                    f"{qlabel}: choice_feedback['{cid}'] duplicates "
                    f"generic wrong_feedback instead of giving a specific reason"
                )

        # --- grounding: Arabic text in question/choices/feedback ---
        for field_name in ["question", "correct_feedback", "wrong_feedback",
                            "explanation"]:
            _check_no_unknown_arabic(q.get(field_name, ""), allowed_arabic,
                                      f"{qlabel}.{field_name}", result)
        for c in choices:
            _check_no_unknown_arabic(c.get("text", ""), allowed_arabic,
                                      f"{qlabel}.choice[{c.get('id')}]", result)
        for cid, fb in choice_feedback.items():
            _check_no_unknown_arabic(fb, allowed_arabic,
                                      f"{qlabel}.choice_feedback[{cid}]", result)

    # --- distinct types across the quiz ---
    if len(set(seen_types)) != 5:
        result.add(f"quiz: expected 5 distinct types, got {seen_types}")

    # --- answer position distribution: no letter appears 3+ times ---
    for letter in CHOICE_IDS:
        count = answer_positions.count(letter)
        if count > 2:
            result.add(
                f"quiz: answer_id '{letter}' used {count} times "
                f"(max allowed is 2), positions={answer_positions}"
            )

    # --- pattern_application: choices must be real leaf words ---
    leaf_words = {leaf.get("arabic", "") for leaf in evidence.get("leaves", [])}
    for q in quiz:
        if q.get("type") == "pattern_application":
            for c in q.get("choices", []):
                if c.get("text") not in leaf_words:
                    result.add(
                        f"q(id={q.get('id')}): pattern_application choice "
                        f"'{c.get('text')}' is not a real leaf word from input"
                    )

    return result