// Inline SVG icons for the K2 Think panel. All use `currentColor` so the
// numbered CSS cascade controls their color (kept to greens/gold — never the
// reserved orange or red).

import { useId } from "react";

export function CheckIcon({ className }) {
  return (
    <svg className={className} viewBox="0 0 24 24" aria-hidden="true" focusable="false">
      <circle cx="12" cy="12" r="11" fill="currentColor" />
      <path
        d="M7 12.5l3.2 3.2L17 9"
        fill="none"
        stroke="#faf8ef"
        strokeWidth="2.2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

export function DotIcon({ className }) {
  return (
    <svg className={className} viewBox="0 0 24 24" aria-hidden="true" focusable="false">
      <circle cx="12" cy="12" r="10" fill="none" stroke="currentColor" strokeWidth="2" />
    </svg>
  );
}

export function ChevronIcon({ className }) {
  return (
    <svg className={className} viewBox="0 0 24 24" aria-hidden="true" focusable="false">
      <path
        d="M6 9l6 6 6-6"
        fill="none"
        stroke="currentColor"
        strokeWidth="2.2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

export function LeafSprig({ className, flip = false }) {
  return (
    <svg
      className={className}
      viewBox="0 0 24 24"
      aria-hidden="true"
      focusable="false"
      style={flip ? { transform: "scaleX(-1)" } : undefined}
    >
      <path
        d="M4 20c0-7 5-13 15-16-2 9-7 14-15 16z"
        fill="currentColor"
        opacity="0.55"
      />
      <path
        d="M4 20C7 14 12 9 19 6"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.3"
        strokeLinecap="round"
      />
    </svg>
  );
}

// Solid leaf for section heads (inspiration: the leaf before "Agentic
// Reasoning Flow"). Full-opacity sibling of LeafSprig.
export function LeafIcon({ className }) {
  return (
    <svg className={className} viewBox="0 0 24 24" aria-hidden="true" focusable="false">
      <path d="M20 4C10.5 4.5 4.5 10.5 4 20c9.5-.5 15.5-6.5 16-16z" fill="currentColor" />
      <path
        d="M6.5 17.5C9.5 13.5 13.5 9.5 17.5 6.5"
        fill="none"
        stroke="#faf8ef"
        strokeWidth="1.5"
        strokeLinecap="round"
      />
    </svg>
  );
}

export function ClipboardIcon({ className }) {
  return (
    <svg className={className} viewBox="0 0 24 24" aria-hidden="true" focusable="false">
      <rect x="5" y="4" width="14" height="18" rx="2.5" fill="none" stroke="currentColor" strokeWidth="1.6" />
      <rect x="9" y="2.5" width="6" height="3.4" rx="1.2" fill="currentColor" />
      <path d="M8.5 12l2 2 4-4.5" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

export function BulbIcon({ className }) {
  return (
    <svg className={className} viewBox="0 0 24 24" aria-hidden="true" focusable="false">
      <path
        d="M12 3a6 6 0 0 0-3.6 10.8c.6.5 1 1.2 1.1 2h5c.1-.8.5-1.5 1.1-2A6 6 0 0 0 12 3z"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinejoin="round"
      />
      <path d="M9.5 20h5M10 22h4" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
    </svg>
  );
}

export function ShieldIcon({ className }) {
  return (
    <svg className={className} viewBox="0 0 24 24" aria-hidden="true" focusable="false">
      <path
        d="M12 2l8 3v6c0 5-3.4 8.5-8 11-4.6-2.5-8-6-8-11V5l8-3z"
        fill="currentColor"
      />
      <path
        d="M8.5 12.2l2.4 2.4L16 9.4"
        fill="none"
        stroke="#faf8ef"
        strokeWidth="1.8"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

// A single star that can be full, half, or empty.
export function StarIcon({ fill = "full", className }) {
  const id = `half-${useId().replace(/:/g, "")}`;
  const path =
    "M12 2.5l2.9 6 6.6.9-4.8 4.6 1.2 6.5L12 17.9 6.1 20.5l1.2-6.5L2.5 9.4l6.6-.9L12 2.5z";
  let fillValue = "currentColor";
  if (fill === "empty") fillValue = "none";
  if (fill === "half") fillValue = `url(#${id})`;
  return (
    <svg className={className} viewBox="0 0 24 24" aria-hidden="true" focusable="false">
      {fill === "half" && (
        <defs>
          <linearGradient id={id}>
            <stop offset="50%" stopColor="currentColor" />
            <stop offset="50%" stopColor="transparent" />
          </linearGradient>
        </defs>
      )}
      <path
        d={path}
        fill={fillValue}
        stroke="currentColor"
        strokeWidth="1.1"
        strokeLinejoin="round"
      />
    </svg>
  );
}

export function StarRating({ value = 0, outOf = 5, className }) {
  const stars = [];
  for (let i = 1; i <= outOf; i += 1) {
    let fill = "empty";
    if (value >= i) fill = "full";
    else if (value >= i - 0.5) fill = "half";
    stars.push(<StarIcon key={i} fill={fill} className="k2-star" />);
  }
  return (
    <span className={className} role="img" aria-label={`${value} out of ${outOf} stars`}>
      {stars}
    </span>
  );
}
