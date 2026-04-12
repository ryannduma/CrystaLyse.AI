"""Tests for crystalyse.plan.commands — Feature 2.5 acceptance criteria.

Critical tests per thought-partner review:
  1. --plan-file query_hash verification: change one character → must fail
  2. /plan re-runs LAST user message (not next turn), tested with chat history
  3. --auto-approve-plan budget thresholds: ALL three AND-combined, not OR

Acceptance criteria from spec §5 Feature 2.5:
  - --plan-file with matching query runs successfully
  - --plan-file with different query fails with "query hash mismatch"
  - --auto-approve-plan blocks when budget exceeded
  - --auto-approve-plan --force runs regardless
  - /plans list and /plan show work
  - /plan re-runs last user message in plan mode
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from crystalyse.plan.commands import (
    AUTO_APPROVE_DEFAULTS,
    get_last_user_message,
    get_latest_plan,
    is_plan_auto_approvable,
    list_plans,
    verify_plan_file_query,
)
from crystalyse.plan.schema import Plan, PlanBudget, PlanMetadata, compute_query_hash

QUERY = "Predict five new stable quaternary compositions formed of K, Y, Zr and O"
QUERY_HASH = compute_query_hash(QUERY)


def _make_plan(
    tmp_path: Path,
    filename: str = "test-plan.md",
    query: str = QUERY,
    wall_time: int = 60,
    polymorph_count: int = 3,
    tool_scope: str = "chemistry_creative",
) -> Plan:
    """Create a valid plan file on disk and return the Plan."""
    meta = PlanMetadata(
        schema_version="1.0",
        session_id="sess-test",
        created_at=datetime(2026, 4, 12, 14, 30, 0, tzinfo=UTC),
        query=query,
        query_hash=compute_query_hash(query),
        intended_mode="validate",
        model="openai_o3",
        budget=PlanBudget(
            wall_time_seconds=wall_time,
            estimated_tokens=45000,
            polymorph_count=polymorph_count,
            tool_scope=tool_scope,
        ),
    )
    plan = Plan(metadata=meta, body="## Steps\n\n1. Do things\n", path=tmp_path / filename)
    plan.path.write_text(plan.to_markdown(), encoding="utf-8")
    return plan


# ---------------------------------------------------------------------------
# 1. --plan-file query_hash verification (CRITICAL)
# ---------------------------------------------------------------------------


class TestPlanFileQueryHashVerification:
    """--plan-file replay verifies query_hash against the provided query.

    This is the reproducibility story for the response letter.
    """

    def test_matching_query_succeeds(self, tmp_path):
        plan = _make_plan(tmp_path, query=QUERY)
        ok, error = verify_plan_file_query(plan, QUERY)
        assert ok
        assert error == ""

    def test_one_character_change_fails(self, tmp_path):
        """Change ONE character of the query → must fail with clear error."""
        plan = _make_plan(tmp_path, query=QUERY)
        # Change "five" to "Five" — one character case change
        altered_query = QUERY.replace("five", "Five")
        assert altered_query != QUERY  # sanity check

        ok, error = verify_plan_file_query(plan, altered_query)
        assert not ok
        assert "Query hash mismatch" in error
        assert "different query" in error

    def test_whitespace_difference_matters(self, tmp_path):
        """Extra internal whitespace changes the hash (only strip is applied)."""
        plan = _make_plan(tmp_path, query=QUERY)
        # Add extra space inside the query
        spaced_query = QUERY.replace("new stable", "new  stable")
        assert spaced_query != QUERY

        ok, error = verify_plan_file_query(plan, spaced_query)
        assert not ok

    def test_leading_trailing_whitespace_does_not_matter(self, tmp_path):
        """Leading/trailing whitespace is stripped (spec W6)."""
        plan = _make_plan(tmp_path, query=QUERY)
        padded_query = f"  {QUERY}  "

        ok, error = verify_plan_file_query(plan, padded_query)
        assert ok

    def test_completely_different_query_fails(self, tmp_path):
        plan = _make_plan(tmp_path, query=QUERY)
        ok, error = verify_plan_file_query(plan, "What is NaCl")
        assert not ok
        assert "mismatch" in error


# ---------------------------------------------------------------------------
# 2. /plan re-runs LAST user message (CRITICAL)
# ---------------------------------------------------------------------------


class TestGetLastUserMessage:
    """``/plan`` re-runs the LAST user message, not the next one.

    Tests use explicit chat history to verify the semantics.
    """

    def test_gets_last_user_message(self):
        history = [
            {"role": "user", "content": "First query about NaCl"},
            {"role": "assistant", "content": "NaCl is..."},
            {"role": "user", "content": "Find stable perovskites for solar cells"},
            {"role": "assistant", "content": "Let me search..."},
        ]
        result = get_last_user_message(history)
        assert result == "Find stable perovskites for solar cells"

    def test_skips_slash_commands(self):
        history = [
            {"role": "user", "content": "Find stable perovskites"},
            {"role": "assistant", "content": "Result..."},
            {"role": "user", "content": "/mode validate"},
            {"role": "user", "content": "/plan"},
        ]
        result = get_last_user_message(history)
        assert result == "Find stable perovskites"

    def test_empty_history_returns_none(self):
        assert get_last_user_message([]) is None

    def test_only_slash_commands_returns_none(self):
        history = [
            {"role": "user", "content": "/help"},
            {"role": "user", "content": "/plan"},
        ]
        assert get_last_user_message(history) is None

    def test_only_assistant_messages_returns_none(self):
        history = [
            {"role": "assistant", "content": "Hello!"},
        ]
        assert get_last_user_message(history) is None

    def test_multiple_user_messages_gets_last_non_slash(self):
        """Explicit test with a chat history containing multiple user messages."""
        history = [
            {"role": "user", "content": "What is the bandgap of CsPbI3?"},
            {"role": "assistant", "content": "CsPbI3 has..."},
            {"role": "user", "content": "Now find five stable double perovskites"},
            {"role": "assistant", "content": "I'll search..."},
            {"role": "user", "content": "/plan"},
        ]
        result = get_last_user_message(history)
        # Should get the second query, NOT the first, and NOT the /plan command
        assert result == "Now find five stable double perovskites"


# ---------------------------------------------------------------------------
# 3. --auto-approve-plan budget thresholds (CRITICAL)
# ---------------------------------------------------------------------------


class TestAutoApprovalBudgetThresholds:
    """Budget thresholds: wall_time ≤ 120 AND polymorph_count ≤ 5 AND
    tool_scope == chemistry_creative.  All three AND-combined, not OR.
    """

    def test_within_all_thresholds_approved(self, tmp_path):
        plan = _make_plan(
            tmp_path, wall_time=60, polymorph_count=3, tool_scope="chemistry_creative"
        )
        ok, reasons = is_plan_auto_approvable(plan)
        assert ok
        assert reasons == []

    def test_exactly_at_thresholds_approved(self, tmp_path):
        plan = _make_plan(
            tmp_path, wall_time=120, polymorph_count=5, tool_scope="chemistry_creative"
        )
        ok, reasons = is_plan_auto_approvable(plan)
        assert ok

    def test_wall_time_exceeded_blocked(self, tmp_path):
        plan = _make_plan(
            tmp_path, wall_time=121, polymorph_count=3, tool_scope="chemistry_creative"
        )
        ok, reasons = is_plan_auto_approvable(plan)
        assert not ok
        assert any("wall_time" in r for r in reasons)

    def test_polymorph_count_exceeded_blocked(self, tmp_path):
        plan = _make_plan(
            tmp_path, wall_time=60, polymorph_count=30, tool_scope="chemistry_creative"
        )
        ok, reasons = is_plan_auto_approvable(plan)
        assert not ok
        assert any("polymorph_count" in r for r in reasons)

    def test_tool_scope_unified_blocked(self, tmp_path):
        plan = _make_plan(tmp_path, wall_time=60, polymorph_count=3, tool_scope="chemistry_unified")
        ok, reasons = is_plan_auto_approvable(plan)
        assert not ok
        assert any("tool_scope" in r for r in reasons)

    def test_all_three_exceeded_gives_three_reasons(self, tmp_path):
        """When all three thresholds are exceeded, all three reasons appear."""
        plan = _make_plan(
            tmp_path, wall_time=300, polymorph_count=30, tool_scope="chemistry_unified"
        )
        ok, reasons = is_plan_auto_approvable(plan)
        assert not ok
        assert len(reasons) == 3

    def test_and_not_or_two_within_one_exceeded_blocks(self, tmp_path):
        """AND-combined: even if two are within threshold, one exceeded blocks."""
        plan = _make_plan(tmp_path, wall_time=60, polymorph_count=3, tool_scope="chemistry_unified")
        ok, reasons = is_plan_auto_approvable(plan)
        assert not ok
        assert len(reasons) == 1

    def test_force_bypasses_all(self, tmp_path):
        """--force unconditionally approves regardless of budget."""
        plan = _make_plan(
            tmp_path, wall_time=9999, polymorph_count=100, tool_scope="chemistry_unified"
        )
        ok, reasons = is_plan_auto_approvable(plan, force=True)
        assert ok
        assert reasons == []

    def test_default_thresholds_match_spec(self):
        """Verify default thresholds match spec §2.9."""
        assert AUTO_APPROVE_DEFAULTS["max_wall_time_seconds"] == 120
        assert AUTO_APPROVE_DEFAULTS["max_polymorph_count"] == 5
        assert AUTO_APPROVE_DEFAULTS["max_tool_scope"] == "chemistry_creative"


# ---------------------------------------------------------------------------
# Plan listing
# ---------------------------------------------------------------------------


class TestListPlans:
    def test_empty_directory(self, tmp_path):
        plans_dir = tmp_path / "plans"
        plans_dir.mkdir()
        assert list_plans(plans_dir) == []

    def test_lists_plans_newest_first(self, tmp_path):
        import os
        import time

        plans_dir = tmp_path / "plans"
        plans_dir.mkdir()

        # Create two plans with different mtimes
        old = plans_dir / "old.md"
        old.write_text("old plan")
        old_time = time.time() - 86400
        os.utime(old, (old_time, old_time))

        new = plans_dir / "new.md"
        new.write_text("new plan")

        result = list_plans(plans_dir)
        assert len(result) == 2
        assert result[0]["name"] == "new.md"
        assert result[1]["name"] == "old.md"

    def test_skips_latest_symlink(self, tmp_path):
        plans_dir = tmp_path / "plans"
        plans_dir.mkdir()
        real = plans_dir / "real.md"
        real.write_text("content")
        (plans_dir / "latest.md").symlink_to(real)

        result = list_plans(plans_dir)
        assert len(result) == 1
        assert result[0]["name"] == "real.md"

    def test_nonexistent_directory(self, tmp_path):
        assert list_plans(tmp_path / "nope") == []


class TestGetLatestPlan:
    def test_latest_symlink(self, tmp_path):
        plans_dir = tmp_path / "plans"
        plans_dir.mkdir()
        _make_plan(tmp_path=plans_dir, filename="actual.md")
        (plans_dir / "latest.md").symlink_to(plans_dir / "actual.md")

        plan = get_latest_plan(plans_dir)
        assert plan is not None
        assert plan.metadata.session_id == "sess-test"

    def test_no_symlink_falls_back_to_newest(self, tmp_path):
        plans_dir = tmp_path / "plans"
        plans_dir.mkdir()
        _make_plan(tmp_path=plans_dir, filename="only-plan.md")

        plan = get_latest_plan(plans_dir)
        assert plan is not None

    def test_empty_directory_returns_none(self, tmp_path):
        plans_dir = tmp_path / "plans"
        plans_dir.mkdir()
        assert get_latest_plan(plans_dir) is None
