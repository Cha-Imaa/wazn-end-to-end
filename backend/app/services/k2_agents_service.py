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

import copy
import json
import random
import re
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
from app.prompt_lab.shared.validators.common_validator import (
    extract_arabic_runs,
    normalize_arabic,
    replace_arabic_runs,
)
from app.prompt_lab.shared.validators.quiz_claim_checker import affirmed_choice_id
from app.prompt_lab.shared.validators.quiz_validator import (
    derive_correct_choice_id,
    validate_quiz_output,
)


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

    # Per-agent thinking budget, or None for the server default. All four
    # agents need a bound: at default effort K2 loops in self-checking on some
    # inputs until it consumes the whole completion budget as reasoning (empty
    # content), or emits malformed objects (§1.3). Measured for the guardrail
    # across 8 roots on 2026-07-29: default validated 6/11 at ~16k reasoning
    # tokens / ~13s median; "medium" validated 11/11 at ~2.5k tokens / ~4s, and
    # still caught every injected error in the poisoned runs.
    reasoning_effort: str | None = None

    def system_prompt_path(self) -> Path:
        return PROMPT_LAB_DIR / self.prompt_version_dir / "system.txt"

    def user_prompt_path(self) -> Path:
        return PROMPT_LAB_DIR / self.prompt_version_dir / "user.txt"


