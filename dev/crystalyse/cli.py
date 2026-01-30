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

# Sessions subcommand group
sessions_app = typer.Typer(help="Manage saved chat sessions.")
app.add_typer(sessions_app, name="sessions")

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
        False,
        "--rigorous",
        "-r",
        help="Use rigorous mode (gpt-5.2 model, slower but more thorough).",
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
    session_id: str | None = typer.Option(
        None, "--session-id", "-s", help="Resume existing session by ID."
    ),
    new_session: bool = typer.Option(False, "--new", help="Start fresh session (ignore last)."),
):
    """
    Start an interactive chat session for materials discovery.

    Use --rigorous for thorough analysis mode.
    Sessions are automatically persisted. Use --new to start fresh.
    """
    import uuid

    effective_rigorous = rigorous or state["rigorous"]
    effective_project = project or state["project"]

    # Session ID logic: explicit > resume last > generate new
    if new_session:
        effective_session_id = str(uuid.uuid4())[:8]
        console.print(f"[dim]New session: {effective_session_id}[/dim]")
    elif session_id:
        effective_session_id = session_id
        console.print(f"[dim]Resuming session: {effective_session_id}[/dim]")
    else:
        # Try to resume last session, or create new
        from crystalyse.memory.session import list_sessions

        sessions = list_sessions(limit=1)
        if sessions:
            effective_session_id = sessions[0].session_id
            console.print(f"[dim]Resuming last session: {effective_session_id}[/dim]")
        else:
            effective_session_id = str(uuid.uuid4())[:8]
            console.print(f"[dim]New session: {effective_session_id}[/dim]")

    mode_str = "rigorous" if effective_rigorous else "creative"

    console.print(
        Panel(
            f"[bold]CrystaLyse Interactive Session[/bold]\n\n"
            f"Mode: [cyan]{mode_str}[/cyan]\n"
            f"Project: [cyan]{effective_project}[/cyan]\n"
            f"Session: [cyan]{effective_session_id}[/cyan]\n\n"
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

        return await agent.query(q, session_id=effective_session_id)

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
def tui(
    rigorous: bool = typer.Option(
        False, "--rigorous", "-r", help="Use rigorous mode for all queries."
    ),
    session_id: str | None = typer.Option(
        None, "--session-id", "-s", help="Resume existing session by ID."
    ),
):
    """
    Launch the Terminal User Interface (TUI).

    Provides a rich terminal interface for interactive materials discovery
    with scrollable chat history, keyboard shortcuts, and streaming responses.

    Requires: pip install crystalyse[tui]
    """
    try:
        from crystalyse.tui import run_tui

        effective_rigorous = rigorous or state["rigorous"]
        run_tui(rigorous=effective_rigorous, session_id=session_id)
    except ImportError as e:
        console.print("[red]TUI requires textual library.[/red]")
        console.print("[dim]Install with: pip install crystalyse[tui][/dim]")
        console.print(f"[dim]Error: {e}[/dim]")
        raise typer.Exit(code=1) from None


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
    edit: bool = typer.Option(False, "--edit", help="Edit user preferences in $EDITOR"),
    path: bool = typer.Option(False, "--path", help="Show path to config file"),
    init: bool = typer.Option(False, "--init", help="Create default config file"),
):
    """Show, validate, or edit configuration.

    Examples:
        crystalyse config --show        Show current settings
        crystalyse config --path        Show config file path
        crystalyse config --edit        Edit config in $EDITOR
        crystalyse config --init        Create default config file
        crystalyse config --validate    Check environment setup
    """
    from crystalyse.user_config.preferences import (
        DEFAULT_CONFIG_PATH,
        get_default_config_template,
        load_preferences,
    )

    cfg = Config.load()

    if path:
        console.print(str(DEFAULT_CONFIG_PATH))
        return

    if init:
        if DEFAULT_CONFIG_PATH.exists():
            if not Confirm.ask(f"Overwrite existing {DEFAULT_CONFIG_PATH}?", default=False):
                console.print("[yellow]Cancelled.[/yellow]")
                return
        DEFAULT_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        DEFAULT_CONFIG_PATH.write_text(get_default_config_template())
        console.print(f"[green]Created config at: {DEFAULT_CONFIG_PATH}[/green]")
        return

    if edit:
        import os

        editor = os.environ.get("EDITOR", os.environ.get("VISUAL", ""))
        if not editor:
            console.print("[yellow]No $EDITOR set.[/yellow]")
            console.print(f"[dim]Config file: {DEFAULT_CONFIG_PATH}[/dim]")
            console.print("[dim]Set $EDITOR environment variable (e.g., export EDITOR=nano)[/dim]")
            return

        # Create default config if it doesn't exist
        if not DEFAULT_CONFIG_PATH.exists():
            DEFAULT_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
            DEFAULT_CONFIG_PATH.write_text(get_default_config_template())
            console.print(f"[dim]Created default config at {DEFAULT_CONFIG_PATH}[/dim]")

        os.system(f"{editor} {DEFAULT_CONFIG_PATH}")
        console.print("[green]Config file edited.[/green]")
        return

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
        return

    if show:
        from crystalyse.config import CREATIVE_MODEL, RIGOROUS_MODEL

        prefs = load_preferences()
        config_exists = DEFAULT_CONFIG_PATH.exists()

        console.print(
            Panel(
                f"[bold]Models[/bold]\n"
                f"  Creative: [cyan]{CREATIVE_MODEL}[/cyan]\n"
                f"  Rigorous: [cyan]{RIGOROUS_MODEL}[/cyan]\n\n"
                f"[bold]User Preferences[/bold] "
                f"[{'green' if config_exists else 'yellow'}]"
                f"({'loaded' if config_exists else 'using defaults'})[/]\n"
                f"  Default Mode: [cyan]{prefs.analysis.default_mode}[/cyan]\n"
                f"  Batch Size: [cyan]{prefs.analysis.parallel_batch_size}[/cyan]\n"
                f"  Max Candidates: [cyan]{prefs.analysis.max_candidates}[/cyan]\n"
                f"  Verbosity: [cyan]{prefs.display.verbosity}[/cyan]\n"
                f"  HTML Viz: [cyan]{prefs.display.enable_html_viz}[/cyan]\n"
                f"  Skill Timeout: [cyan]{prefs.skills.script_timeout_secs}s[/cyan]\n\n"
                f"[bold]Paths[/bold]\n"
                f"  Config File: [dim]{DEFAULT_CONFIG_PATH}[/dim]\n"
                f"  Base Dir: [dim]{cfg.base_dir}[/dim]\n\n"
                f"[bold]API[/bold]\n"
                f"  Key Set: [{'green' if cfg.openai_api_key else 'red'}]"
                f"{'Yes' if cfg.openai_api_key else 'No'}[/]",
                title="[bold]Configuration[/bold]",
                border_style="cyan",
            )
        )
        return

    # Default: show help
    console.print("Configuration commands:")
    console.print("  --show      Show current settings")
    console.print("  --path      Show config file path")
    console.print("  --edit      Edit config in $EDITOR")
    console.print("  --init      Create default config file")
    console.print("  --validate  Check environment setup")


# --- Sessions Subcommands ---


@sessions_app.command("list")
def sessions_list():
    """List all saved sessions."""
    from crystalyse.memory.session import list_sessions

    sessions = list_sessions()
    if not sessions:
        console.print("[yellow]No saved sessions found.[/yellow]")
        console.print("[dim]Start a chat to create your first session.[/dim]")
        return

    console.print(Panel("[bold]Saved Sessions[/bold]", border_style="cyan"))
    for s in sessions:
        updated = s.last_updated[:16] if s.last_updated else "unknown"
        console.print(
            f"  [cyan]{s.session_id}[/cyan]  {s.message_count} msgs  [dim]{updated}[/dim]"
        )


@sessions_app.command("delete")
def sessions_delete(
    session_id: str = typer.Argument(..., help="Session ID to delete"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
):
    """Delete a saved session."""
    from crystalyse.memory.session import delete_session

    if not force:
        if not Confirm.ask(f"Delete session {session_id}?", default=False):
            console.print("[yellow]Cancelled.[/yellow]")
            return

    if delete_session(session_id):
        console.print(f"[green]Deleted session: {session_id}[/green]")
    else:
        console.print(f"[red]Session not found: {session_id}[/red]")


@sessions_app.command("show")
def sessions_show(
    session_id: str = typer.Argument(..., help="Session ID to show"),
):
    """Show conversation history for a session."""
    import asyncio

    from crystalyse.memory.session import get_session

    session = get_session(session_id)
    items = asyncio.run(session.get_items())

    if not items:
        console.print(f"[yellow]No messages in session: {session_id}[/yellow]")
        return

    console.print(Panel(f"[bold]Session: {session_id}[/bold]", border_style="cyan"))
    for item in items:
        role = item.get("role", "unknown")
        content = str(item.get("content", ""))[:200]
        color = "blue" if role == "user" else "green"
        console.print(f"  [{color}]{role}[/{color}]: {content}")


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
