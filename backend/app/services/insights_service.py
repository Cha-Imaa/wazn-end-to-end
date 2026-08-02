"""Shapes the GET /api/insights response.

This is the seam between the deterministic pipeline and the K2 agents:
`run_pipeline_components` runs the pipeline once, `build_state_from_components`
turns that run into the evidence state, and `k2_agents_service.build_insights`
runs the four agents over it. `build_base_state(word)` is never called here —
that variant re-runs the pipeline and belongs to the offline prompt lab only.

The response mirrors /api/analyze's `k2_think` shape so the frontend can swap
the block in wholesale, with three deliberate differences:

- Agents 3-6 carry live output and a per-agent `engine_status`
  (`k2_live` / `fallback` / `skipped`) alongside the legacy `engine` key.
- `evaluation` is the mapped live rubric score or None — this endpoint never
  serves the hardcoded demo numbers. An absent score is honest; 94/100 is not.
- `guardrails` is the live 12-check verdict when the guardrail agent succeeded,
  otherwise the same deterministic checks /api/analyze already serves.

Top-level `quiz` is the K2-upgraded quiz or None; None means "keep the quiz
/api/analyze already sent".
"""

from typing import Any

from app.core.config import Settings, get_settings
from app.modules.morphology_reasoning_module import build_morphology_output
from app.pipeline.wazn_pipeline import run_pipeline_components
from app.prompt_lab.shared.evidence_builder import build_state_from_components
from app.services.k2_agents_service import (
    AGENT_EVALUATION,
    AGENT_GUARDRAIL,
    AGENT_SENTENCE,
    ENGINE_STATUS_FALLBACK,
    ENGINE_STATUS_K2_LIVE,
    ENGINE_STATUS_SKIPPED,
    build_insights,
    run_sentence_agent,
)
from app.services.k2_think_service import build_k2_think


INSIGHTS_SOURCE = "k2"

STATUS_FOUND = "found"
STATUS_NOT_FOUND = "not_found"

# The guardrail prompt names failure modes; the panel shows checks that pass.
# Each label states what holds when the check is NOT flagged.
_GUARDRAIL_CHECK_LABELS = {
    "tutor_selected_explanation_incorrect": "Explanation matches the evidence",
    "tutor_pattern_explanation_incorrect": "Pattern explanation is correct",
    "tutor_same_pattern_explanation_incorrect": "Same-pattern examples are correct",
    "tutor_introduced_incorrect_meaning": "No incorrect meanings introduced",
    "tutor_introduced_unsupported_pattern": "No unsupported patterns introduced",
    "tutor_introduced_unsupported_card": "No unsupported related words",
    "quiz_introduced_unsupported_content": "Quiz uses only verified content",
    "quiz_answer_incorrect": "Quiz answers are correct",
    "quiz_feedback_incorrect": "Quiz feedback is accurate",
    "quiz_question_target_mismatch": "Questions match what they test",
    "quiz_ambiguous_correct_answer": "One unambiguous correct answer",
    "quiz_pattern_or_card_not_in_tree": "Quiz content stays inside the tree",
}


def build_pipeline_state(word: str) -> dict[str, Any]:
    """
    One pipeline run → the evidence state the agents consume.

    Also the `state_builder` handed to `prewarm_insights` at startup. Returns
    the components' `{"found": False, ...}` dict unchanged when the word does
    not resolve.
    """
    components = run_pipeline_components(word)

    if not components["found"]:
        return components

    morphology_result = components["morphology_result"]

    return build_state_from_components(
        query=components["query"],
        normalized_query=components["normalized_query"],
        selected_word_id=components["selected_word_id"],
        selected_word=components["selected_word"],
        root=components["root"],
        pattern=components["pattern"],
        tree=components["tree"],
        leaf_details=components["leaf_details"],
        selected_leaf=components["selected_leaf"],
        quiz=components["quiz"],
        morphology=build_morphology_output(morphology_result),
        family_words=components["family_words"],
        same_pattern_words=components["same_pattern_words"],
        pipeline_trace=components["pipeline_trace"],
    )


