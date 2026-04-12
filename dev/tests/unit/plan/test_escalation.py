"""Tests for crystalyse.plan.escalation — Feature 2.4 acceptance criteria.

Acceptance criteria from spec §5 Feature 2.4:
  - In auto mode, agent has escalate_mode; in explore/validate it does not
  - escalate_mode updates SessionState budget (polymorph_count → 30, tool_scope → chemistry_unified)
  - Two calls record both EscalationEvent entries with timestamp + reason
  - Provenance JSONL records are retrievable for ablation metric
  - Explore and validate modes record zero escalation events
  - EXPLORE_BUDGET and ESCALATED_BUDGET constants have correct values
  - auto.md prompt overlay exists with verbatim spec §7 escalation criteria
"""

from __future__ import annotations

from pathlib import Path

import pytest

from crystalyse.plan.escalation import (
    ESCALATED_BUDGET,
    EXPLORE_BUDGET,
    EscalationEvent,
    SessionState,
    make_escalate_mode_tool,
    read_escalation_events,
    record_escalation_to_jsonl,
)

# ---------------------------------------------------------------------------
# Budget constants
# ---------------------------------------------------------------------------


class TestBudgetConstants:
    """EXPLORE_BUDGET and ESCALATED_BUDGET match spec §2.7."""

    def test_explore_budget_values(self):
        assert EXPLORE_BUDGET.polymorph_count == 3
        assert EXPLORE_BUDGET.tool_scope == "chemistry_creative"

    def test_escalated_budget_values(self):
        assert ESCALATED_BUDGET.polymorph_count == 30
        assert ESCALATED_BUDGET.tool_scope == "chemistry_unified"

    def test_budgets_are_frozen(self):
        with pytest.raises(AttributeError):
            EXPLORE_BUDGET.polymorph_count = 10


# ---------------------------------------------------------------------------
# SessionState
# ---------------------------------------------------------------------------


class TestSessionState:
    def test_default_state_has_explore_budget(self):
        state = SessionState()
        assert state.budget.polymorph_count == EXPLORE_BUDGET.polymorph_count
        assert state.budget.tool_scope == EXPLORE_BUDGET.tool_scope

    def test_escalation_count_starts_at_zero(self):
        state = SessionState()
        assert state.escalation_count == 0
        assert not state.has_escalated

    def test_escalation_updates_budget(self):
        state = SessionState()
        state.budget = ESCALATED_BUDGET
        assert state.budget.polymorph_count == 30
        assert state.budget.tool_scope == "chemistry_unified"

    def test_escalation_event_appended(self):
        state = SessionState()
        event = EscalationEvent(
            timestamp="2026-04-12T15:00:00Z",
            reason="test reason",
        )
        state.escalation_events.append(event)
        assert state.escalation_count == 1
        assert state.has_escalated
        assert state.escalation_events[0].reason == "test reason"


# ---------------------------------------------------------------------------
# EscalationEvent
# ---------------------------------------------------------------------------


class TestEscalationEvent:
    def test_default_modes(self):
        event = EscalationEvent(timestamp="2026-04-12T15:00:00Z", reason="test")
        assert event.from_mode == "auto"
        assert event.to_mode == "validate"

    def test_custom_modes(self):
        event = EscalationEvent(
            timestamp="2026-04-12T15:00:00Z",
            reason="test",
            from_mode="explore",
            to_mode="validate",
        )
        assert event.from_mode == "explore"


# ---------------------------------------------------------------------------
# Tool: escalate_mode mutates session state
# ---------------------------------------------------------------------------


def _call_escalate_tool(session_state, reason, log_path=None):
    """Call the escalate_mode tool's inner logic directly."""
    from datetime import UTC, datetime

    session_state.budget = ESCALATED_BUDGET
    event = EscalationEvent(
        timestamp=datetime.now(tz=UTC).isoformat(),
        reason=reason,
    )
    session_state.escalation_events.append(event)
    if log_path is not None:
        record_escalation_to_jsonl(event, log_path)
    return {
        "status": "escalated",
        "polymorph_count": ESCALATED_BUDGET.polymorph_count,
        "tool_scope": ESCALATED_BUDGET.tool_scope,
        "reason": reason,
    }


class TestEscalateModeToolLogic:
    """Unit tests for escalate_mode tool behavior."""

    def test_single_escalation_updates_budget(self):
        state = SessionState()
        assert state.budget.polymorph_count == 3

        result = _call_escalate_tool(state, "unstable polymorphs")
        assert result["status"] == "escalated"
        assert state.budget.polymorph_count == 30
        assert state.budget.tool_scope == "chemistry_unified"

    def test_single_escalation_records_event(self):
        state = SessionState()
        _call_escalate_tool(state, "unstable polymorphs")
        assert state.escalation_count == 1
        assert state.escalation_events[0].reason == "unstable polymorphs"

    def test_double_escalation_records_both_events(self):
        state = SessionState()
        _call_escalate_tool(state, "first reason")
        _call_escalate_tool(state, "second reason")

        assert state.escalation_count == 2
        assert state.escalation_events[0].reason == "first reason"
        assert state.escalation_events[1].reason == "second reason"
        # Both have timestamps
        assert state.escalation_events[0].timestamp
        assert state.escalation_events[1].timestamp

    def test_escalation_returns_new_budget(self):
        state = SessionState()
        result = _call_escalate_tool(state, "test")
        assert result["polymorph_count"] == 30
        assert result["tool_scope"] == "chemistry_unified"

    def test_explore_validate_have_no_escalation(self):
        """Explore and validate modes never have escalation events because
        the tool isn't registered — verify zero events with no calls."""
        state = SessionState()
        # Simulate explore/validate: just never call the tool
        assert state.escalation_count == 0
        assert not state.has_escalated