# `explanation_agent/v3_basic` and `quiz_agent/v3_tree_quiz` are the versions the
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
        # v4 grounds the pattern-function claim in the KB's name /
        # meaning_effect — v3 guessed it from the pattern shape (فَعَل was
        # described as "points to the person who does the action"). Medium
        # effort for the same reason as quiz/guardrail: at default effort,
        # 2 of 16 audited calls spent the whole budget reasoning and
        # returned empty content.
        prompt_version_dir="explanation_agent/v4_grounded_pattern",
        reasoning_effort="medium",
    ),
    AGENT_QUIZ: AgentSpec(
        id=AGENT_QUIZ,
        name="Quiz Agent",
        step=4,
        flag_attribute="enable_k2_quiz",
        flag_env_name="ENABLE_K2_QUIZ",
        # v4 grounds the claims feedback prose makes: pattern function comes
        # from the KB's pattern.name, a word's pattern and meaning from its own
        # entry. v3 said neither, and on قَاسِم produced a fully grounded,
        # correctly keyed quiz whose distractor feedback called the verb pattern
        # فَعَلَ "a noun pattern" — caught only by the guardrail, after serving.
        prompt_version_dir="quiz_agent/v4_grounded_feedback",
        reasoning_effort="medium",
    ),
    AGENT_GUARDRAIL: AgentSpec(
        id=AGENT_GUARDRAIL,
        name="Guardrail Agent",
        step=5,
        flag_attribute="enable_k2_guardrail_review",
        flag_env_name="ENABLE_K2_GUARDRAIL_REVIEW",
        # v5 scopes quiz grounding checks to content presented as true —
        # v4 flagged legitimate out-of-family distractors on 6 of 8 words.
        prompt_version_dir="guardrail_agent/v5_combined",
        reasoning_effort="medium",
    ),
    AGENT_EVALUATION: AgentSpec(
        id=AGENT_EVALUATION,
        name="Evaluation Agent",
        step=6,
        flag_attribute="enable_k2_evaluation",
        flag_env_name="ENABLE_K2_EVALUATION",
        prompt_version_dir="evaluation_agent/v2_scoring",
        # Same disease as the other three, plus a scoring defect of its own.
        # Measured across 8 roots on 2026-07-29 reviewing deterministic tutor +
        # quiz content: at default effort 7/8 validated (مدرسة spent its whole
        # budget reasoning and returned empty content) at ~9k reasoning tokens /
        # ~8s median, and the scores showed exactly the central-tendency bias
        # the prompt's calibration section warns against — clarity never left
        # 4-7, and quiz_quality fell to 3 on content the guardrail passes with
        # zero flags. At medium: 8/8 validated, ~1.2k tokens, ~2.9s, scores
        # spread 7-10 and word-specific. Calibration still discriminates —
        # injecting a wrong meaning into the tutor explanation pulled
        # groundedness from 10 to 3-5 and overall to 5-6 on 3/3 words.
        reasoning_effort="medium",
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

# The tree quiz's evidence is the root plus its 8 leaves — identical for every
# word in a family — and its questions span the whole tree, so one live quiz per
# root is correct, not a loss. Keyed by root_id so searching مدرسة then دَرَسَ
# costs one K2 call, not two. Only k2_live results are stored: a fallback's
# output is the word-specific deterministic quiz and its error belongs to the
# call that failed. (Explanation stays word-keyed — it genuinely differs per
# word — via _INSIGHTS_CACHE above.)
_QUIZ_CACHE_BY_ROOT: dict[str, dict[str, Any]] = {}


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
    quiz_result = _run_quiz(state, word, active_settings, use_cache=use_cache)

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
    _QUIZ_CACHE_BY_ROOT.clear()


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

    def postprocess(output: dict[str, Any] | None) -> list[str]:
        # Root-citation repair first, and deliberately *outside* the
        # content-preservation check: rewriting "the root زَرَعَ" to "the root
        # ز ر ع" is an intentional change of which item the run refers to, which
        # is why validation — running after this — is what checks it.
        llm_input = packet.get("llm_input", {})
        root = llm_input.get("root") if isinstance(llm_input, dict) else None
        if isinstance(root, dict):
            _repair_root_citations(output, root.get("arabic"))

        canonical_by_key = _explanation_canonical_map(packet)

        return _canonicalize_checked(
            output,
            lambda value: _canonicalize_explanation_arabic(value, canonical_by_key),
            _kb_forms(canonical_by_key),
        )

    return _call_and_validate(
        spec=spec,
        packet=packet,
        word=word,
        settings=settings,
        validate=_validate_via_validation_result(validate_explanation_output),
        fallback_output=_deterministic_explanation(state),
        postprocess=postprocess,
    )


def _run_quiz(
    state: dict[str, Any],
    word: str,
    settings: Settings,
    use_cache: bool = True,
) -> dict[str, Any]:
    spec = AGENT_SPECS[AGENT_QUIZ]

    if not getattr(settings, spec.flag_attribute):
        return _skipped(spec)

    root_id = (state.get("root") or {}).get("id")

    if use_cache and root_id and root_id in _QUIZ_CACHE_BY_ROOT:
        # Deep copy: the result is embedded in per-word insights that are
        # themselves cached, so two words must never share mutable structures.
        return copy.deepcopy(_QUIZ_CACHE_BY_ROOT[root_id])

    packet = build_quiz_evidence_from_state(state)

    def repair(output: dict[str, Any] | None) -> None:
        # Answer keys first — redistribution then moves the *right* text
        # around, and the distribution is judged on the repaired answers.
        repair_answer_ids(output, packet.get("llm_input", {}))
        redistribute_answer_positions(output, seed=word)

    def postprocess(output: dict[str, Any] | None) -> list[str]:
        canonical_by_key = _quiz_canonical_map(packet)

        return _canonicalize_checked(
            output,
            lambda value: _canonicalize_quiz_arabic(value, canonical_by_key),
            _kb_forms(canonical_by_key),
        )

    result = _call_and_validate(
        spec=spec,
        packet=packet,
        word=word,
        settings=settings,
        validate=_validate_via_validation_result(validate_quiz_output),
        fallback_output={"quiz": state.get("quiz", [])},
        repair=repair,
        postprocess=postprocess,
    )

    # Cached content is now post-canonicalization *and* post-validation — the
    # cache can no longer hold a quiz that was never checked in the form served.
    if result.get("engine_status") == ENGINE_STATUS_K2_LIVE and use_cache and root_id:
        _QUIZ_CACHE_BY_ROOT[root_id] = copy.deepcopy(result)

    return result


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
    repair: Callable[[dict[str, Any] | None], None] | None = None,
    postprocess: Callable[[dict[str, Any] | None], list[str]] | None = None,
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
            max_tokens=(
                settings.k2_max_completion_tokens
                if settings.k2_max_completion_tokens > 0
                else None
            ),
            reasoning_effort=spec.reasoning_effort,
        )
    except K2ClientError as error:
        return _fallback(spec, fallback_output, str(error))

    answer_content = response.get("answer_content") or ""
    parsed_output = response.get("parsed_output")

    if repair is not None:
        # Mechanical fixes applied before validation — only for defects that are
        # safe to correct in code (e.g. answer-position distribution). The
        # validated content is the repaired content, so answer_content must be
        # re-serialized to keep the two in sync for string-based validators.
        repair(parsed_output)
        answer_content = json.dumps(parsed_output, ensure_ascii=False)

    if postprocess is not None:
        # Spelling passes (canonicalization, root-citation repair) run *here*,
        # before validation, so validation is the last thing that touches
        # learner-facing content. They used to run after the result was already
        # accepted, which left the one code path that rewrites Arabic on screen
        # with nothing checking its output (§1.3) — and it had already shipped a
        # false quiz answer that way. Their own content-preservation violations
        # reject the agent outright: a pass that changed the meaning of what it
        # was only supposed to re-spell is not something to serve.
        postprocess_violations = postprocess(parsed_output)
        answer_content = json.dumps(parsed_output, ensure_ascii=False)

        if postprocess_violations:
            result = _fallback(spec, fallback_output, "postprocess_failed")
            result["violations"] = postprocess_violations
            result["reasoning"] = response.get("reasoning")
            result["reasoning_tokens"] = response.get("reasoning_tokens")
            return result

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


