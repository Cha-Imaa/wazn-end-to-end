"""Runs the four live K2 agents that enrich a word, for GET /api/insights.

Four agents run **sequentially**, because guardrail and evaluation review what
explanation and quiz produced:

    explanation → quiz → guardrail → evaluation

That is why this work lives off /api/analyze entirely (see NEXT_STEPS.md §1.1).
Each agent independently either succeeds against a live K2 call or falls back,
and the caller can always render a full response:

    k2_live      the call returned validated, grounded output
    fallback     the call or its validation failed; deterministic content is used
    skipped      the agent's ENABLE_K2_* flag is off

Two rules this module exists to enforce:

1. **No pipeline re-run.** `build_base_state(word)` redoes lookup, morphology,
   tree, leaf details and quiz. It must never be called from a request path, so
   everything here takes the state the pipeline already produced, assembled by
   `build_state_from_components`.

2. **A failed agent never degrades into a lie.** Explanation and quiz fall back
   to the deterministic content that /api/analyze already serves. Guardrail and
   evaluation fall back to *nothing* — a fabricated 94/100 is worse than an
   absent score, so `output` stays None and the status says why.

Prompt text is read from `app/prompt_lab/<agent>/<version>/`, which is where
prompts are authored and iterated. No prompt-lab *code* runs here: the lab's
runner uses module-level env vars, a 30s timeout, and prints to stdout. Its
evidence builders and validators are shared deliberately (§1.4 requires reusing
`quiz_validator`), so the request path validates against the same contract the
lab tunes against.
"""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from app.agents.k2_client import K2ClientError, call_k2_json
from app.core.config import Settings, get_settings
from app.prompt_lab.shared.evidence_builder import (
    build_combined_evaluation_input_from_state,
    build_combined_guardrail_input_from_state,
    build_explanation_evidence_from_state,
    build_quiz_evidence_from_state,
)
from app.prompt_lab.shared.validators.evaluation_validator import (
    validate_evaluation_output,
)
from app.prompt_lab.shared.validators.explanation_validator import (
    validate_explanation_output,
)
from app.prompt_lab.shared.validators.guardrail_validator import (
    validate_guardrail_output,
)
from app.prompt_lab.shared.validators.quiz_validator import validate_quiz_output


PROMPT_LAB_DIR = Path(__file__).resolve().parents[1] / "prompt_lab"

K2_MODEL_NAME = "K2-Think-v2"

ENGINE_STATUS_K2_LIVE = "k2_live"
ENGINE_STATUS_FALLBACK = "fallback"
ENGINE_STATUS_SKIPPED = "skipped"

AGENT_EXPLANATION = "explanation"
AGENT_QUIZ = "quiz"
AGENT_GUARDRAIL = "guardrail"
AGENT_EVALUATION = "evaluation"

# Words the demo opens on, one per root so a pre-warm spans four of the six
# families. Pre-warming costs four sequential calls per word, so it stays behind
# ENABLE_K2_INSIGHTS_PREWARM.
#
# NEXT_STEPS.md §1.1 named مدرسة / مكتبة / مفتاح / تجارة, but the knowledge base
# has no ktb or ftḥ root — مكتبة and مفتاح resolve to word_not_found. The six
# roots are ع ل م, د ر س, ق ر ء, س م ع, ن ظ ر, ت ج ر.
PREWARM_WORDS = ["مدرسة", "تجارة", "علم", "نظر"]


@dataclass(frozen=True)
class AgentSpec:
    id: str
    name: str
    step: int
    flag_attribute: str
    flag_env_name: str
    prompt_version_dir: str

    def system_prompt_path(self) -> Path:
        return PROMPT_LAB_DIR / self.prompt_version_dir / "system.txt"

    def user_prompt_path(self) -> Path:
        return PROMPT_LAB_DIR / self.prompt_version_dir / "user.txt"


