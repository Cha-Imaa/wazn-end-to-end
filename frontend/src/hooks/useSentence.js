import { useEffect, useState } from "react";
import { resolveSentenceResult } from "../services/learningDataService.js";

// Per-word sentence cache for the session, keyed by the displayed Arabic.
// The backend caches per word too, but this keeps a tab switch or a re-click
// from even leaving the component. "absent" results are cached too — but
// softly (§2.9): the agent's validation failures are transient ~10-17% of the
// time, so a first "absent" is retried once on the next panel open before it
// becomes final. A hard absent cache made one transient miss permanently hide
// that word's sentence until reload.
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
    const cached = wordArabic ? sentenceCache.get(wordArabic) : null;
    const retryAbsent =
      cached?.status === SENTENCE_STATUS.ABSENT && !cached.final;

    if (!wordArabic || (cached && !retryAbsent)) {
      return undefined;
    }

    let cancelled = false;

    resolveSentenceResult(wordArabic).then((payload) => {
      const resolved =
        payload?.status === "found" && payload.sentence
          ? { status: SENTENCE_STATUS.READY, sentence: payload.sentence }
          : // A second miss is final — a disabled flag or a genuinely
            // rejected word must not refire on every click.
            { status: SENTENCE_STATUS.ABSENT, sentence: null, final: retryAbsent };

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
