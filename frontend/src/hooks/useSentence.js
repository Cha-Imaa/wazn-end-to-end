import { useEffect, useState } from "react";
import { resolveSentenceResult } from "../services/learningDataService.js";

// Per-word sentence cache for the session, keyed by the displayed Arabic.
// The backend caches per word too, but this keeps a tab switch or a re-click
// from even leaving the component. "absent" results are cached as well: a
// disabled flag or a rejected agent would otherwise refire on every click.
const sentenceCache = new Map();

export const SENTENCE_STATUS = {
  PENDING: "pending",
  READY: "ready",
  ABSENT: "absent",
};

const PENDING_ENTRY = { status: SENTENCE_STATUS.PENDING, sentence: null };

/**
 * The "In a sentence" data for a displayed word, generated per clicked leaf.
 *
 * Returns null (no word — render nothing), or `{ status, sentence }` where
 * `sentence` is the backend's `{ arabic, translation, engine_status, model }`
 * block once status is "ready". "absent" is the clean no-section state: the
 * agent failed, its flag is off, or the request never returned — the Details
 * tab must not hold a permanent placeholder for content that is not coming.
 */
export function useSentence(wordArabic) {
  // Only the async resolution needs state; everything synchronous is derived
  // from the cache during render, so a word change never double-renders.
  const [resolvedFor, setResolvedFor] = useState(null);

  useEffect(() => {
    if (!wordArabic || sentenceCache.has(wordArabic)) {
      return undefined;
    }

    let cancelled = false;

    resolveSentenceResult(wordArabic).then((payload) => {
      const resolved =
        payload?.status === "found" && payload.sentence
          ? { status: SENTENCE_STATUS.READY, sentence: payload.sentence }
          : { status: SENTENCE_STATUS.ABSENT, sentence: null };

      sentenceCache.set(wordArabic, resolved);

      if (!cancelled) {
        setResolvedFor(wordArabic);
      }
    });

    return () => {
      cancelled = true;
    };
  }, [wordArabic]);

  // `resolvedFor` only exists to re-render when the fetch lands; the value
  // itself always comes from the cache.
  void resolvedFor;

  if (!wordArabic) {
    return null;
  }

  return sentenceCache.get(wordArabic) || PENDING_ENTRY;
}
