"""
Crystalyse -- Intelligent Scientific Agent for Materials Design

This CLI uses a skills-based architecture with two modes:
- Creative (default): Fast exploration using gpt-5-mini
- Rigorous (--rigorous): Thorough analysis using gpt-5.2
"""

import asyncio
import logging
import sys
import warnings
from pathlib import Path

# Suppress specific e3nn warning about weights_only parameter
warnings.filterwarnings(
    "ignore", category=UserWarning, module="e3nn", message=".*TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD.*"
)

import typer
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm
from rich.text import Text

from crystalyse.agents.agent import MaterialsAgent
from crystalyse.config import Config
from crystalyse.ui.clarification import ClarificationSystem

# --- Setup ---
app = typer.Typer(
    name="crystalyse",
    help="Crystalyse -- Intelligent Scientific Agent for Materials Design",
    add_completion=False,
    no_args_is_help=True,
    rich_markup_mode="rich",
)
console = Console()
logger = logging.getLogger(__name__)


# --- State for global options ---
state = {
    "project": "crystalyse_session",
    "rigorous": False,
    "verbose": False,
}


# --- Approval System (Safety Gate) ---
def approval_callback(path: Path, content: str) -> bool:
    """Presents a file write operation to the user for approval."""
    console.print("\n")
    preview = content[:400] + "..." if len(content) > 400 else content

    panel = Panel(
        Text(preview, overflow="fold"),
        title="[bold yellow]Approval Required[/bold yellow]",
        subtitle=f"About to write {len(content)} bytes to [cyan]{path.relative_to(Path.cwd())}[/cyan]",
        border_style="yellow",
    )
    console.print(panel)

    return Confirm.ask("Do you approve this file write operation?", default=True)


# --- Helper Functions ---
def display_results(results: dict):
    """Display final results in a structured format."""
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
    mode = results.get("mode", "creative")
    model = results.get("model", "unknown")

    console.print(
        Panel(
            response,
            title=f"[bold green]Discovery Report[/bold green] [dim]({mode} mode, {model})[/dim]",
            border_style="green",
        )
    )


# --- Typer Commands ---


@app.command()
def analyse(
    query: str = typer.Argument(..., help="A materials discovery query."),
    rigorous: bool = typer.Option(
        False, "--rigorous", "-r", help="Use rigorous mode (gpt-5.2 model, slower but more thorough)."
    ),
    project: str | None = typer.Option(None, "--project", "-p", help="Project name for workspace."),
    clarify: bool = typer.Option(
        True, "--clarify/--no-clarify", help="Ask clarifying questions for ambiguous queries."
    ),
):
    """
    Run a materials discovery query.

    By default, uses creative mode (gpt-5-mini) for fast exploration.
    Use --rigorous for thorough analysis with the gpt-5.2 model.

    Examples:
        crystalyse analyse "Find stable perovskites"
        crystalyse analyse "Predict Li-ion cathodes" --rigorous
        crystalyse analyse "Quick test" --no-clarify
    """
    effective_rigorous = rigorous or state["rigorous"]
    effective_project = project or state["project"]

    mode_str = "rigorous" if effective_rigorous else "creative"
    console.print(f"[cyan]Starting discovery:[/cyan] {query}")
    console.print(f"[dim]Mode: {mode_str} | Project: {effective_project}[/dim]\n")

    # Handle clarification
    if clarify:
        clarification = ClarificationSystem(console)
        if clarification.needs_clarification(query):
            result = clarification.clarify(query)
            if not result.skipped:
                # Enhance query with clarification answers
                answers_str = ", ".join(f"{k}={v}" for k, v in result.answers.items())
                query = f"{query} (Context: {answers_str})"

    async def _run():
        agent = MaterialsAgent(
            rigorous=effective_rigorous,
            project_name=effective_project,
        )

        results = await agent.query(query)

        if results:
            display_results(results)

    asyncio.run(_run())


# Alias for backwards compatibility
discover = analyse


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
        console.print(f"[green]Phase diagram data ready at:[/green] {path}")
    except Exception as e:
        console.print(f"[red]Failed to setup data:[/red] {e}")
        raise typer.Exit(code=1) from None


