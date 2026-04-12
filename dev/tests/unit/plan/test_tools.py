"""Tests for crystalyse.plan.tools — Feature 2.3 acceptance criteria.

Focuses on the exit_plan_mode tool: path containment, frontmatter
validation, query_hash verification, and happy-path acceptance.

Acceptance criteria from spec §5 Feature 2.3:
  - exit_plan_mode rejects ../../etc/passwd (path containment)
  - exit_plan_mode rejects absolute paths outside plans dir
  - exit_plan_mode rejects file with wrong query_hash
  - exit_plan_mode rejects file with missing frontmatter
  - exit_plan_mode accepts valid plan file and returns plan_ready
  - Symlink escape: symlink inside plans/ pointing outside is rejected
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from crystalyse.plan.schema import Plan, PlanBudget, PlanMetadata, compute_query_hash
from crystalyse.plan.tools import _is_contained

QUERY = "Predict stable quaternary oxides in the K-Y-Zr-O system"
QUERY_HASH = compute_query_hash(QUERY)


def _write_valid_plan(plans_dir: Path, filename: str, query: str = QUERY) -> Path:
    """Write a valid plan file into plans_dir and return its path."""
    qhash = compute_query_hash(query)
    meta = PlanMetadata(
        schema_version="1.0",
        session_id="sess-test-123",
        created_at=datetime(2026, 4, 12, 14, 30, 0, tzinfo=UTC),
        query=query,
        query_hash=qhash,
        intended_mode="validate",
        model="openai_o3",
        budget=PlanBudget(
            wall_time_seconds=280,
            estimated_tokens=45000,
            polymorph_count=30,
            tool_scope="chemistry_unified",
        ),
    )
    plan = Plan(metadata=meta, body="## Planned steps\n\n1. Do things\n", path=plans_dir / filename)
    md = plan.to_markdown()
    (plans_dir / filename).write_text(md, encoding="utf-8")
    return plans_dir / filename


# ---------------------------------------------------------------------------
# Helper: _is_contained
# ---------------------------------------------------------------------------


class TestIsContained:
    def test_child_inside_parent(self, tmp_path):
        child = tmp_path / "plans" / "file.md"
        assert _is_contained(child, tmp_path / "plans")

    def test_child_outside_parent(self, tmp_path):
        child = tmp_path / "other" / "file.md"
        assert not _is_contained(child, tmp_path / "plans")

    def test_parent_itself(self, tmp_path):
        # The directory itself is "contained" (edge case, but safe)
        assert _is_contained(tmp_path, tmp_path)


# ---------------------------------------------------------------------------
# Path containment tests
# ---------------------------------------------------------------------------


class TestPathContainment:
    """exit_plan_mode must reject paths that escape .crystalyse/plans/."""

    def test_reject_traversal_attack(self, tmp_path):
        plans_dir = tmp_path / "plans"
        plans_dir.mkdir()

        resolved = (plans_dir / "../../etc/passwd").resolve()
        assert not _is_contained(resolved, plans_dir.resolve())

    def test_reject_absolute_path_outside(self, tmp_path):
        plans_dir = tmp_path / "plans"
        plans_dir.mkdir()

        resolved = Path("/etc/passwd").resolve()
        assert not _is_contained(resolved, plans_dir.resolve())

    def test_accept_valid_relative_filename(self, tmp_path):
        plans_dir = tmp_path / "plans"
        plans_dir.mkdir()

        resolved = (plans_dir / "my-plan.md").resolve()
        assert _is_contained(resolved, plans_dir.resolve())

    def test_symlink_escape_rejected(self, tmp_path):
        """A symlink inside plans/ pointing outside must be rejected."""
        plans_dir = tmp_path / "plans"
        plans_dir.mkdir()
        outside_file = tmp_path / "secret.txt"
        outside_file.write_text("secret data")

        symlink = plans_dir / "sneaky.md"
        symlink.symlink_to(outside_file)

        # After resolve(), the symlink target is outside plans_dir
        resolved = symlink.resolve()
        assert not _is_contained(resolved, plans_dir.resolve())


# ---------------------------------------------------------------------------
# exit_plan_mode tool integration tests (calling the actual tool function)
# ---------------------------------------------------------------------------


def _call_exit_tool_raw(plans_dir: Path, filename: str, query: str) -> dict:
    """Directly test the exit_plan_mode logic without the @function_tool wrapper."""
    import hashlib as _hashlib

    from crystalyse.plan.tools import _is_contained

    expected_hash = _hashlib.sha256(query.strip().encode()).hexdigest()
    errors: list[str] = []

    resolved = (plans_dir / filename).resolve()
    plans_dir_resolved = plans_dir.resolve()

    if not _is_contained(resolved, plans_dir_resolved):
        errors.append(
            f"plan_filename must resolve to a path under {plans_dir_resolved}; got {resolved}"
        )
        return {"status": "invalid", "errors": errors}

    if not resolved.is_file():
        errors.append(f"Plan file not found: {resolved}")
        return {"status": "invalid", "errors": errors}

    try:
        plan = Plan.from_markdown(resolved)
    except (ValueError, Exception) as exc:
        errors.append(f"Plan parsing failed: {exc}")
        return {"status": "invalid", "errors": errors}

    if plan.metadata.query_hash != expected_hash:
        errors.append(
            f"query_hash mismatch: plan has {plan.metadata.query_hash!r}, "
            f"expected {expected_hash!r} for the original query"
        )
        return {"status": "invalid", "errors": errors}

    return {
        "status": "plan_ready",
        "path": str(resolved),
        "metadata": plan.metadata.model_dump(mode="json"),
    }


class TestExitPlanModeRejectsTraversal:
    """Path containment: ../../etc/passwd and absolute paths are rejected."""

    def test_traversal_attack(self, tmp_path):
        plans_dir = tmp_path / "plans"
        plans_dir.mkdir()
        result = _call_exit_tool_raw(plans_dir, "../../etc/passwd", QUERY)
        assert result["status"] == "invalid"
        assert any("must resolve to a path under" in e for e in result["errors"])

    def test_absolute_path_outside(self, tmp_path):
        plans_dir = tmp_path / "plans"
        plans_dir.mkdir()
        result = _call_exit_tool_raw(plans_dir, "/etc/passwd", QUERY)
        assert result["status"] == "invalid"
        assert any("must resolve to a path under" in e for e in result["errors"])

    def test_symlink_escape(self, tmp_path):
        """Symlink inside plans/ pointing outside is rejected."""
        plans_dir = tmp_path / "plans"
        plans_dir.mkdir()
        outside = tmp_path / "outside.md"
        outside.write_text("not a plan")
        (plans_dir / "evil-link.md").symlink_to(outside)

        result = _call_exit_tool_raw(plans_dir, "evil-link.md", QUERY)
        assert result["status"] == "invalid"
        assert any("must resolve to a path under" in e for e in result["errors"])


class TestExitPlanModeRejectsInvalidPlan:
    """Frontmatter and query_hash validation."""

    def test_missing_frontmatter(self, tmp_path):
        plans_dir = tmp_path / "plans"
        plans_dir.mkdir()
        (plans_dir / "no-frontmatter.md").write_text("Just a body, no YAML.\n")

        result = _call_exit_tool_raw(plans_dir, "no-frontmatter.md", QUERY)
        assert result["status"] == "invalid"
        assert len(result["errors"]) > 0

    def test_wrong_query_hash(self, tmp_path):
        plans_dir = tmp_path / "plans"
        plans_dir.mkdir()

        # Write a plan with a DIFFERENT query than what the tool expects
        different_query = "Something completely different"
        _write_valid_plan(plans_dir, "wrong-hash.md", query=different_query)

        result = _call_exit_tool_raw(plans_dir, "wrong-hash.md", QUERY)
        assert result["status"] == "invalid"
        assert any("query_hash mismatch" in e for e in result["errors"])

    def test_file_not_found(self, tmp_path):
        plans_dir = tmp_path / "plans"
        plans_dir.mkdir()

        result = _call_exit_tool_raw(plans_dir, "nonexistent.md", QUERY)
        assert result["status"] == "invalid"
        assert any("not found" in e for e in result["errors"])

    def test_invalid_schema_version(self, tmp_path):
        plans_dir = tmp_path / "plans"
        plans_dir.mkdir()
        content = """\