def build_insights_response(
    word: str,
    settings: Settings | None = None,
) -> dict[str, Any]:
    """Always a fully shaped body — agent failures surface per agent, never as an error."""
    active_settings = settings or get_settings()

    state = build_pipeline_state(word)

    if not state.get("found"):
        return {
            "status": STATUS_NOT_FOUND,
            "query": state.get("query", word),
            "normalized_query": state.get("normalized_query", ""),
            "selected_word_id": None,
            "cached": False,
            "k2_think": None,
            "quiz": None,
            "source": INSIGHTS_SOURCE,
            "reason": state.get("reason", "word_not_found"),
            "message": state.get("message", "Word not found in the knowledge base."),
        }

    insights = build_insights(state, settings=active_settings)

    return {
        "status": STATUS_FOUND,
        "query": state["query"],
        "normalized_query": state["normalized_query"],
        "selected_word_id": state["selected_word_id"],
        "cached": bool(insights.get("cached")),
        "k2_think": _enriched_k2_think(state, insights, active_settings),
        "quiz": insights.get("quiz"),
        "sentence": _sentence_block(insights.get("agents", {}).get(AGENT_SENTENCE)),
        "source": INSIGHTS_SOURCE,
    }


def build_sentence_response(
    word: str,
    settings: Settings | None = None,
) -> dict[str, Any]:
    """
    Shapes GET /api/sentence — the sentence agent alone, for whichever leaf
    the Details tab is showing. The full insights chain is 15-45s; this is one
    K2 call (or a cache hit shared with that chain). Always a fully shaped
    body: `sentence` is the block or None, never an error.
    """
    active_settings = settings or get_settings()

    state = build_pipeline_state(word)

    if not state.get("found"):
        return {
            "status": STATUS_NOT_FOUND,
            "query": state.get("query", word),
            "normalized_query": state.get("normalized_query", ""),
            "selected_word_id": None,
            "sentence": None,
            "source": INSIGHTS_SOURCE,
            "reason": state.get("reason", "word_not_found"),
            "message": state.get("message", "Word not found in the knowledge base."),
        }

    result = run_sentence_agent(state, active_settings)

    return {
        "status": STATUS_FOUND,
        "query": state["query"],
        "normalized_query": state["normalized_query"],
        "selected_word_id": state["selected_word_id"],
        "sentence": _sentence_block(result),
        "source": INSIGHTS_SOURCE,
    }


def _sentence_block(result: dict[str, Any] | None) -> dict[str, Any] | None:
    """
    The Details tab's "In a sentence" payload, or None.

    None is the clean absence §2.2c asks for — the section simply does not
    render when the agent failed, was skipped, or never produced valid output.
    Only k2_live content ships: there is no deterministic sentence to fall
    back to, and an unvalidated one must never reach a learner.
    """
    if not result or result.get("engine_status") != ENGINE_STATUS_K2_LIVE:
        return None

    output = result.get("output")
    if not isinstance(output, dict):
        return None

    arabic = output.get("sentence")
    translation = output.get("translation")
    if not isinstance(arabic, str) or not isinstance(translation, str):
        return None

    return {
        "arabic": arabic,
        "translation": translation,
        "engine_status": ENGINE_STATUS_K2_LIVE,
        "model": result.get("model"),
    }


# --- the enriched k2_think block -----------------------------------------------


def _enriched_k2_think(
    state: dict[str, Any],
    insights: dict[str, Any],
    settings: Settings,
) -> dict[str, Any]:
    base = build_k2_think(
        selected_word=state["selected_word"],
        root=state["root"],
        pattern=state["pattern"],
        quiz=state["quiz"],
        pipeline_trace=state["pipeline_trace"],
        selected_leaf=state["selected_leaf"],
        settings=settings,
    )

    agent_results = insights.get("agents", {})

    agents = []
    for agent in base["agents"]:
        result = agent_results.get(agent["id"])

        if result is None:
            # lookup / morphology — genuinely deterministic, kept as-is
            entry = dict(agent)
            entry["engine_status"] = "deterministic"
            agents.append(entry)
        else:
            agents.append(_panel_agent(result, state))

    return {
        "source": INSIGHTS_SOURCE,
        "demo": False,
        "subtitle": base["subtitle"],
        "agents": agents,
        "evaluation": _live_evaluation(agent_results.get(AGENT_EVALUATION)),
        "guardrails": _live_guardrails(agent_results.get(AGENT_GUARDRAIL))
        or base["guardrails"],
        "fallback_note": base["fallback_note"],
    }


