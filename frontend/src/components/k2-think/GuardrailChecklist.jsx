// Safety & guardrails: a bordered card with an internal header, a pass/fail
// checklist, and an overall status badge (matches inspiration/details-tab.png).

import { CheckIcon, DotIcon, ShieldIcon } from "./icons.jsx";

export default function GuardrailChecklist({ guardrails }) {
  const checks = Array.isArray(guardrails?.checks) ? guardrails.checks : [];
  const passed = Boolean(guardrails?.passed);

  return (
    <div className="k2-guardrails">
      <div className="k2-guardrails-head">
        <ShieldIcon className="k2-guardrails-head-icon" />
        <span>Safety &amp; Guardrails</span>
      </div>

      <ul className="k2-check-list">
        {checks.map((check) => (
          <li
            key={check.id}
            className={`k2-check k2-check--${check.passed ? "pass" : "fail"}`}
          >
            {check.passed ? (
              <CheckIcon className="k2-check-icon" />
            ) : (
              <DotIcon className="k2-check-icon" />
            )}
            <span className="k2-check-label">{check.label}</span>
          </li>
        ))}
      </ul>

      <div className={`k2-check-badge k2-check-badge--${passed ? "pass" : "fail"}`}>
        <ShieldIcon className="k2-check-badge-icon" />
        <span>{guardrails?.summary || (passed ? "All Checks Passed" : "Needs Review")}</span>
      </div>
    </div>
  );
}
