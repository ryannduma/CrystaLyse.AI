"""Tests for ToolMetrics and TurnMetrics."""

from datetime import datetime, timedelta

import pytest

from crystalyse.orchestration.metrics import ToolMetrics, TurnMetrics


class TestToolMetrics:
    """Tests for ToolMetrics."""

    def test_duration_ms_not_complete(self):
        """Duration is None when not complete."""
        metrics = ToolMetrics(tool_name="test", tool_call_id="1")
        assert metrics.duration_ms is None

    def test_duration_ms_after_complete(self):
        """Duration is calculated after complete."""
        metrics = ToolMetrics(tool_name="test", tool_call_id="1")
        metrics.complete(success=True)
        assert metrics.duration_ms is not None
        assert metrics.duration_ms >= 0

    def test_complete_sets_fields(self):
        """Complete sets all relevant fields."""
        metrics = ToolMetrics(tool_name="test", tool_call_id="1")
        metrics.complete(success=True, error=None)

        assert metrics.success is True
        assert metrics.error is None
        assert metrics.end_time is not None

    def test_complete_with_error(self):
        """Complete can record errors."""
        metrics = ToolMetrics(tool_name="test", tool_call_id="1")
        metrics.complete(success=False, error="Something went wrong")

        assert metrics.success is False
        assert metrics.error == "Something went wrong"


class TestTurnMetrics:
    """Tests for TurnMetrics."""

    def test_empty_turn(self):
        """Empty turn has zero counts."""
        metrics = TurnMetrics(turn_id="turn_1")
        assert metrics.parallel_count == 0
        assert metrics.serial_count == 0
        assert metrics.success_count == 0
        assert metrics.total_duration_ms == 0

    def test_add_tool(self):
        """Can add tool metrics."""
        turn = TurnMetrics(turn_id="turn_1")
        tool = ToolMetrics(tool_name="test", tool_call_id="1", parallel=True)
        tool.complete(success=True)

        turn.add_tool(tool)

        assert len(turn.tool_calls) == 1
        assert turn.parallel_count == 1
        assert turn.serial_count == 0

    def test_counts_parallel_and_serial(self):
        """Correctly counts parallel vs serial tools."""
        turn = TurnMetrics(turn_id="turn_1")

        parallel = ToolMetrics(tool_name="read", tool_call_id="1", parallel=True)
        serial = ToolMetrics(tool_name="write", tool_call_id="2", parallel=False)
        parallel.complete(success=True)
        serial.complete(success=True)

        turn.add_tool(parallel)
        turn.add_tool(serial)

        assert turn.parallel_count == 1
        assert turn.serial_count == 1

    def test_success_count(self):
        """Correctly counts successes."""
        turn = TurnMetrics(turn_id="turn_1")

        success = ToolMetrics(tool_name="test", tool_call_id="1")
        failure = ToolMetrics(tool_name="test", tool_call_id="2")
        success.complete(success=True)
        failure.complete(success=False, error="Failed")

        turn.add_tool(success)
        turn.add_tool(failure)

        assert turn.success_count == 1

    def test_total_duration(self):
        """Total duration sums all tool durations."""
        turn = TurnMetrics(turn_id="turn_1")

        tool1 = ToolMetrics(tool_name="test", tool_call_id="1")
        tool2 = ToolMetrics(tool_name="test", tool_call_id="2")

        # Manually set durations for predictable test
        tool1.start_time = datetime.now()
        tool1.end_time = tool1.start_time + timedelta(milliseconds=100)
        tool1.success = True

        tool2.start_time = datetime.now()
        tool2.end_time = tool2.start_time + timedelta(milliseconds=200)
        tool2.success = True

        turn.add_tool(tool1)
        turn.add_tool(tool2)

        assert turn.total_duration_ms == pytest.approx(300, rel=0.01)
