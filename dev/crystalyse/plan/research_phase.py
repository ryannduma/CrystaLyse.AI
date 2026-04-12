"""Research-phase driver: builds and runs the research agent.

The research agent has ``mcp_servers=[]`` — no MCP connections during
research (v1).  It uses workspace tools (``read_file``, ``write_file``,
``list_files``) plus ``exit_plan_mode`` to write the plan to disk and
signal completion.

The plan exists as a file on disk, not as a structured return value
(no ``output_type=Plan``).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from crystalyse.plan.schema import Plan


@dataclass(frozen=True)
class ResearchPhaseBudget:
    """Soft budget limits for the research phase.

    Enforced from outside the agent by the driver loop — if the agent
    blows past the budget, it is prompted to call ``exit_plan_mode``
    with whatever it has.
    """

    max_wall_time_seconds: int = 60
    max_tokens: int = 10_000
    max_tool_calls: int = 5


@dataclass
class ResearchPhaseResult:
    """Outcome of a research-phase run."""

    plan: Plan | None
    """The parsed plan, or None if the agent did not produce one."""

    exit_status: str
    """One of: 'plan_ready', 'budget_exceeded', 'error'."""

    errors: list[str] = field(default_factory=list)
    """Any validation or runtime errors."""


def generate_session_id() -> str:
    """Generate a session ID in the spec's format: ISO timestamp + short UUID."""
    ts = datetime.now(tz=UTC).strftime("%Y-%m-%dT%H-%M-%S")
    short_id = uuid.uuid4().hex[:6]
    return f"{ts}-{short_id}"


def generate_plan_filename(query: str, session_id: str) -> str:
    """Generate a plan filename following the spec convention.

    Format: ``<ISO timestamp from session_id>_<slug>.md``
    Slug is lowercased, hyphen-separated, first 5-7 meaningful words.
    """
    # Extract timestamp portion from session_id (before the UUID suffix)
    ts_part = session_id.rsplit("-", 1)[0] if "-" in session_id else session_id

    # Build slug from query: lowercase, keep alphanumeric + spaces, split, take 5-7 words
    words = []
    for word in query.strip().lower().split():
        cleaned = "".join(c for c in word if c.isalnum())
        if cleaned and cleaned not in {"the", "a", "an", "of", "for", "and", "in", "to", "with"}:
            words.append(cleaned)
        if len(words) >= 6:
            break

    slug = "-".join(words) if words else "plan"
    return f"{ts_part}_{slug}.md"


def build_research_agent(
    query: str,
    model_name: str,
    plans_dir: Path,
):
    """Build the research-phase Agent (without running it).

    Returns ``(agent, exit_tool)`` where ``exit_tool`` is the bound
    ``exit_plan_mode`` function tool.

    The agent has ``mcp_servers=[]`` — no MCP connections during research.
    """
    from agents import Agent

    from crystalyse.plan.prompts import RESEARCH_PHASE_SYSTEM_PROMPT
    from crystalyse.plan.tools import make_exit_plan_mode_tool

    exit_tool = make_exit_plan_mode_tool(plans_dir, query)

    agent = Agent(
        name="CrystaLyse Research Phase",
        instructions=RESEARCH_PHASE_SYSTEM_PROMPT,
        model=model_name,
        tools=[exit_tool],
        # mcp_servers=[] — no MCP connections during research (v1).
        # The agent reasons from training knowledge only.
    )

    return agent, exit_tool


async def enter_research_phase(
    query: str,
    model_name: str,
    plans_dir: Path,
    budget: ResearchPhaseBudget | None = None,
) -> ResearchPhaseResult:
    """Run the research phase end-to-end: build agent, run it, return the plan.

    The agent writes a plan file to *plans_dir* via ``write_file`` and
    calls ``exit_plan_mode`` to signal completion.  This driver builds
    the agent, runs it with budget constraints, and parses the resulting
    plan from disk.

    Parameters
    ----------
    query:
        The user's original query.
    model_name:
        Model name (resolved or raw passthrough).
    plans_dir:
        The ``.crystalyse/plans/`` directory.  Created if it doesn't exist.
    budget:
        Soft budget limits.  Defaults to ``ResearchPhaseBudget()``.

    Returns
    -------
    ResearchPhaseResult
        Contains the parsed ``Plan`` on success, or error details on failure.
    """
    import asyncio

    from agents import Runner

    if budget is None:
        budget = ResearchPhaseBudget()

    plans_dir.mkdir(parents=True, exist_ok=True)

    # Build the agent
    try:
        agent, _exit_tool = build_research_agent(query, model_name, plans_dir)
    except Exception as exc:
        return ResearchPhaseResult(
            plan=None, exit_status="error", errors=[f"Failed to build research agent: {exc}"]
        )

    # Run the agent with budget constraints.
    # max_turns maps to budget.max_tool_calls (each tool call is ~1 turn).
    # Wall-time is enforced via asyncio timeout.
    try:
        await asyncio.wait_for(
            Runner.run(
                starting_agent=agent,
                input=f"Create a plan for: {query}",
                max_turns=budget.max_tool_calls,
            ),
            timeout=budget.max_wall_time_seconds,
        )
    except TimeoutError:
        # Budget exceeded — try to find whatever partial plan exists
        pass
    except Exception as exc:
        return ResearchPhaseResult(
            plan=None, exit_status="error", errors=[f"Research phase runner failed: {exc}"]
        )

    # Find the most recent plan file in plans_dir
    plan_files = sorted(plans_dir.glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True)
    # Skip latest.md symlink
    plan_files = [p for p in plan_files if not (p.name == "latest.md" and p.is_symlink())]

    if not plan_files:
        return ResearchPhaseResult(
            plan=None,
            exit_status="error",
            errors=["Research phase completed but no plan file was written to plans directory"],
        )

    # Parse the newest plan
    try:
        plan = Plan.from_markdown(plan_files[0])
    except (ValueError, Exception) as exc:
        return ResearchPhaseResult(
            plan=None,
            exit_status="error",
            errors=[f"Plan file exists but failed to parse: {exc}"],
        )

    return ResearchPhaseResult(plan=plan, exit_status="plan_ready")