def repair_answer_ids(output: Any, evidence: dict[str, Any]) -> None:
    """
    Point each answer_id at the evidence-derived correct choice, in place.

    K2 sometimes emits an answer key that contradicts its own choice_feedback
    (observed live on زَرَعَ: 3 of 5 answers wrong while every choice was
    grounded, so validation passed). The correct choice is a KB fact the
    validator can derive (`derive_correct_choice_id`); when it derives one,
    the key is repaired rather than costing the learner the whole live quiz.

    Only where the model's own prose agrees, though. This used to repair
    unconditionally, on the stated grounds that "choice_feedback is keyed per
    choice and correct_feedback states the fact, not the letter" — which is
    wrong about choice_feedback, whose entries open with "Correct." or "Not
    quite". Moving the key past a "Correct." leaves it congratulating a wrong
    pick and rejecting the right one; observed live on عِلْم, 2026-07-29. So a
    key is repaired when the affirming feedback names the derived choice (a
    clerical slip, feedback proves the intent) and left alone when it names a
    different one — the model then genuinely believes a wrong answer, which is
    not a repair but a rejection, and validation makes it one.

    Underivable questions are left alone; the validator skips them too, and the
    live guardrail remains the reviewer of last resort.
    """
    if not isinstance(output, dict) or not isinstance(output.get("quiz"), list):
        return

    for question in output["quiz"]:
        if not isinstance(question, dict):
            continue

        derived = derive_correct_choice_id(question, evidence)

        if derived is None or derived == question.get("answer_id"):
            continue

        affirmed = affirmed_choice_id(question)

        if affirmed is not None and affirmed != derived:
            continue

        question["answer_id"] = derived


def redistribute_answer_positions(output: Any, seed: str) -> None:
    """
    Repair correct-answer clustering in place, seeded so it is reproducible.

    The validator rejects a quiz whose correct answer sits in the same slot
    more than twice — a presentational rule K2 satisfies unreliably (observed:
    'b' three times out of five). Slot assignment carries no content, so it is
    repaired in code rather than costing the learner a whole live quiz: the
    correct choice is swapped into a target slot, and choice_feedback follows
    its text. Question text never references choice letters (the prompt's
    feedback style contrasts contents, not letters), so swapping is safe.

    Only runs when the distribution is actually violated.
    """
    if not isinstance(output, dict) or not isinstance(output.get("quiz"), list):
        return

    quiz = [q for q in output["quiz"] if isinstance(q, dict)]

    answer_ids = [q.get("answer_id") for q in quiz]

    if not any(answer_ids.count(letter) > 2 for letter in ("a", "b", "c", "d")):
        return

    rng = random.Random(seed)

    letters = ["a", "b", "c", "d"]
    targets = letters[:]
    rng.shuffle(targets)
    # Four distinct slots plus extras drawn one per remaining question keeps
    # every letter's count at 2 or below for the 5-question quiz.
    while len(targets) < len(quiz):
        targets.append(rng.choice(letters))

    for question, target in zip(quiz, targets):
        current = question.get("answer_id")
        choices = question.get("choices")
        feedback = question.get("choice_feedback")

        if current == target or current not in letters or target not in letters:
            continue
        if not isinstance(choices, list) or not isinstance(feedback, dict):
            continue

        by_id = {
            choice.get("id"): choice
            for choice in choices
            if isinstance(choice, dict)
        }
        if current not in by_id or target not in by_id:
            continue

        by_id[current]["text"], by_id[target]["text"] = (
            by_id[target]["text"],
            by_id[current]["text"],
        )
        feedback[current], feedback[target] = (
            feedback.get(target),
            feedback.get(current),
        )
        question["answer_id"] = target


