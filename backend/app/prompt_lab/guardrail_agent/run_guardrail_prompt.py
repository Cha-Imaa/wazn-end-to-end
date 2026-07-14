import json
from pathlib import Path
from typing import Any

from app.data_loader import kb
from app.prompt_lab.shared.evidence_builder import (
    build_combined_guardrail_input,
    build_explanation_evidence,
    build_quiz_evidence,
)
from app.prompt_lab.shared.k2_prompt_runner import (
    call_k2,
    parse_json_answer,
    run_prompt_lab_once,
    split_k2_think_output,
)
from app.prompt_lab.shared.validators.guardrail_validator import (
    validate_guardrail_output,
)


WORD = "سَمِعَ"

EXPLANATION_SYSTEM_PROMPT_PATH = "app/prompt_lab/explanation_agent/v3_basic/system.txt"
EXPLANATION_USER_PROMPT_PATH = "app/prompt_lab/explanation_agent/v3_basic/user.txt"

QUIZ_SYSTEM_PROMPT_PATH = "app/prompt_lab/quiz_agent/v2_tree_quiz/system.txt"
QUIZ_USER_PROMPT_PATH = "app/prompt_lab/quiz_agent/v2_tree_quiz/user.txt"

GUARDRAIL_AGENT_NAME = "guardrail_agent"
GUARDRAIL_PROMPT_VERSION = "v3_combined"
GUARDRAIL_SYSTEM_PROMPT_PATH = "app/prompt_lab/guardrail_agent/v2_basic_review/system.txt"
GUARDRAIL_USER_PROMPT_PATH = "app/prompt_lab/guardrail_agent/v2_basic_review/user.txt"
GUARDRAIL_OUTPUT_DIR = "app/prompt_lab/guardrail_agent/v2_basic_review/outputs"


def main() -> None:
    kb.load()

    tutor_output = run_agent_json(
        word=WORD,
        system_prompt_path=EXPLANATION_SYSTEM_PROMPT_PATH,
        user_prompt_path=EXPLANATION_USER_PROMPT_PATH,
        evidence_packet=build_explanation_evidence(WORD),
    )

    quiz_output = run_agent_json(
        word=WORD,
        system_prompt_path=QUIZ_SYSTEM_PROMPT_PATH,
        user_prompt_path=QUIZ_USER_PROMPT_PATH,
        evidence_packet=build_quiz_evidence(WORD),
    )

    guardrail_input = build_combined_guardrail_input(
        word=WORD,
        tutor_output=tutor_output,
        quiz_output=quiz_output,
    )

    evidence_packet = {
        "agent": "guardrail_agent",
        "prompt_lab_packet_version": "guardrail_v3_combined",
        "llm_input": guardrail_input,
        "review_context": {
            "word": WORD,
            "tutor_output_was_json": isinstance(tutor_output, dict),
            "quiz_output_was_json": isinstance(quiz_output, dict),
        },
    }

    saved_path = run_prompt_lab_once(
        agent_name=GUARDRAIL_AGENT_NAME,
        prompt_version=GUARDRAIL_PROMPT_VERSION,
        word=WORD,
        system_prompt_path=GUARDRAIL_SYSTEM_PROMPT_PATH,
        user_prompt_path=GUARDRAIL_USER_PROMPT_PATH,
        output_dir=GUARDRAIL_OUTPUT_DIR,
        evidence_packet=evidence_packet,
        validator=validate_guardrail_output,
    )

    print("Tutor output parsed:", isinstance(tutor_output, dict))
    print("Quiz output parsed:", isinstance(quiz_output, dict))
    print(f"Saved guardrail prompt lab output to {saved_path}")


def run_agent_json(
    word: str,
    system_prompt_path: str,
    user_prompt_path: str,
    evidence_packet: dict[str, Any],
) -> dict[str, Any] | None:
    system_prompt = Path(system_prompt_path).read_text(encoding="utf-8")
    user_template = Path(user_prompt_path).read_text(encoding="utf-8")

    llm_input = evidence_packet.get("llm_input", evidence_packet)

    user_prompt = (
        user_template
        .replace("{word}", word)
        .replace(
            "{evidence_packet}",
            json.dumps(evidence_packet, ensure_ascii=False, indent=2),
        )
        .replace(
            "{llm_input}",
            json.dumps(llm_input, ensure_ascii=False, indent=2),
        )
    )

    raw_output = call_k2(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
    )

    _reasoning, answer = split_k2_think_output(raw_output)
    parsed_answer = parse_json_answer(answer)

    return parsed_answer


if __name__ == "__main__":
    main()