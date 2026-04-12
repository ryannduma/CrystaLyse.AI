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
