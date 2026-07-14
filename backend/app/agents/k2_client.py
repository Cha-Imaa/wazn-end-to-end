import json
import urllib.error
import urllib.request
from typing import Any

from app.core.config import Settings, get_settings


class K2ClientError(Exception):
    """Raised when the K2 client cannot complete a request safely."""


def call_k2_json(
    system_prompt: str,
    user_prompt: str,
    settings: Settings | None = None,
) -> dict[str, Any]:
    active_settings = settings or get_settings()

    if not active_settings.k2_api_key:
        raise K2ClientError("K2_API_KEY is not configured.")

    payload = {
        "model": active_settings.k2_model,
        "messages": [
            {
                "role": "system",
                "content": system_prompt,
            },
            {
                "role": "user",
                "content": user_prompt,
            },
        ],
        "temperature": 0.2,
        "stream": False,
    }

    request = urllib.request.Request(
        url=active_settings.k2_base_url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "accept": "application/json",
            "Authorization": f"Bearer {active_settings.k2_api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(
            request,
            timeout=active_settings.k2_timeout_seconds,
        ) as response:
            response_body = response.read().decode("utf-8")
    except urllib.error.HTTPError as error:
        error_body = error.read().decode("utf-8", errors="replace")
        raise K2ClientError(
            f"K2 HTTP error {error.code}: {error_body}"
        ) from error
    except urllib.error.URLError as error:
        raise K2ClientError(f"K2 network error: {error}") from error
    except TimeoutError as error:
        raise K2ClientError("K2 request timed out.") from error

    try:
        raw_response = json.loads(response_body)
    except json.JSONDecodeError as error:
        raise K2ClientError("K2 returned invalid JSON response.") from error

    raw_content = extract_message_content(raw_response)

    separated_content = split_k2_reasoning_and_answer(raw_content)

    try:
        parsed_output = parse_json_object_from_answer(
            separated_content["answer_content"]
        )
    except K2ClientError:
        raise
    except Exception as error:
        raise K2ClientError(
            "K2 answer content could not be parsed as a JSON object."
        ) from error

    return {
        "raw_response": raw_response,
        "raw_content": raw_content,
        "reasoning": separated_content["reasoning"],
        "answer_content": separated_content["answer_content"],
        "parsed_output": parsed_output,
    }


def extract_message_content(raw_response: dict[str, Any]) -> str:
    choices = raw_response.get("choices")

    if not isinstance(choices, list) or not choices:
        raise K2ClientError("K2 response does not include choices.")

    first_choice = choices[0]

    if not isinstance(first_choice, dict):
        raise K2ClientError("K2 response choice is invalid.")

    message = first_choice.get("message")

    if not isinstance(message, dict):
        raise K2ClientError("K2 response does not include a message.")

    content = message.get("content")

    if not isinstance(content, str) or not content.strip():
        raise K2ClientError("K2 response message content is empty.")

    return content


def split_k2_reasoning_and_answer(raw_content: str) -> dict[str, str | None]:
    """
    K2 always returns reasoning between <think> and </think>, then the final answer.

    Example:
        <think>
        reasoning here
        </think>
        {"explanation": "..."}

    For the prompt lab, we preserve reasoning because it helps prompt debugging.
    For JSON parsing, we parse only the answer after </think>.
    """
    opening_tag = "<think>"
    closing_tag = "</think>"

    start_index = raw_content.find(opening_tag)
    end_index = raw_content.find(closing_tag)

    if start_index == -1 or end_index == -1 or end_index < start_index:
        return {
            "reasoning": None,
            "answer_content": raw_content.strip(),
        }

    reasoning_start = start_index + len(opening_tag)
    reasoning = raw_content[reasoning_start:end_index].strip()

    answer_start = end_index + len(closing_tag)
    answer_content = raw_content[answer_start:].strip()

    return {
        "reasoning": reasoning,
        "answer_content": answer_content,
    }


def parse_json_object_from_answer(answer_content: str) -> dict[str, Any]:
    """
    Parse the final answer content as a JSON object.

    This function is intentionally strict after the reasoning block has been
    removed. The lab should reveal prompt failures clearly.
    """
    cleaned_answer = strip_markdown_json_fence(answer_content).strip()

    try:
        parsed = json.loads(cleaned_answer)
    except json.JSONDecodeError as error:
        preview = cleaned_answer[:300].replace("\n", " ")
        raise K2ClientError(
            "K2 answer content was not valid JSON after the reasoning block. "
            f"Preview: {preview}"
        ) from error

    if not isinstance(parsed, dict):
        raise K2ClientError("K2 JSON output must be an object.")

    return parsed


def strip_markdown_json_fence(content: str) -> str:
    """
    Remove a single surrounding Markdown code fence, if K2 adds one.

    The prompt should ask K2 not to use Markdown, but this keeps the lab usable
    while experimenting.
    """
    text = content.strip()

    if not text.startswith("```"):
        return text

    lines = text.splitlines()

    if lines and lines[0].strip().startswith("```"):
        lines = lines[1:]

    if lines and lines[-1].strip() == "```":
        lines = lines[:-1]

    return "\n".join(lines).strip()