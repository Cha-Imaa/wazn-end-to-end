import { SENTENCE_STATUS, useSentence } from "../hooks/useSentence.js";

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
  const breakdownSegments = selectedDetail?.breakdown?.segments || [];
  const samePatternWords = selectedDetail?.same_pattern_words || [];

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

            <section className="word-detail-section">
              <p className="word-detail-section-label">Pattern</p>

              <p className="word-detail-pattern" lang="ar" dir="rtl">
                {pattern?.arabic || "—"}
              </p>

              {pattern?.name && (
                <p className="word-detail-pattern-name">{pattern.name}</p>
              )}

              {(pattern?.meaning_effect || pattern?.short_explanation) && (
                <p className="word-detail-pattern-meaning">
                  {pattern.meaning_effect || pattern.short_explanation}
                </p>
              )}
            </section>

            <div className="word-detail-divider" />

            <section className="word-detail-section">
              <p className="word-detail-section-label">Word Breakdown</p>

              <p className="word-detail-breakdown-word" lang="ar" dir="rtl">
                {breakdownSegments.length ? (
                  breakdownSegments.map((part, index) => (
                    <span
                      key={`${part.text}-${index}`}
                      className={`word-breakdown-part word-breakdown-part--${part.type}`}
                    >
                      {part.text}
                    </span>
                  ))
                ) : (
                  <span className="word-breakdown-part word-breakdown-part--pattern">
                    {panelWord.arabic}
                  </span>
                )}
              </p>

              <div className="word-detail-legend">
                <div className="word-detail-legend-item">
                  <span className="word-detail-legend-dot word-detail-legend-dot--root" />
                  <span>root letters</span>
                </div>

                <div className="word-detail-legend-item">
                  <span className="word-detail-legend-dot word-detail-legend-dot--pattern" />
                  <span>pattern letters</span>
                </div>
              </div>
            </section>

            <div className="word-detail-divider" />

            <section className="word-detail-section word-detail-explanation-section">
              <p className="word-detail-section-label">Explanation</p>

              <p className="word-detail-explanation">
                {selectedDetail?.explanation || "Details coming next."}
              </p>
            </section>

            {showSentenceSection && (
              <>
                <div className="word-detail-divider" />

                <section className="word-detail-section word-detail-sentence-section">
                  <p className="word-detail-section-label">In a Sentence</p>

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

                      <p className="word-detail-sentence-source">
                        Generated live by K2
                      </p>
                    </>
                  )}
                </section>
              </>
            )}

            <div className="word-detail-divider" />

            <section className="word-detail-section">
              <p className="word-detail-section-label">
                Same Pattern
                {pattern?.arabic && (
                  <span
                    className="word-detail-section-label-arabic"
                    lang="ar"
                    dir="rtl"
                  >
                    {" "}
                    ({pattern.arabic})
                  </span>
                )}
              </p>

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

                    <p className="same-pattern-english">
                      {word.short_meaning || word.meaning}
                    </p>
                  </button>
                ))}
              </div>
            </section>
          </div>
        </>
      )}
    </aside>
  );
}