def _arabic_comparison_key(text: str) -> str:
    """Match the validator's grounding key: tashkeel-, spacing-insensitive."""
    return normalize_arabic(text).replace(" ", "")


def _canonical_key(text: str) -> str:
    """
    A canonicalization key that keeps roots and words apart.

    `_arabic_comparison_key` folds spacing, which is right for *grounding* — a
    root written در س is still the root د ر س — but wrong for choosing a
    replacement: a root's spaced letters and its bare Form-I verb reduce to the
    same key on most roots (غ ف ر and غَفَرَ both fold to غفر), so one
    overwrote the other. Observed live on غَفَرَ 2026-07-29: the root registers
    first, so a quiz asking which word فَعَلَ forms had its correct answer
    غَفَرَ rewritten *by this pass* into the bare root غ ف ر — feedback and
    all — and only the guardrail caught it. The explanation map registers the
    selected word first and so corrupted the same collision in the opposite
    direction, rewriting genuine root citations into the full word.

    Bucketing by spacing fixes both: a run with internal spaces can only be
    replaced by a spaced canonical form (so در س → د ر س still works), and a
    run without them only by a word form.
    """
    normalized = normalize_arabic(text).strip()
    bucket = "spaced" if " " in normalized else "solid"

    return f"{bucket}:{normalized.replace(' ', '')}"


def _arabic_run_sequence(value: Any) -> list[str]:
    """
    Every Arabic run reachable in `value`, verbatim, in the same order
    `_arabic_key_sequence` walks. Paired with that sequence it says not only
    which KB items the output refers to, but exactly how each one was spelled.
    """
    if isinstance(value, str):
        return list(extract_arabic_runs(value))

    if isinstance(value, dict):
        runs: list[str] = []
        for name in sorted(value, key=str):
            runs.extend(_arabic_run_sequence(value[name]))
        return runs

    if isinstance(value, list):
        runs = []
        for item in value:
            runs.extend(_arabic_run_sequence(item))
        return runs

    return []


def _arabic_key_sequence(value: Any) -> list[str]:
    """
    Every Arabic run reachable in `value`, as canonical keys, in a stable order.

    The fingerprint the canonicalization contract is checked against: which KB
    items the output's Arabic refers to, and in what order. Dict keys are walked
    sorted so the sequence does not depend on insertion order.
    """
    if isinstance(value, str):
        return [_canonical_key(run) for run in extract_arabic_runs(value)]

    if isinstance(value, dict):
        keys: list[str] = []
        for name in sorted(value, key=str):
            keys.extend(_arabic_key_sequence(value[name]))
        return keys

    if isinstance(value, list):
        keys = []
        for item in value:
            keys.extend(_arabic_key_sequence(item))
        return keys

    return []


