import { useMemo, useState } from "react";
import SearchBox from "./SearchBox.jsx";
import ArabicKeyboard from "./ArabicKeyboard.jsx";
import WordTree from "./WordTree.jsx";
import WordQuiz from "./WordQuiz.jsx";
import WordDetailPanel from "./WordDetailPanel.jsx";
import K2ThinkPanel from "./k2-think/K2ThinkPanel.jsx";
import MobileLearningNav from "./MobileLearningNav.jsx";
import MobileTreeViewport from "./MobileTreeViewport.jsx";
import { BulbIcon } from "./k2-think/icons.jsx";
import { useArabicKeyboardInput } from "../hooks/useArabicKeyboardInput.js";

const MOBILE_VIEW_TITLES = {
  details: "Details",
  quiz: "Quiz",
  k2think: "Insights",
};

function normalizeText(value = "") {
  return String(value)
    .trim()
    .replace(/[ًٌٍَُِّْٰـ]/g, "")
    .toLowerCase();
}

export default function LearningInterface({
  learningResult,
  selectedNode,
  isPanelOpen,
  query,
  setQuery,
  keyboardOpen,
  setKeyboardOpen,
  inputRef,
  onSearch,
  onLeafClick,
  onClosePanel,
  onReturnHome,
  isSearching = false,
  insightsPending = false,
}) {
  const searchedWord = learningResult?.normalized_query || "";
  const activeTree = learningResult?.tree || null;
  const leafDetails = learningResult?.leaf_details || {};
  const activeQuizQuestions = learningResult?.quiz || [];
  const selectedLeafDetail = learningResult?.selected_leaf || null;
  const activeWord = selectedLeafDetail?.word || null;
  const k2Think = learningResult?.k2_think || null;

  const [companionTab, setCompanionTab] = useState("details");

  // Phone-only view state: "tree" shows the results panel, anything else
  // shows the companion panel (whose content companionTab already drives).
  // Desktop ignores it — the data attribute only matters inside the phone
  // media query.
  const [mobileView, setMobileView] = useState("tree");

  const shouldShowQuiz = activeQuizQuestions.length > 0;
  const leaves = activeTree?.leaves || [];
  const isNotFound = learningResult?.status === "not_found";

  // A new search result lands on the Tree view. Keyed on the word id, not
  // the result object: the async insights enrichment replaces the object
  // for the same word and must not yank the user back to the tree.
  const resultKey =
    learningResult?.selected_word_id || learningResult?.normalized_query || "";

  const [seenResultKey, setSeenResultKey] = useState(resultKey);

  if (seenResultKey !== resultKey) {
    setSeenResultKey(resultKey);
    setMobileView("tree");
  }

  const searchedNode = useMemo(() => {
    if (!leaves.length) {
      return null;
    }

    const normalizedSearch = normalizeText(searchedWord || query);
    const normalizedSelectedId = normalizeText(learningResult?.selected_word_id);
    const normalizedActiveWord = normalizeText(activeWord?.arabic);

    return (
      leaves.find((leaf) => {
        const leafArabic = normalizeText(leaf.arabic);
        const leafMeaning = normalizeText(leaf.meaning);
        const leafShortMeaning = normalizeText(leaf.short_meaning);
        const leafId = normalizeText(leaf.id);

        return (
          leaf.is_selected ||
          leafId === normalizedSelectedId ||
          leafArabic === normalizedSearch ||
          leafArabic === normalizedActiveWord ||
          leafMeaning === normalizedSearch ||
          leafShortMeaning === normalizedSearch ||
          leafId === normalizedSearch
        );
      }) || leaves[0]
    );
  }, [
    leaves,
    searchedWord,
    query,
    activeWord,
    learningResult?.selected_word_id,
  ]);

  const displayTree = useMemo(() => {
    if (!activeTree?.leaves?.length || !searchedNode?.id) {
      return activeTree;
    }

    const searchedNodeId = normalizeText(searchedNode.id);

    const searchedLeaf = activeTree.leaves.find(
      (leaf) => normalizeText(leaf.id) === searchedNodeId
    );

    if (!searchedLeaf) {
      return activeTree;
    }

    const remainingLeaves = activeTree.leaves.filter(
      (leaf) => normalizeText(leaf.id) !== searchedNodeId
    );

    return {
      ...activeTree,
      leaves: [searchedLeaf, ...remainingLeaves],
    };
  }, [activeTree, searchedNode]);

  const activeCompanionNode = selectedNode || searchedNode;

  const activeCompanionDetail =
    activeCompanionNode?.id && leafDetails[activeCompanionNode.id]
      ? leafDetails[activeCompanionNode.id]
      : selectedLeafDetail;

  const hasTree = Boolean(leaves.length);
  const hasCompanionContent = Boolean(activeCompanionDetail || shouldShowQuiz);

  function handleSubmit() {
    setCompanionTab("details");
    setMobileView("tree");
    onSearch(query);
  }

  function handleTryAnotherWord() {
    setQuery("");
    inputRef?.current?.focus();
  }

  function handleLeafClick(node) {
    setCompanionTab("details");
    // Tapping a leaf on the phone goes straight to its Details view.
    setMobileView("details");

    if (typeof onLeafClick === "function") {
      onLeafClick(node);
    }
  }

  function handleMobileNavigate(view) {
    if (view !== "tree") {
      if (isNotFound) {
        return;
      }

      if (view === "quiz" && !shouldShowQuiz) {
        return;
      }

      setCompanionTab(view === "insights" ? "k2think" : view);
    }

    setMobileView(view);
  }

  function handleTabChange(nextTab) {
    if (isNotFound) {
      return;
    }

    if (nextTab === "quiz" && !shouldShowQuiz) {
      return;
    }

    setCompanionTab(nextTab);
  }

  const isOriginCompanionNode = useMemo(() => {
    if (!activeCompanionNode) {
      return false;
    }

    return (
      activeCompanionNode.is_selected ||
      normalizeText(activeCompanionNode.id) ===
        normalizeText(learningResult?.selected_word_id)
    );
  }, [activeCompanionNode, learningResult?.selected_word_id]);

  const { insertText, handleBackspace, handleSpace, handleEnter } =
    useArabicKeyboardInput({
      value: query,
      setValue: setQuery,
      inputRef,
      onSubmit: handleSubmit,
    });

  return (
    <div className="learning-main" data-mobile-view={mobileView}>
      <div
        className={`learning-panels ${
          companionTab === "quiz" ? "learning-panels--quiz-active" : ""
        }`}
      >
        <section className="learning-results-panel" aria-label="Word tree results">
          <button
            type="button"
            className="learning-home-button"
            onClick={onReturnHome}
          >
            <svg
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2.4"
              strokeLinecap="round"
              strokeLinejoin="round"
              aria-hidden="true"
            >
              <path d="M15 5l-7 7 7 7" />
            </svg>
            <span>Home</span>
          </button>

          <div className="learning-search-area">
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
          </div>

          <div className="tree-stage" aria-live="polite">
            <MobileTreeViewport>
              <WordTree
                activeTree={displayTree}
                selectedNode={activeCompanionNode}
                onLeafClick={handleLeafClick}
                searchTerm={query}
                isQuizActive={companionTab === "quiz"}
                notFoundReason={isNotFound ? learningResult?.reason || "" : ""}
                onTryAnotherWord={handleTryAnotherWord}
              />
            </MobileTreeViewport>

            {companionTab === "quiz" && hasTree && (
              <div className="tree-quiz-overlay" aria-hidden="true">
                <p className="tree-quiz-overlay-title">Answer from memory</p>
                <p className="tree-quiz-overlay-text">
                  Tree labels are hidden during the quiz.
                </p>
              </div>
            )}
          </div>

          <footer className="learning-footer">
            <img
              className="learning-footer-icon"
              src="/assets/decor/footer-learning-page.png"
              alt=""
              aria-hidden="true"
            />
            <span>
              {isNotFound
                ? "Try another word to grow a new tree."
                : companionTab === "quiz"
                  ? "Answer from memory. Switch back to Details to review."
                  : "Click any leaf on the tree to explore its meaning."}
            </span>
          </footer>
        </section>

        <aside className="learning-companion-panel" aria-label="Learning companion">
          <header className="mobile-context-header">
            <span className="mobile-context-title">
              {MOBILE_VIEW_TITLES[companionTab] || "Details"}
            </span>

            {!isNotFound && activeCompanionNode?.arabic && (
              <span className="mobile-context-word" lang="ar" dir="rtl">
                {activeCompanionNode.arabic}
              </span>
            )}
          </header>

          <div className="companion-tabs" role="tablist" aria-label="Learning tools">
            <button
              type="button"
              role="tab"
              aria-selected={companionTab === "details"}
              className={`companion-tab ${
                companionTab === "details" ? "companion-tab--active" : ""
              }`}
              onClick={() => handleTabChange("details")}
              disabled={isNotFound}
            >
              <img
                className="companion-tab-icon"
                src="/assets/icons/details.svg"
                alt=""
                aria-hidden="true"
              />
              Details
            </button>

            <button
              type="button"
              role="tab"
              aria-selected={companionTab === "quiz"}
              className={`companion-tab ${
                companionTab === "quiz" ? "companion-tab--active" : ""
              }`}
              onClick={() => handleTabChange("quiz")}
              disabled={isNotFound || !shouldShowQuiz}
            >
              <img
                className="companion-tab-icon"
                src="/assets/icons/quiz.svg"
                alt=""
                aria-hidden="true"
              />
              Quiz
            </button>

            <button
              type="button"
              role="tab"
              aria-selected={companionTab === "k2think"}
              className={`companion-tab ${
                companionTab === "k2think" ? "companion-tab--active" : ""
              }`}
              onClick={() => handleTabChange("k2think")}
              disabled={isNotFound}
            >
              <span className="companion-tab-icon companion-tab-icon--insight" aria-hidden="true">
                <BulbIcon className="companion-tab-glyph" />
              </span>
              Insights
            </button>
          </div>

          <div className="companion-panel-body">
            {isNotFound && (
              <div className="companion-empty-state companion-empty-state--not-found">
                <img
                  className="companion-empty-illustration"
                  src="/assets/decor/leaf-rightside.png"
                  alt=""
                  aria-hidden="true"
                />
                <p className="companion-empty-title">Nothing to explore yet</p>
                <div className="companion-empty-divider" aria-hidden="true" />
                <p className="companion-empty-text">
                  When WAZN finds a word, its root, pattern, family, quiz, and
                  insights will appear here.
                </p>
              </div>
            )}

            {!isNotFound && companionTab === "details" && (
              <WordDetailPanel
                selectedDetail={activeCompanionDetail}
                selectedNode={activeCompanionNode}
                isOpen={Boolean(activeCompanionDetail || activeCompanionNode)}
                isOriginNode={isOriginCompanionNode}
                onClose={onClosePanel}
                onSearch={onSearch}
              />
            )}

            {!isNotFound && companionTab === "quiz" && (
              <WordQuiz
                // Keyed on question source too: when the K2-upgraded quiz
                // replaces the templates mid-session, the quiz must remount —
                // its per-question state is seeded in a useState initializer.
                key={`${searchedWord}:${activeQuizQuestions[0]?.source || "template"}`}
                questions={activeQuizQuestions}
              />
            )}

            {!isNotFound && companionTab === "k2think" && (
              <K2ThinkPanel
                k2Think={k2Think}
                word={activeWord?.arabic || searchedWord}
                insightsPending={insightsPending}
              />
            )}

            {!isNotFound && !hasCompanionContent && (
              <div className="companion-empty-state">
                <p className="companion-empty-title">Start exploring</p>
                <p className="companion-empty-text">
                  Search for an Arabic word to see its family tree, details, and practice
                  quiz.
                </p>
              </div>
            )}
          </div>
        </aside>
      </div>

      <MobileLearningNav
        activeView={mobileView}
        onNavigate={handleMobileNavigate}
        onHome={onReturnHome}
        quizAvailable={shouldShowQuiz}
        viewsDisabled={isNotFound}
      />
    </div>
  );
}