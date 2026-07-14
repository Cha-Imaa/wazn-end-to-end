import { forwardRef } from "react";

const SearchBox = forwardRef(function SearchBox(
  {
    value,
    onChange,
    onSubmit,
    keyboardOpen,
    onToggleKeyboard,
    isLoading = false,
  },
  ref
) {
  const hasValue = Boolean(String(value || "").length);

  function handleSubmit(event) {
    event.preventDefault();

    if (isLoading) {
      return;
    }

    onSubmit();
  }

  function handleKeyDown(event) {
    if (event.key === "Enter") {
      event.preventDefault();

      if (!isLoading) {
        onSubmit();
      }
    }
  }

  function handleClear() {
    onChange("");

    requestAnimationFrame(() => {
      ref?.current?.focus();
    });
  }

  return (
    <form className="search-row" role="search" onSubmit={handleSubmit}>
      <label className="sr-only" htmlFor="arabic-search">
        Search Arabic word
      </label>

      <button
        className={`keyboard-toggle ${keyboardOpen ? "is-active" : ""}`}
        type="button"
        onClick={onToggleKeyboard}
        aria-label={keyboardOpen ? "Hide Arabic keyboard" : "Show Arabic keyboard"}
        aria-pressed={keyboardOpen}
      >
        <img
          className="keyboard-icon-img"
          src="/assets/icons/keyboard.png"
          alt=""
          aria-hidden="true"
        />
      </button>

      <div className="search-input-wrap">
        <input
          ref={ref}
          id="arabic-search"
          className="search-input"
          value={value}
          onChange={(event) => onChange(event.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Search any Arabic word..."
          autoComplete="off"
          spellCheck="false"
          inputMode="text"
          dir="auto"
          lang="ar"
          aria-busy={isLoading}
        />
      </div>

      {hasValue && (
        <button
          className="search-clear-button"
          type="button"
          onClick={handleClear}
          aria-label="Clear search text"
          title="Clear search"
        >
          <img
            className="search-clear-icon-img"
            src="/assets/icons/clear.png"
            alt=""
            aria-hidden="true"
            onError={(event) => {
              event.currentTarget.style.display = "none";
              event.currentTarget.parentElement.textContent = "×";
            }}
          />
        </button>
      )}

      <button
        className="find-root-button search-submit-button"
        type="submit"
        aria-label={isLoading ? "Searching" : "Find root"}
        disabled={isLoading}
      >
        <img
          className="search-action-icon-img"
          src="/assets/icons/search.png"
          alt=""
          aria-hidden="true"
        />
      </button>
    </form>
  );
});

export default SearchBox;