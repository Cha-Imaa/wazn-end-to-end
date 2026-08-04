import { SENTENCE_STATUS, useSentence } from "../hooks/useSentence.js";
import { buildSubstitution } from "../utils/buildSubstitution.js";

// Thin-line section icons, currentColor like k2-think/icons.jsx so the
// cascade keeps them to greens/gold.
function BookIcon({ className }) {
  return (
    <svg className={className} viewBox="0 0 24 24" aria-hidden="true" focusable="false">
      <path
        d="M3.5 5.6c3 0 5.8.9 8.5 2.7 2.7-1.8 5.5-2.7 8.5-2.7v12.1c-3 0-5.8.9-8.5 2.7-2.7-1.8-5.5-2.7-8.5-2.7z"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <path
        d="M12 8.3v12.1"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
      />
    </svg>
  );
}

function SpeechIcon({ className }) {
  return (
    <svg className={className} viewBox="0 0 24 24" aria-hidden="true" focusable="false">
      <path
        d="M12 4.6c-4.6 0-8.3 3-8.3 6.8 0 2.1 1.2 4 3 5.2-.1 1-.5 1.9-1.2 2.8 1.5-.2 2.8-.7 3.8-1.5.9.2 1.8.3 2.7.3 4.6 0 8.3-3 8.3-6.8s-3.7-6.8-8.3-6.8z"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <circle cx="8.6" cy="11.4" r="0.95" fill="currentColor" />
      <circle cx="12" cy="11.4" r="0.95" fill="currentColor" />
      <circle cx="15.4" cy="11.4" r="0.95" fill="currentColor" />
    </svg>
  );
}

function SproutIcon({ className }) {
  return (
    <svg className={className} viewBox="0 0 24 24" aria-hidden="true" focusable="false">
      <path
        d="M12 20.5V12"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
      />
      <path
        d="M11.8 12.6C11.6 8.8 9.2 6.8 5 6.5c.2 4.1 2.5 6.3 6.8 6.1z"
        fill="currentColor"
        opacity="0.8"
      />
      <path
        d="M12.2 11.2c.2-3 2.2-4.6 6-4.8-.2 3.5-2.1 5.3-6 5z"
        fill="currentColor"
        opacity="0.5"
      />
    </svg>
  );
}

function getPanelWord(selectedDetail, selectedNode) {
  const detailWord = selectedDetail?.word;

  return {
    id: detailWord?.id || selectedNode?.id || "",
    arabic: detailWord?.arabic || selectedNode?.arabic || "",
    transliteration: detailWord?.transliteration || selectedNode?.transliteration || "",
    meaning:
      detailWord?.meaning ||
      detailWord?.short_meaning ||
      selectedNode?.meaning ||
      selectedNode?.short_meaning ||
      "",
    word_type: detailWord?.word_type || "",
    level: detailWord?.level || "",
  };
}

function getSamePatternSearchValue(word) {
  return word?.arabic || word?.id || "";
}

function toDottedTransliteration(text) {
  return (text || "").split("-").filter(Boolean).join(" · ");
}

function BreakdownWord({ segments, fallback }) {
  if (!segments.length) {
    return <span className="word-breakdown-part word-breakdown-part--pattern">{fallback}</span>;
  }

  return segments.map((part, index) => (
    <span
      key={`${part.text}-${index}`}
      className={`word-breakdown-part word-breakdown-part--${part.type}`}
    >
      {part.text}
    </span>
  ));
}

