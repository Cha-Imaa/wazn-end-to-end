const ARABIC_DIACRITICS_REGEX = /[\u064B-\u065F\u0670\u0640]/g;
const ALEF_VARIANTS_REGEX = /[إأآٱ]/g;

export function normalizeArabic(value = "") {
  return String(value)
    .trim()
    .replace(ARABIC_DIACRITICS_REGEX, "")
    .replace(ALEF_VARIANTS_REGEX, "ا")
    .replace(/ى/g, "ي")
    .replace(/ؤ/g, "و")
    .replace(/ئ/g, "ي");
}