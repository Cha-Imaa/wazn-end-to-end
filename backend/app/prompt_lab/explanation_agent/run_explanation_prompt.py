from app.data_loader import kb
from app.prompt_lab.shared.evidence_builder import build_explanation_evidence
from app.prompt_lab.shared.k2_prompt_runner import run_prompt_lab_once
from app.prompt_lab.shared.validators.explanation_validator import validate_explanation_output


WORD = "تَعْلِيم"

AGENT_NAME = "explanation_agent"
PROMPT_VERSION = "v3_basic"

SYSTEM_PROMPT_PATH = "app/prompt_lab/explanation_agent/v3_basic/system.txt"
USER_PROMPT_PATH = "app/prompt_lab/explanation_agent/v3_basic/user.txt"
OUTPUT_DIR = "app/prompt_lab/explanation_agent/v3_basic/outputs"


def main() -> None:
    kb.load()

    evidence_packet = build_explanation_evidence(WORD)

    saved_path = run_prompt_lab_once(
        agent_name=AGENT_NAME,
        prompt_version=PROMPT_VERSION,
        word=WORD,
        system_prompt_path=SYSTEM_PROMPT_PATH,
        user_prompt_path=USER_PROMPT_PATH,
        output_dir=OUTPUT_DIR,
        evidence_packet=evidence_packet,
        validator=validate_explanation_output,
    )

    print(f"Saved prompt lab output to {saved_path}")


if __name__ == "__main__":
    main()