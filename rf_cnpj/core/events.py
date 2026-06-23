from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any

PipelineEvent = dict[str, Any]
EventEmitter = Callable[[PipelineEvent], None]


def format_bytes(value: int | None) -> str:
    if value is None:
        return "? MB"
    return f"{value / (1024 * 1024):.1f} MB"


def build_event(
    event_type: str,
    message: str,
    *,
    level: str = "info",
    data: dict[str, Any] | None = None,
) -> PipelineEvent:
    return {
        "type": event_type,
        "level": level,
        "message": message,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "data": data or {},
    }


def emit_event(
    emit: EventEmitter | None,
    event_type: str,
    message: str,
    *,
    level: str = "info",
    data: dict[str, Any] | None = None,
) -> None:
    if emit is not None:
        emit(build_event(event_type, message, level=level, data=data))
