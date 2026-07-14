const letterRows = [
  ["ض", "ص", "ث", "ق", "ف", "غ", "ع", "ه", "خ", "ح", "ج"],
  ["ش", "س", "ي", "ب", "ل", "ا", "ت", "ن", "م", "ك", "ط"],
  ["ئ", "ء", "ؤ", "ر", "لا", "ى", "و", "ز", "ظ", "ذ", "د", "ة"],
];

const diacritics = [
  { label: "◌َ", value: "\u064E", name: "fatha" },
  { label: "◌ُ", value: "\u064F", name: "damma" },
  { label: "◌ِ", value: "\u0650", name: "kasra" },
  { label: "◌ْ", value: "\u0652", name: "sukun" },
  { label: "◌ّ", value: "\u0651", name: "shadda" },
  { label: "◌ً", value: "\u064B", name: "fathatan" },
  { label: "◌ٌ", value: "\u064C", name: "dammatan" },
  { label: "◌ٍ", value: "\u064D", name: "kasratan" },
];

export default function ArabicKeyboard({
  onInsert,
  onBackspace,
  onSpace,
  onEnter,
}) {
  return (
    <div className="keyboard-panel" aria-label="Arabic keyboard">
      <div className="keyboard-section">
        {letterRows.map((row, rowIndex) => (
          <div className="keyboard-row" key={`letter-row-${rowIndex}`}>
            {row.map((letter) => (
              <button
                key={letter}
                type="button"
                className="keyboard-key letter-key"
                onClick={() => onInsert(letter)}
                aria-label={`Insert Arabic letter ${letter}`}
              >
                {letter}
              </button>
            ))}
          </div>
        ))}
      </div>

      <div className="keyboard-section">

        <div className="keyboard-row diacritics-row">
          {diacritics.map((mark) => (
            <button
              key={mark.name}
              type="button"
              className="keyboard-key diacritic-key"
              onClick={() => onInsert(mark.value)}
              aria-label={`Insert ${mark.name}`}
            >
              {mark.label}
            </button>
          ))}
        </div>
      </div>

      <div className="keyboard-row keyboard-actions">
        <button
          type="button"
          className="keyboard-key space"
          onClick={onSpace}
          aria-label="Insert space"
        >
          space
        </button>

        <button
          type="button"
          className="keyboard-key icon-key"
          onClick={onBackspace}
          aria-label="Backspace"
        >
          <img src="/assets/icons/backspace.png" alt="" aria-hidden="true" />
        </button>

        <button
          type="button"
          className="keyboard-key icon-key"
          onClick={onEnter}
          aria-label="Enter search"
        >
          <img src="/assets/icons/enter.png" alt="" aria-hidden="true" />
        </button>
      </div>
    </div>
  );
}