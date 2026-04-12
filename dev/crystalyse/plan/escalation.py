"""Auto-mode escalation: ``escalate_mode`` tool and session budget state.

In auto mode the agent starts at explore-level budgets (3 polymorphs,
chemistry_creative) and can call ``escalate_mode(reason)`` to raise to
validate-level budgets (30 polymorphs, chemistry_unified) mid-run.

The tool mutates ``SessionState`` in place and records an
``EscalationEvent`` to provenance JSONL so the PR 3 ablation can compute
"escalation rate" as a metric.

Design: Option B from spec §7 — the agent calls a tool from its own
reasoning, not a per-tool-call structured-output check.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

# ---------------------------------------------------------------------------
# Budget constants (spec §2.7)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ModeBudget:
    """Hard-enforced budget limits for a given mode level."""

    polymorph_count: int
    tool_scope: Literal["chemistry_creative", "chemistry_unified"]


EXPLORE_BUDGET = ModeBudget(polymorph_count=3, tool_scope="chemistry_creative")
"""Default budget for explore mode and auto mode's initial phase."""

ESCALATED_BUDGET = ModeBudget(polymorph_count=30, tool_scope="chemistry_unified")
"""Budget after escalation — matches validate mode's full sweep."""


# ---------------------------------------------------------------------------
# Escalation event
# ---------------------------------------------------------------------------


@dataclass
class EscalationEvent:
    """A single escalation decision recorded to provenance."""

    timestamp: str
    reason: str
    from_mode: str = "auto"
    to_mode: str = "validate"


# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------


@dataclass
class SessionState:
    """Per-session mutable state tracking current budget and escalation history.

    MCP tool wrappers (Python-side) read ``budget.polymorph_count`` to cap
    ``structures_per_composition``.  When ``escalate_mode`` fires, the cap
    rises for subsequent calls.
    """

    budget: ModeBudget = field(
        default_factory=lambda: ModeBudget(
            polymorph_count=EXPLORE_BUDGET.polymorph_count,
            tool_scope=EXPLORE_BUDGET.tool_scope,
        )
    )
    escalation_events: list[EscalationEvent] = field(default_factory=list)

    @property
    def escalation_count(self) -> int:
        return len(self.escalation_events)

    @property
    def has_escalated(self) -> bool:
        return self.escalation_count > 0


# ---------------------------------------------------------------------------
# Provenance recording
# ---------------------------------------------------------------------------


def record_escalation_to_jsonl(
    event: EscalationEvent,
    output_path: Path,
) -> None:
    """Append an escalation event to a JSONL file.

    Uses the same format as ``provenance.core.event_logger`` for
    consistency, but writes to a dedicated escalation log so the PR 3
    ablation can compute escalation rate without parsing the full event
    stream.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "type": "escalation",
        "ts": event.timestamp,
        "data": {
            "reason": event.reason,
            "from_mode": event.from_mode,
            "to_mode": event.to_mode,
        },
    }
    with output_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")


def read_escalation_events(path: Path) -> list[dict[str, Any]]:
    """Read escalation events from a JSONL file.  Returns a list of dicts."""
    if not path.exists():
        return []
    events = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                events.append(json.loads(line))
    return events


# ---------------------------------------------------------------------------
# Tool factory
# ---------------------------------------------------------------------------


def make_escalate_mode_tool(
    session_state: SessionState,
    escalation_log_path: Path | None = None,
):
    """Factory returning an ``escalate_mode`` @function_tool bound to session state.

    Parameters
    ----------
    session_state:
        Mutable session state.  Budget is updated in place on escalation.
    escalation_log_path:
        Optional path to a JSONL file for provenance recording.  If None,
        events are only recorded in ``session_state.escalation_events``.
    """
    from agents import function_tool

    @function_tool
    def escalate_mode(reason: str) -> dict[str, Any]:
        """Escalate from explore-level to validate-level budgets.

        Call this when tool results indicate the query needs more thorough
        investigation than the current explore-level sampling can provide.

        Criteria for calling:
        - First polymorph batch returned all unstable (E_hull > 100 meV/atom)
        - SMACT screening returned fewer valid compositions than needed
        - User asked for N candidates and you have <N after explore sweep
        - Any other measurable signal that exploration is insufficient

        Returns the new budget state.

        :param reason: A short description of why escalation is needed.
        :return: New budget parameters after escalation.
        """
        # Update budget
        session_state.budget = ESCALATED_BUDGET

        # Record event
        event = EscalationEvent(
            timestamp=datetime.now(tz=UTC).isoformat(),
            reason=reason,
        )
        session_state.escalation_events.append(event)

        # Write to provenance JSONL if path is configured
        if escalation_log_path is not None:
            record_escalation_to_jsonl(event, escalation_log_path)

        return {
            "status": "escalated",
            "polymorph_count": ESCALATED_BUDGET.polymorph_count,
            "tool_scope": ESCALATED_BUDGET.tool_scope,
            "reason": reason,
        }

    return escalate_mode