# `explanation_agent/v3_basic` and `quiz_agent/v2_tree_quiz` are the versions the
# lab last ran. Guardrail and evaluation point at new directories: the released
# ones could not work on a request path — `evaluation_agent/v1_rubric/user.txt`
# has no {llm_input} placeholder, so that agent scored a literal "<...>"
# skeleton and never saw a word, and `guardrail_agent/v2_basic_review/user.txt`
# asked for rubric scores while its system prompt asked for check verdicts.
AGENT_SPECS: dict[str, AgentSpec] = {
    AGENT_EXPLANATION: AgentSpec(
        id=AGENT_EXPLANATION,
        name="Explanation Agent",
        step=3,
        flag_attribute="enable_k2_explanation",
        flag_env_name="ENABLE_K2_EXPLANATION",
        prompt_version_dir="explanation_agent/v3_basic",
    ),
    AGENT_QUIZ: AgentSpec(
        id=AGENT_QUIZ,
        name="Quiz Agent",
        step=4,
        flag_attribute="enable_k2_quiz",
        flag_env_name="ENABLE_K2_QUIZ",
        prompt_version_dir="quiz_agent/v2_tree_quiz",
    ),
    AGENT_GUARDRAIL: AgentSpec(
        id=AGENT_GUARDRAIL,
        name="Guardrail Agent",
        step=5,
        flag_attribute="enable_k2_guardrail_review",
        flag_env_name="ENABLE_K2_GUARDRAIL_REVIEW",
        prompt_version_dir="guardrail_agent/v4_combined",
    ),
    AGENT_EVALUATION: AgentSpec(
        id=AGENT_EVALUATION,
        name="Evaluation Agent",
        step=6,
        flag_attribute="enable_k2_evaluation",
        flag_env_name="ENABLE_K2_EVALUATION",
        prompt_version_dir="evaluation_agent/v2_scoring",
    ),
}

# K2 question `type` values carry the same information the deterministic quiz
# puts in `category`, which the Insights tab reads. Mapping the label keeps a K2
# quiz drop-in compatible; it adds no content.
_QUIZ_TYPE_TO_CATEGORY = {
    "root_meaning": "root",
    "leaf_meaning": "meaning",
    "meaning_to_leaf": "meaning",
    "pattern_recognition": "pattern",
    "pattern_meaning_effect": "pattern",
    "pattern_application": "pattern",
}

_INSIGHTS_CACHE: dict[str, dict[str, Any]] = {}


def build_insights(
    state: dict[str, Any],
    settings: Settings | None = None,
    use_cache: bool = True,
) -> dict[str, Any]:
    """
    Run the four agents over an already-computed pipeline state.

    `state` must come from `build_state_from_components` (or `build_base_state`
    off the request path). Never raises for agent failure — inspect each agent's
    `engine_status`.
    """
    active_settings = settings or get_settings()

    if not state.get("found"):
        # The evidence builders raise RuntimeError on an unresolved state. The
        # caller should not have to catch that to keep /api/insights on HTTP 200.
        return _not_found_insights(state)

    selected_word_id = state.get("selected_word_id")

    if use_cache and selected_word_id and selected_word_id in _INSIGHTS_CACHE:
        cached = dict(_INSIGHTS_CACHE[selected_word_id])
        cached["cached"] = True
        return cached

    word = state.get("query", "")
    selected_leaf = state.get("selected_leaf") or {}
    deterministic_quiz = state.get("quiz", [])

    explanation_result = _run_explanation(state, word, active_settings)
    quiz_result = _run_quiz(state, word, active_settings)

    # Guardrail and evaluation review whatever the first two actually produced,
    # live output or deterministic fallback, so their verdicts describe what the
    # learner will really see.
    tutor_output = _tutor_output_for_review(explanation_result, selected_leaf)
    quiz_output = _quiz_output_for_review(quiz_result, deterministic_quiz)

    guardrail_result = _run_guardrail(
        state=state,
        word=word,
        tutor_output=tutor_output,
        quiz_output=quiz_output,
        settings=active_settings,
    )

    evaluation_result = _run_evaluation(
        state=state,
        word=word,
        tutor_output=tutor_output,
        quiz_output=quiz_output,
        settings=active_settings,
    )

    insights = {
        "selected_word_id": selected_word_id,
        "cached": False,
        "agents": {
            AGENT_EXPLANATION: explanation_result,
            AGENT_QUIZ: quiz_result,
            AGENT_GUARDRAIL: guardrail_result,
            AGENT_EVALUATION: evaluation_result,
        },
        "quiz": _upgraded_quiz(quiz_result),
    }

    if use_cache and selected_word_id:
        _INSIGHTS_CACHE[selected_word_id] = insights

    return insights


