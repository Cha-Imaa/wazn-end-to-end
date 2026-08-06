// A metric card with an icon + label on top, a semicircular arc gauge, and a
// rating below — matching inspiration/details-tab.png.

const RADIUS = 44; // must match the arc radius in the path below
const ARC_LENGTH = Math.PI * RADIUS; // semicircle circumference ≈ 138.23

// Painted disc art per metric (owner-supplied, 2026-08-07).
const METRIC_ICON = {
  groundedness: "/assets/k2/metric-groundedness.png",
  quiz_validity: "/assets/k2/metric-quiz-validity.png",
  clarity: "/assets/k2/metric-clarity.png",
};

function ratingModifier(rating = "") {
  return rating.toLowerCase().replace(/\s+/g, "-"); // "Very Good" -> "very-good"
}

export default function ScoreGauge({ metric }) {
  const percent = Math.max(0, Math.min(100, metric.percent ?? 0));
  const fillLength = (percent / 100) * ARC_LENGTH;
  const iconSrc = METRIC_ICON[metric.id];

  return (
    <div className={`k2-gauge k2-gauge--${ratingModifier(metric.rating)}`}>
      <div className="k2-gauge-head">
        {iconSrc && (
          <img className="k2-gauge-icon" src={iconSrc} alt="" aria-hidden="true" />
        )}
        <span className="k2-gauge-label">{metric.label}</span>
      </div>
      <div className="k2-gauge-arc">
        <svg viewBox="0 0 100 58" className="k2-gauge-svg" aria-hidden="true">
          <path className="k2-gauge-track" d="M6 54 A44 44 0 0 1 94 54" />
          <path
            className="k2-gauge-fill"
            d="M6 54 A44 44 0 0 1 94 54"
            style={{ strokeDasharray: `${fillLength} ${ARC_LENGTH * 2}` }}
          />
        </svg>
        <span className="k2-gauge-value">{percent}%</span>
      </div>
      <span className="k2-gauge-rating">{metric.rating}</span>
    </div>
  );
}
