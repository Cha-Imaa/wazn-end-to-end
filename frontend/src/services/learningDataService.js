import {
  fetchInsightsFromBackend,
  fetchLearningResultFromBackend,
  fetchSentenceFromBackend,
} from "../api/learningApi.js";
import { normalizeArabic } from "../utils/normalizeArabic.js";

export const LEARNING_DATA_SOURCE = {
  BACKEND: "backend",
  NOT_FOUND: "not_found",
};

export function compactArabic(word) {
  return normalizeArabic(word).replace(/\s+/g, "");
}

function createNotFoundResult(query) {
  const normalizedQuery = compactArabic(query);

  return {
    status: "not_found",
    query,
    normalized_query: normalizedQuery,
    selected_word_id: null,
    root: null,
    tree: {
      trunk: null,
      leaves: [],
    },
    leaf_details: {},
    selected_leaf: null,
    quiz: [],
    source: LEARNING_DATA_SOURCE.NOT_FOUND,
    reason: "empty_query",
    message: "Empty query.",
  };
}

function createLearningError(error) {
  return {
    message:
      error instanceof Error
        ? error.message
        : "Something went wrong while loading the learning result.",
    name: error?.name || "LearningDataError",
    details: error?.details || {},
  };
}

export async function resolveInsightsResult(rawWord) {
  const query = rawWord.trim();

  if (!query) {
    return null;
  }

  try {
    return await fetchInsightsFromBackend(query);
  } catch (error) {
    // Insights are enrichment only — the deterministic view already rendered,
    // so a failed fetch is silent and the caller just keeps what it has.
    console.error("Backend insights fetch failed.", error);
    return null;
  }
}

export async function resolveSentenceResult(rawWord) {
  const query = rawWord.trim();

  if (!query) {
    return null;
  }

  try {
    return await fetchSentenceFromBackend(query);
  } catch (error) {
    // The sentence is enrichment only — the Details tab renders without it,
    // so a failed fetch means the section is simply absent.
    console.error("Backend sentence fetch failed.", error);
    return null;
  }
}

export async function resolveSearchResult(rawWord) {
  const query = rawWord.trim();

  if (!query) {
    return createNotFoundResult("");
  }

  try {
    const backendResult = await fetchLearningResultFromBackend(query);

    return {
      ...backendResult,
      source: backendResult.source || LEARNING_DATA_SOURCE.BACKEND,
    };
  } catch (error) {
    console.error("Backend learning search failed.", error);

    return {
      ...createNotFoundResult(query),
      reason: "backend_error",
      message: "Could not connect to the WAZN backend.",
      error: createLearningError(error),
    };
  }
}