def _not_found_insights(state: dict[str, Any]) -> dict[str, Any]:
    """A fully shaped response for a word that does not resolve. Nothing is run."""
    return {
        "selected_word_id": None,
        "cached": False,
        "agents": {
            agent_id: {
                "id": spec.id,
                "name": spec.name,
                "step": spec.step,
                "engine_status": ENGINE_STATUS_SKIPPED,
                "model": None,
                "reasoning": None,
                "reasoning_tokens": None,
                "output": None,
                "violations": [],
                "error": state.get("reason", "word_not_found"),
            }
            for agent_id, spec in AGENT_SPECS.items()
        },
        "quiz": None,
    }


def clear_insights_cache() -> None:
    _INSIGHTS_CACHE.clear()


def insights_cache_size() -> int:
    return len(_INSIGHTS_CACHE)


def prewarm_insights(
    state_builder: Callable[[str], dict[str, Any] | None],
    words: list[str] | None = None,
    settings: Settings | None = None,
) -> dict[str, str]:
    """
    Fill the cache for the demo words before the first request arrives.

    `state_builder` maps a word to a pipeline state (or None if it does not
    resolve); the caller supplies it so this module stays off the pipeline's
    import path. Returns a per-word outcome for logging. Never raises.
    """
    active_settings = settings or get_settings()

    if not active_settings.enable_k2_insights_prewarm:
        return {}

    outcomes: dict[str, str] = {}

    for word in words or PREWARM_WORDS:
        try:
            state = state_builder(word)
        except Exception as error:  # a bad KB entry must not stop startup
            outcomes[word] = f"state_error: {error}"
            continue

        if not state or not state.get("found"):
            outcomes[word] = "not_found"
            continue

        try:
            insights = build_insights(state, settings=active_settings)
        except Exception as error:
            outcomes[word] = f"insights_error: {error}"
            continue

        statuses = {
            agent_id: result.get("engine_status")
            for agent_id, result in insights.get("agents", {}).items()
        }
        outcomes[word] = ", ".join(
            f"{agent_id}={status}" for agent_id, status in sorted(statuses.items())
        )

    return outcomes


# --- per-agent runners --------------------------------------------------------


def _run_explanation(
    state: dict[str, Any],
    word: str,
    settings: Settings,
) -> dict[str, Any]:
    spec = AGENT_SPECS[AGENT_EXPLANATION]

    if not getattr(settings, spec.flag_attribute):
        return _skipped(spec)

    packet = build_explanation_evidence_from_state(state)

    return _call_and_validate(
        spec=spec,
        packet=packet,
        word=word,
        settings=settings,
        validate=_validate_via_validation_result(validate_explanation_output),
        fallback_output=_deterministic_explanation(state),
    )


def _run_quiz(
    state: dict[str, Any],
    word: str,
    settings: Settings,
) -> dict[str, Any]:
    spec = AGENT_SPECS[AGENT_QUIZ]

    if not getattr(settings, spec.flag_attribute):
        return _skipped(spec)

    packet = build_quiz_evidence_from_state(state)

    return _call_and_validate(
        spec=spec,
        packet=packet,
        word=word,
        settings=settings,
        validate=_validate_via_validation_result(validate_quiz_output),
        fallback_output={"quiz": state.get("quiz", [])},
    )


def _run_guardrail(
    state: dict[str, Any],
    word: str,
    tutor_output: dict[str, Any],
    quiz_output: dict[str, Any],
    settings: Settings,
) -> dict[str, Any]:
    spec = AGENT_SPECS[AGENT_GUARDRAIL]

    if not getattr(settings, spec.flag_attribute):
        return _skipped(spec)

    packet = {
        "llm_input": build_combined_guardrail_input_from_state(
            state=state,
            tutor_output=tutor_output,
            quiz_output=quiz_output,
        ),
    }

    return _call_and_validate(
        spec=spec,
        packet=packet,
        word=word,
        settings=settings,
        validate=_validate_guardrail,
        # No deterministic guardrail verdict exists yet — §1.7 wires the real
        # validator. Reporting "checks passed" without running them would be
        # exactly the fabrication this module is meant to prevent.
        fallback_output=None,
    )


