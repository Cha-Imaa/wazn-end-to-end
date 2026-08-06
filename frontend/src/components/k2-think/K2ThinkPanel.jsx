// The "K2 Think" transparency tab: agentic reasoning flow + quality evaluation
// + safety & guardrails. Renders from the backend's `k2_think` object, falling
// back to sample data if a result predates that field. Styled to match
// inspiration/details-tab.png.

import { getK2ThinkSample } from "../../data/k2ThinkSample.js";
import AgentFlowItem from "./AgentFlowItem.jsx";
import ScoreGauge from "./ScoreGauge.jsx";
import GuardrailChecklist from "./GuardrailChecklist.jsx";
import { StarRating, LeafIcon, ShieldIcon } from "./icons.jsx";

const HEADER_BRANCH = "/assets/k2/header-branch.png";
const K2_MARK = "/assets/k2/k2-mark.png";

// Mirrors the backend's _rating thresholds (insights_service.py) so the
// overall card carries the same word the metric rows do.
function ratingWord(value) {
  if (value >= 90) return "Excellent";
  if (value >= 80) return "Very Good";
  if (value >= 70) return "Good";
  if (value >= 50) return "Fair";
  return "Needs Review";
}

export default function K2ThinkPanel({ k2Think, word = "", insightsPending = false }) {
  const data = k2Think || getK2ThinkSample(word);
  const agents = Array.isArray(data.agents) ? data.agents : [];
  const evaluation = data.evaluation;
  const overall = evaluation?.overall;
  const metrics = Array.isArray(evaluation?.metrics) ? evaluation.metrics : [];

  // Sample data has no live steps, so a missing k2_think must not read as live.
  const pending = insightsPending && Boolean(k2Think);

  return (
    <section className="k2-think-panel" aria-label="Insights">
      <header className="k2-think-header">
        <img className="k2-think-mark" src={K2_MARK} alt="" aria-hidden="true" />
        <div className="k2-think-heading">
          <h2 className="k2-think-title">Insights</h2>
          <p className="k2-think-subtitle">{data.subtitle}</p>
        </div>
        <img
          className="k2-think-header-branch"
          src={HEADER_BRANCH}
          alt=""
          aria-hidden="true"
        />
      </header>

      <section className="k2-think-section">
        {/* Inspiration-style card head: leaf icon + left-aligned title inside
            the container, matching the Safety & Guardrails head. */}
        <div className="k2-flow-container">
          <p className="k2-flow-head">
            <LeafIcon className="k2-flow-head-icon" />
            <span>Agentic Reasoning Flow</span>
          </p>
          <ol className="k2-agent-flow">
            {agents.map((agent) => (
              <AgentFlowItem key={agent.id} agent={agent} pending={pending} />
            ))}
          </ol>
        </div>
      </section>

      {evaluation && (
        <section className="k2-think-section">
          {/* Inspiration-style card head: shield icon + left-aligned title,
              matching the flow and guardrails heads (owner direction,
              2026-08-07 — the provenance chip is gone with the pill). */}
          <div className="k2-eval-container">
            <p className="k2-eval-head">
              <ShieldIcon className="k2-eval-head-icon" />
              <span>Quality Evaluation</span>
            </p>
            <div className="k2-eval-row">
              {overall && (
                <div className="k2-eval-overall-card">
                  <span className="k2-eval-overall-label">Overall Quality</span>
                  <div className="k2-eval-overall-figure">
                    <span className="k2-eval-branch k2-eval-branch--left" aria-hidden="true" />
                    <span className="k2-eval-overall-score">
                      {overall.value}
                      <span className="k2-eval-overall-max">/{overall.max}</span>
                    </span>
                    <span className="k2-eval-branch k2-eval-branch--right" aria-hidden="true" />
                  </div>
                  <span className="k2-eval-overall-rating">
                    {ratingWord(overall.value)}
                  </span>
                  <StarRating value={overall.stars} className="k2-eval-stars" />
                </div>
              )}
              <div className="k2-eval-metrics">
                {metrics.map((metric) => (
                  <ScoreGauge key={metric.id} metric={metric} />
                ))}
              </div>
            </div>
          </div>
        </section>
      )}

      {data.guardrails && (
        <section className="k2-think-section">
          <GuardrailChecklist guardrails={data.guardrails} />
        </section>
      )}

    </section>
  );
}
