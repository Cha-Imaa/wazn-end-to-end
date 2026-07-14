import json
import os
import re
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any
import html
from dotenv import load_dotenv


load_dotenv()


K2_API_KEY = os.getenv("K2_API_KEY")
K2_BASE_URL = os.getenv(
    "K2_BASE_URL",
    "https://api.k2think.ai/v1/chat/completions",
)
K2_MODEL = os.getenv(
    "K2_MODEL",
    "MBZUAI-IFM/K2-Think-v2",
)
K2_TIMEOUT_SECONDS = int(os.getenv("K2_TIMEOUT_SECONDS", "30"))


def load_text_file(file_path: str) -> str:
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    if path.is_dir():
        raise IsADirectoryError(f"Expected a file but got a directory: {file_path}")

    return path.read_text(encoding="utf-8")


def render_user_prompt(
    user_prompt_template: str,
    word: str,
    evidence_packet: dict[str, Any],
) -> str:
    llm_input = evidence_packet.get("llm_input", evidence_packet)

    input_json = json.dumps(
        llm_input,
        ensure_ascii=False,
        indent=2,
    )

    rendered = user_prompt_template.replace("{word}", word)
    rendered = rendered.replace("{evidence_packet}", input_json)
    rendered = rendered.replace("{llm_input}", input_json)

    return rendered

def call_k2(
    system_prompt: str,
    user_prompt: str,
) -> str:
    if not K2_API_KEY:
        raise RuntimeError("K2_API_KEY is not set.")

    messages: list[dict[str, str]] = []

    if system_prompt.strip():
        messages.append(
            {
                "role": "system",
                "content": system_prompt,
            }
        )

    messages.append(
        {
            "role": "user",
            "content": user_prompt,
        }
    )

    payload = {
        "model": K2_MODEL,
        "messages": messages,
        "stream": False,
    }

    request = urllib.request.Request(
        url=K2_BASE_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {K2_API_KEY}",
            "Content-Type": "application/json",
            "accept": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=K2_TIMEOUT_SECONDS) as response:
            response_body = response.read().decode("utf-8")

    except urllib.error.HTTPError as error:
        error_body = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP ERROR {error.code}: {error_body}") from error

    except urllib.error.URLError as error:
        raise RuntimeError(f"NETWORK ERROR: {error}") from error

    response_json = json.loads(response_body)

    return response_json["choices"][0]["message"]["content"]


def split_k2_think_output(raw_output: str) -> dict[str, str]:
    """
    K2 Think may return:

    Case 1:
        <think>
        reasoning
        </think>
        answer

    Case 2:
        reasoning
        </think>
        answer

    Case 3:
        answer only

    This function separates reasoning and final answer.
    """
    closing_tag = "</think>"

    if closing_tag not in raw_output:
        return {
            "reasoning": "",
            "answer": raw_output.strip(),
        }

    before_tag, after_tag = raw_output.split(closing_tag, 1)

    reasoning = before_tag.replace("<think>", "").strip()
    answer = after_tag.strip()

    return {
        "reasoning": reasoning,
        "answer": answer,
    }


def parse_json_answer(answer: str) -> dict[str, Any] | None:
    """
    Tries to parse the final K2 answer as JSON.

    Returns:
        dict if valid JSON object
        None if parsing fails or output is not a JSON object
    """
    try:
        parsed = json.loads(answer)
    except json.JSONDecodeError:
        return None

    if not isinstance(parsed, dict):
        return None

    return parsed


def get_nested_value(data: dict[str, Any], path: list[str]) -> Any:
    current: Any = data

    for key in path:
        if not isinstance(current, dict):
            return None

        current = current.get(key)

    return current


