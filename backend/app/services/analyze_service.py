from typing import Any

from app.pipeline.wazn_pipeline import run_wazn_pipeline


def analyze_word(query: str) -> dict[str, Any]:
    return run_wazn_pipeline(query)
