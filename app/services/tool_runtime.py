import json
import re
from typing import Any


TOOL_CALL_PATTERN = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL | re.IGNORECASE)


def extract_tool_call_response(raw_text: str) -> dict[str, Any] | None:
    text = raw_text.strip()
    if not text:
        return None

    fenced_match = TOOL_CALL_PATTERN.search(text)
    if fenced_match:
        text = fenced_match.group(1).strip()

    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return None

    if not isinstance(parsed, dict):
        return None

    if str(parsed.get("type", "")).strip().lower() != "tool_call":
        return None

    tool_name = str(parsed.get("tool", "")).strip()
    arguments = parsed.get("arguments", {})

    if not tool_name:
        return None
    if not isinstance(arguments, dict):
        return None

    return {
        "tool": tool_name,
        "arguments": arguments,
    }


def parse_tool_call_response(raw_text: str, allowed_tools: set[str]) -> dict[str, Any] | None:
    parsed = extract_tool_call_response(raw_text)
    if parsed is None:
        return None
    if parsed["tool"] not in allowed_tools:
        return None
    return parsed


def format_tool_result(tool_name: str, result: Any) -> str:
    if isinstance(result, str):
        result_payload = result
    else:
        result_payload = json.dumps(result, ensure_ascii=True)

    return (
        "TOOL_RESULT\n"
        f"tool: {tool_name}\n"
        f"result: {result_payload}\n\n"
        "Usa este resultado para continuar. "
        "Se ja tiveres informacao suficiente, responde ao utilizador de forma final e direta. "
        "Se ainda precisares de outra tool, devolve apenas um novo JSON de tool_call."
    )
