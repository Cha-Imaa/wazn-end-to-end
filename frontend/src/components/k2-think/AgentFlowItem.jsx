// One row in the agentic reasoning flow: numbered step, botanical icon, name,
// summary, status, and an expandable panel showing the agent's engine badge, a
// typewriter-animated reasoning trace, and its final output.

import { useState } from "react";
import { CheckIcon, DotIcon, ChevronIcon } from "./icons.jsx";
import { useTypewriter } from "./useTypewriter.js";

const STATUS_LABEL = { completed: "Completed", skipped: "Skipped" };
const K2_MARK = "/assets/k2/k2-mark.png";

export default function AgentFlowItem({ agent }) {
  const [open, setOpen] = useState(false);
  const isCompleted = agent.status === "completed";
  const isK2 = agent.engine === "k2";
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
          <span
            className={`k2-agent-status k2-agent-status--${
              isCompleted ? "completed" : "skipped"
            }`}
          >
            <span className="k2-agent-status-label">
              {STATUS_LABEL[agent.status] || agent.status}
            </span>
            {isCompleted ? (
              <CheckIcon className="k2-agent-status-icon" />
            ) : (
              <DotIcon className="k2-agent-status-icon" />
            )}
            <ChevronIcon className="k2-agent-chevron" />
          </span>
        </summary>

        <div className="k2-agent-trace">
          <span
            className={`k2-engine-badge k2-engine-badge--${isK2 ? "k2" : "det"}`}
          >
            {isK2 ? (
              <>
                <img className="k2-engine-badge-mark" src={K2_MARK} alt="" aria-hidden="true" />
                {agent.model || "K2 Think"}
              </>
            ) : (
              "Deterministic"
            )}
          </span>

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
              <span className="k2-trace-label">
                {isK2 ? "Output" : "Result"}
              </span>
              <p className="k2-output-text">{agent.output}</p>
            </div>
          )}
        </div>
      </details>
    </li>
  );
}
