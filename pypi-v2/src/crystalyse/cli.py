
"""
CrystaLyse.AI 2.0 - Enhanced Materials Discovery
"""

import asyncio
import logging
import sys
import warnings
from typing import Optional
from enum import Enum
from pathlib import Path

# Suppress specific e3nn warning about weights_only parameter
# This is a known issue with e3nn not explicitly passing weights_only to torch.load()
warnings.filterwarnings('ignore', category=UserWarning, module='e3nn',
                       message='.*TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD.*')

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
from rich.text import Text
from rich.prompt import Confirm

from crystalyse.config import Config
from crystalyse.agents.openai_agents_bridge import EnhancedCrystaLyseAgent
from crystalyse.workspace import workspace_tools
from crystalyse.ui.progress import PhaseAwareProgress
from crystalyse.ui.chat_ui import ChatExperience
from crystalyse.ui.enhanced_clarification import IntegratedClarificationSystem

# --- Setup ---
app = typer.Typer(
    name="crystalyse",
    help="CrystaLyse.AI 2.0 - Enhanced Materials Discovery",
    add_completion=False,
    no_args_is_help=True,
    rich_markup_mode="rich",
)
console = Console()
logger = logging.getLogger(__name__)

# --- Type Enums for CLI choices ---
class AgentMode(str, Enum):
    creative = "creative"
    rigorous = "rigorous"
    adaptive = "adaptive"

# --- State for global options ---
state = {
    "project": "crystalyse_session",
    "mode": AgentMode.adaptive,
    "model": None,
    "query": "",
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
        border_style="yellow"
    )
    console.print(panel)
    
    return Confirm.ask("Do you approve this file write operation?", default=True)

# --- Non-Interactive Clarification Handler ---
async def non_interactive_clarification(request: workspace_tools.ClarificationRequest) -> dict:
    """
    Handles clarification for non-interactive mode by making smart assumptions.
    """
    # Use the adaptive clarification system even in non-interactive mode
    system = IntegratedClarificationSystem(console, user_id="non_interactive")
    analysis = system._analyze_query(state["query"])
    
    # Check if we should skip clarification entirely (high-confidence queries)
    should_skip = await system._should_skip_clarification(analysis, request)
    
    if should_skip:
        # Skip clarification and return smart assumptions
        return await system._handle_high_confidence_skip(state["query"], request, analysis)
    
    # For non-expert queries, use the adaptive clarification system
    # but simulate responses for non-interactive mode
    if analysis.expertise_level == "novice":
        # Show educational guidance and make reasonable choices
        console.print(Panel(
            "🔎 Discovery Mode: I'll help you explore battery materials!\n\n"
            "Since this is non-interactive mode, I'm assuming you want:\n"
            "• General exploration of battery technologies\n"
            "• Focus on common, practical options\n"
            "• Earth-abundant materials (cost-effective)",
            title="[bold cyan]🎓 Educational Guidance[/bold cyan]",
            border_style="cyan"
        ))
        
        # Simulate guided discovery responses
        simulated_answers = {
            "approach_preference": "explore",
            "_mode": "creative",
            "_method": "guided_discovery_simulated",
            "_user_type": "novice"
        }
        
        # Fill in reasonable defaults for any specific questions
        for question in request.questions:
            if question.options:
                # Choose educational/accessible option
                if "Li-ion" in question.options:
                    simulated_answers[question.id] = "Li-ion"  # Most common
                elif "Cathode" in question.options:
                    simulated_answers[question.id] = "Cathode"  # Most common
                elif "High capacity" in question.options:
                    simulated_answers[question.id] = "High capacity"  # Good starting point
                else:
                    simulated_answers[question.id] = question.options[0]
            else:
                simulated_answers[question.id] = ""
        
        return simulated_answers
    
    # For intermediate/expert queries in non-interactive mode, use assumptions
    console.print("[dim]Making smart assumptions based on your technical query...[/dim]")
    
    # Generate assumptions without asking for confirmation
    assumptions = await system._generate_smart_assumptions(request.questions, analysis)
    suggested_mode = system._suggest_initial_mode(analysis)

    assumption_lines = "\n".join(
        f"• {q.text}: {assumptions.get(q.id, '[Not specified]')}" for q in request.questions
    )
    
    console.print(Panel(
        f"Based on the query, the following assumptions were made:\n{assumption_lines}"
        f"\n\n→ Proceeding with [bold]{suggested_mode}[/bold] mode.",
        title="[bold blue]🤖 Auto-Clarification[/bold blue]",
        border_style="blue"
    ))
    
    return {
        **assumptions,
        "_mode": suggested_mode,
        "_method": "assumed_in_non_interactive_mode",
    }

