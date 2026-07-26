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

    message = extract_message(raw_response)
    raw_content = extract_content_from_message(message)

    separated_content = split_k2_reasoning_and_answer(
        raw_content,
        reasoning_field=message.get("reasoning"),
    )

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
        "reasoning_tokens": extract_reasoning_tokens(raw_response),
        "answer_content": separated_content["answer_content"],
        "parsed_output": parsed_output,
    }


def extract_message(raw_response: dict[str, Any]) -> dict[str, Any]:
    choices = raw_response.get("choices")

    if not isinstance(choices, list) or not choices:
        raise K2ClientError("K2 response does not include choices.")

    first_choice = choices[0]

    if not isinstance(first_choice, dict):
        raise K2ClientError("K2 response choice is invalid.")

    message = first_choice.get("message")

    if not isinstance(message, dict):
        raise K2ClientError("K2 response does not include a message.")

    return message


def extract_content_from_message(message: dict[str, Any]) -> str:
    content = message.get("content")

    if not isinstance(content, str) or not content.strip():
        raise K2ClientError("K2 response message content is empty.")

    return content


def extract_message_content(raw_response: dict[str, Any]) -> str:
    return extract_content_from_message(extract_message(raw_response))


def extract_reasoning_tokens(raw_response: dict[str, Any]) -> int | None:
    """
    Read the reasoning-token count, if the endpoint reports one.

    Present as `usage.completion_tokens_details.reasoning_tokens` on
    api.k2think.ai. Absent on hosts that don't break usage down, so this is
    always optional — never treat a None as an error.
    """
    usage = raw_response.get("usage")

    if not isinstance(usage, dict):
        return None

    details = usage.get("completion_tokens_details")

    if not isinstance(details, dict):
        return None

    reasoning_tokens = details.get("reasoning_tokens")

    if not isinstance(reasoning_tokens, int):
        return None

    return reasoning_tokens


def split_k2_reasoning_and_answer(
    raw_content: str,
    reasoning_field: str | None = None,
) -> dict[str, str | None]:
    """
    Separate K2's reasoning trace from its final answer.

    K2 Think generates reasoning inside <think> / </think>, but it does not
    always arrive that way — it depends on whether the host strips the tags
    before responding. This endpoint has served both shapes:

    1. A dedicated `message.reasoning` field, tags already stripped by the
       server. This is what api.k2think.ai returns for K2-Think-v2 as of
       2026-07-26: `content` is the bare answer. Pass the field in as
       `reasoning_field`.
    2. Inline in `content`, delimited by the tags. Saved prompt-lab runs from
       2026-07-03 have this shape, so the endpoint changed under us; raw model
       hosts still return it. The opening tag is sometimes missing, leaving
       reasoning followed by a lone </think>.

    `reasoning_field` wins when it holds text; tag-splitting is the fallback,
    so a change in either direction keeps working. Either way the answer is the
    content with any reasoning block removed, which is what gets parsed as JSON.

    Returns `reasoning: None` only when neither shape carried a trace.
    """
    opening_tag = "<think>"
    closing_tag = "</think>"

    end_index = raw_content.find(closing_tag)

    if end_index == -1:
        inline_reasoning = None
        answer_content = raw_content.strip()
    else:
        before_tag = raw_content[:end_index].lstrip()

        if before_tag.startswith(opening_tag):
            before_tag = before_tag[len(opening_tag):]

        inline_reasoning = before_tag.strip() or None
        answer_content = raw_content[end_index + len(closing_tag):].strip()

    reasoning = None

    if isinstance(reasoning_field, str) and reasoning_field.strip():
        reasoning = reasoning_field.strip()
    elif inline_reasoning:
        reasoning = inline_reasoning

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