def _canonicalize_checked(
    output: Any,
    canonicalize: Callable[[Any], None],
    kb_forms: set[str],
) -> list[str]:
    """
    Run a canonicalization pass and prove it preserved the output's content.

    The contract has two halves:

    1. The pass may not change which item a run refers to, nor add, drop, or
       reorder runs — the `_canonical_key` sequence before versus after.
    2. A run that is *already* one of the KB's exact forms may not be rewritten
       at all. There is nothing to canonicalize about a form the KB already
       spells that way, so any such rewrite is the pass mistaking one item for
       another.

    The second half exists because the first cannot see the collision that
    matters most: `_canonical_key` strips tashkeel, and within a single root's
    evidence that is not injective. Measured over the KB: on **35 of 58 roots**
    two words share the stripped key (دَرَسَ / دَرْس, عَلِمَ / عَلَّمَ / عِلْم)
    and on 35 two patterns do (فَعَلَ / فَعْل). So the replacement map held one
    arbitrary member per collision and rewrote the others into it — turning a
    correct word into a different, also-correct-looking KB word, in prose and in
    choice text, with the key-sequence check passing because both spellings fold
    to the same key. `_register_canonical` now declines ambiguous keys, and this
    is the check that would have caught it.

    Returns violations — empty when the pass was content-preserving.
    """
    before_keys = _arabic_key_sequence(output)
    before_runs = _arabic_run_sequence(output)

    canonicalize(output)

    after_keys = _arabic_key_sequence(output)
    after_runs = _arabic_run_sequence(output)

    if before_keys != after_keys:
        return [
            "canonicalization changed the output's Arabic content: "
            f"{len(before_keys)} run(s) referring to {sorted(set(before_keys))} became "
            f"{len(after_keys)} referring to {sorted(set(after_keys))}"
        ]

    return [
        f"canonicalization rewrote '{before}', which the knowledge base already"
        f" spells that way, into '{after}'"
        for before, after in zip(before_runs, after_runs)
        if before != after and before.strip() in kb_forms
    ]


def _register_canonical(
    canonical_by_key: dict[str, set[str]],
    value: Any,
) -> None:
    if isinstance(value, str) and value.strip():
        canonical_by_key.setdefault(_canonical_key(value), set()).add(value.strip())


def _canonical_form(canonical_by_key: dict[str, set[str]], run: str) -> str:
    """
    The KB spelling for `run`, or `run` unchanged when there isn't exactly one.

    Ambiguity is the important case, not an edge case: a root's evidence
    routinely contains two items whose only difference is tashkeel (35 of 58
    roots — دَرَسَ / دَرْس, the patterns فَعَلَ / فَعْل), and the key this map
    is built on strips tashkeel. When two KB forms answer to one key there is no
    way to tell which one the model meant, so the run is left as written: a
    learner seeing an under-vocalized near-miss is a cosmetic failure, and a
    learner shown a *different word from the same family* is the corruption
    §1.3 is about.
    """
    forms = canonical_by_key.get(_canonical_key(run))

    if not forms or len(forms) != 1:
        return run

    return next(iter(forms))


def _canonicalize_prose(
    text: Any,
    canonical_by_key: dict[str, set[str]],
) -> Any:
    """
    Replace each Arabic run with the KB's exact form, or leave it alone.

    Whole runs only. This used to `str.replace(run, canonical)`, which rewrites
    the run's letters wherever they occur — including inside a *longer* Arabic
    word later in the same string, which is a corruption no validator was
    looking for. `replace_arabic_runs` works on the run boundaries the grounding
    check itself uses.
    """
    if not isinstance(text, str):
        return text

    return replace_arabic_runs(
        text,
        lambda run: _canonical_form(canonical_by_key, run),
    )


# An Arabic run directly following the English word "root" (optionally "root
# letters", or with a colon) — the only context where citing the full word
# instead of the spaced letters is a teaching error worth repairing.
_ROOT_CITATION_RE = re.compile(
    r"(root(?:\s+letters)?[\s:]+)"
    r"([؀-ۿ][؀-ۿ\s]*[؀-ۿ]|[؀-ۿ])",
    re.IGNORECASE,
)


def _repair_root_citations(output: Any, root_arabic: Any) -> None:
    """
    Rewrite "the root زَرَعَ" to "the root ز ر ع", in place.

    The prompt asks for the spaced letters, but on bare Form-I verbs — where
    the word *is* the vocalized root — K2 keeps citing the full word (observed
    live on زَرَعَ and كَتَبَ, and flagged by the live guardrail as "Root
    Arabic mismatched"). Canonicalization cannot fix it: the word and the root
    share a comparison key, so the map cannot tell them apart. The English
    word "root" immediately before the run is what disambiguates.
    """
    if not isinstance(output, dict) or not isinstance(root_arabic, str):
        return
    if not root_arabic.strip():
        return

    root_key = _arabic_comparison_key(root_arabic)

    def fix(match: re.Match) -> str:
        run = match.group(2)
        if _arabic_comparison_key(run) == root_key and run != root_arabic:
            return match.group(1) + root_arabic
        return match.group(0)

    for field_name in (
        "explanation",
        "pattern_explanation",
        "same_pattern_explanation",
    ):
        value = output.get(field_name)
        if isinstance(value, str):
            output[field_name] = _ROOT_CITATION_RE.sub(fix, value)


