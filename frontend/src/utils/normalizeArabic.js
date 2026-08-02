// Mirrors backend/app/core/normalizer.py exactly. The backend resolves every
// search, so its normalizer is the authority; if these two drift, the result is
// a silent lookup miss rather than an error. Change both or neither.
//
// The two had drifted: this copy kept ta-marbuta (so the backend produced
// mim-dal-ra-sin-ha where this produced ...ta-marbuta), folded hamza-waw and
// hamza-ya that the backend leaves alone, missed two diacritic blocks, and left
// internal whitespace in place - 181 divergences across the KB and its aliases.
//
// Escapes rather than literal Arabic on purpose: a bidi-rendered character
// class is unreadable in review and easy to get silently wrong.

// The same four blocks as ARABIC_DIACRITICS in the Python normalizer.
const ARABIC_DIACRITICS_REGEX =
  /[ؐ-ًؚ-ٰٟۖ-ۭ]/g;
const TATWEEL_REGEX = /ـ/g;
const ALEF_VARIANTS_REGEX = /[أإآٱ]/g;
const ALEF = "ا";
const ALEF_MAQSURA_REGEX = /ى/g;
const YA = "ي";
const TA_MARBUTA_REGEX = /ة/g;
const HA = "ه";
const WHITESPACE_REGEX = /\s+/g;

export function normalizeArabic(value = "") {
  return String(value)
    .trim()
    .replace(TATWEEL_REGEX, "")
    .replace(ARABIC_DIACRITICS_REGEX, "")
    .replace(ALEF_VARIANTS_REGEX, ALEF)
    .replace(ALEF_MAQSURA_REGEX, YA)
    .replace(TA_MARBUTA_REGEX, HA)
    .replace(WHITESPACE_REGEX, "");
}
