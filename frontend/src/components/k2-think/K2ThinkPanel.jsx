// The "K2 Think" transparency tab: agentic reasoning flow + quality evaluation
// + safety & guardrails. Renders from the backend's `k2_think` object, falling
// back to sample data if a result predates that field. Styled to match
// inspiration/details-tab.png.

import { getK2ThinkSample } from "../../data/k2ThinkSample.js";
import AgentFlowItem from "./AgentFlowItem.jsx";
import ScoreGauge from "./ScoreGauge.jsx";
import GuardrailChecklist from "./GuardrailChecklist.jsx";
import { StarRating, LeafSprig } from "./icons.jsx";
import {
  describeEngineStatus,
  describePanelProvenance,
  engineStatusOf,
} from "./engineStatus.js";

const HEADER_BRANCH = "/assets/k2/header-branch.png";
const K2_MARK = "/assets/k2/k2-mark.png";

function SectionLabel({ children }) {
  return (
    <p className="k2-think-section-label">
      <LeafSprig className="k2-label-leaf" />
      <span>{children}</span>
      <LeafSprig className="k2-label-leaf" flip />
    </p>
  );
}

// The same badge the agent rows use, so a section's provenance reads identically
// to the provenance of the steps that produced it.
function ProvenanceChip({ descriptor, className = "" }) {
  return (
    <span
      className={`k2-engine-badge k2-engine-badge--${descriptor.variant} ${className}`.trim()}
    >
      {descriptor.mark && (
        <img
          className="k2-engine-badge-mark"
          src={K2_MARK}
          alt=""
          aria-hidden="true"
        />
      )}
      {descriptor.label}
    </span>
  );
}

export default function K2ThinkPanel({ k2Think, word = "", insightsPending = false }) {
  const data = k2Think || getK2ThinkSample(word);
  const agents = Array.isArray(data.agents) ? data.agents : [];
  const evaluation = data.evaluation;
  const overall = evaluation?.overall;
  const metrics = Array.isArray(evaluation?.metrics) ? evaluation.metrics : [];

  // Sample data has no live steps, so a missing k2_think must not read as live.
  const pending = insightsPending && Boolean(k2Think);

  const panelProvenance = describePanelProvenance(agents, pending);
  const evaluationProvenance = evaluation
    ? describeEngineStatus(engineStatusOf(evaluation))
    : null;

  return (
    <section className="k2-think-panel" aria-label="Insights">
      <header className="k2-think-header">
        <img className="k2-think-mark" src={K2_MARK} alt="" aria-hidden="true" />
        <div className="k2-think-heading">
          <h2 className="k2-think-title">Insights</h2>
          <p className="k2-think-subtitle">{data.subtitle}</p>
          <ProvenanceChip
            descriptor={panelProvenance}
            className="k2-think-provenance"
          />
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
              <AgentFlowItem key={agent.id} agent={agent} pending={pending} />
            ))}
          </ol>
        </div>
      </section>

      {evaluation && (
        <section className="k2-think-section">
          <SectionLabel>Quality Evaluation</SectionLabel>
          <div className="k2-eval-container">
            {/* The demo scores are hand-written and identical for every word.
                Unlabelled beside real morphology they read as measured (§1.5).
                Inside the container so the section label keeps its negative
                margin overlap. */}
            {evaluationProvenance && (
              <ProvenanceChip
                descriptor={evaluationProvenance}
                className="k2-section-provenance"
              />
            )}
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
