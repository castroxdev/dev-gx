from __future__ import annotations

from collections import deque
from copy import deepcopy
from datetime import UTC, datetime
from threading import Lock
from typing import Any


class TraceStore:
    def __init__(self, max_traces: int = 200) -> None:
        self.max_traces = max_traces
        self._traces: deque[str] = deque()
        self._items: dict[str, dict[str, Any]] = {}
        self._lock = Lock()

    def start_trace(
        self,
        *,
        request_id: str,
        endpoint: str,
        conversation_id: str | None,
        model: str | None,
    ) -> None:
        trace = {
            "request_id": request_id,
            "endpoint": endpoint,
            "conversation_id": conversation_id or "none",
            "model": model or "none",
            "status": "running",
            "started_at": self._now_iso(),
            "finished_at": None,
            "total_duration_ms": None,
            "steps": [],
        }

        with self._lock:
            if request_id not in self._items:
                self._traces.append(request_id)
            self._items[request_id] = trace
            self._trim_if_needed()

    def add_step(
        self,
        request_id: str,
        *,
        stage: str,
        status: str,
        duration_ms: float | None = None,
        **data: Any,
    ) -> None:
        with self._lock:
            trace = self._items.get(request_id)
            if trace is None:
                return

            step = {
                "stage": stage,
                "status": status,
                "timestamp": self._now_iso(),
            }

            if duration_ms is not None:
                step["duration_ms"] = round(duration_ms, 2)

            for key, value in data.items():
                if value is not None:
                    step[key] = value

            trace["steps"].append(step)

    def finish_trace(
        self,
        request_id: str,
        *,
        status: str,
        total_duration_ms: float | None = None,
    ) -> None:
        with self._lock:
            trace = self._items.get(request_id)
            if trace is None:
                return

            trace["status"] = status
            trace["finished_at"] = self._now_iso()
            if total_duration_ms is not None:
                trace["total_duration_ms"] = round(total_duration_ms, 2)

    def get_trace(self, request_id: str) -> dict[str, Any] | None:
        with self._lock:
            trace = self._items.get(request_id)
            if trace is None:
                return None
            return deepcopy(trace)

    def list_traces(self, limit: int = 20) -> list[dict[str, Any]]:
        safe_limit = max(1, min(limit, self.max_traces))

        with self._lock:
            request_ids = list(self._traces)[-safe_limit:]
            request_ids.reverse()
            return [
                deepcopy(self._items[request_id])
                for request_id in request_ids
                if request_id in self._items
            ]

    def _trim_if_needed(self) -> None:
        while len(self._traces) > self.max_traces:
            oldest_request_id = self._traces.popleft()
            self._items.pop(oldest_request_id, None)

    def _now_iso(self) -> str:
        return datetime.now(UTC).isoformat()


trace_store = TraceStore()