def _run_evaluation(
    state: dict[str, Any],
    word: str,
    tutor_output: dict[str, Any],
    quiz_output: dict[str, Any],
    settings: Settings,
) -> dict[str, Any]:
    spec = AGENT_SPECS[AGENT_EVALUATION]

    if not getattr(settings, spec.flag_attribute):
        return _skipped(spec)

    packet = {
        "llm_input": build_combined_evaluation_input_from_state(
            state=state,
            tutor_output=tutor_output,
            quiz_output=quiz_output,
        ),
    }

    return _call_and_validate(
        spec=spec,
        packet=packet,
        word=word,
        settings=settings,
        validate=_validate_evaluation,
        # Never invent a score. An absent evaluation block is honest; a
        # hardcoded 94/100 is not.
        fallback_output=None,
    )


# --- the shared call path -----------------------------------------------------


def _call_and_validate(
    spec: AgentSpec,
    packet: dict[str, Any],
    word: str,
    settings: Settings,
    validate: Callable[[dict[str, Any], str, dict[str, Any] | None], tuple[bool, list[str]]],
    fallback_output: Any,
) -> dict[str, Any]:
    try:
        system_prompt = spec.system_prompt_path().read_text(encoding="utf-8")
        user_prompt = _render_user_prompt(
            template=spec.user_prompt_path().read_text(encoding="utf-8"),
            word=word,
            packet=packet,
        )
    except OSError as error:
        return _fallback(spec, fallback_output, f"prompt_unreadable: {error}")

    try:
        response = call_k2_json(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            settings=settings,
            timeout_seconds=settings.k2_insights_timeout_seconds,
        )
    except K2ClientError as error:
        return _fallback(spec, fallback_output, str(error))

    answer_content = response.get("answer_content") or ""
    parsed_output = response.get("parsed_output")

    passed, violations = validate(packet, answer_content, parsed_output)

    if not passed:
        result = _fallback(spec, fallback_output, "validation_failed")
        result["violations"] = violations
        # Keep the trace even on rejection — it is the record of what K2 said,
        # and the Insights tab is the place to see why an agent was rejected.
        result["reasoning"] = response.get("reasoning")
        result["reasoning_tokens"] = response.get("reasoning_tokens")
        return result

    return {
        "id": spec.id,
        "name": spec.name,
        "step": spec.step,
        "engine_status": ENGINE_STATUS_K2_LIVE,
        "model": K2_MODEL_NAME,
        "reasoning": response.get("reasoning"),
        "reasoning_tokens": response.get("reasoning_tokens"),
        "output": parsed_output,
        "violations": [],
        "error": None,
    }


def _render_user_prompt(
    template: str,
    word: str,
    packet: dict[str, Any],
) -> str:
    """
    Fill the same placeholders the prompt lab fills, so a prompt tuned in the lab
    behaves identically here.
    """
    llm_input = packet.get("llm_input", packet)

    input_json = json.dumps(llm_input, ensure_ascii=False, indent=2)

    rendered = template.replace("{word}", word)
    rendered = rendered.replace("{evidence_packet}", input_json)
    rendered = rendered.replace("{llm_input}", input_json)

    return rendered


def _skipped(spec: AgentSpec) -> dict[str, Any]:
    return {
        "id": spec.id,
        "name": spec.name,
        "step": spec.step,
        "engine_status": ENGINE_STATUS_SKIPPED,
        "model": None,
        "reasoning": None,
        "reasoning_tokens": None,
        "output": None,
        "violations": [],
        "error": f"{spec.flag_env_name} is not enabled.",
    }


