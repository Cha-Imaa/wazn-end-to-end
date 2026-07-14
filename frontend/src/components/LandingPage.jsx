import { landingExamples } from "../data/index.js";
import { useArabicKeyboardInput } from "../hooks/useArabicKeyboardInput.js";
import SearchBox from "./SearchBox.jsx";
import ArabicKeyboard from "./ArabicKeyboard.jsx";
import ExampleCard from "./ExampleCard.jsx";

export default function LandingPage({
  query,
  setQuery,
  keyboardOpen,
  setKeyboardOpen,
  inputRef,
  onSearch,
  onExampleSearch = onSearch,
  isSearching = false,
}) {
  function handleSubmit() {
    onSearch(query);
  }
  

  const { insertText, handleBackspace, handleSpace, handleEnter } =
    useArabicKeyboardInput({
      value: query,
      setValue: setQuery,
      inputRef,
      onSubmit: handleSubmit,
    });

  return (
    <div className="main">
      <div className="content-column">
        <section className="hero">
          <div className="hero-brand-lockup" aria-label="Wazn">
            <div className="hero-brand-main">
              <h1 className="hero-english">wazn</h1>

              <img
                className="hero-brand-sprout"
                src="/assets/decor/leaves-sprout-hero.png"
                alt=""
                aria-hidden="true"
              />
            </div>
          </div>

          <div className="hero-title-divider" aria-hidden="true" />

          <p className="hero-title">Learn Arabic from the root up.</p>

          <p className="hero-subtitle">
            Search any word to see its root, pattern, and family.
          </p>
        </section>

        <section className="search-area">
          <SearchBox
            ref={inputRef}
            value={query}
            onChange={setQuery}
            onSubmit={handleSubmit}
            keyboardOpen={keyboardOpen}
            onToggleKeyboard={() => setKeyboardOpen((open) => !open)}
            isLoading={isSearching}
          />
          {keyboardOpen && (
            <ArabicKeyboard
              onInsert={insertText}
              onBackspace={handleBackspace}
              onSpace={handleSpace}
              onEnter={handleEnter}
            />
          )}
        </section>

        <section className="examples-section">
          <div className="examples-title-row">
            <h2 className="examples-title">Try these examples</h2>
          </div>

          <img
            className="examples-sprout"
            src="/assets/decor/leaves-small.png"
            alt=""
            aria-hidden="true"
          />

          <div className="examples-grid">
            {landingExamples.map((example) => (
              <ExampleCard
                key={example.id}
                arabic={example.arabic}
                english={example.english}
                imageSrc={example.imageSrc}
                alt={example.alt}
                onClick={() => onExampleSearch(example)}
              />
            ))}
          </div>
        </section>
      </div>
    </div>
  );
}