def build_explanation_comparison_markdown(
    evidence_packet: dict[str, Any],
    parsed_answer: dict[str, Any] | None,
) -> str:
    review_context = evidence_packet.get("review_context", evidence_packet)

    deterministic = (
        review_context.get("current_explanation_fields")
        or evidence_packet.get("current_explanation_fields")
        or evidence_packet.get("current_deterministic_explanations")
        or evidence_packet.get("deterministic_explanations")
        or evidence_packet.get("selected_leaf")
        or {}
    )

    rows = [
        {
            "label": "Explanation",
            "deterministic_key": "explanation",
            "k2_key": "explanation",
        },
        {
            "label": "Pattern Explanation",
            "deterministic_key": "pattern_explanation",
            "k2_key": "pattern_explanation",
        },
        {
            "label": "Same-Pattern Explanation",
            "deterministic_key": "same_pattern_explanation",
            "k2_key": "same_pattern_explanation",
        },
    ]

    parts: list[str] = []

    for row in rows:
        label = row["label"]
        deterministic_key = row["deterministic_key"]
        k2_key = row["k2_key"]

        deterministic_value = deterministic.get(deterministic_key, "")
        k2_value = ""

        if parsed_answer:
            k2_value = parsed_answer.get(k2_key, "")

        if deterministic_value is None:
            deterministic_value = ""

        if k2_value is None:
            k2_value = ""

        parts.append(
            f"""### {label}

<table>
  <thead>
    <tr>
      <th style="width: 50%; text-align: left;">Deterministic fallback</th>
      <th style="width: 50%; text-align: left;">K2 generated</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td dir="ltr" style="text-align: left; vertical-align: top; line-height: 1.8; padding: 12px;">
        <p><span style="color: #999;">kk</span> {deterministic_value}</p>
      </td>
      <td dir="ltr" style="text-align: left; vertical-align: top; line-height: 1.8; padding: 12px;">
        <p><span style="color: #999;">kk</span> {k2_value}</p>
      </td>
    </tr>
  </tbody>
</table>
"""
        )

    return "\n---\n\n".join(parts)

def safe_filename_part(value: str) -> str:
    value = value.strip()
    value = re.sub(r"\s+", "_", value)
    value = re.sub(r"[^\w\u0600-\u06FF-]+", "", value)
    return value or "word"

