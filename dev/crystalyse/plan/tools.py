"""Plan-mode tools exposed to the research-phase agent.

The ``exit_plan_mode`` tool is the single transition point out of
research phase.  It validates the plan file (path containment,
frontmatter, query_hash) before accepting it.

Modelled on Gemini CLI's ``exit-plan-mode.ts:118-251`` and the path
containment check from ``storage.ts:323-341``.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from crystalyse.plan.schema import Plan


def make_exit_plan_mode_tool(
    plans_dir: Path,
    original_query: str,
):
    """Factory that returns an ``exit_plan_mode`` function tool bound to a
    specific plans directory and query.

    The returned function is decorated with ``@function_tool`` so it can be
    passed directly to ``Agent(tools=[...])``.

    Parameters
    ----------
    plans_dir:
        Absolute path to the ``.crystalyse/plans/`` directory.
    original_query:
        The verbatim user query.  Used to verify ``query_hash``.
    """
    from agents import function_tool

    expected_hash = hashlib.sha256(original_query.strip().encode()).hexdigest()

    @function_tool
    def exit_plan_mode(plan_filename: str) -> dict[str, Any]:
        """Signal that the research-phase plan is ready for review.

        Validates the plan file at ``.crystalyse/plans/<plan_filename>``:
        path containment, frontmatter schema, and query_hash match.

        :param plan_filename: Filename (not full path) of the plan inside
            the plans directory.  Example: ``2026-04-12T14-30-00_quaternary-oxide-discovery.md``
        :return: ``{"status": "plan_ready", ...}`` on success, or
            ``{"status": "invalid", "errors": [...]}`` on failure.
        """
        errors: list[str] = []

        # ---------------------------------------------------------------
        # Step 1: Resolve against plans_dir
        # ---------------------------------------------------------------
        resolved = (plans_dir / plan_filename).resolve()

        # ---------------------------------------------------------------
        # Step 2: Path containment check (closes prompt-adherence gap)
        # Modelled on Gemini CLI storage.ts:323-341 isSubpath check.
        # ---------------------------------------------------------------
        plans_dir_resolved = plans_dir.resolve()
        if not _is_contained(resolved, plans_dir_resolved):
            errors.append(
                f"plan_filename must resolve to a path under {plans_dir_resolved}; got {resolved}"
            )
            return {"status": "invalid", "errors": errors}

        # ---------------------------------------------------------------
        # Step 3: File existence
        # ---------------------------------------------------------------
        if not resolved.is_file():
            errors.append(f"Plan file not found: {resolved}")
            return {"status": "invalid", "errors": errors}

        # ---------------------------------------------------------------
        # Step 4: Parse via Plan.from_markdown() — validates frontmatter
        # ---------------------------------------------------------------
        try:
            plan = Plan.from_markdown(resolved)
        except (ValueError, Exception) as exc:
            errors.append(f"Plan parsing failed: {exc}")
            return {"status": "invalid", "errors": errors}

        # ---------------------------------------------------------------
        # Step 5: Verify query_hash matches original query
        # ---------------------------------------------------------------
        if plan.metadata.query_hash != expected_hash:
            errors.append(
                f"query_hash mismatch: plan has {plan.metadata.query_hash!r}, "
                f"expected {expected_hash!r} for the original query"
            )
            return {"status": "invalid", "errors": errors}

        # ---------------------------------------------------------------
        # Step 6: Success
        # ---------------------------------------------------------------
        return {
            "status": "plan_ready",
            "path": str(resolved),
            "metadata": plan.metadata.model_dump(mode="json"),
        }

    return exit_plan_mode


def _is_contained(child: Path, parent: Path) -> bool:
    """Check that *child* is strictly under *parent* (both resolved).

    Uses ``Path.is_relative_to`` (Python 3.9+) after resolving symlinks
    to prevent symlink escape attacks.
    """
    try:
        child.relative_to(parent)
        return True
    except ValueError:
        return False
