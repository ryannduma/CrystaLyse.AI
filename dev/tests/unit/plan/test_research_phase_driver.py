"""Integration test for enter_research_phase driver.

Mocks Runner.run to no-op, writes a plan file directly to plans_dir
(simulating what exit_plan_mode would produce), and asserts
enter_research_phase returns the parsed Plan.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import AsyncMock, patch

from crystalyse.plan.research_phase import (
    ResearchPhaseBudget,
    enter_research_phase,
)
from crystalyse.plan.schema import Plan, PlanBudget, PlanMetadata, compute_query_hash

QUERY = "Predict five new stable quaternary compositions formed of K, Y, Zr and O"


def _write_plan_to_dir(plans_dir: Path, query: str = QUERY) -> Path:
    """Write a valid plan file into plans_dir (simulating agent's write_file + exit_plan_mode)."""
    meta = PlanMetadata(
        schema_version="1.0",
        session_id="sess-test",
        created_at=datetime(2026, 4, 12, 14, 30, 0, tzinfo=UTC),
        query=query,
        query_hash=compute_query_hash(query),
        intended_mode="validate",
        model="openai_o3",
        budget=PlanBudget(
            wall_time_seconds=280,
            estimated_tokens=45000,
            polymorph_count=30,
            tool_scope="chemistry_unified",
        ),
    )
    plan = Plan(
        metadata=meta,
        body="## Steps\n\n1. Generate\n2. Rank\n",
        path=plans_dir / "2026-04-12T14-30-00_quaternary-oxide.md",
    )
    plan.path.write_text(plan.to_markdown(), encoding="utf-8")
    return plan.path


class TestEnterResearchPhase:
    """Integration test: mock Runner.run, write plan to disk, assert driver returns it."""

    def test_returns_plan_on_success(self, tmp_path, monkeypatch):
        """Mock Runner.run to no-op, pre-write a plan file, assert parsed plan returned."""
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test-fake")
        plans_dir = tmp_path / "plans"
        plans_dir.mkdir()

        # Pre-write the plan file (simulating what the agent + exit_plan_mode would produce)
        _write_plan_to_dir(plans_dir)

        # Mock Runner.run to return a no-op result
        mock_result = AsyncMock()
        mock_run = AsyncMock(return_value=mock_result)

        with patch("agents.Runner.run", new=mock_run):
            result = asyncio.run(enter_research_phase(QUERY, "o4-mini", plans_dir))

        assert result.exit_status == "plan_ready"
        assert result.plan is not None
        assert result.plan.metadata.query == QUERY
        assert result.plan.metadata.intended_mode == "validate"
        assert result.plan.metadata.budget.polymorph_count == 30
        assert result.errors == []

    def test_returns_error_when_no_plan_written(self, tmp_path, monkeypatch):
        """If the agent runs but writes no plan file, driver returns error."""
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test-fake")
        plans_dir = tmp_path / "plans"
        plans_dir.mkdir()

        # Don't write any plan file — simulate agent failure to produce output
        mock_run = AsyncMock(return_value=AsyncMock())

        with patch("agents.Runner.run", new=mock_run):
            result = asyncio.run(enter_research_phase(QUERY, "o4-mini", plans_dir))

        assert result.exit_status == "error"
        assert result.plan is None
        assert any("no plan file" in e.lower() for e in result.errors)

    def test_creates_plans_dir_if_missing(self, tmp_path, monkeypatch):
        """plans_dir is created if it doesn't exist."""
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test-fake")
        plans_dir = tmp_path / "nonexistent" / "plans"

        # The directory will be created, but no plan file will be written
        mock_run = AsyncMock(return_value=AsyncMock())

        with patch("agents.Runner.run", new=mock_run):
            result = asyncio.run(enter_research_phase(QUERY, "o4-mini", plans_dir))

        assert plans_dir.exists()
        # No plan written → error
        assert result.exit_status == "error"

    def test_budget_defaults(self):
        budget = ResearchPhaseBudget()
        assert budget.max_wall_time_seconds == 60
        assert budget.max_tool_calls == 5
