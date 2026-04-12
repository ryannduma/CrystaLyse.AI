"""
Crystalyse v1.0.0-dev - Intelligent Scientific AI Agent for Inorganic Materials Design
"""

import asyncio
import logging
import sys
import warnings
from pathlib import Path

# Suppress specific e3nn warning about weights_only parameter
# This is a known issue with e3nn not explicitly passing weights_only to torch.load()
warnings.filterwarnings(
    "ignore", category=UserWarning, module="e3nn", message=".*TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD.*"
)

# Add provenance_system to path for installed package
# This ensures provenance works when using 'crystalyse' command
# Need to add parent directory of provenance_system to sys.path
crystalyse_root = Path(__file__).parent.parent.parent
provenance_system_path = crystalyse_root / "provenance_system"
if provenance_system_path.exists() and str(crystalyse_root) not in sys.path:
    sys.path.insert(0, str(crystalyse_root))

import typer
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm
from rich.text import Text

from crystalyse.agents.openai_agents_bridge import EnhancedCrystaLyseAgent
from crystalyse.config import Config
from crystalyse.config.modes import MODE_ALIASES, Mode, resolve_mode_name
from crystalyse.ui.chat_ui import ChatExperience
from crystalyse.workspace import workspace_tools

# --- Setup ---
app = typer.Typer(
    name="crystalyse",
    help="Crystalyse v1.0.0-dev - Intelligent Scientific AI Agent for Inorganic Materials Design",
    add_completion=False,
    no_args_is_help=True,
    rich_markup_mode="rich",
)
console = Console()
logger = logging.getLogger(__name__)


# All accepted mode strings for CLI help text.
_VALID_MODE_STRINGS = sorted(MODE_ALIASES.keys())


# --- State for global options ---
state: dict = {
    "project": "crystalyse_session",
    "mode": Mode.AUTO,
    "model": None,
}


# --- Approval System (Safety Gate) ---
def approval_callback(path: Path, content: str) -> bool:
    """Presents a file write operation to the user for approval."""
    console.print("\n")
    preview = content[:400] + "..." if len(content) > 400 else content

    panel = Panel(
        Text(preview, overflow="fold"),
        title="[bold yellow]📝 Approval Required[/bold yellow]",
        subtitle=f"About to write {len(content)} bytes to [cyan]{path.relative_to(Path.cwd())}[/cyan]",
        border_style="yellow",
    )
    console.print(panel)

    return Confirm.ask("Do you approve this file write operation?", default=True)


# --- Helper Functions ---
def display_results(results: dict, show_provenance_summary: bool = True):
    """
    Display final results in a structured format.

    Args:
        results: Discovery results dictionary
        show_provenance_summary: Whether to display provenance summary table
    """
    if results.get("status") == "failed":
        console.print(
            Panel(
                f"[bold red]Error:[/bold red] {results.get('error', 'Unknown error')}",
                title="Discovery Failed",
                border_style="red",
            )
        )
        return

    # Display main response
    response = results.get("response", "No response from agent.")
    console.print(
        Panel(response, title="[bold green]Discovery Report[/bold green]", border_style="green")
    )

    # Display provenance summary if available and enabled
    if show_provenance_summary and "provenance" in results:
        display_provenance_summary(results["provenance"])


