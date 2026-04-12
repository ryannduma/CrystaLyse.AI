"""Plan-mode slash commands and CLI flag logic (Feature 2.5).

Provides:
  - ``/plan`` — re-runs the last user message in plan mode
  - ``/plan approve`` — executes the latest plan
  - ``/plan show [id]`` — displays a plan (default: latest)
  - ``/plan cancel`` — discards the current plan
  - ``/plans list`` — lists all plans in .crystalyse/plans/
  - ``--plan-file`` replay with query_hash verification
  - ``--auto-approve-plan`` budget threshold checking

UX decision (CrystaLyse-specific, not Claude Code's pattern):
  ``/plan`` re-runs the LAST user message in plan mode, not the next one.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from crystalyse.plan.schema import Plan, compute_query_hash

# ---------------------------------------------------------------------------
# --auto-approve-plan budget thresholds (spec §2.9)
# ---------------------------------------------------------------------------

#: Default auto-approval thresholds.  ALL three must be satisfied (AND).
AUTO_APPROVE_DEFAULTS = {
    "max_wall_time_seconds": 120,
    "max_polymorph_count": 5,
    "max_tool_scope": "chemistry_creative",
}


def is_plan_auto_approvable(
    plan: Plan,
    *,
    force: bool = False,
    max_wall_time: int = AUTO_APPROVE_DEFAULTS["max_wall_time_seconds"],
    max_polymorph_count: int = AUTO_APPROVE_DEFAULTS["max_polymorph_count"],
    max_tool_scope: str = AUTO_APPROVE_DEFAULTS["max_tool_scope"],
) -> tuple[bool, list[str]]:
    """Check whether a plan can be auto-approved without user interaction.

    Returns ``(True, [])`` if the plan is within all thresholds, or
    ``(False, [reasons...])`` listing which thresholds were exceeded.

    If *force* is True, always returns ``(True, [])``.

    All three conditions must be satisfied (AND-combined, not OR):
      - wall_time_seconds ≤ max_wall_time
      - polymorph_count ≤ max_polymorph_count
      - tool_scope == max_tool_scope (chemistry_creative)
    """
    if force:
        return True, []

    reasons: list[str] = []
    budget = plan.metadata.budget

    if budget.wall_time_seconds > max_wall_time:
        reasons.append(
            f"wall_time_seconds={budget.wall_time_seconds} exceeds threshold {max_wall_time}"
        )

    if budget.polymorph_count > max_polymorph_count:
        reasons.append(
            f"polymorph_count={budget.polymorph_count} exceeds threshold {max_polymorph_count}"
        )

    # tool_scope must be exactly chemistry_creative for auto-approval
    if budget.tool_scope != max_tool_scope:
        reasons.append(f"tool_scope='{budget.tool_scope}' != required '{max_tool_scope}'")

    return len(reasons) == 0, reasons


# ---------------------------------------------------------------------------
# --plan-file replay: query_hash verification
# ---------------------------------------------------------------------------


def verify_plan_file_query(plan: Plan, query: str) -> tuple[bool, str]:
    """Verify that a plan file's query_hash matches the provided query.

    This is the reproducibility check for ``--plan-file`` replay.
    Returns ``(True, "")`` on match, or ``(False, error_message)`` on mismatch.
    """
    expected_hash = compute_query_hash(query)
    if plan.metadata.query_hash != expected_hash:
        return False, (
            f"Query hash mismatch: plan file has query_hash={plan.metadata.query_hash!r} "
            f"(from query {plan.metadata.query!r}), but the provided query "
            f"{query!r} hashes to {expected_hash!r}. "
            f"The plan was created for a different query."
        )
    return True, ""


# ---------------------------------------------------------------------------
# Plan listing and display
# ---------------------------------------------------------------------------


def list_plans(plans_dir: Path) -> list[dict[str, Any]]:
    """List all plan files in plans_dir, sorted newest first.

    Returns a list of dicts with keys: name, path, mtime, size_bytes.
    """
    if not plans_dir.is_dir():
        return []

    plans = []
    for path in sorted(plans_dir.glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True):
        if path.name == "latest.md" and path.is_symlink():
            continue
        plans.append(
            {
                "name": path.name,
                "path": str(path),
                "mtime": path.stat().st_mtime,
                "size_bytes": path.stat().st_size,
            }
        )
    return plans


def get_latest_plan(plans_dir: Path) -> Plan | None:
    """Load the latest plan (via latest.md symlink or newest file)."""
    latest = plans_dir / "latest.md"
    if latest.exists():
        target = latest.resolve()
        if target.exists():
            try:
                return Plan.from_markdown(target)
            except (ValueError, Exception):
                pass

    # Fallback: newest .md file
    plans = list_plans(plans_dir)
    if plans:
        try:
            return Plan.from_markdown(Path(plans[0]["path"]))
        except (ValueError, Exception):
            pass

    return None


def get_last_user_message(history: list[dict[str, Any]]) -> str | None:
    """Extract the last user message from chat history.

    This implements the CrystaLyse-specific UX: ``/plan`` re-runs the
    LAST user message, not the next one.
    """
    for entry in reversed(history):
        if entry.get("role") == "user":
            content = entry.get("content", "")
            # Skip slash commands themselves
            if content.strip().startswith("/"):
                continue
            return content
    return None
