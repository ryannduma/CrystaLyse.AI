"""
JSONL Event Logger for structured provenance capture
"""

import json
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass
class Event:
    """Represents a single provenance event."""

    type: str
    ts: str
    data: dict[str, Any]

    def to_jsonl(self) -> str:
        """Convert to JSONL string."""
        return json.dumps(asdict(self))


class JSONLLogger:
    """
    Logger that writes events to JSONL files.
    Each line is a complete JSON object for streaming processing.
    """

    def __init__(self, path: Path) -> None:
        """
        Initialize logger with output path.

        Args:
            path: Path to JSONL file
        """
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._file = None
        self._event_count = 0

    def log(self, event_type: str, data: dict[str, Any]) -> None:
        """
        Log an event to the JSONL file.

        Args:
            event_type: Type of event (e.g., "tool_start", "material_found")
            data: Event data dictionary
        """
        event = Event(type=event_type, ts=datetime.utcnow().isoformat(), data=data)

        # Write immediately for real-time tracking
        with self.path.open("a", encoding="utf-8") as f:
            f.write(event.to_jsonl() + "\n")

        self._event_count += 1

    def log_session_start(self, session_id: str, metadata: dict | None = None) -> None:
        """Log session start with metadata."""
        data = {"session_id": session_id, "timestamp": datetime.now().isoformat(), "event_count": 0}
        if metadata:
            data.update(metadata)
        self.log("session_start", data)

    def log_session_end(self, session_id: str, summary: dict[str, Any]) -> None:
        """Log session end with summary."""
        data = {
            "session_id": session_id,
            "timestamp": datetime.now().isoformat(),
            "event_count": self._event_count,
            **summary,
        }
        self.log("session_end", data)

    def log_tool_start(self, tool_name: str, call_id: str, args: dict | None = None) -> None:
        """Log tool call start."""
        self.log(
            "tool_start",
            {
                "tool": tool_name,
                "call_id": call_id,
                "args": args or {},
                "timestamp": datetime.now().isoformat(),
            },
        )

    def log_tool_end(
        self,
        tool_name: str,
        call_id: str,
        duration_ms: float,
        success: bool = True,
        output_summary: str | None = None,
    ) -> None:
        """Log tool call end."""
        self.log(
            "tool_end",
            {
                "tool": tool_name,
                "call_id": call_id,
                "duration_ms": duration_ms,
                "success": success,
                "output_summary": output_summary,
                "timestamp": datetime.now().isoformat(),
            },
        )

    def log_material(self, material: dict[str, Any]) -> None:
        """Log a discovered material."""
        self.log("material", {**material, "timestamp": datetime.now().isoformat()})

    def get_event_count(self) -> int:
        """Get total number of events logged."""
        return self._event_count

    def read_events(self) -> list:
        """Read all events from the file."""
        if not self.path.exists():
            return []

        events = []
        with self.path.open("r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    events.append(json.loads(line))
        return events
