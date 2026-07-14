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

    k2_api_key: str | None
    k2_base_url: str
    k2_model: str
    k2_timeout_seconds: int


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
    )