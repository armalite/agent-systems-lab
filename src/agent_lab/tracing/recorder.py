"""JSONL trace writing and reading.

One event per line, append-only, in emission order. `sequence` is monotonic per run, so
ordering survives any downstream tooling that does not preserve file order.
"""

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from agent_lab.tracing.events import TraceEvent


class TraceRecorder:
    """Writes one run's ordered events to a JSONL file."""

    def __init__(self, path: Path, context: dict[str, Any]) -> None:
        self._path = path
        self._context = context
        self._sequence = 0
        self._events: list[TraceEvent] = []
        path.parent.mkdir(parents=True, exist_ok=True)
        self._handle = path.open("w", encoding="utf-8")

    @property
    def path(self) -> Path:
        return self._path

    @property
    def events(self) -> tuple[TraceEvent, ...]:
        return tuple(self._events)

    def emit(
        self, event_type: str, layer: str, payload: dict[str, Any] | None = None
    ) -> TraceEvent:
        event = TraceEvent(
            sequence=self._sequence,
            timestamp=datetime.now(UTC).isoformat(),
            layer=layer,  # pyright: ignore[reportArgumentType]
            event_type=event_type,
            payload=payload or {},
            **self._context,
        )
        self._sequence += 1
        self._events.append(event)
        self._handle.write(json.dumps(event.model_dump(mode="json"), ensure_ascii=False) + "\n")
        self._handle.flush()
        return event

    def close(self) -> None:
        self._handle.close()

    def __enter__(self) -> "TraceRecorder":
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()


def read_trace(path: Path) -> tuple[TraceEvent, ...]:
    """Read a persisted trace back, ordered by sequence."""
    events = [
        TraceEvent.model_validate_json(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    return tuple(sorted(events, key=lambda event: event.sequence))
