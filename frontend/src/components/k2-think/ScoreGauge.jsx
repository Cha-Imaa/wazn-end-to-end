// A quality metric row: painted disc icon, label + percent on one line, a
// filled progress bar, and a rating word below — matching the inspiration's
// Quality Evaluation list. (Kept the ScoreGauge name from the arc-gauge era so
// imports stay stable.)

// Painted disc art per metric (owner-supplied, 2026-08-07).
const METRIC_ICON = {
  groundedness: "/assets/k2/metric-groundedness.png",
  quiz_validity: "/assets/k2/metric-quiz-validity.png",
  clarity: "/assets/k2/metric-clarity.png",
};

export default function ScoreGauge({ metric }) {
  const percent = Math.max(0, Math.min(100, metric.percent ?? 0));
  const iconSrc = METRIC_ICON[metric.id];

  return (
    <div className={`k2-metric k2-metric--${metric.id}`}>
      {iconSrc && (
        <img className="k2-metric-icon" src={iconSrc} alt="" aria-hidden="true" />
      )}
      <div className="k2-metric-body">
        <div className="k2-metric-top">
          <span className="k2-metric-label">{metric.label}</span>
          <span className="k2-metric-value">{percent}%</span>
        </div>
        <div className="k2-metric-bar">
          <span className="k2-metric-fill" style={{ width: `${percent}%` }} />
        </div>
        <span className="k2-metric-rating">{metric.rating}</span>
      </div>
    </div>
  );
}