@app.command()
def chat(
    rigorous: bool = typer.Option(
        False, "--rigorous", "-r", help="Use rigorous mode for all queries in this session."
    ),
    project: str | None = typer.Option(None, "--project", "-p", help="Project name for workspace."),
):
    """
    Start an interactive chat session for materials discovery.

    Use --rigorous for thorough analysis mode.
    """
    effective_rigorous = rigorous or state["rigorous"]
    effective_project = project or state["project"]

    mode_str = "rigorous" if effective_rigorous else "creative"

    console.print(
        Panel(
            f"[bold]CrystaLyse Interactive Session[/bold]\n\n"
            f"Mode: [cyan]{mode_str}[/cyan]\n"
            f"Project: [cyan]{effective_project}[/cyan]\n\n"
            "Type your query and press Enter. Type 'quit' or 'exit' to end.\n"
            "Use '/rigorous' to toggle rigorous mode.",
            title="[bold green]CrystaLyse v2.0[/bold green]",
            border_style="green",
        )
    )

    agent = None
    current_rigorous = effective_rigorous

    async def run_query(q: str, rig: bool):
        nonlocal agent
        # Create new agent if mode changed or not initialized
        if agent is None or agent.rigorous != rig:
            agent = MaterialsAgent(
                rigorous=rig,
                project_name=effective_project,
            )

        return await agent.query(q)

    clarification = ClarificationSystem(console)

    try:
        while True:
            try:
                query = console.input("[bold blue]You:[/bold blue] ")
            except EOFError:
                break

            query = query.strip()

            if not query:
                continue

            if query.lower() in ("quit", "exit", "q"):
                console.print("[cyan]Ending session.[/cyan]")
                break

            # Toggle rigorous mode
            if query.lower() == "/rigorous":
                current_rigorous = not current_rigorous
                mode_str = "rigorous" if current_rigorous else "creative"
                console.print(f"[yellow]Switched to {mode_str} mode.[/yellow]")
                agent = None  # Force recreation
                continue

            if query.startswith("/"):
                console.print(f"[yellow]Unknown command: {query}[/yellow]")
                continue

            # Clarification
            if clarification.needs_clarification(query):
                result = clarification.clarify(query)
                if not result.skipped:
                    answers_str = ", ".join(f"{k}={v}" for k, v in result.answers.items())
                    query = f"{query} (Context: {answers_str})"

            # Run the query
            try:
                results = asyncio.run(run_query(query, current_rigorous))
                if results:
                    display_results(results)
            except KeyboardInterrupt:
                console.print("\n[yellow]Query interrupted.[/yellow]")
                continue

    except KeyboardInterrupt:
        console.print("\n[cyan]Session ended by user.[/cyan]")


@app.command()
def skills():
    """List all available skills and their scripts."""
    from crystalyse.skills.executor import get_available_skills

    available = get_available_skills()

    if not available:
        console.print("[yellow]No skills found.[/yellow]")
        console.print("[dim]Skills should be in the dev/skills/ directory.[/dim]")
        return

    console.print(
        Panel(
            "[bold]Available Skills[/bold]",
            border_style="cyan",
        )
    )

    for skill_name, scripts in available.items():
        scripts_str = ", ".join(scripts)
        console.print(f"  [cyan]{skill_name}[/cyan]: {scripts_str}")


@app.command()
def config(
    show: bool = typer.Option(False, "--show", help="Show current configuration"),
    validate: bool = typer.Option(False, "--validate", help="Validate environment"),
):
    """Show or validate configuration."""
    cfg = Config.load()

    if validate:
        status = cfg.validate_environment()
        console.print(
            Panel(
                f"Overall: [{'green' if status['overall'] == 'healthy' else 'yellow'}]{status['overall']}[/]\n\n"
                f"Dependencies:\n"
                + "\n".join(
                    f"  {k}: [{'green' if v else 'red'}]{v}[/]"
                    for k, v in status["dependencies"].items()
                )
                + "\n\nSkills:\n"
                + f"  Directory: {status['skills'].get('directory', 'Not found')}\n"
                + f"  Count: {status['skills'].get('count', 0)}",
                title="[bold]Environment Status[/bold]",
                border_style="cyan",
            )
        )
    elif show:
        from crystalyse.config import CREATIVE_MODEL, RIGOROUS_MODEL

        console.print(
            Panel(
                f"Creative Model: [cyan]{CREATIVE_MODEL}[/cyan]\n"
                f"Rigorous Model: [cyan]{RIGOROUS_MODEL}[/cyan]\n"
                f"Base Directory: [dim]{cfg.base_dir}[/dim]\n"
                f"API Key Set: [{'green' if cfg.openai_api_key else 'red'}]"
                f"{'Yes' if cfg.openai_api_key else 'No'}[/]",
                title="[bold]Configuration[/bold]",
                border_style="cyan",
            )
        )
    else:
        console.print("Use --show to display configuration or --validate to check environment.")


@app.callback()
def main_callback(
    ctx: typer.Context,
    project: str = typer.Option(
        "crystalyse_session", "-p", "--project", help="Project name for workspace."
    ),
    rigorous: bool = typer.Option(
        False, "--rigorous", "-r", help="Use rigorous mode (gpt-5.2 model, thorough analysis)."
    ),
    version: bool | None = typer.Option(
        None,
        "--version",
        help="Show version and exit.",
        callback=lambda v: (console.print("Crystalyse v2.0.0-dev"), exit(0)) if v else None,
        is_eager=True,
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose output"),
):
    """
    Crystalyse v2.0.0-dev - Intelligent Scientific AI Agent for Inorganic Materials Design

    Two modes:
    - Creative (default): Fast exploration with gpt-5-mini
    - Rigorous (--rigorous): Thorough analysis with gpt-5.2
    """
    state["project"] = project
    state["rigorous"] = rigorous
    state["verbose"] = verbose

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
        console.print(f"\n[red]An unexpected error occurred: {e}[/red]")
        console.print("[dim]Check crystalyse.log for details.[/dim]")
        sys.exit(1)


if __name__ == "__main__":
    run()
