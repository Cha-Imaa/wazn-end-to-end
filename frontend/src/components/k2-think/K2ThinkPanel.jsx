// The "K2 Think" transparency tab: agentic reasoning flow + quality evaluation
// + safety & guardrails. Renders from the backend's `k2_think` object, falling
// back to sample data if a result predates that field. Styled to match
// inspiration/details-tab.png.

import { getK2ThinkSample } from "../../data/k2ThinkSample.js";
import AgentFlowItem from "./AgentFlowItem.jsx";
import ScoreGauge from "./ScoreGauge.jsx";
import GuardrailChecklist from "./GuardrailChecklist.jsx";
import { StarRating, LeafSprig, BulbIcon } from "./icons.jsx";

const HEADER_BRANCH = "/assets/k2/header-branch.png";

function SectionLabel({ children }) {
  return (
    <p className="k2-think-section-label">
      <LeafSprig className="k2-label-leaf" />
      <span>{children}</span>
      <LeafSprig className="k2-label-leaf" flip />
    </p>
  );
}

export default function K2ThinkPanel({ k2Think, word = "" }) {
  const data = k2Think || getK2ThinkSample(word);
  const agents = Array.isArray(data.agents) ? data.agents : [];
  const evaluation = data.evaluation;
  const overall = evaluation?.overall;
  const metrics = Array.isArray(evaluation?.metrics) ? evaluation.metrics : [];

  return (
    <section className="k2-think-panel" aria-label="Insights">
      <header className="k2-think-header">
        <BulbIcon className="k2-think-mark" />
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
        <SectionLabel>Agentic Reasoning Flow</SectionLabel>
        <div className="k2-flow-container">
          <ol className="k2-agent-flow">
            {agents.map((agent) => (
              <AgentFlowItem key={agent.id} agent={agent} />
            ))}
          </ol>
        </div>
      </section>

      {evaluation && (
        <section className="k2-think-section">
          <SectionLabel>Quality Evaluation</SectionLabel>
          <div className="k2-eval-container">
            <div className="k2-eval-row">
              {overall && (
                <div className="k2-eval-overall-card">
                  <span className="k2-eval-overall-label">Overall Score</span>
                  <div className="k2-eval-overall-figure">
                    <span className="k2-eval-branch k2-eval-branch--left" aria-hidden="true" />
                    <span className="k2-eval-overall-score">
                      {overall.value}
                      <span className="k2-eval-overall-max">/{overall.max}</span>
                    </span>
                    <span className="k2-eval-branch k2-eval-branch--right" aria-hidden="true" />
                  </div>
                  <StarRating value={overall.stars} className="k2-eval-stars" />
                </div>
              )}
              {metrics.map((metric) => (
                <ScoreGauge key={metric.id} metric={metric} />
              ))}
            </div>
          </div>
        </section>
      )}

      {data.guardrails && (
        <section className="k2-think-section">
          <GuardrailChecklist guardrails={data.guardrails} />
        </section>
      )}

      {data.fallback_note && (
        <p className="k2-think-fallback-note">{data.fallback_note}</p>
      )}
    </section>
  );
}
