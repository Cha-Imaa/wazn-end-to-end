import { useRef, useState } from "react";
import AppShell from "./components/AppShell.jsx";
import LandingPage from "./components/LandingPage.jsx";
import LearningInterface from "./components/LearningInterface.jsx";
import {
  resolveInsightsResult,
  resolveSearchResult,
} from "./services/learningDataService.js";

export default function App() {
  const [view, setView] = useState("landing");
  const [query, setQuery] = useState("");
  const [keyboardOpen, setKeyboardOpen] = useState(false);

  const [learningResult, setLearningResult] = useState(null);

  const [selectedNode, setSelectedNode] = useState(null);
  const [isPanelOpen, setIsPanelOpen] = useState(false);
  const [isSearching, setIsSearching] = useState(false);

  // True while GET /api/insights is in flight. The learning view has already
  // rendered deterministic content by then, so the Insights tab must say which
  // steps are still waiting rather than presenting sample text as final.
  const [insightsPending, setInsightsPending] = useState(false);

  const inputRef = useRef(null);

  // Increments on every search so a slow /api/insights response for an earlier
  // word can never overwrite the result of a later one.
  const searchSeqRef = useRef(0);

  function resetSelectedNode() {
    setSelectedNode(null);
    setIsPanelOpen(false);
  }

  function resetLearningState() {
    setLearningResult(null);
    setInsightsPending(false);
    resetSelectedNode();
  }

  function showLearningResult(result, cleanedQuery) {
    setLearningResult(result);
    resetSelectedNode();

    setQuery(cleanedQuery);
    setKeyboardOpen(false);
    setView("learning");
  }

  async function handleSearch(rawWord) {
    const cleaned = rawWord.trim();

    if (!cleaned || isSearching) {
      return;
    }

    setIsSearching(true);
    // Cleared up front so a not_found or failed search cannot leave the
    // previous word's pending flag set.
    setInsightsPending(false);

    const searchSeq = ++searchSeqRef.current;

    try {
      const result = await resolveSearchResult(cleaned);
      showLearningResult(result, cleaned);

      if (result.status === "found") {
        // Deliberately not awaited: /api/analyze renders immediately and the
        // K2 enrichment (live Insights + upgraded quiz) swaps in on arrival.
        setInsightsPending(true);
        enrichWithInsights(cleaned, searchSeq);
      }
    } finally {
      setIsSearching(false);
    }
  }

  async function enrichWithInsights(word, searchSeq) {
    const insights = await resolveInsightsResult(word);

    // A superseded search must not clear the newer one's pending state.
    if (searchSeq !== searchSeqRef.current) {
      return;
    }

    setInsightsPending(false);

    if (!insights || insights.status !== "found") {
      return;
    }

    setLearningResult((previous) => {
      if (!previous || previous.selected_word_id !== insights.selected_word_id) {
        return previous;
      }

      const upgradedQuiz =
        Array.isArray(insights.quiz) && insights.quiz.length > 0
          ? insights.quiz
          : previous.quiz;

      return {
        ...previous,
        k2_think: insights.k2_think || previous.k2_think,
        quiz: upgradedQuiz,
      };
    });
  }

  function handleStaticExampleSearch(example) {
    const cleaned =
      example?.plain?.trim() ||
      example?.arabic?.trim() ||
      example?.staticDataKey?.trim() ||
      "";

    if (!cleaned) {
      return;
    }

    handleSearch(cleaned);
  }

  function handleLeafClick(node) {
    if (!node) {
      return;
    }

    if (selectedNode?.id === node.id) {
      resetSelectedNode();
      return;
    }

    setSelectedNode(node);
    setIsPanelOpen(true);
  }

  function handleClosePanel() {
    resetSelectedNode();
  }

  function handleLogoClick() {
    setView("landing");
    setQuery("");
    setKeyboardOpen(false);
    resetLearningState();
  }

  return (
    <AppShell
      keyboardOpen={keyboardOpen}
      onLogoClick={handleLogoClick}
      variant={view}
    >
      {view === "landing" ? (
        <LandingPage
          query={query}
          setQuery={setQuery}
          keyboardOpen={keyboardOpen}
          setKeyboardOpen={setKeyboardOpen}
          inputRef={inputRef}
          onSearch={handleSearch}
          onExampleSearch={handleStaticExampleSearch}
          isSearching={isSearching}
        />
      ) : (
        <LearningInterface
          learningResult={learningResult}
          selectedNode={selectedNode}
          isPanelOpen={isPanelOpen}
          query={query}
          setQuery={setQuery}
          keyboardOpen={keyboardOpen}
          setKeyboardOpen={setKeyboardOpen}
          inputRef={inputRef}
          onSearch={handleSearch}
          onLeafClick={handleLeafClick}
          onClosePanel={handleClosePanel}
          onReturnHome={handleLogoClick}
          isSearching={isSearching}
          insightsPending={insightsPending}
        />
      )}
    </AppShell>
  );
}