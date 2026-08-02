# app/prompt_lab/shared/validators/sentence_validator.py

# The sentence agent's grounding contract is deliberately different from the
# other agents'. §1.4's "every Arabic token traced to the evidence" cannot hold
# for a natural sentence — any real Arabic sentence contains function words and
# vocabulary the knowledge base does not carry. What CAN be checked
# deterministically, is:
#
# 1. Output is valid JSON, an object, with exactly {sentence, translation}
# 2. Both values are non-empty strings
# 3. sentence: exactly one sentence, maximum 12 words
# 4. sentence: contains the selected word in the KB's exact vocalized
#    spelling, as its own token — a definite article or one of the
#    single-letter clitics may be attached, nothing else. This is the
#    target-word contract: the one piece of Arabic whose spelling the app
#    vouches for must be the KB's, character for character.
# 5. sentence: Arabic script only (no Latin letters, no digits)
# 6. translation: no Arabic script, one sentence, maximum 20 words
#
# Everything the contract cannot check is covered by labelling: the section
# renders with the same engine_status provenance as every other agent output,
# so a generated sentence never presents itself as verified morphology.

import re
import unicodedata
from typing import Any

from app.prompt_lab.shared.validators.common_validator import (
    ValidationResult,
    extract_arabic_runs,
    get_llm_input,
    parse_json_output,
    require_exact_keys,
    require_non_empty_string,
    sentence_count,
    word_count,
)

REQUIRED_SENTENCE_KEYS = {"sentence", "translation"}

MAX_SENTENCE_WORDS = 12
MAX_TRANSLATION_WORDS = 20

# Attachable clitics tolerated in front of the target word, longest first so
# compound forms (وَال) match before their one-letter prefixes (وَ). Written
# both bare and with their usual short vowel, because the prompt asks for full
# tashkeel and K2 obliges.
CLITIC_PREFIXES = (
    "وَالْ", "وَال", "وال",
    "فَالْ", "فَال", "فال",
    "بِالْ", "بِال", "بال",
    "كَالْ", "كَال", "كال",
    "لِلْ", "لِل", "لل",
    "الْ", "ال",
    "وَ", "و",
    "فَ", "ف",
    "بِ", "ب",
    "لِ", "ل",
    "كَ", "ك",
    "سَ", "س",
)

_LATIN_OR_DIGIT = tuple("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789")

# The marks that may sit on a word's final letter — tanween, a short vowel,
# shadda, or sukun (U+064B–U+0652). The KB spells words without case endings,
# but a fully vocalized sentence correctly adds one (المَدْرَسَةُ), and
# refusing it would reject exactly the well-formed sentences the prompt asks
# for. At most two extra marks (shadda + vowel).
_FINAL_MARKS_RE = re.compile(r"[ً-ْ]*$")

MAX_EXTRA_CASE_MARKS = 2


def token_is_target(token: str, target: str) -> bool:
    """
    Whether a whitespace token IS the target word: the word itself, exactly as
    the KB spells it, optionally behind one attached clitic and optionally
    carrying a case ending. Trailing punctuation is stripped; nothing else is
    tolerated — a pronoun suffix or a re-vowelled copy is not the word the app
    vouches for.

    Both sides are put in NFC first. 54 of the KB's words stack shadda before
    the short vowel (مُعَلِّم), which is how Arabic is conventionally typed but
    is *not* Unicode canonical order — NFC reorders those two marks. The two
    spellings render identically and are the same word, so comparing raw code
    points would reject a correct sentence purely on mark order. K2 currently
    copies the KB spelling out of the prompt, which is the only reason this has
    not bitten; that is a property of the model's behaviour, not a guarantee.

    The case ending is compared as a *set of marks on the final letter* rather
    than as a string suffix. Appending a case ending to a word that already
    ends in a vowel (دَرَسَ + tanween) puts two marks on one letter, and NFC
    reorders them by combining class — so the target is no longer a literal
    prefix of the token even though the word is unchanged.
    """
    stripped = _nfc(token).strip("؟!.،؛:,\"'()«»…")

    for prefix in ("",) + CLITIC_PREFIXES:
        candidate = _nfc(prefix + _nfc(target))

        if stripped == candidate:
            return True

        token_base, token_marks = _split_final_marks(stripped)
        cand_base, cand_marks = _split_final_marks(candidate)

        # Same word up to its final letter's marks, and the token keeps every
        # mark the KB spelling has while adding no more than a case ending.
        if (
            token_base == cand_base
            and set(cand_marks) <= set(token_marks)
            and len(token_marks) <= len(cand_marks) + MAX_EXTRA_CASE_MARKS
        ):
            return True

    return False


def _nfc(text: str) -> str:
    return unicodedata.normalize("NFC", text)


def _split_final_marks(text: str) -> tuple[str, str]:
    """Split a word into its body and the diacritics on its final letter."""
    match = _FINAL_MARKS_RE.search(text)
    return text[: match.start()], match.group()


def sentence_contains_target(sentence: str, target: str) -> bool:
    return any(token_is_target(token, target) for token in sentence.split())


def validate_sentence_output(
    evidence_packet: dict[str, Any],
    raw_output: str,
) -> ValidationResult:
    """Deterministic validator for Sentence Agent raw output."""

    result = parse_json_output(raw_output)

    if not result.passed or result.parsed_json is None:
        return result

    output = result.parsed_json

    require_exact_keys(
        actual=output,
        expected_keys=REQUIRED_SENTENCE_KEYS,
        label="sentence_output",
        result=result,
    )

    if not result.passed:
        return result

    for key in REQUIRED_SENTENCE_KEYS:
        require_non_empty_string(output.get(key), key, result)

    if not result.passed:
        return result

    evidence = get_llm_input(evidence_packet)
    target = (evidence.get("selected_word") or {}).get("arabic") or ""

    sentence = output["sentence"]
    translation = output["translation"]

    if sentence_count(sentence) > 1:
        result.add("sentence: must be exactly one sentence")

    if word_count(sentence) > MAX_SENTENCE_WORDS:
        result.add(f"sentence: exceeds {MAX_SENTENCE_WORDS} word limit")

    if any(char in sentence for char in _LATIN_OR_DIGIT):
        result.add("sentence: must contain Arabic script only")

    if "ـ" in sentence:
        result.add("sentence: must not contain the tatweel character")

    if not target:
        result.add("evidence: selected_word.arabic is missing")
    elif not sentence_contains_target(sentence, target):
        result.add(
            "sentence: does not contain the selected word"
            f" '{target}' in its exact spelling"
        )

    if extract_arabic_runs(translation):
        result.add("translation: must not contain Arabic script")

    if sentence_count(translation) > 1:
        result.add("translation: must be exactly one sentence")

    if word_count(translation) > MAX_TRANSLATION_WORDS:
        result.add(f"translation: exceeds {MAX_TRANSLATION_WORDS} word limit")

    return result
