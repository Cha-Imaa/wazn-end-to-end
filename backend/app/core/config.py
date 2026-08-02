import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env", override=True)

def _get_bool_env(name: str, default: bool = False) -> bool:
    value = os.getenv(name)

    if value is None:
        return default

    return value.strip().lower() in {"1", "true", "yes", "on"}


def _get_int_env(name: str, default: int) -> int:
    value = os.getenv(name)

    if value is None:
        return default

    try:
        return int(value)
    except ValueError:
        return default


@dataclass(frozen=True)
class Settings:
    enable_k2_explanation: bool
    enable_k2_tutor: bool
    enable_k2_guardrail_review: bool
    enable_k2_evaluation: bool

    # The quiz agent was labelled `engine: "k2"` while running deterministic
    # templates, so it had no flag of its own. It has one now.
    enable_k2_quiz: bool

    # The "In a sentence" section on the Details tab. Generated, never
    # hand-written (see NEXT_STEPS "Decisions taken"): off means the section
    # is simply absent — there is no deterministic fallback sentence.
    enable_k2_sentence: bool

    # Pre-warm the insights cache at startup for the demo words. Off by default:
    # it fires four sequential K2 calls per word before the app serves traffic.
    enable_k2_insights_prewarm: bool

    # When true (default), the K2 Think transparency tab is fed mockup-faithful
    # sample values for the LLM-dependent parts (explanation / guardrail /
    # evaluation) that are not yet on the request path. When false, those parts
    # are reported as "skipped" and no sample scores are emitted.
    enable_k2_think_demo: bool

    k2_api_key: str | None
    k2_base_url: str
    k2_model: str

    # Prompt-lab timeout. Generous on purpose — an offline experiment can wait.
    k2_timeout_seconds: int

    # Per-call ceiling for /api/insights, bounding four sequential agents.
    #
    # NEXT_STEPS.md §1.1 proposed ~12s. Measured against the live endpoint, that
    # would make the feature useless: the guardrail agent alone spends 17-18k
    # reasoning tokens and the evaluation agent 7-8k, so both take ~10-25s and
    # would fall back every time. Observed worst case is ~25s per call, with all
    # four completing in 31-43s total — consistent with the "up to ~2 min"
    # sequential budget the same document assumes elsewhere.
    k2_insights_timeout_seconds: int

    # Completion cap (reasoning + answer) for /api/insights calls. The server's
    # own default proved too small for the quiz agent: it spent the whole budget
    # reasoning and returned empty content on some words (§1.3). 32k clears the
    # heaviest observed reasoning (guardrail, 17-20k tokens) plus a full quiz
    # JSON with room to spare. 0 or negative disables the field entirely.
    k2_max_completion_tokens: int


def get_settings() -> Settings:
    return Settings(
        enable_k2_explanation=_get_bool_env(
            "ENABLE_K2_EXPLANATION",
            default=False,
        ),
        enable_k2_tutor=_get_bool_env(
            "ENABLE_K2_TUTOR",
            default=False,
        ),
        enable_k2_guardrail_review=_get_bool_env(
            "ENABLE_K2_GUARDRAIL_REVIEW",
            default=False,
        ),
        enable_k2_evaluation=_get_bool_env(
            "ENABLE_K2_EVALUATION",
            default=False,
        ),
        enable_k2_quiz=_get_bool_env(
            "ENABLE_K2_QUIZ",
            default=False,
        ),
        enable_k2_sentence=_get_bool_env(
            "ENABLE_K2_SENTENCE",
            default=False,
        ),
        enable_k2_insights_prewarm=_get_bool_env(
            "ENABLE_K2_INSIGHTS_PREWARM",
            default=False,
        ),
        enable_k2_think_demo=_get_bool_env(
            "ENABLE_K2_THINK_DEMO",
            default=True,
        ),
        k2_api_key=os.getenv("K2_API_KEY"),
        k2_base_url=os.getenv(
            "K2_BASE_URL",
            "https://api.k2think.ai/v1/chat/completions",
        ),
        k2_model=os.getenv(
            "K2_MODEL",
            "MBZUAI-IFM/K2-Think-v2",
        ),
        k2_timeout_seconds=_get_int_env(
            "K2_TIMEOUT_SECONDS",
            default=30,
        ),
        k2_insights_timeout_seconds=_get_int_env(
            "K2_INSIGHTS_TIMEOUT_SECONDS",
            default=45,
        ),
        k2_max_completion_tokens=_get_int_env(
            "K2_MAX_COMPLETION_TOKENS",
            default=32000,
        ),
    )