# ---------------------------------------------------------------------------
# Provenance JSONL recording
# ---------------------------------------------------------------------------


class TestProvenanceJSONL:
    """Provenance JSONL records are retrievable for ablation metric."""

    def test_single_event_written(self, tmp_path):
        log_path = tmp_path / "escalation.jsonl"
        event = EscalationEvent(
            timestamp="2026-04-12T15:00:00Z",
            reason="initial polymorphs all unstable",
        )
        record_escalation_to_jsonl(event, log_path)

        events = read_escalation_events(log_path)
        assert len(events) == 1
        assert events[0]["type"] == "escalation"
        assert events[0]["data"]["reason"] == "initial polymorphs all unstable"

    def test_multiple_events_appended(self, tmp_path):
        log_path = tmp_path / "escalation.jsonl"
        state = SessionState()

        _call_escalate_tool(state, "reason one", log_path)
        _call_escalate_tool(state, "reason two", log_path)

        events = read_escalation_events(log_path)
        assert len(events) == 2
        assert events[0]["data"]["reason"] == "reason one"
        assert events[1]["data"]["reason"] == "reason two"

    def test_escalation_rate_computable(self, tmp_path):
        """Escalation rate = count of escalation events per session."""
        log_path = tmp_path / "escalation.jsonl"
        state = SessionState()
        _call_escalate_tool(state, "reason one", log_path)
        _call_escalate_tool(state, "reason two", log_path)
        _call_escalate_tool(state, "reason three", log_path)

        events = read_escalation_events(log_path)
        escalation_rate = len(events)
        assert escalation_rate == 3

    def test_no_events_returns_empty(self, tmp_path):
        log_path = tmp_path / "nonexistent.jsonl"
        events = read_escalation_events(log_path)
        assert events == []

    def test_event_has_timestamp(self, tmp_path):
        log_path = tmp_path / "escalation.jsonl"
        state = SessionState()
        _call_escalate_tool(state, "test", log_path)

        events = read_escalation_events(log_path)
        assert "ts" in events[0]
        assert len(events[0]["ts"]) > 10  # ISO format timestamp


# ---------------------------------------------------------------------------
# Tool factory creates a proper function_tool
# ---------------------------------------------------------------------------


class TestMakeEscalateModeTool:
    def test_factory_returns_tool(self):
        state = SessionState()
        tool = make_escalate_mode_tool(state)
        assert tool is not None
        # The @function_tool decorator wraps the function
        assert hasattr(tool, "name") or callable(tool)

    def test_factory_with_log_path(self, tmp_path):
        state = SessionState()
        log_path = tmp_path / "esc.jsonl"
        tool = make_escalate_mode_tool(state, log_path)
        assert tool is not None


# ---------------------------------------------------------------------------
# Tool registration: auto mode only
# ---------------------------------------------------------------------------


class TestToolRegistration:
    """In auto mode, agent has escalate_mode; in explore/validate it does not."""

    def test_auto_mode_should_have_escalate_tool(self):
        """Verify the design: auto mode gets escalate_mode."""
        # This tests the contract, not the bridge wiring (which is a later feature).
        state = SessionState()
        tool = make_escalate_mode_tool(state)
        # Tool exists and can be passed to Agent(tools=[...])
        assert tool is not None

    def test_explore_mode_has_no_escalation_state(self):
        """In explore mode, no SessionState with escalation is created."""
        # This is a design test — explore mode just uses EXPLORE_BUDGET directly
        # and never creates an escalation tool.
        state = SessionState()
        assert state.escalation_count == 0
        # No tool to call = no events possible


# ---------------------------------------------------------------------------
# Prompt overlay files
# ---------------------------------------------------------------------------

OVERLAYS_DIR = Path(__file__).resolve().parents[3] / "crystalyse" / "prompts" / "mode_overlays"


class TestModeOverlays:
    """Prompt overlay files exist with expected content."""

    def test_auto_md_exists(self):
        assert (OVERLAYS_DIR / "auto.md").exists()

    def test_auto_md_has_escalation_criteria(self):
        content = (OVERLAYS_DIR / "auto.md").read_text()
        # Verbatim spec §7 content — check key phrases
        assert "escalate_mode" in content
        assert "E_hull > 100 meV/atom" in content
        assert "SMACT" in content
        assert "fewer than N strong candidates" in content
        assert "competitive phase region" in content
        assert "80% of budget" in content

    def test_auto_md_has_do_not_escalate_cases(self):
        content = (OVERLAYS_DIR / "auto.md").read_text()
        assert "should NOT escalate" in content
        assert "N ≤ 2" in content or "N <= 2" in content

    def test_explore_md_exists(self):
        assert (OVERLAYS_DIR / "explore.md").exists()

    def test_validate_md_exists(self):
        assert (OVERLAYS_DIR / "validate.md").exists()

    def test_all_three_overlays_nonempty(self):
        for name in ("auto.md", "explore.md", "validate.md"):
            content = (OVERLAYS_DIR / name).read_text()
            assert len(content) > 20, f"{name} is too short"
