"""Builds the `k2_think` transparency object for the /api/analyze response.

This powers the frontend "K2 Think" tab: a 6-step agentic reasoning flow (each
agent exposing a reasoning trace + final output), a quality-evaluation summary,
and a safety/guardrails checklist.

Nothing here calls an LLM — it stays on the deterministic request path. The
`lookup` / `morphology` / `quiz` agents are genuinely deterministic. The
`explanation` / `guardrail` / `evaluation` agents emit **mock** but
word-specific text while `enable_k2_think_demo` is true (the default). Live K2
output for those three arrives on GET /api/insights, which reshapes this same
block (see `insights_service`).

Every agent carries `engine_status`, the single field describing where its
content came from (§1.5). It replaces the old `engine` + `demo` combination,
which could not distinguish "deterministic by design" from "a K2 step showing a
canned sample" — both read as `engine: "k2"` with `demo: true` somewhere else
in the response. `engine` is still emitted for older clients but nothing should
branch on it.

    deterministic   real deterministic logic ran; this is its actual output
    demo_sample     a hand-written sample stands in for a K2 step that has not
                    run — never to be presented as a live or verified result
    skipped         the step's ENABLE_K2_* flag is off
    k2_live         a live validated K2 call (only ever set by /api/insights)
    fallback        the live call failed; deterministic content is shown
"""

from typing import Any

from app.core.config import Settings, get_settings
from app.modules.guardrail_validator_module import run_guardrail_validator_module


DETERMINISTIC_SOURCE = "deterministic"
K2_ENGINE = "k2"
DETERMINISTIC_ENGINE = "deterministic"
K2_MODEL_NAME = "K2-Think-v2"

ENGINE_STATUS_DETERMINISTIC = "deterministic"
ENGINE_STATUS_DEMO_SAMPLE = "demo_sample"
ENGINE_STATUS_SKIPPED = "skipped"

STATUS_COMPLETED = "completed"
STATUS_SKIPPED = "skipped"

SUBTITLE = "See the reasoning behind every word."
FALLBACK_NOTE = (
    "If any step fails, WAZN falls back to deterministic template explanations."
)

_DEMO_EVALUATION = {
    "overall": {"value": 94, "max": 100, "stars": 4.5},
    "metrics": [
        {"id": "groundedness", "label": "Groundedness", "percent": 100, "rating": "Excellent"},
        {"id": "quiz_validity", "label": "Quiz Validity", "percent": 100, "rating": "Excellent"},
        {"id": "clarity", "label": "Clarity", "percent": 92, "rating": "Very Good"},
    ],
}


def build_k2_think(
    selected_word: dict[str, Any],
    root: dict[str, Any],
    pattern: dict[str, Any] | None,
    quiz: list[dict[str, Any]],
    pipeline_trace: dict[str, Any],
    selected_leaf: dict[str, Any] | None = None,
    settings: Settings | None = None,
    guardrails: dict[str, Any] | None = None,
) -> dict[str, Any]:
    active_settings = settings or get_settings()
    demo = active_settings.enable_k2_think_demo

    lookup_trace = pipeline_trace.get("lookup", {})
    if guardrails is None:
        # The analyze pipeline hands over the verdict its guardrail stage
        # already computed; callers shaping from an evidence state (insights)
        # run the same module here.
        guardrails = run_guardrail_validator_module(
            selected_word=selected_word,
            root=root,
            pattern=pattern,
            quiz=quiz,
            selected_leaf=selected_leaf,
        )["guardrails"]
    evaluation = _build_evaluation(demo)

    # shared facts for word-specific mock reasoning
    facts = _facts(selected_word, root, pattern, quiz, lookup_trace)

    agents = [
        _lookup_agent(facts),
        _morphology_agent(facts),
        _explanation_agent(facts, selected_leaf, demo),
        _quiz_agent(facts),
        _guardrail_agent(facts, guardrails, demo),
        _evaluation_agent(facts, evaluation, demo),
    ]

    return {
        "source": DETERMINISTIC_SOURCE,
        "demo": demo,
        "subtitle": SUBTITLE,
        "agents": agents,
        "evaluation": evaluation,
        "guardrails": guardrails,
        "fallback_note": FALLBACK_NOTE,
    }


# --- shared facts -------------------------------------------------------------


