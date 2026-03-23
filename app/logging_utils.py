def format_log_event(
    *,
    request_id: str | None = None,
    endpoint: str | None = None,
    conversation_id: str | None = None,
    model: str | None = None,
    stage: str,
    duration_ms: float | None = None,
    status: str | None = None,
    **extra: str | int | float | None,
) -> str:
    parts: list[str] = [
        f"request_id={request_id or 'none'}",
        f"endpoint={endpoint or 'none'}",
        f"conversation_id={conversation_id or 'none'}",
        f"model={model or 'none'}",
        f"stage={stage}",
        f"duration_ms={duration_ms:.2f}" if duration_ms is not None else "duration_ms=none",
        f"status={status or 'none'}",
    ]

    for key, value in extra.items():
        if value is None:
            continue
        parts.append(f"{key}={value}")

    return " | ".join(parts)