export default function WordDetailPanel({
  selectedDetail = null,
  selectedNode = null,
  isOpen,
  isOriginNode = false,
  onClose,
  onSearch,
}) {
  const shouldShowPanel = isOpen && (selectedDetail || selectedNode);
  const panelWord = getPanelWord(selectedDetail, selectedNode);

  const pattern = selectedDetail?.pattern || null;
  const root = selectedDetail?.root || null;
  const breakdown = selectedDetail?.breakdown || null;
  const breakdownSegments = breakdown?.segments || [];
  const samePatternWords = selectedDetail?.same_pattern_words || [];

  const rootLetters =
    breakdown?.root_letters || (root?.arabic ? root.arabic.split(" ") : []);
  const substitution = buildSubstitution(
    pattern?.arabic || "",
    rootLetters,
    breakdown?.display || panelWord.arabic,
  );
  // Only lay the word out as an equation when the substitution actually
  // rebuilds it — the panel never shows a mapping it can't justify.
  const showEquation =
    Boolean(pattern?.arabic) &&
    breakdownSegments.length > 0 &&
    substitution.status !== "mismatch";

  // Generated per displayed word, so it arrives after first paint: pending
  // while the agent runs, and simply absent when nothing valid comes back.
  const sentenceEntry = useSentence(shouldShowPanel ? panelWord.arabic : "");
  const showSentenceSection =
    sentenceEntry && sentenceEntry.status !== SENTENCE_STATUS.ABSENT;

  return (
    <aside
      className={`word-detail-panel ${
        shouldShowPanel ? "word-detail-panel--open" : ""
      } ${isOriginNode ? "word-detail-panel--origin" : ""}`}
      aria-label="Selected word details"
      aria-hidden={!shouldShowPanel}
    >
      {shouldShowPanel && (
        <>
          <button
            className="word-detail-close"
            type="button"
            onClick={onClose}
            aria-label="Close word details"
          >
            ×
          </button>

          <div className="word-detail-shell-content">
            <header className="word-detail-header">
              <h2 className="word-detail-arabic" lang="ar" dir="rtl">
                {panelWord.arabic}
              </h2>

              {panelWord.transliteration && (
                <p className="word-detail-transliteration">
                  {panelWord.transliteration}
                </p>
              )}

              <p className="word-detail-english">{panelWord.meaning}</p>
            </header>

            <div className="word-detail-divider" />

            {breakdownSegments.length > 0 && (
              <section className="word-detail-section word-detail-formation-section">
                <p className="word-detail-section-label word-detail-section-label--left">
                  How it is formed
                </p>

                <div className="word-formation-card">
                  {showEquation ? (
                    <div className="word-formation-row">
                      <div className="word-formation-cell">
                        <p className="word-formation-cell-label">Root</p>
                        <p className="word-formation-root" lang="ar" dir="rtl">
                          {rootLetters.join(" ")}
                        </p>
                        {root?.transliteration && (
                          <p className="word-formation-cell-sub">
                            {toDottedTransliteration(root.transliteration)}
                          </p>
                        )}
                      </div>

                      <span className="word-formation-op" aria-hidden="true">
                        +
                      </span>

                      <div className="word-formation-cell">
                        <p className="word-formation-cell-label">Pattern</p>
                        <p className="word-formation-pattern" lang="ar" dir="rtl">
                          {pattern.arabic}
                        </p>
                        {pattern?.name && (
                          <p className="word-formation-cell-sub">{pattern.name}</p>
                        )}
                      </div>

                      <span className="word-formation-op" aria-hidden="true">
                        =
                      </span>

                      <div className="word-formation-cell">
                        <p className="word-formation-cell-label">Word</p>
                        <p className="word-formation-word" lang="ar" dir="rtl">
                          <BreakdownWord
                            segments={breakdownSegments}
                            fallback={panelWord.arabic}
                          />
                        </p>
                        {panelWord.transliteration && (
                          <p className="word-formation-cell-sub">
                            {panelWord.transliteration}
                          </p>
                        )}
                      </div>
                    </div>
                  ) : (
                    <p className="word-formation-fallback" lang="ar" dir="rtl">
                      <BreakdownWord
                        segments={breakdownSegments}
                        fallback={panelWord.arabic}
                      />
                    </p>
                  )}

                  {substitution.status === "respelled" && (
                    <p className="word-formation-note">
                      The hamza&rsquo;s written seat shifts as the letters join —
                      the structure above still holds.
                    </p>
                  )}

                  {!showEquation && breakdownSegments.length > 0 && (
                    <p className="word-formation-note">
                      In this word the pattern&rsquo;s letters merge with the root
                      as they join (idghām), so the spelling shifts.
                    </p>
                  )}

                  <div className="word-formation-legend">
                    <span className="word-formation-legend-item">
                      <span
                        className="word-formation-swatch word-formation-swatch--root"
                        aria-hidden="true"
                      />
                      Root letters
                    </span>

                    <span className="word-formation-legend-item">
                      <span
                        className="word-formation-swatch word-formation-swatch--pattern"
                        aria-hidden="true"
                      />
                      Pattern letters
                    </span>
                  </div>
                </div>
              </section>
            )}

            {selectedDetail?.explanation && (
              <>
                <div className="word-detail-divider" />

                <section className="word-detail-section word-detail-keyed-section">
                  <span className="word-detail-section-icon" aria-hidden="true">
                    <BookIcon className="word-detail-section-glyph" />
                  </span>

                  <div className="word-detail-keyed-body">
                    <p className="word-detail-section-label word-detail-section-label--left">
                      Why this means &ldquo;{panelWord.meaning}&rdquo;
                    </p>

                    <p className="word-detail-explanation">
                      {selectedDetail.explanation}
                    </p>
                  </div>
                </section>
              </>
            )}

            {showSentenceSection && (
              <>
                <div className="word-detail-divider" />

                <section className="word-detail-section word-detail-sentence-section">
                  {/* Header keeps the icon-gutter look, but the sentence
                      itself spans the panel so it centres truly. */}
                  <div className="word-detail-keyed-header">
                    <span className="word-detail-section-icon" aria-hidden="true">
                      <SpeechIcon className="word-detail-section-glyph" />
                    </span>

                    <p className="word-detail-section-label word-detail-section-label--left">
                      In a sentence
                    </p>
                  </div>

                  {sentenceEntry.status === SENTENCE_STATUS.PENDING ? (
                    <p className="word-detail-sentence-pending">
                      Writing an example sentence…
                    </p>
                  ) : (
                    <>
                      <p
                        className="word-detail-sentence-arabic"
                        lang="ar"
                        dir="rtl"
                      >
                        {sentenceEntry.sentence.arabic}
                      </p>

                      <p className="word-detail-sentence-translation">
                        {sentenceEntry.sentence.translation}
                      </p>
                    </>
                  )}
                </section>
              </>
            )}

            {samePatternWords.length > 0 && (
              <>
                <div className="word-detail-divider" />

                <section className="word-detail-section word-detail-more-words-section">
                  {/* Icon-gutter header, full-width grid — keeps the cards
                      centred in the panel rather than pushed right. */}
                  <div className="word-detail-keyed-header">
                    <span className="word-detail-section-icon" aria-hidden="true">
                      <SproutIcon className="word-detail-section-glyph" />
                    </span>

                    <p className="word-detail-section-label word-detail-section-label--left">
                      More words on{" "}
                      {pattern?.arabic && (
                        <span
                          className="word-detail-section-label-arabic"
                          lang="ar"
                          dir="rtl"
                        >
                          {pattern.arabic}
                        </span>
                      )}
                    </p>
                  </div>

                  <div className="same-pattern-grid">
                    {samePatternWords.slice(0, 3).map((word) => (
                      <button
                        className="same-pattern-card"
                        key={word.id}
                        type="button"
                        onClick={() => onSearch(getSamePatternSearchValue(word))}
                      >
                        <p className="same-pattern-arabic" lang="ar" dir="rtl">
                          {word.arabic}
                        </p>

                        {word.transliteration && (
                          <p className="same-pattern-transliteration">
                            {word.transliteration}
                          </p>
                        )}

                        <p className="same-pattern-english">
                          {word.short_meaning || word.meaning}
                        </p>
                      </button>
                    ))}
                  </div>
                </section>
              </>
            )}

          </div>
        </>
      )}
    </aside>
  );
}
