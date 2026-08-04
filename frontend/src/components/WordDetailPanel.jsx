import { SENTENCE_STATUS, useSentence } from "../hooks/useSentence.js";
import { buildSubstitution } from "../utils/buildSubstitution.js";

// Thin-line section icons, currentColor like k2-think/icons.jsx so the
// cascade keeps them to greens/gold.
function BookIcon({ className }) {
  return (
    <svg className={className} viewBox="0 0 24 24" aria-hidden="true" focusable="false">
      <path
        d="M12 6.5C10.4 5 8.2 4.4 5 4.4v13.2c3.2 0 5.4.6 7 2.1 1.6-1.5 3.8-2.1 7-2.1V4.4c-3.2 0-5.4.6-7 2.1zm0 0v13.2"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function SpeechIcon({ className }) {
  return (
    <svg className={className} viewBox="0 0 24 24" aria-hidden="true" focusable="false">
      <path
        d="M4.5 6.8A2.3 2.3 0 0 1 6.8 4.5h10.4a2.3 2.3 0 0 1 2.3 2.3v7a2.3 2.3 0 0 1-2.3 2.3H10l-4.2 3.4v-3.4h-1a2.3 2.3 0 0 1-2.3-2.3v-5z"
        transform="translate(1.5 0)"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function SproutIcon({ className }) {
  return (
    <svg className={className} viewBox="0 0 24 24" aria-hidden="true" focusable="false">
      <path
        d="M12 20v-7.5M12 12.5C12 8.9 9.4 6.6 5 6.4c.2 4.4 2.5 6.9 7 6.1zm0-1.5c.4-3 2.6-4.7 6.6-4.9-.3 3.9-2.4 5.8-6.2 5.4"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function QuizMarkIcon({ className }) {
  return (
    <svg className={className} viewBox="0 0 24 24" aria-hidden="true" focusable="false">
      <circle cx="12" cy="12" r="9.5" fill="none" stroke="currentColor" strokeWidth="1.6" />
      <path
        d="M9.6 9.4c.2-1.3 1.2-2.2 2.5-2.2 1.4 0 2.5 1 2.5 2.3 0 1.7-2.3 2-2.3 3.6"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinecap="round"
      />
      <circle cx="12.2" cy="16.6" r="1" fill="currentColor" />
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

function capitalize(text) {
  return text ? text.charAt(0).toUpperCase() + text.slice(1) : "";
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
  onStartQuiz = null,
  quizQuestionCount = 0,
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

  const metaParts = [
    capitalize(panelWord.word_type),
    capitalize(pattern?.name || ""),
  ].filter(Boolean);

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

              {(metaParts.length > 0 || pattern?.arabic) && (
                <p className="word-detail-meta">
                  {metaParts.join(" · ")}
                  {pattern?.arabic && (
                    <>
                      {metaParts.length > 0 && " · "}
                      Pattern{" "}
                      <span lang="ar" dir="rtl">
                        {pattern.arabic}
                      </span>
                    </>
                  )}
                </p>
              )}
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
                      {/* One text node so the bidi algorithm keeps the
                          closing paren attached to the Arabic run. */}
                      {root?.arabic
                        ? `Root letters (from ${root.arabic})`
                        : "Root letters"}
                    </span>

                    <span className="word-formation-legend-item">
                      <span
                        className="word-formation-swatch word-formation-swatch--pattern"
                        aria-hidden="true"
                      />
                      Pattern letters (added by the pattern)
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

                <section className="word-detail-section word-detail-keyed-section word-detail-sentence-section">
                  <span className="word-detail-section-icon" aria-hidden="true">
                    <SpeechIcon className="word-detail-section-glyph" />
                  </span>

                  <div className="word-detail-keyed-body">
                    <p className="word-detail-section-label word-detail-section-label--left">
                      In a sentence
                    </p>

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
                  </div>
                </section>
              </>
            )}

            {samePatternWords.length > 0 && (
              <>
                <div className="word-detail-divider" />

                <section className="word-detail-section word-detail-keyed-section">
                  <span className="word-detail-section-icon" aria-hidden="true">
                    <SproutIcon className="word-detail-section-glyph" />
                  </span>

                  <div className="word-detail-keyed-body">
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
                  </div>
                </section>
              </>
            )}

            {typeof onStartQuiz === "function" && quizQuestionCount > 0 && (
              <div className="word-detail-quiz-cta">
                <span className="word-detail-quiz-cta-icon" aria-hidden="true">
                  <QuizMarkIcon className="word-detail-section-glyph" />
                </span>

                <div className="word-detail-quiz-cta-copy">
                  <p className="word-detail-quiz-cta-title">
                    Test your understanding
                  </p>
                  <p className="word-detail-quiz-cta-text">
                    Practice this pattern with {quizQuestionCount} questions.
                  </p>
                </div>

                <button
                  className="word-detail-quiz-cta-button"
                  type="button"
                  onClick={onStartQuiz}
                >
                  Start quiz
                </button>
              </div>
            )}
          </div>
        </>
      )}
    </aside>
  );
}