def display_provenance_summary(provenance: dict):
    """
    Display provenance summary in a formatted table.

    Args:
        provenance: Provenance dictionary from discovery results
    """
    from rich.table import Table

    summary = provenance.get("summary", {})

    # Create summary table
    table = Table(title="Provenance Summary", show_header=True, header_style="bold cyan")
    table.add_column("Metric", style="cyan", no_wrap=True)
    table.add_column("Value", style="yellow")

    # Add rows with available data
    table.add_row("Session ID", provenance.get("session_id", "N/A"))

    materials_found = summary.get("materials_found", 0)
    table.add_row("Materials Found", str(materials_found))

    materials_summary = summary.get("materials_summary", {})
    if materials_summary:
        with_energy = materials_summary.get("with_energy", 0)
        table.add_row("With Energy Data", str(with_energy))

        if materials_summary.get("min_energy") is not None:
            energy_range = f"{materials_summary['min_energy']:.3f} to {materials_summary['max_energy']:.3f} eV/atom"
            table.add_row("Energy Range", energy_range)

    runtime = summary.get("total_time_s", 0)
    table.add_row("Runtime", f"{runtime:.1f}s")

    mcp_tools = summary.get("mcp_tools", {})
    if mcp_tools:
        tools_list = ", ".join(mcp_tools.keys())
        table.add_row("MCP Tools Used", tools_list)

    if provenance.get("output_dir"):
        table.add_row("Output Location", provenance["output_dir"])

    console.print("\n")
    console.print(table)


# --- Typer Commands ---


@app.command()
def discover(
    query: str = typer.Argument(
        ..., help="A non-interactive, single-shot materials discovery query."
    ),
    provenance_dir: str | None = typer.Option(
        None,
        "--provenance-dir",
        help="Custom directory for provenance output (default: ./provenance_output)",
    ),
    hide_summary: bool = typer.Option(
        False, "--hide-summary", help="Hide provenance summary table (data still captured)"
    ),
    mode: str | None = typer.Option(
        None, "--mode", help="Agent operating mode (explore, validate, auto; or legacy: creative, rigorous, adaptive)."
    ),
    project: str | None = typer.Option(
        None, "--project", "-p", help="Project name for workspace (overrides global option)."
    ),
):
    """
    Run a single, non-interactive discovery query with automatic provenance capture.

    Provenance is always enabled - every query generates a complete audit trail
    including materials discovered, MCP tool calls, and performance metrics.

    Examples:
        crystalyse discover "Find stable perovskites"
        crystalyse discover "Predict Li-ion cathodes" --provenance-dir ./my_research
        crystalyse discover "Quick test" --hide-summary
        crystalyse discover "Analysis" --mode validate
    """
    # Determine effective mode and project (local overrides global)
    effective_mode = resolve_mode_name(mode) if mode is not None else state["mode"]
    effective_project = project if project is not None else state["project"]

    console.print(f"[cyan]Starting non-interactive discovery:[/cyan] {query}")
    console.print(f"[dim]Mode: {effective_mode.value} | Project: {effective_project}[/dim]\n")

    # Set up non-interactive handlers
    workspace_tools.APPROVAL_CALLBACK = approval_callback

    async def _run():
        # Load config and customise provenance settings if needed
        config = Config.load()
        if provenance_dir:
            config.provenance["output_dir"] = Path(provenance_dir)

        agent = EnhancedCrystaLyseAgent(
            config=config,
            project_name=effective_project,
            mode=effective_mode.value,
            model=state["model"],
        )

        # Discovery automatically creates provenance handler
        results = await agent.discover(query)

        if results:
            # Display results with optional provenance summary
            show_summary = config.provenance["show_summary"] and not hide_summary
            display_results(results, show_provenance_summary=show_summary)

    asyncio.run(_run())


@app.command()
def setup(
    force: bool = typer.Option(False, "--force", "-f", help="Force re-download of data files"),
):
    """
    Download and set up required data files (e.g., phase diagrams).
    """
    from crystalyse.tools.downloader import ensure_phase_diagram_data

    console.print("[cyan]Setting up Crystalyse data files...[/cyan]")
    try:
        path = ensure_phase_diagram_data(force=force)
        console.print(f"[green]✓ Phase diagram data ready at:[/green] {path}")
    except Exception as e:
        console.print(f"[red]✗ Failed to setup data:[/red] {e}")
        raise typer.Exit(code=1) from None