# --- Helper Functions ---
def display_results(results: dict, show_provenance_summary: bool = True):
    """
    Display final results in a structured format.

    Args:
        results: Discovery results dictionary
        show_provenance_summary: Whether to display provenance summary table
    """
    if results.get("status") == "failed":
        console.print(Panel(
            f"[bold red]Error:[/bold red] {results.get('error', 'Unknown error')}",
            title="Discovery Failed",
            border_style="red"
        ))
        return

    # Display main response
    response = results.get("response", "No response from agent.")
    console.print(Panel(
        response,
        title="[bold green]Discovery Report[/bold green]",
        border_style="green"
    ))

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
    query: str = typer.Argument(..., help="A non-interactive, single-shot materials discovery query."),
    provenance_dir: Optional[str] = typer.Option(
        None,
        "--provenance-dir",
        help="Custom directory for provenance output (default: ./provenance_output)"
    ),
    hide_summary: bool = typer.Option(
        False,
        "--hide-summary",
        help="Hide provenance summary table (data still captured)"
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
    """
    console.print(f"[cyan]Starting non-interactive discovery:[/cyan] {query}")
    console.print(f"[dim]Mode: {state['mode']} | Project: {state['project']}[/dim]\n")

    # Set up non-interactive handlers
    state["query"] = query
    workspace_tools.APPROVAL_CALLBACK = approval_callback
    workspace_tools.CLARIFICATION_CALLBACK = non_interactive_clarification

    async def _run():
        # Load config and customise provenance settings if needed
        config = Config.load()
        if provenance_dir:
            config.provenance['output_dir'] = Path(provenance_dir)

        agent = EnhancedCrystaLyseAgent(
            config=config,
            project_name=state['project'],
            mode=state['mode'].value,
            model=state['model'],
        )

        # Discovery automatically creates provenance handler
        results = await agent.discover(query)

        if results:
            # Display results with optional provenance summary
            show_summary = config.provenance['show_summary'] and not hide_summary
            display_results(results, show_provenance_summary=show_summary)

    asyncio.run(_run())

@app.command()
def chat(
    user: str = typer.Option("default", "--user", "-u", help="User ID for personalized experience"),
    session: Optional[str] = typer.Option(None, "--session", "-s", help="Session name for organization"),
):
    """
    Start an interactive chat session for materials discovery.
    
    Features:
    • Adaptive clarification based on expertise level  
    • Cross-session learning and personalization
    • Mode switching and smart defaults
    """
    workspace_tools.APPROVAL_CALLBACK = approval_callback
    
    # Create chat experience
    chat_experience = ChatExperience(
        project=state['project'] + (f"_{session}" if session else ""),
        mode=state['mode'].value,
        model=state['model'],
        user_id=user
    )
    
    try:
        asyncio.run(chat_experience.run_loop())
    except KeyboardInterrupt:
        console.print(f"\n[cyan]Session ended by user.[/cyan]")


@app.command(name="analyse-provenance")
def analyse_provenance(
    session_id: Optional[str] = typer.Option(None, "--session", help="Specific session ID to analyse"),
    latest: bool = typer.Option(False, "--latest", help="Analyse the most recent session"),
    provenance_dir: str = typer.Option("./provenance_output", "--dir", help="Provenance directory to search"),
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
                        str(summary.get("materials_found", 0))
                    )

        console.print(table)
        console.print("\n[dim]Use --latest or --session <id> to analyse a specific session[/dim]")
        return

    # Analyse the selected session
    console.print(Panel(
        f"[bold]Analysing Session:[/bold] {session_dir.name}",
        border_style="cyan"
    ))

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
    if summary.get('ttfb_ms'):
        perf_table.add_row("Time to First Byte", f"{summary['ttfb_ms']:.0f}ms")
    perf_table.add_row("Total Tool Calls", str(summary.get('tool_calls_total', 0)))

    console.print(perf_table)

    # Display materials summary
    mat_summary = summary.get("materials_summary", {})
    if mat_summary:
        console.print("\n[bold]Materials Summary:[/bold]")
        mat_table = Table(show_header=False)
        mat_table.add_column("Metric", style="cyan")
        mat_table.add_column("Value", style="green")

        mat_table.add_row("Total Found", str(mat_summary.get('total', 0)))
        mat_table.add_row("With Energy Data", str(mat_summary.get('with_energy', 0)))

        if mat_summary.get('min_energy') is not None:
            mat_table.add_row("Energy Range",
                            f"{mat_summary['min_energy']:.3f} to {mat_summary['max_energy']:.3f} eV/atom")
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
                border_style="blue"
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
                key=lambda x: x["formation_energy"]
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


@app.command()
def user_stats(user: str = typer.Option("default", "--user", "-u", help="User ID to show stats for")):
    """
    Display learning statistics and preferences for a user.
    """
    from crystalyse.ui.user_preference_memory import UserPreferenceMemory
    
    memory = UserPreferenceMemory()
    stats = memory.get_user_statistics(user)
    
    if stats['interaction_count'] == 0:
        console.print(f"[yellow]No interaction history found for user '{user}'[/yellow]")
        return
    
    console.print(Panel(
        f"""[bold cyan]CrystaLyse Learning Profile[/bold cyan]

"""
        f"User ID: {stats['user_id']}\n"
        f"Total Interactions: {stats['interaction_count']}\n"
        f"Detected Expertise: {stats['expertise_level']} ({stats['expertise_score']:.2f})\n"
        f"Speed Preference: {stats['speed_preference']:.2f} (0=thorough, 1=fast)\n"
        f"Preferred Mode: {stats['preferred_mode']}\n"
        f"Days Since First Use: {stats['days_since_creation']}\n"
        f"Personalization Active: {'Yes' if stats['personalization_active'] else 'No (need 3+ interactions)'}\n\n"
        f"Domain Expertise:\n" + 
        ("\n".join(f"  {domain}: {score:.2f}" for domain, score in stats['domain_expertise'].items()) if stats['domain_expertise'] else "  No domain-specific data yet\n") +
        "\n\nSuccessful Mode Performance:\n" +
        ("\n".join(f"  {mode}: {score:.2f} avg satisfaction" for mode, score in stats['successful_modes'].items()) if stats['successful_modes'] else "  No mode performance data yet"),
        title="[bold green]📊 User Learning Statistics[/bold green]",
        border_style="green"
    ))


@app.callback()
def main_callback(
    ctx: typer.Context,
    project: str = typer.Option("crystalyse_session", "-p", "--project", help="Project name for workspace."),
    mode: AgentMode = typer.Option(AgentMode.adaptive, "--mode", help="Agent operating mode.", case_sensitive=False),
    model: Optional[str] = typer.Option(None, "--model", help="Language model to use."),
    version: Optional[bool] = typer.Option(None, "--version", help="Show version and exit.", callback=lambda v: (console.print("CrystaLyse.AI 2.0"), exit(0)) if v else None, is_eager=True),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose output"),
):
    """
    CrystaLyse.AI 2.0: Enhanced Materials Discovery
    """
    state["project"] = project
    state["mode"] = mode
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
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[logging.FileHandler('crystalyse.log')]
    )
    
    # If no arguments or no command specified, insert 'chat' as default command
    if len(sys.argv) == 1:
        sys.argv.append('chat')
    elif len(sys.argv) > 1 and sys.argv[1].startswith('-') and sys.argv[1] not in ['--help', '-h']:
        # If first arg is an option (not help), insert 'chat' command before options
        sys.argv.insert(1, 'chat')

    try:
        app()
    except KeyboardInterrupt:
        console.print(f"\n[cyan]CrystaLyse.AI session ended.[/cyan]")
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        console.print(f"\n[red]❌ An unexpected error occurred: {e}[/red]")
        console.print("[dim]Check crystalyse.log for details.[/dim]")
        sys.exit(1)

if __name__ == "__main__":
    run()