def _facts(selected_word, root, pattern, quiz, lookup_trace) -> dict[str, Any]:
    breakdown = selected_word.get("breakdown") or {}
    root_letters = breakdown.get("root_letters") or []
    categories = sorted(
        {q.get("category") for q in quiz if isinstance(q, dict) and q.get("category")}
    )
    return {
        "word_ar": selected_word.get("arabic", ""),
        "translit": selected_word.get("transliteration", ""),
        "meaning": selected_word.get("meaning", ""),
        "word_id": selected_word.get("id", ""),
        "root_ar": (root or {}).get("arabic", ""),
        "root_id": (root or {}).get("id", ""),
        "root_meaning": (root or {}).get("meaning", ""),
        "root_letters": root_letters,
        "root_display": "·".join(root_letters),
        "pattern_ar": (pattern or {}).get("arabic", ""),
        "pattern_name": (pattern or {}).get("name", ""),
        "pattern_effect": (pattern or {}).get("meaning_effect", ""),
        "segment_count": len(breakdown.get("segments") or []),
        "family_count": lookup_trace.get("family_word_count", 0),
        "normalized": lookup_trace.get("normalized_query", ""),
        "alias_match": bool(lookup_trace.get("alias_match")),
        "quiz_count": len(quiz),
        "categories": categories,
    }


def _agent(
    id,
    step,
    name,
    engine,
    status,
    summary,
    reasoning,
    output,
    model=None,
    engine_status=ENGINE_STATUS_DETERMINISTIC,
):
    return {
        "id": id,
        "step": step,
        "name": name,
        # Legacy: `engine_status` is the field to branch on. Kept so a client
        # that predates it still renders.
        "engine": engine,
        "engine_status": engine_status,
        "model": model,
        "status": status,
        "summary": summary,
        "reasoning": reasoning.strip(),
        "output": output,
    }


# --- deterministic agents (real logic) ----------------------------------------


def _lookup_agent(f) -> dict[str, Any]:
    reasoning = f"""Received the query and normalized it to "{f['normalized']}".
Searched the verified knowledge base for a matching entry{' (via alias table)' if f['alias_match'] else ''}.
Resolved it to word id "{f['word_id']}" on root "{f['root_id']}".
Collected {f['family_count']} words that share this root to grow the family tree."""
    return _agent(
        "lookup", 1, "Lookup Module", DETERMINISTIC_ENGINE, STATUS_COMPLETED,
        f"Found {f['word_ar']} in the verified knowledge base.",
        reasoning,
        f"Word: {f['word_ar']} ({f['translit']}) · Root: {f['root_id']} · Family: {f['family_count']} words",
    )


def _morphology_agent(f) -> dict[str, Any]:
    reasoning = f"""Split {f['word_ar']} into {f['segment_count']} letter segments.
Separated the root letters from the pattern (وزن) letters.
Root letters detected: {f['root_display']}.
Pattern detected: {f['pattern_ar']} — "{f['pattern_name']}"."""
    return _agent(
        "morphology", 2, "Morphology Module", DETERMINISTIC_ENGINE, STATUS_COMPLETED,
        f"Identified root {f['root_display']} and pattern {f['pattern_ar']}.",
        reasoning,
        f"Root {f['root_display']} + pattern {f['pattern_ar']} → {f['meaning']}",
    )


def _quiz_agent(f) -> dict[str, Any]:
    cats = ", ".join(f["categories"]) if f["categories"] else "n/a"
    reasoning = f"""Selected question templates suited to this word family.
Built one correct answer and three plausible distractors per question.
Covered categories: {cats}.
Verified every question has exactly one correct answer."""
    # Deterministic, not K2. This agent was labelled `engine: "k2"` with
    # `model: "K2-Think-v2"` while running 100% template logic — the exact
    # mislabelling §1.5 exists to remove. A live K2 quiz does exist now, but it
    # is served by /api/insights, which relabels this entry to k2_live.
    return _agent(
        "quiz", 4, "Quiz Agent", DETERMINISTIC_ENGINE, STATUS_COMPLETED,
        f"Created {f['quiz_count']} practice question{'s' if f['quiz_count'] != 1 else ''} based on root, pattern, and meaning.",
        reasoning,
        f"{f['quiz_count']} questions · categories: {cats}",
        engine_status=ENGINE_STATUS_DETERMINISTIC,
    )


# --- K2-powered agents (mock while demo, real K2 later) -----------------------