def _fallback(spec: AgentSpec, output: Any, error: str) -> dict[str, Any]:
    return {
        "id": spec.id,
        "name": spec.name,
        "step": spec.step,
        "engine_status": ENGINE_STATUS_FALLBACK,
        "model": None,
        "reasoning": None,
        "reasoning_tokens": None,
        "output": output,
        "violations": [],
        "error": error,
    }


# --- validator adapters -------------------------------------------------------
#
# The four validators disagree on both signature and return type: two take the
# raw answer string and return a ValidationResult dataclass, one takes a parsed
# dict and returns a plain dict, one takes the string and returns a plain dict.
# These adapters give the call path one shape.


def _validate_via_validation_result(
    validator: Callable[[dict[str, Any], str], Any],
) -> Callable[[dict[str, Any], str, dict[str, Any] | None], tuple[bool, list[str]]]:
    def adapter(
        packet: dict[str, Any],
        answer_content: str,
        parsed_output: dict[str, Any] | None,
    ) -> tuple[bool, list[str]]:
        result = validator(packet, answer_content)
        return bool(result.passed), list(result.violations)

    return adapter


def _validate_guardrail(
    packet: dict[str, Any],
    answer_content: str,
    parsed_output: dict[str, Any] | None,
) -> tuple[bool, list[str]]:
    result = validate_guardrail_output(packet, parsed_output)
    return bool(result.get("passed")), list(result.get("violations", []))


def _validate_evaluation(
    packet: dict[str, Any],
    answer_content: str,
    parsed_output: dict[str, Any] | None,
) -> tuple[bool, list[str]]:
    result = validate_evaluation_output(packet, answer_content)
    return bool(result.get("passed")), list(result.get("violations", []))


# --- shaping outputs for the next agent and the caller ------------------------


def _deterministic_explanation(state: dict[str, Any]) -> dict[str, Any]:
    selected_leaf = state.get("selected_leaf") or {}

    return {
        "explanation": selected_leaf.get("explanation", ""),
        "pattern_explanation": selected_leaf.get("pattern_explanation", ""),
        "same_pattern_explanation": selected_leaf.get("same_pattern_explanation", ""),
    }


def _tutor_output_for_review(
    explanation_result: dict[str, Any],
    selected_leaf: dict[str, Any],
) -> dict[str, Any]:
    output = explanation_result.get("output")

    if isinstance(output, dict):
        return output

    return {
        "explanation": selected_leaf.get("explanation", ""),
        "pattern_explanation": selected_leaf.get("pattern_explanation", ""),
        "same_pattern_explanation": selected_leaf.get("same_pattern_explanation", ""),
    }


def _quiz_output_for_review(
    quiz_result: dict[str, Any],
    deterministic_quiz: list[dict[str, Any]],
) -> dict[str, Any]:
    output = quiz_result.get("output")

    if isinstance(output, dict) and isinstance(output.get("quiz"), list):
        return {"quiz": output["quiz"]}

    return {"quiz": deterministic_quiz}


def _upgraded_quiz(quiz_result: dict[str, Any]) -> list[dict[str, Any]] | None:
    """
    Return the K2 quiz in the deterministic quiz's shape, or None.

    None means "no upgrade" — the caller keeps the quiz /api/analyze already
    sent rather than swapping in something different.
    """
    if quiz_result.get("engine_status") != ENGINE_STATUS_K2_LIVE:
        return None

    output = quiz_result.get("output")

    if not isinstance(output, dict) or not isinstance(output.get("quiz"), list):
        return None

    return [
        _normalize_k2_question(question)
        for question in output["quiz"]
        if isinstance(question, dict)
    ]


def _normalize_k2_question(question: dict[str, Any]) -> dict[str, Any]:
    """
    Add the two keys the deterministic quiz has and K2's output does not.

    `choices` already agree exactly — both are `{"id": "a".."d", "text": ...}` —
    and K2 additionally carries `correct_feedback` / `wrong_feedback` /
    `choice_feedback`, which are kept as-is for the frontend to use.
    """
    normalized = dict(question)

    question_type = question.get("type")

    normalized["category"] = _QUIZ_TYPE_TO_CATEGORY.get(question_type, question_type)
    normalized["source"] = "k2"

    return normalized
