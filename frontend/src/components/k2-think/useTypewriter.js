import { useCallback, useEffect, useState } from "react";

function prefersReducedMotion() {
  return (
    typeof window !== "undefined" &&
    window.matchMedia &&
    window.matchMedia("(prefers-reduced-motion: reduce)").matches
  );
}

function usePrefersReducedMotion() {
  const [reduced, setReduced] = useState(prefersReducedMotion);
  useEffect(() => {
    const mq = window.matchMedia("(prefers-reduced-motion: reduce)");
    const onChange = () => setReduced(mq.matches); // set inside event handler, not effect body
    mq.addEventListener("change", onChange);
    return () => mq.removeEventListener("change", onChange);
  }, []);
  return reduced;
}

// Reveals `text` progressively while `active` is true — a typewriter/"streaming"
// effect. Respects prefers-reduced-motion (renders full text instantly). The
// same render path works for a future real token stream: feed growing `text`.
//
// The animation simulates the response *arriving*, so each text plays at most
// once: after it completes (or `skip()` is called), re-activating shows it in
// full immediately. A different `text` — a new search, or the live enrichment
// replacing a deterministic trace — is a new arrival and animates again.
//
// `cps` is a floor, not the speed: live K2 traces run to ~40k characters, which
// at a fixed 110 cps is ~6 minutes of typing. Long texts accelerate so that
// nothing takes longer than `maxSeconds` to finish.
export function useTypewriter(
  text = "",
  active = false,
  { cps = 110, maxSeconds = 8 } = {},
) {
  const reduced = usePrefersReducedMotion();
  const [count, setCount] = useState(0);
  const [playedText, setPlayedText] = useState(null);

  const alreadyPlayed = playedText === text;
  const animate = active && !reduced && Boolean(text) && !alreadyPlayed;
  const effectiveCps = Math.max(cps, text.length / maxSeconds);

  useEffect(() => {
    if (!animate) return undefined;
    let raf;
    let start = null;
    const step = (now) => {
      if (start === null) start = now;
      const n = Math.min(
        text.length,
        Math.floor(((now - start) / 1000) * effectiveCps),
      );
      setCount(n); // set inside rAF callback, not synchronously in the effect body
      if (n < text.length) raf = requestAnimationFrame(step);
      else setPlayedText(text);
    };
    raf = requestAnimationFrame(step);
    return () => cancelAnimationFrame(raf);
  }, [animate, text, effectiveCps]);

  // Jump to the end of the current text; the effect above sees alreadyPlayed
  // flip and cancels its animation frame in cleanup.
  const skip = useCallback(() => setPlayedText(text), [text]);

  let shown = "";
  if (animate) shown = text.slice(0, count);
  else if (active) shown = text; // played / reduced-motion: show in full

  const done = !animate || count >= text.length;
  return { shown, done, skip };
}
