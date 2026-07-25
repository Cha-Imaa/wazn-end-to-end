import { useEffect, useState } from "react";

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
export function useTypewriter(text = "", active = false, { cps = 110 } = {}) {
  const reduced = usePrefersReducedMotion();
  const animate = active && !reduced && Boolean(text);
  const [count, setCount] = useState(0);

  useEffect(() => {
    if (!animate) return undefined;
    let raf;
    let start = null;
    const step = (now) => {
      if (start === null) start = now;
      const n = Math.min(text.length, Math.floor(((now - start) / 1000) * cps));
      setCount(n); // set inside rAF callback, not synchronously in the effect body
      if (n < text.length) raf = requestAnimationFrame(step);
    };
    raf = requestAnimationFrame(step);
    return () => cancelAnimationFrame(raf);
  }, [animate, text, cps]);

  let shown = "";
  if (animate) shown = text.slice(0, count);
  else if (active) shown = text; // reduced-motion / no animation: show in full

  const done = !animate || count >= text.length;
  return { shown, done };
}
