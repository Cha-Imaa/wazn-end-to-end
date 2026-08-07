// Safety & guardrails: a bordered card with an internal header and a
// pass/fail checklist (matches inspiration/details-tab.png).

import { CheckIcon, DotIcon, ShieldIcon } from "./icons.jsx";

const CORNER_FLOWER = "/assets/k2/guardrails-flower.png";

// The live K2 verdict carries 12 checks and the deterministic block 5; the
// card shows at most this many. Failed checks sort first so capping the list
// can never hide a failure behind passing rows.
const MAX_VISIBLE_CHECKS = 4;

// When everything passes, prefer a spread that covers both halves of the
// review (2 explanation + 2 quiz) over the backend's tutor-first order.
// Ids not listed (including the deterministic block's) keep their order.
const PREFERRED_CHECK_IDS = [
  "tutor_selected_explanation_incorrect",
  "tutor_pattern_explanation_incorrect",
  "quiz_answer_incorrect",
  "quiz_introduced_unsupported_content",
];

const displayRank = (check) => {
  const rank = PREFERRED_CHECK_IDS.indexOf(check.id);
  return rank === -1 ? PREFERRED_CHECK_IDS.length : rank;
};

export default function GuardrailChecklist({ guardrails }) {
  const checks = Array.isArray(guardrails?.checks) ? guardrails.checks : [];

  const visibleChecks = [...checks]
    .sort(
      (a, b) =>
        Number(Boolean(a.passed)) - Number(Boolean(b.passed)) ||
        displayRank(a) - displayRank(b),
    )
    .slice(0, MAX_VISIBLE_CHECKS);

  return (
    <div className="k2-guardrails">
      <div className="k2-guardrails-head">
        <ShieldIcon className="k2-guardrails-head-icon" />
        <span>Safety &amp; Guardrails</span>
      </div>

      <ul className="k2-check-list">
        {visibleChecks.map((check) => (
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

      {/* Decorative sprig filling the card's bottom-right (inspiration). */}
      <img
        className="k2-guardrails-flower"
        src={CORNER_FLOWER}
        alt=""
        aria-hidden="true"
      />
    </div>
  );
}