def _panel_agent(result: dict[str, Any], state: dict[str, Any]) -> dict[str, Any]:
    engine_status = result.get("engine_status")

    return {
        "id": result["id"],
        "step": result["step"],
        "name": result["name"],
        "engine": "k2",
        "engine_status": engine_status,
        "model": result.get("model"),
        "status": "skipped" if engine_status == ENGINE_STATUS_SKIPPED else "completed",
        "summary": _agent_summary(result, state),
        "reasoning": (result.get("reasoning") or _fallback_reasoning(result)).strip(),
        "output": _agent_output_text(result, state),
        "reasoning_tokens": result.get("reasoning_tokens"),
        "violations": result.get("violations", []),
        "error": result.get("error"),
    }


def _fallback_reasoning(result: dict[str, Any]) -> str:
    engine_status = result.get("engine_status")

    if engine_status == ENGINE_STATUS_SKIPPED:
        return "This K2 step did not run. " + (result.get("error") or "")

    if engine_status == ENGINE_STATUS_FALLBACK:
        return (
            "The live K2 call did not produce usable output"
            f" ({result.get('error') or 'unknown error'})."
            " WAZN is showing verified deterministic content instead."
        )

    return ""


def _agent_summary(result: dict[str, Any], state: dict[str, Any]) -> str:
    agent_id = result["id"]
    engine_status = result.get("engine_status")

    if engine_status == ENGINE_STATUS_SKIPPED:
        return f"Skipped — {result.get('error') or 'flag not enabled.'}"

    if engine_status == ENGINE_STATUS_FALLBACK:
        if agent_id in ("guardrail", "evaluation"):
            return "K2 review unavailable — no verdict is shown rather than an invented one."
        if agent_id == "sentence":
            return "K2 output was rejected — the example sentence is left out rather than shown unverified."
        return "K2 output was rejected — verified deterministic content is shown instead."

    live_summaries = {
        "explanation": "Generated a learner-friendly explanation from a live K2 call.",
        "quiz": f"Generated {_quiz_question_count(result, state)} practice questions from a live K2 call.",
        "sentence": "Wrote an example sentence using the word, from a live K2 call.",
        "guardrail": _guardrail_live_summary(result),
        "evaluation": "Scored the response against the quality rubric.",
    }
    return live_summaries.get(agent_id, "Completed.")


def _agent_output_text(result: dict[str, Any], state: dict[str, Any]) -> str:
    agent_id = result["id"]
    engine_status = result.get("engine_status")
    output = result.get("output")

    if agent_id == "explanation":
        if isinstance(output, dict):
            return output.get("explanation", "")
        return ""

    if agent_id == "quiz":
        count = _quiz_question_count(result, state)
        if engine_status == ENGINE_STATUS_K2_LIVE:
            return f"{count} questions · generated live by K2"
        if engine_status == ENGINE_STATUS_FALLBACK:
            return f"{count} questions · deterministic templates (fallback)"
        return ""

    if agent_id == "sentence":
        if engine_status == ENGINE_STATUS_K2_LIVE and isinstance(output, dict):
            arabic = output.get("sentence", "")
            translation = output.get("translation", "")
            return f"{arabic} — {translation}" if translation else arabic
        return ""

    if agent_id == "guardrail" and engine_status == ENGINE_STATUS_K2_LIVE:
        return _guardrail_live_summary(result)

    if agent_id == "evaluation" and engine_status == ENGINE_STATUS_K2_LIVE:
        return _evaluation_live_output(output)

    return ""


def _quiz_question_count(result: dict[str, Any], state: dict[str, Any]) -> int:
    output = result.get("output")

    if isinstance(output, dict) and isinstance(output.get("quiz"), list):
        return len(output["quiz"])

    return len(state.get("quiz", []))