def get_quiz_list_from_answer(parsed_answer: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not parsed_answer:
        return []

    quiz = parsed_answer.get("quiz", [])

    if not isinstance(quiz, list):
        return []

    return [
        item
        for item in quiz
        if isinstance(item, dict)
    ]


def format_quiz_question_for_markdown(question: dict[str, Any]) -> str:
    if not question:
        return ""

    question_text = question.get("question", "")
    question_type = question.get("type", question.get("category", ""))
    answer_id = question.get("answer_id", "")

    choices = question.get("choices", [])
    if not isinstance(choices, list):
        choices = []

    choice_lines: list[str] = []

    for choice in choices:
        if not isinstance(choice, dict):
            continue

        choice_id = choice.get("id", "")
        choice_text = choice.get("text", "")

        if not choice_text:
            choice_text = choice.get("label", "")

        choice_lines.append(f"<li><strong>{choice_id}</strong>: {choice_text}</li>")

    correct_feedback = question.get("correct_feedback", "")
    wrong_feedback = question.get("wrong_feedback", "")
    explanation = question.get("explanation", "")

    choice_feedback = question.get("choice_feedback", {})
    if not isinstance(choice_feedback, dict):
        choice_feedback = {}

    choice_feedback_lines: list[str] = []

    for choice_id in ["a", "b", "c", "d"]:
        feedback = choice_feedback.get(choice_id, "")
        choice_feedback_lines.append(
            f"<li><strong>{choice_id}</strong>: {feedback}</li>"
        )

    choices_html = "\n".join(choice_lines)
    choice_feedback_html = "\n".join(choice_feedback_lines)

    return f"""
<p><strong>Type:</strong> {question_type}</p>
<p><strong>Question:</strong> {question_text}</p>

<p><strong>Choices:</strong></p>
<ul>
{choices_html}
</ul>

<p><strong>Answer ID:</strong> {answer_id}</p>
<p><strong>Correct feedback:</strong> {correct_feedback}</p>
<p><strong>Wrong feedback:</strong> {wrong_feedback}</p>

<p><strong>Mistake-aware choice feedback:</strong></p>
<ul>
{choice_feedback_html}
</ul>

<p><strong>Explanation:</strong> {explanation}</p>
""".strip()


def build_quiz_comparison_markdown(
    evidence_packet: dict[str, Any],
    parsed_answer: dict[str, Any] | None,
) -> str:
    review_context = evidence_packet.get("review_context", evidence_packet)

    deterministic_quiz = (
        review_context.get("deterministic_quiz")
        or evidence_packet.get("deterministic_quiz")
        or evidence_packet.get("quiz")
        or []
    )

    if not isinstance(deterministic_quiz, list):
        deterministic_quiz = []

    k2_quiz = get_quiz_list_from_answer(parsed_answer)

    max_count = max(len(deterministic_quiz), len(k2_quiz), 5)

    parts: list[str] = []

    for index in range(max_count):
        deterministic_question = {}
        k2_question = {}

        if index < len(deterministic_quiz) and isinstance(deterministic_quiz[index], dict):
            deterministic_question = deterministic_quiz[index]

        if index < len(k2_quiz) and isinstance(k2_quiz[index], dict):
            k2_question = k2_quiz[index]

        deterministic_html = format_quiz_question_for_markdown(deterministic_question)
        k2_html = format_quiz_question_for_markdown(k2_question)

        deterministic_html = html.escape(deterministic_html, quote=False)
        k2_html = html.escape(k2_html, quote=False)

        # After escaping, restore the basic HTML tags we intentionally generated.
        for tag in [
            "p",
            "strong",
            "ul",
            "li",
        ]:
            deterministic_html = deterministic_html.replace(f"&lt;{tag}&gt;", f"<{tag}>")
            deterministic_html = deterministic_html.replace(f"&lt;/{tag}&gt;", f"</{tag}>")
            k2_html = k2_html.replace(f"&lt;{tag}&gt;", f"<{tag}>")
            k2_html = k2_html.replace(f"&lt;/{tag}&gt;", f"</{tag}>")

        parts.append(
            f"""### Question {index + 1}

<table>
  <thead>
    <tr>
      <th style="width: 50%; text-align: left;">Deterministic fallback</th>
      <th style="width: 50%; text-align: left;">K2 generated</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td dir="ltr" style="text-align: left; vertical-align: top; line-height: 1.8; padding: 12px;">
        <p><span style="color: #999;">kk</span></p>
        {deterministic_html}
      </td>
      <td dir="ltr" style="text-align: left; vertical-align: top; line-height: 1.8; padding: 12px;">
        <p><span style="color: #999;">kk</span></p>
        {k2_html}
      </td>
    </tr>
  </tbody>
</table>
"""
        )

    return "\n---\n\n".join(parts)

# def _format_validation_result(validation_result) -> str:
#     if validation_result is None:
#         return "Validation was not run."

#     status = "PASSED" if validation_result.passed else "FAILED"

#     lines = [
#         f"Status: {status}",
#         "",
#         "Violations:",
#     ]

#     if not validation_result.violations:
#         lines.append("- None")
#     else:
#         for violation in validation_result.violations:
#             lines.append(f"- {violation}")

#     return "\n".join(lines)

def _format_validation_result(validation_result) -> str:
    if validation_result is None:
        return "Validation was not run."

    if isinstance(validation_result, dict):
        passed = validation_result.get("passed", False)
        violations = validation_result.get("violations", [])
    else:
        passed = validation_result.passed
        violations = validation_result.violations

    status = "PASSED" if passed else "FAILED"

    lines = [
        f"Status: {status}",
        "",
        "Violations:",
    ]

    if not violations:
        lines.append("- None")
    else:
        for violation in violations:
            lines.append(f"- {violation}")

    return "\n".join(lines)

def build_comparison_markdown(
    agent_name: str,
    evidence_packet: dict[str, Any],
    parsed_answer: dict[str, Any] | None,
) -> tuple[str, str]:
    if agent_name == "quiz_agent":
        return (
            "Quiz Comparison",
            build_quiz_comparison_markdown(
                evidence_packet=evidence_packet,
                parsed_answer=parsed_answer,
            ),
        )

    if agent_name == "explanation_agent":
        return (
            "Explanation Comparison",
            build_explanation_comparison_markdown(
                evidence_packet=evidence_packet,
                parsed_answer=parsed_answer,
            ),
        )

    return (
        "Comparison",
        "No comparison view is configured for this agent.",
    )

def save_markdown_output(
    output_dir: str,
    agent_name: str,
    prompt_version: str,
    word: str,
    system_prompt_path: str,
    user_prompt_path: str,
    system_prompt: str,
    user_prompt: str,
    evidence_packet: dict[str, Any],
    raw_output: str,
    validation_result=None,
) -> str:
    parsed = split_k2_think_output(raw_output)

    parsed_answer_json = parse_json_answer(parsed["answer"])

    comparison_title, comparison_markdown = build_comparison_markdown(
        agent_name=agent_name,
        evidence_packet=evidence_packet,
        parsed_answer=parsed_answer_json,
    )

    validation_markdown = _format_validation_result(validation_result)

    llm_input = evidence_packet.get("llm_input", evidence_packet)

    llm_input_json = json.dumps(
        llm_input,
        ensure_ascii=False,
        indent=2,
    )

    full_prompt_lab_packet_json = json.dumps(
        evidence_packet,
        ensure_ascii=False,
        indent=2,
    )

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    safe_word = safe_filename_part(word)

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    markdown_path = output_path / f"{safe_word}_{timestamp}.md"

    markdown = f"""# WAZN Prompt Lab Run

<details open>
<summary><strong>Metadata</strong></summary>

- Agent: {agent_name}
- Prompt version: {prompt_version}
- Word: {word}
- Timestamp: {timestamp}
- System prompt path: `{system_prompt_path}`
- User prompt path: `{user_prompt_path}`
- Model: {K2_MODEL}

</details>

---

<details open>
<summary><strong>{comparison_title}</strong></summary>

{comparison_markdown}

</details>

---

<details open>
<summary><strong>Input Sent to K2</strong></summary>

```json
{llm_input_json}
```

</details>

---

<details>
<summary><strong>Full Prompt Lab Packet</strong></summary>

```json
{full_prompt_lab_packet_json}
```

</details>

---

<details>
<summary><strong>System Prompt</strong></summary>

```text
{system_prompt}
```

</details>

---

<details>
<summary><strong>User Prompt</strong></summary>

```text
{user_prompt}
```

</details>

---

<details open>
<summary><strong>Answer</strong></summary>

```text
{parsed["answer"]}
```

</details>

---

<details>
<summary><strong>Validation</strong></summary>

```text
{validation_markdown}
```

</details>

---

<details>
<summary><strong>Reasoning</strong></summary>

```text
{parsed["reasoning"]}
```

</details>

---

<details>
<summary><strong>Raw K2 Output</strong></summary>

```text
{raw_output}
```

</details>
"""

    markdown_path.write_text(markdown, encoding="utf-8")

    return str(markdown_path)

def run_prompt_lab_once(
    agent_name: str,
    prompt_version: str,
    word: str,
    system_prompt_path: str,
    user_prompt_path: str,
    output_dir: str,
    evidence_packet: dict[str, Any],
    validator=None,
) -> str:
    system_prompt = load_text_file(system_prompt_path)
    user_prompt_template = load_text_file(user_prompt_path)

    user_prompt = render_user_prompt(
        user_prompt_template=user_prompt_template,
        word=word,
        evidence_packet=evidence_packet,
    )

    raw_output = call_k2(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
    )

    parsed = split_k2_think_output(raw_output)
    answer = parsed["answer"]

    print("\n================ DEBUG: FINAL ANSWER SENT TO VALIDATOR ================")
    print(answer)
    print("================ END DEBUG: FINAL ANSWER SENT TO VALIDATOR ================\n")

    validation_result = None

    if validator is not None:
        validation_result = validator(evidence_packet, answer)

    saved_path = save_markdown_output(
        output_dir=output_dir,
        agent_name=agent_name,
        prompt_version=prompt_version,
        word=word,
        system_prompt_path=system_prompt_path,
        user_prompt_path=user_prompt_path,
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        evidence_packet=evidence_packet,
        raw_output=raw_output,
        validation_result=validation_result,
    )

    return saved_path
