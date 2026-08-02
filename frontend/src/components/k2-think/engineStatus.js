// Provenance vocabulary for the Insights tab.
//
// One place decides what each `engine_status` is called and which badge variant
// it uses, so the agent rows, the evaluation section, and the guardrail card can
// never disagree about where a piece of content came from. The backend sets the
// value (see k2_think_service.py); this file only names it.
//
// Why this exists: the panel used to branch on `engine === "k2"`, which was true
// for the quiz agent while it ran 100% deterministic templates, and true for the
// three agents showing hand-written samples. Everything K2-adjacent looked live.

export const ENGINE_STATUS = {
  K2_LIVE: "k2_live",
  DEMO_SAMPLE: "demo_sample",
  DETERMINISTIC: "deterministic",
  FALLBACK: "fallback",
  SKIPPED: "skipped",
  PENDING: "pending",
};

// `variant` maps to a `--<variant>` CSS modifier in 24-k2-think-panel.css.
const DESCRIPTORS = {
  [ENGINE_STATUS.K2_LIVE]: { variant: "k2", label: "K2 Think", mark: true },
  [ENGINE_STATUS.DEMO_SAMPLE]: { variant: "demo", label: "Demo sample" },
  [ENGINE_STATUS.DETERMINISTIC]: { variant: "det", label: "Deterministic" },
  [ENGINE_STATUS.FALLBACK]: { variant: "fallback", label: "Deterministic fallback" },
  [ENGINE_STATUS.SKIPPED]: { variant: "skipped", label: "Not run" },
  [ENGINE_STATUS.PENDING]: { variant: "pending", label: "Running live K2…" },
};

// The five steps GET /api/insights replaces. While that request is in flight the
// panel shows what /api/analyze served, so these rows are explicitly pending
// rather than silently presenting sample content as final.
const ENRICHED_AGENT_IDS = new Set([
  "explanation",
  "quiz",
  "sentence",
  "guardrail",
  "evaluation",
]);

export function isEnrichedAgent(agentId) {
  return ENRICHED_AGENT_IDS.has(agentId);
}

/**
 * Resolve an agent's effective status, accounting for a pending enrichment.
 *
 * `pending` only applies to a step the enrichment will actually replace, and
 * never overrides a status the enrichment has already delivered.
 */
export function resolveAgentStatus(agent, pending = false) {
  const status = engineStatusOf(agent);

  const awaitingEnrichment =
    pending &&
    isEnrichedAgent(agent?.id) &&
    status !== ENGINE_STATUS.K2_LIVE &&
    status !== ENGINE_STATUS.FALLBACK;

  return awaitingEnrichment ? ENGINE_STATUS.PENDING : status;
}

/**
 * Read `engine_status`, falling back to the legacy `engine` key.
 *
 * A response cached before `engine_status` existed still renders — and it
 * degrades to the old, less precise reading rather than to nothing.
 */
export function engineStatusOf(agent) {
  if (agent?.engine_status) {
    return agent.engine_status;
  }

  if (agent?.status === ENGINE_STATUS.SKIPPED) {
    return ENGINE_STATUS.SKIPPED;
  }

  return agent?.engine === "k2"
    ? ENGINE_STATUS.DEMO_SAMPLE
    : ENGINE_STATUS.DETERMINISTIC;
}

/** Badge descriptor for a status. `model` names the live model when known. */
export function describeEngineStatus(status, model = null) {
  const descriptor = DESCRIPTORS[status];

  if (!descriptor) {
    return { variant: "det", label: "Deterministic" };
  }

  if (descriptor.mark && model) {
    return { ...descriptor, label: model };
  }

  return descriptor;
}

/**
 * One provenance chip for the whole panel, from the agents it is showing.
 *
 * Deliberately pessimistic ordering: pending and sample content are called out
 * ahead of live content, so a panel that is partly canned never advertises
 * itself as live.
 */
export function describePanelProvenance(agents = [], pending = false) {
  const statuses = agents.map((agent) => resolveAgentStatus(agent, pending));

  if (statuses.includes(ENGINE_STATUS.PENDING)) {
    return { variant: "pending", label: "Running live K2…" };
  }

  if (statuses.includes(ENGINE_STATUS.DEMO_SAMPLE)) {
    return { variant: "demo", label: "Demo sample" };
  }

  if (statuses.includes(ENGINE_STATUS.K2_LIVE)) {
    // "Live K2" alone would overstate a panel where some steps never ran or
    // were rejected — with only ENABLE_K2_EXPLANATION on, that is 1 live step
    // out of 4.
    const partial =
      statuses.includes(ENGINE_STATUS.SKIPPED) ||
      statuses.includes(ENGINE_STATUS.FALLBACK);

    return {
      variant: "k2",
      label: partial ? "Live K2 · partial" : "Live K2",
      mark: true,
    };
  }

  if (statuses.includes(ENGINE_STATUS.FALLBACK)) {
    return { variant: "fallback", label: "Deterministic fallback" };
  }

  if (statuses.every((status) => status === ENGINE_STATUS.SKIPPED)) {
    return { variant: "skipped", label: "K2 steps not run" };
  }

  return { variant: "det", label: "Deterministic" };
}
