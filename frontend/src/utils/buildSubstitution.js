// An Arabic wazn is a literal template: ف / ع / ل mark the three root slots
// and every other character is scaffolding the word keeps. Substituting the
// root letters into the slots rebuilds the word for 456 of the 464 KB words
// (measured 2026-07-31), which lets the formation card show root + pattern =
// word as a verified equation instead of hand-authored prose.
//
// The 8 that do not rebuild split into two real linguistic classes:
// - 5 words on the root ق ر ء, where the hamza's written seat shifts with its
//   vowel environment (ء / أ / ئ / آ) — the structure is right, only the
//   spelling differs, so they match after hamza-seat folding ("respelled").
// - 3 words on ت ج ر, where the pattern's ت assimilates into the root's
//   (إدغام: اِتْتَجَرَ → اِتَّجَرَ) — genuinely not a substitution, so the card
//   must fall back to the plain coloured word ("mismatch").

const SLOT_TO_ROOT_INDEX = { "ف": 0, "ع": 1, "ل": 2 }; // ف ع ل

const TASHKEEL = /[ً-ْٰ]/g;

// Fold every written hamza seat to the abstract radical so a seat shift does
// not read as a structural failure. آ is hamza + alef merged, so it unfolds
// to both characters.
function foldHamzaSeats(text) {
  return text
    .replace(/آ/g, "ءا") // آ → ء + ا
    .replace(/[أإؤئ]/g, "ء"); // أ إ ؤ ئ → ء
}

function comparable(text) {
  return foldHamzaSeats(text.normalize("NFC")).replace(TASHKEEL, "");
}

/**
 * Rebuild a word by substituting the root letters into the pattern's
 * ف / ع / ل slots, and grade the result against the word as written.
 *
 * The three slots are filled in ONE pass over the pattern string. Six roots
 * (ع ل م, ع م ل, ع ر ف, ل ب س, ل م س, ط ل ب) contain slot letters themselves,
 * so a sequential replace-chain would corrupt every word of theirs.
 *
 * @param {string} patternArabic  e.g. "مَفْعَلَة"
 * @param {string[]} rootLetters  e.g. ["د", "ر", "س"]
 * @param {string} display        the word as written, e.g. "مَدْرَسَة"
 * @returns {{ built: string, status: "exact" | "respelled" | "mismatch" }}
 *   exact     — built === display; the equation holds letter for letter
 *   respelled — identical after hamza-seat folding; show with a spelling note
 *   mismatch  — the word does not rebuild (assimilation); use the fallback
 */
export function buildSubstitution(patternArabic, rootLetters, display) {
  if (!patternArabic || !display || (rootLetters || []).length !== 3) {
    return { built: "", status: "mismatch" };
  }

  const built = Array.from(patternArabic.normalize("NFC"), (char) => {
    const slot = SLOT_TO_ROOT_INDEX[char];
    return slot === undefined ? char : rootLetters[slot];
  }).join("");

  if (built === display.normalize("NFC")) {
    return { built, status: "exact" };
  }

  if (comparable(built) === comparable(display)) {
    return { built, status: "respelled" };
  }

  return { built, status: "mismatch" };
}