def _explanation_canonical_map(packet: dict[str, Any]) -> dict[str, set[str]]:
    """Canonical key → the KB form(s) answering to it, for explanation prose."""
    llm_input = packet.get("llm_input", packet)

    canonical_by_key: dict[str, set[str]] = {}

    for key in ("selected_word", "root", "pattern"):
        source = llm_input.get(key)
        if isinstance(source, dict):
            _register_canonical(canonical_by_key, source.get("arabic"))

    cards = llm_input.get("same_pattern_cards")
    if isinstance(cards, list):
        for card in cards:
            if isinstance(card, dict):
                _register_canonical(canonical_by_key, card.get("arabic"))

    return canonical_by_key


def _canonicalize_explanation_arabic(
    output: Any,
    canonical_by_key: dict[str, set[str]],
) -> None:
    """
    Rewrite Arabic in explanation prose to the KB's exact vocalized form, in
    place — the same rule as the quiz (§1.4): validation is tashkeel- and
    spacing-insensitive, but the learner must never see the model's
    under-vocalized near-miss (observed live: حَكم for the card حَكَمَ).
    """
    if not isinstance(output, dict):
        return

    for field_name in (
        "explanation",
        "pattern_explanation",
        "same_pattern_explanation",
    ):
        output[field_name] = _canonicalize_prose(
            output.get(field_name), canonical_by_key
        )


def _quiz_canonical_map(packet: dict[str, Any]) -> dict[str, set[str]]:
    """Canonical key → the KB form(s) answering to it, for quiz content."""
    llm_input = packet.get("llm_input", packet)

    canonical_by_key: dict[str, set[str]] = {}

    root = llm_input.get("root")
    if isinstance(root, dict):
        _register_canonical(canonical_by_key, root.get("arabic"))

    leaves = llm_input.get("leaves")
    if isinstance(leaves, list):
        for leaf in leaves:
            if not isinstance(leaf, dict):
                continue
            _register_canonical(canonical_by_key, leaf.get("arabic"))
            pattern = leaf.get("pattern")
            if isinstance(pattern, dict):
                _register_canonical(canonical_by_key, pattern.get("arabic"))

    return canonical_by_key


def _kb_forms(canonical_by_key: dict[str, set[str]]) -> set[str]:
    return {form for forms in canonical_by_key.values() for form in forms}


def _canonicalize_quiz_arabic(
    output: Any,
    canonical_by_key: dict[str, set[str]],
) -> None:
    """
    Rewrite Arabic in the quiz to the KB's exact vocalized form, in place.

    The grounding check is tashkeel- and spacing-insensitive (§1.4), so K2 may
    pass validation with فاعِل where the KB has فَاعِل, or در س for the root
    د ر س. The learner must see the curated form, never the model's near-miss —
    the KB stays the only source of Arabic spelling on screen. Choice texts are
    replaced whole; prose fields have each Arabic run replaced individually.
    """
    if not isinstance(output, dict) or not isinstance(output.get("quiz"), list):
        return

    for question in output["quiz"]:
        if not isinstance(question, dict):
            continue

        for field_name in ("question", "correct_feedback", "wrong_feedback", "explanation"):
            question[field_name] = _canonicalize_prose(
                question.get(field_name), canonical_by_key
            )

        choice_feedback = question.get("choice_feedback")
        if isinstance(choice_feedback, dict):
            for choice_id, feedback in choice_feedback.items():
                choice_feedback[choice_id] = _canonicalize_prose(
                    feedback, canonical_by_key
                )

        choices = question.get("choices")
        if not isinstance(choices, list):
            continue
        for choice in choices:
            if not isinstance(choice, dict):
                continue
            text = choice.get("text")
            if not isinstance(text, str):
                continue
            choice["text"] = _canonical_form(canonical_by_key, text)


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