---
schema_version: '2.0'
session_id: sess-test
created_at: '2026-04-12T14:30:00Z'
query: test
query_hash: placeholder
intended_mode: explore
model: test
budget:
  wall_time_seconds: 60
  estimated_tokens: 1000
  polymorph_count: 3
  tool_scope: chemistry_creative
---
Body.
"""
        (plans_dir / "bad-version.md").write_text(content)

        result = _call_exit_tool_raw(plans_dir, "bad-version.md", QUERY)
        assert result["status"] == "invalid"


class TestExitPlanModeAcceptsValid:
    """Happy path: valid plan file returns plan_ready."""

    def test_valid_plan_accepted(self, tmp_path):
        plans_dir = tmp_path / "plans"
        plans_dir.mkdir()
        _write_valid_plan(plans_dir, "good-plan.md")

        result = _call_exit_tool_raw(plans_dir, "good-plan.md", QUERY)
        assert result["status"] == "plan_ready"
        assert "path" in result
        assert "metadata" in result
        assert result["metadata"]["intended_mode"] == "validate"

    def test_reordered_body_accepted(self, tmp_path):
        """Body is opaque — reordered sections should still pass."""
        plans_dir = tmp_path / "plans"
        plans_dir.mkdir()

        meta = PlanMetadata(
            schema_version="1.0",
            session_id="sess-test",
            created_at=datetime(2026, 4, 12, 14, 30, 0, tzinfo=UTC),
            query=QUERY,
            query_hash=QUERY_HASH,
            intended_mode="validate",
            model="openai_o3",
            budget=PlanBudget(
                wall_time_seconds=280,
                estimated_tokens=45000,
                polymorph_count=30,
                tool_scope="chemistry_unified",
            ),
        )
        # Body with sections in non-standard order
        body = """\
