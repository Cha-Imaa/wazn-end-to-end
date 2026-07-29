// One row in the agentic reasoning flow: numbered step, botanical icon, name,
// summary, status, and an expandable panel showing the agent's provenance badge,
// a typewriter-animated reasoning trace, and its final output.

import { useState } from "react";
import { CheckIcon, DotIcon, ChevronIcon } from "./icons.jsx";
import { useTypewriter } from "./useTypewriter.js";
import {
  ENGINE_STATUS,
  describeEngineStatus,
  resolveAgentStatus,
} from "./engineStatus.js";

const STATUS_LABEL = {
  completed: "Completed",
  skipped: "Skipped",
  pending: "Running",
};
const K2_MARK = "/assets/k2/k2-mark.png";

export default function AgentFlowItem({ agent, pending = false }) {
  const [open, setOpen] = useState(false);

  const engineStatus = resolveAgentStatus(agent, pending);
  const badge = describeEngineStatus(engineStatus, agent.model);

  const isPending = engineStatus === ENGINE_STATUS.PENDING;
  const isLive = engineStatus === ENGINE_STATUS.K2_LIVE;

  // The row's own state, not its provenance: a pending step has not finished,
  // and a skipped one never started. Everything else ran, whatever produced it.
  const rowStatus = isPending
    ? "pending"
    : agent.status === "skipped"
      ? "skipped"
      : "completed";

  const reasoning = agent.reasoning || "";
  const { shown, done } = useTypewriter(reasoning, open);

  return (
    <li className="k2-agent-item">
      <span className="k2-agent-step">{agent.step}</span>
      <details
        className="k2-agent"
        onToggle={(e) => setOpen(e.currentTarget.open)}
      >
        <summary className="k2-agent-summary">
          <img
            className="k2-agent-icon"
            src={`/assets/k2/agent-${agent.id}.png`}
            alt=""
            aria-hidden="true"
          />
          <span className="k2-agent-text">
            <span className="k2-agent-name">{agent.name}</span>
            <span className="k2-agent-desc">{agent.summary}</span>
          </span>
          <span className={`k2-agent-status k2-agent-status--${rowStatus}`}>
            <span className="k2-agent-status-label">
              {STATUS_LABEL[rowStatus]}
            </span>
            {rowStatus === "completed" ? (
              <CheckIcon className="k2-agent-status-icon" />
            ) : (
              <DotIcon className="k2-agent-status-icon" />
            )}
            <ChevronIcon className="k2-agent-chevron" />
          </span>
        </summary>

        <div className="k2-agent-trace">
          <span className={`k2-engine-badge k2-engine-badge--${badge.variant}`}>
            {badge.mark && (
              <img
                className="k2-engine-badge-mark"
                src={K2_MARK}
                alt=""
                aria-hidden="true"
              />
            )}
            {badge.label}
          </span>

          {/* Why an agent was rejected belongs in the transparency tab, not
              only in the server log — the badge says "fallback", this says
              what failed. */}
          {agent.error && engineStatus === ENGINE_STATUS.FALLBACK && (
            <p className="k2-agent-error">{agent.error}</p>
          )}

          {Array.isArray(agent.violations) && agent.violations.length > 0 && (
            <ul className="k2-agent-violations">
              {agent.violations.map((violation) => (
                <li key={violation}>{violation}</li>
              ))}
            </ul>
          )}

          {reasoning && (
            <div className="k2-trace-block">
              <span className="k2-trace-label">Reasoning</span>
              <pre className="k2-trace-text">
                {open ? shown : ""}
                {open && !done && <span className="k2-caret" aria-hidden="true" />}
              </pre>
            </div>
          )}

          {agent.output && (
            <div className="k2-trace-block">
              <span className="k2-trace-label">{isLive ? "Output" : "Result"}</span>
              <p className="k2-output-text">{agent.output}</p>
            </div>
          )}
        </div>
      </details>
    </li>
  );
}