@app.command()
def chat(
    user: str = typer.Option("default", "--user", "-u", help="User ID for personalized experience"),
    session: str | None = typer.Option(
        None, "--session", "-s", help="Session name for organization"
    ),
):
    """
    Start an interactive chat session for materials discovery.

    Features:
    • Mode switching and smart defaults
    • Provenance-tracked tool calls
    """
    workspace_tools.APPROVAL_CALLBACK = approval_callback

    # Create chat experience
    chat_experience = ChatExperience(
        project=state["project"] + (f"_{session}" if session else ""),
        mode=state["mode"].value,
        model=state["model"],
        user_id=user,
    )

    try:
        asyncio.run(chat_experience.run_loop())
    except KeyboardInterrupt:
        console.print("\n[cyan]Session ended by user.[/cyan]")


@app.command(name="analyse-provenance")
def analyse_provenance(
    session_id: str | None = typer.Option(None, "--session", help="Specific session ID to analyse"),
    latest: bool = typer.Option(False, "--latest", help="Analyse the most recent session"),
    provenance_dir: str = typer.Option(
        "./provenance_output", "--dir", help="Provenance directory to search"
    ),
):
    """
    Analyse provenance data from previous discovery sessions.

    Examples:
        crystalyse analyse-provenance --latest
        crystalyse analyse-provenance --session crystalyse_creative_20250910_120000
        crystalyse analyse-provenance --dir ./my_research/provenance
    """
    import json

    from rich.table import Table

    base_dir = Path(provenance_dir) / "runs"

    # Check if provenance directory exists
    if not base_dir.exists():
        console.print(f"[red]Provenance directory not found: {base_dir}[/red]")
        console.print("[dim]Run a discovery query first to generate provenance data.[/dim]")
        return

    # Find session to analyse
    if latest:
        sessions = sorted(base_dir.glob("*"), key=lambda p: p.stat().st_mtime, reverse=True)
        if not sessions:
            console.print("[red]No provenance sessions found[/red]")
            return
        session_dir = sessions[0]
    elif session_id:
        session_dir = base_dir / session_id
        if not session_dir.exists():
            console.print(f"[red]Session '{session_id}' not found[/red]")
            return
    else:
        # List available sessions
        sessions = sorted(base_dir.glob("*"), key=lambda p: p.stat().st_mtime, reverse=True)
        if not sessions:
            console.print("[red]No provenance sessions found[/red]")
            return

        table = Table(title="Available Provenance Sessions")
        table.add_column("Session ID", style="cyan", no_wrap=True)
        table.add_column("Timestamp", style="yellow")
        table.add_column("Materials", style="green")

        for session in sessions[:10]:  # Show last 10
            summary_file = session / "summary.json"
            if summary_file.exists():
                with open(summary_file) as f:
                    summary = json.load(f)
                    table.add_row(
                        session.name,
                        summary.get("timestamp", "N/A")[:19],  # Trim to datetime
                        str(summary.get("materials_found", 0)),
                    )

        console.print(table)
        console.print("\n[dim]Use --latest or --session <id> to analyse a specific session[/dim]")
        return

    # Analyse the selected session
    console.print(Panel(f"[bold]Analysing Session:[/bold] {session_dir.name}", border_style="cyan"))

    # Load summary
    summary_file = session_dir / "summary.json"
    if not summary_file.exists():
        console.print("[red]Summary file not found for this session[/red]")
        return

    with open(summary_file) as f:
        summary = json.load(f)

    # Display performance metrics
    console.print("\n[bold]Performance Metrics:[/bold]")
    perf_table = Table(show_header=False)
    perf_table.add_column("Metric", style="cyan")
    perf_table.add_column("Value", style="yellow")

    perf_table.add_row("Total Runtime", f"{summary.get('total_time_s', 0):.2f}s")
    if summary.get("ttfb_ms"):
        perf_table.add_row("Time to First Byte", f"{summary['ttfb_ms']:.0f}ms")
    perf_table.add_row("Total Tool Calls", str(summary.get("tool_calls_total", 0)))

    console.print(perf_table)

    # Display materials summary
    mat_summary = summary.get("materials_summary", {})
    if mat_summary:
        console.print("\n[bold]Materials Summary:[/bold]")
        mat_table = Table(show_header=False)
        mat_table.add_column("Metric", style="cyan")
        mat_table.add_column("Value", style="green")

        mat_table.add_row("Total Found", str(mat_summary.get("total", 0)))
        mat_table.add_row("With Energy Data", str(mat_summary.get("with_energy", 0)))

        if mat_summary.get("min_energy") is not None:
            mat_table.add_row(
                "Energy Range",
                f"{mat_summary['min_energy']:.3f} to {mat_summary['max_energy']:.3f} eV/atom",
            )
            mat_table.add_row("Average Energy", f"{mat_summary['avg_energy']:.3f} eV/atom")

        console.print(mat_table)

    # Display MCP tools usage
    mcp_tools = summary.get("mcp_tools", {})
    if mcp_tools:
        console.print("\n[bold]MCP Tools Used:[/bold]")
        for tool_name, stats in mcp_tools.items():
            tool_panel = Panel(
                f"Calls: {stats['count']}\n"
                f"Average Time: {stats.get('avg_ms', 0):.1f}ms\n"
                f"Materials Generated: {stats.get('materials', 0)}",
                title=f"[bold]{tool_name}[/bold]",
                border_style="blue",
            )
            console.print(tool_panel)

    # Display materials catalogue if available
    materials_file = session_dir / "materials_catalog.json"
    if materials_file.exists():
        with open(materials_file) as f:
            materials = json.load(f)

        if materials:
            console.print("\n[bold]Top Materials (by formation energy):[/bold]")

            # Sort by energy if available
            sorted_materials = sorted(
                [m for m in materials if m.get("formation_energy") is not None],
                key=lambda x: x["formation_energy"],
            )

            for i, mat in enumerate(sorted_materials[:5], 1):
                console.print(
                    f"  {i}. [cyan]{mat['composition']}[/cyan]: "
                    f"[yellow]{mat['formation_energy']:.3f} eV/atom[/yellow]"
                )
                if mat.get("space_group"):
                    console.print(f"     Space Group: {mat['space_group']}")

    # Show file locations
    console.print(f"\n[dim]Session files located at: {session_dir}[/dim]")