def _guardrail_live_summary(result: dict[str, Any]) -> str:
    output = result.get("output")

    if not isinstance(output, dict) or not isinstance(output.get("checks"), list):
        return "Reviewed the explanation and quiz against the evidence."

    checks = output["checks"]
    flagged = sum(
        1 for check in checks if isinstance(check, dict) and check.get("flagged") is True
    )

    if flagged == 0:
        return f"All {len(checks)} grounding checks passed."

    return f"{flagged} of {len(checks)} grounding checks flagged an issue."


def _evaluation_live_output(output: Any) -> str:
    if not isinstance(output, dict):
        return ""

    def score(key: str) -> Any:
        metric = output.get(key)
        return metric.get("score") if isinstance(metric, dict) else None

    parts = [f"Overall {score('overall_score')}/10"]
    for key, label in (
        ("groundedness", "Groundedness"),
        ("quiz_quality", "Quiz"),
        ("clarity", "Clarity"),
    ):
        value = score(key)
        if value is not None:
            parts.append(f"{label} {value}/10")

    return " · ".join(parts)


# --- evaluation and guardrail blocks for the panel ------------------------------


def _live_evaluation(result: dict[str, Any] | None) -> dict[str, Any] | None:
    """Map the rubric's 1-10 scores onto the panel's percent shape, or None."""
    if not result or result.get("engine_status") != ENGINE_STATUS_K2_LIVE:
        return None

    output = result.get("output")
    if not isinstance(output, dict):
        return None

    def metric(metric_id: str, label: str, key: str) -> dict[str, Any] | None:
        raw = output.get(key)
        score = raw.get("score") if isinstance(raw, dict) else None

        if not isinstance(score, (int, float)):
            return None

        percent = round(score * 10)
        return {
            "id": metric_id,
            "label": label,
            "percent": percent,
            "rating": _rating(percent),
            "justification": raw.get("justification", ""),
        }

    metrics = [
        entry
        for entry in (
            metric("groundedness", "Groundedness", "groundedness"),
            metric("quiz_validity", "Quiz Validity", "quiz_quality"),
            metric("clarity", "Clarity", "clarity"),
        )
        if entry
    ]

    overall_raw = output.get("overall_score")
    overall = overall_raw.get("score") if isinstance(overall_raw, dict) else None

    if not isinstance(overall, (int, float)) or not metrics:
        return None

    return {
        "overall": {
            "value": round(overall * 10),
            "max": 100,
            # 1-10 score → 0-5 stars in half-star steps
            "stars": round(overall) / 2,
        },
        "metrics": metrics,
        "engine_status": ENGINE_STATUS_K2_LIVE,
    }


def _rating(percent: int) -> str:
    if percent >= 90:
        return "Excellent"
    if percent >= 80:
        return "Very Good"
    if percent >= 70:
        return "Good"
    if percent >= 50:
        return "Fair"
    return "Needs Review"


def _live_guardrails(result: dict[str, Any] | None) -> dict[str, Any] | None:
    """Map the 12 live check verdicts onto the panel's checklist shape, or None."""
    if not result or result.get("engine_status") != ENGINE_STATUS_K2_LIVE:
        return None

    output = result.get("output")
    if not isinstance(output, dict) or not isinstance(output.get("checks"), list):
        return None

    checks = []
    for check in output["checks"]:
        if not isinstance(check, dict):
            continue

        name = check.get("name", "")
        checks.append(
            {
                "id": name,
                "label": _GUARDRAIL_CHECK_LABELS.get(
                    name, name.replace("_", " ").capitalize()
                ),
                # `flagged` names a found problem; the panel shows passing checks
                "passed": check.get("flagged") is not True,
                "reason": check.get("reason", ""),
            }
        )

    if not checks:
        return None

    passed = bool(output.get("passed"))
    flagged_count = sum(1 for check in checks if not check["passed"])

    return {
        "passed": passed,
        "summary": "All Checks Passed"
        if passed
        else f"{flagged_count} Check{'s' if flagged_count != 1 else ''} Flagged",
        "checks": checks,
        "engine_status": ENGINE_STATUS_K2_LIVE,
    }