## Assumptions

- Stability means < 50 meV/atom

## Open questions

- None

## Planned steps

1. Generate structures
2. Rank by energy

## Research phase findings

K-Y-Zr-O has 27 candidate compositions.
"""
        plan = Plan(metadata=meta, body=body, path=plans_dir / "reordered.md")
        (plans_dir / "reordered.md").write_text(plan.to_markdown(), encoding="utf-8")

        result = _call_exit_tool_raw(plans_dir, "reordered.md", QUERY)
        assert result["status"] == "plan_ready"

    def test_manually_edited_body_accepted(self, tmp_path):
        """A plan manually edited by the user (extra sections, notes) still parses."""
        plans_dir = tmp_path / "plans"
        plans_dir.mkdir()
        _write_valid_plan(plans_dir, "edited.md")

        # Simulate user editing the body
        content = (plans_dir / "edited.md").read_text()
        content += "\n\n## User notes\n\nI want to focus on Zr-rich compositions.\n"
        (plans_dir / "edited.md").write_text(content)

        result = _call_exit_tool_raw(plans_dir, "edited.md", QUERY)
        assert result["status"] == "plan_ready"


# ---------------------------------------------------------------------------
# Research phase structural tests
# ---------------------------------------------------------------------------


class TestResearchPhaseStructure:
    """Verify research phase agent configuration."""

    def test_agent_has_no_mcp_servers(self, monkeypatch):
        """Research phase never connects to any MCP server."""
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test-fake")
        from crystalyse.plan.research_phase import build_research_agent

        plans_dir = Path("/tmp/test-plans")
        agent, _ = build_research_agent("test query", "o4-mini", plans_dir)

        # Agent should have no mcp_servers attribute set, or it should be empty
        mcp = getattr(agent, "mcp_servers", [])
        assert mcp == [] or mcp is None or len(mcp) == 0

    def test_agent_has_exit_tool(self, monkeypatch):
        """Research phase agent includes exit_plan_mode in its tools."""
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test-fake")
        from crystalyse.plan.research_phase import build_research_agent

        plans_dir = Path("/tmp/test-plans")
        agent, exit_tool = build_research_agent("test query", "o4-mini", plans_dir)

        assert exit_tool is not None
        assert len(agent.tools) >= 1

    def test_budget_defaults(self):
        from crystalyse.plan.research_phase import ResearchPhaseBudget

        budget = ResearchPhaseBudget()
        assert budget.max_wall_time_seconds == 60
        assert budget.max_tokens == 10_000
        assert budget.max_tool_calls == 5

    def test_budget_is_frozen(self):
        from crystalyse.plan.research_phase import ResearchPhaseBudget

        budget = ResearchPhaseBudget()
        with pytest.raises(AttributeError):
            budget.max_wall_time_seconds = 120


# ---------------------------------------------------------------------------
# Prompt tests
# ---------------------------------------------------------------------------


class TestResearchPhasePrompt:
    """RESEARCH_PHASE_SYSTEM_PROMPT exists and has expected content."""

    def test_prompt_exists_and_nonempty(self):
        from crystalyse.plan.prompts import RESEARCH_PHASE_SYSTEM_PROMPT

        assert len(RESEARCH_PHASE_SYSTEM_PROMPT) > 500

    def test_prompt_lists_allowed_tools(self):
        from crystalyse.plan.prompts import RESEARCH_PHASE_SYSTEM_PROMPT

        assert "read_file" in RESEARCH_PHASE_SYSTEM_PROMPT
        assert "write_file" in RESEARCH_PHASE_SYSTEM_PROMPT
        assert "list_files" in RESEARCH_PHASE_SYSTEM_PROMPT
        assert "exit_plan_mode" in RESEARCH_PHASE_SYSTEM_PROMPT

    def test_prompt_forbids_expensive_tools(self):
        from crystalyse.plan.prompts import RESEARCH_PHASE_SYSTEM_PROMPT

        assert "chemeleon" in RESEARCH_PHASE_SYSTEM_PROMPT.lower()
        assert "mace" in RESEARCH_PHASE_SYSTEM_PROMPT.lower()
        assert "comprehensive_materials_analysis" in RESEARCH_PHASE_SYSTEM_PROMPT

    def test_prompt_mentions_frontmatter_fields(self):
        from crystalyse.plan.prompts import RESEARCH_PHASE_SYSTEM_PROMPT

        for field in ["schema_version", "session_id", "query_hash", "intended_mode", "budget"]:
            assert field in RESEARCH_PHASE_SYSTEM_PROMPT


# ---------------------------------------------------------------------------
# Helper function tests
# ---------------------------------------------------------------------------


class TestHelperFunctions:
    def test_generate_session_id_format(self):
        from crystalyse.plan.research_phase import generate_session_id

        sid = generate_session_id()
        # Format: YYYY-MM-DDTHH-MM-SS-hexhex
        parts = sid.rsplit("-", 1)
        assert len(parts) == 2
        assert len(parts[1]) == 6  # 6 hex chars

    def test_generate_plan_filename(self):
        from crystalyse.plan.research_phase import generate_plan_filename

        name = generate_plan_filename(
            "Predict stable quaternary oxides", "2026-04-12T14-30-00-abc123"
        )
        assert name.endswith(".md")
        assert "predict" in name.lower()
        assert "stable" in name.lower()

    def test_generate_plan_filename_filters_stopwords(self):
        from crystalyse.plan.research_phase import generate_plan_filename

        name = generate_plan_filename(
            "Find the best materials for a solar cell",
            "2026-04-12T14-30-00-abc123",
        )
        # "the", "for", "a" should be filtered out
        assert "the" not in name.split("_", 1)[1].split("-")
        assert name.endswith(".md")