@app.callback()
def main_callback(
    ctx: typer.Context,
    project: str = typer.Option(
        "crystalyse_session", "-p", "--project", help="Project name for workspace."
    ),
    mode: str = typer.Option(
        "auto", "--mode", help="Agent operating mode (explore, validate, auto).", case_sensitive=False
    ),
    model: str | None = typer.Option(None, "--model", help="Language model to use."),
    version: bool | None = typer.Option(
        None,
        "--version",
        help="Show version and exit.",
        callback=lambda v: (console.print("Crystalyse v1.0.0-dev"), exit(0)) if v else None,
        is_eager=True,
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose output"),
):
    """
    Crystalyse v1.0.0-dev - Intelligent Scientific AI Agent for Inorganic Materials Design
    """
    state["project"] = project
    state["mode"] = resolve_mode_name(mode)
    state["model"] = model

    # Configure logging
    if verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.WARNING)


def main():
    """Main entry point for crystalyse command."""
    run()


def run():
    """Main entry point."""
    # Setup logging
    logging.basicConfig(
        level=logging.WARNING,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.FileHandler("crystalyse.log")],
    )

    # If no arguments or no command specified, insert 'chat' as default command
    if len(sys.argv) == 1:
        sys.argv.append("chat")

    try:
        app()
    except KeyboardInterrupt:
        console.print("\n[cyan]Crystalyse session ended.[/cyan]")
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        console.print(f"\n[red]❌ An unexpected error occurred: {e}[/red]")
        console.print("[dim]Check crystalyse.log for details.[/dim]")
        sys.exit(1)


if __name__ == "__main__":
    run()
