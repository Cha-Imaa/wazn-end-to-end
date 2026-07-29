import json
from pathlib import Path
from typing import Any

from app.data_loader import kb
from app.prompt_lab.shared.evidence_builder import (
    build_combined_evaluation_input,
    build_explanation_evidence,
    build_quiz_evidence,
)
from app.prompt_lab.shared.k2_prompt_runner import (
    call_k2,
    parse_json_answer,
    run_prompt_lab_once,
    split_k2_think_output,
)
from app.prompt_lab.shared.validators.evaluation_validator import (
    validate_evaluation_output,
)


WORD = "تَعْلِيم"

# The versions the request path serves (k2_agents_service.AGENT_SPECS). The lab
# must run the same ones, or a revision is judged against output the app no
# longer produces: this runner pointed at explanation v3_basic, quiz
# v2_tree_quiz, and evaluation v1_rubric — whose user.txt has no {llm_input}
# placeholder, so every run scored a literal "<...>" skeleton (§1.1).
EXPLANATION_SYSTEM_PROMPT_PATH = (
    "app/prompt_lab/explanation_agent/v4_grounded_pattern/system.txt"
)
EXPLANATION_USER_PROMPT_PATH = (
    "app/prompt_lab/explanation_agent/v4_grounded_pattern/user.txt"
)

QUIZ_SYSTEM_PROMPT_PATH = "app/prompt_lab/quiz_agent/v3_tree_quiz/system.txt"
QUIZ_USER_PROMPT_PATH = "app/prompt_lab/quiz_agent/v3_tree_quiz/user.txt"

EVALUATION_AGENT_NAME = "evaluation_agent"
EVALUATION_PROMPT_VERSION = "v2_scoring"
EVALUATION_SYSTEM_PROMPT_PATH = "app/prompt_lab/evaluation_agent/v2_scoring/system.txt"
EVALUATION_USER_PROMPT_PATH = "app/prompt_lab/evaluation_agent/v2_scoring/user.txt"
EVALUATION_OUTPUT_DIR = "app/prompt_lab/evaluation_agent/v2_scoring/outputs"


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

    evaluation_input = build_combined_evaluation_input(
        word=WORD,
        tutor_output=tutor_output,
        quiz_output=quiz_output,
    )

    evidence_packet = {
        "agent": "evaluation_agent",
        # v2 carries the selected word's pattern and states each same-pattern
        # card's shared pattern, so `same_pattern_explanation`'s central claim
        # is checkable rather than a deduction (§1.3).
        "prompt_lab_packet_version": "evaluation_v2_scoring_carded_pattern",
        "llm_input": evaluation_input,
        "review_context": {
            "word": WORD,
            "tutor_output_was_json": isinstance(tutor_output, dict),
            "quiz_output_was_json": isinstance(quiz_output, dict),
            "note": "Evaluation scores quality only and must not gatekeep output.",
        },
    }

    saved_path = run_prompt_lab_once(
        agent_name=EVALUATION_AGENT_NAME,
        prompt_version=EVALUATION_PROMPT_VERSION,
        word=WORD,
        system_prompt_path=EVALUATION_SYSTEM_PROMPT_PATH,
        user_prompt_path=EVALUATION_USER_PROMPT_PATH,
        output_dir=EVALUATION_OUTPUT_DIR,
        evidence_packet=evidence_packet,
        validator=validate_evaluation_output,
    )

    print("Tutor output parsed:", isinstance(tutor_output, dict))
    print("Quiz output parsed:", isinstance(quiz_output, dict))
    print(f"Saved evaluation prompt lab output to {saved_path}")


def run_agent_json(
    word: str,
    system_prompt_path: str,
    user_prompt_path: str,
    evidence_packet: dict[str, Any],
) -> dict[str, Any] | None:
    system_prompt = Path(system_prompt_path).read_text(encoding="utf-8")
    user_template = Path(user_prompt_path).read_text(encoding="utf-8")

    llm_input = evidence_packet.get("llm_input", evidence_packet)

    input_json = json.dumps(
        llm_input,
        ensure_ascii=False,
        indent=2,
    )

    user_prompt = user_template.replace("{word}", word)
    user_prompt = user_prompt.replace("{evidence_packet}", input_json)
    user_prompt = user_prompt.replace("{llm_input}", input_json)

    raw_output = call_k2(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
    )

    parsed = split_k2_think_output(raw_output)
    answer = parsed["answer"]

    return parse_json_answer(answer)


if __name__ == "__main__":
    main()