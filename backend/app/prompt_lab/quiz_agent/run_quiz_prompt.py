from app.data_loader import kb
from app.prompt_lab.shared.evidence_builder import build_quiz_evidence
from app.prompt_lab.shared.k2_prompt_runner import run_prompt_lab_once
from app.prompt_lab.shared.validators.quiz_validator import validate_quiz_output


WORD = "عَالِم"

AGENT_NAME = "quiz_agent"
PROMPT_VERSION = "v3_tree_quiz"

SYSTEM_PROMPT_PATH = "app/prompt_lab/quiz_agent/v3_tree_quiz/system.txt"
USER_PROMPT_PATH = "app/prompt_lab/quiz_agent/v3_tree_quiz/user.txt"
OUTPUT_DIR = "app/prompt_lab/quiz_agent/v3_tree_quiz/outputs"


def main() -> None:
    kb.load()

    evidence_packet = build_quiz_evidence(WORD)

    saved_path = run_prompt_lab_once(
        agent_name=AGENT_NAME,
        prompt_version=PROMPT_VERSION,
        word=WORD,
        system_prompt_path=SYSTEM_PROMPT_PATH,
        user_prompt_path=USER_PROMPT_PATH,
        output_dir=OUTPUT_DIR,
        evidence_packet=evidence_packet,
        validator=validate_quiz_output,
    )

    print(f"Saved prompt lab output to {saved_path}")


if __name__ == "__main__":
    main()