def _explanation_agent(f, selected_leaf, demo) -> dict[str, Any]:
    if not demo:
        return _k2_skipped("explanation", 3, "Explanation Agent", "ENABLE_K2_EXPLANATION")
    explanation = (selected_leaf or {}).get("explanation") or (
        f"{f['word_ar']} comes from the root {f['root_ar']} and follows the pattern "
        f"{f['pattern_ar']}, giving the meaning \"{f['meaning']}\"."
    )
    reasoning = f"""Goal: explain {f['word_ar']} to a beginner using only verified data.
The root {f['root_ar']} carries the meaning "{f['root_meaning']}".
The pattern {f['pattern_ar']} {f['pattern_effect'] or 'shapes the root meaning'}.
Combining root + pattern yields "{f['meaning']}". I will state this plainly and invent no new Arabic."""
    return _agent(
        "explanation", 3, "Explanation Agent", K2_ENGINE, STATUS_COMPLETED,
        "Sample explanation — this step has not run live.",
        reasoning, explanation, model=K2_MODEL_NAME,
        engine_status=ENGINE_STATUS_DEMO_SAMPLE,
    )


def _guardrail_agent(f, guardrails, demo) -> dict[str, Any]:
    if not demo:
        return _k2_skipped("guardrail", 5, "Guardrail Agent", "ENABLE_K2_GUARDRAIL_REVIEW")
    checks = guardrails.get("checks", [])
    passed = sum(1 for c in checks if c.get("passed"))
    reasoning = f"""Reviewed the tutor and quiz output against the verified evidence for {f['word_ar']}.
Checked that the meaning, root {f['root_ar']}, and pattern {f['pattern_ar']} are all supported.
Confirmed the quiz introduces no words outside the verified family.
Result: no unsupported or invented content detected."""
    return _agent(
        "guardrail", 5, "Guardrail Agent", K2_ENGINE, STATUS_COMPLETED,
        "Sample review — this step has not run live.",
        reasoning, f"{passed}/{len(checks)} checks passed — {guardrails.get('summary', '')}",
        model=K2_MODEL_NAME,
        engine_status=ENGINE_STATUS_DEMO_SAMPLE,
    )


def _evaluation_agent(f, evaluation, demo) -> dict[str, Any]:
    if not demo or not evaluation:
        return _k2_skipped("evaluation", 6, "Evaluation Agent", "ENABLE_K2_EVALUATION")
    overall = evaluation["overall"]["value"]
    m = {metric["id"]: metric["percent"] for metric in evaluation["metrics"]}
    reasoning = f"""Scored the response for {f['word_ar']} on three dimensions.
Groundedness: every claim traces back to the knowledge base ({m.get('groundedness')}%).
Quiz validity: questions are well-formed with a single correct answer ({m.get('quiz_validity')}%).
Clarity: phrasing is beginner-appropriate ({m.get('clarity')}%).
Overall quality: {overall}/100."""
    return _agent(
        "evaluation", 6, "Evaluation Agent", K2_ENGINE, STATUS_COMPLETED,
        "Sample scores — this step has not run live.",
        reasoning,
        f"Overall {overall}/100 · Groundedness {m.get('groundedness')}% · "
        f"Quiz {m.get('quiz_validity')}% · Clarity {m.get('clarity')}%",
        model=K2_MODEL_NAME,
        engine_status=ENGINE_STATUS_DEMO_SAMPLE,
    )


def _k2_skipped(id, step, name, flag) -> dict[str, Any]:
    return _agent(
        id, step, name, K2_ENGINE, STATUS_SKIPPED,
        f"Skipped — {flag} is not enabled.",
        f"This K2 step did not run. Enable {flag} to produce a live reasoning trace.",
        "", model=K2_MODEL_NAME,
        engine_status=ENGINE_STATUS_SKIPPED,
    )


# --- evaluation & guardrails --------------------------------------------------


def _build_evaluation(demo: bool) -> dict[str, Any] | None:
    if not demo:
        return None
    return {
        "overall": dict(_DEMO_EVALUATION["overall"]),
        "metrics": [dict(metric) for metric in _DEMO_EVALUATION["metrics"]],
        # These numbers are hand-written and identical for every word. The panel
        # must label them as a sample — an unlabelled 94/100 next to real
        # morphology reads as a measured score (§1.5). /api/insights replaces
        # this block with `engine_status: "k2_live"` or omits it entirely.
        "engine_status": ENGINE_STATUS_DEMO_SAMPLE,
    }


# The guardrail checks live in `app.modules.guardrail_validator_module` — a
# real pipeline stage over the served content, not predicates over the lookup
# (§1.7). This service only places its verdict in the panel.
