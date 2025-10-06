
"""
CrystaLyse.AI 2.0 - Enhanced Materials Discovery
"""

import asyncio
import logging
import sys
from typing import Optional
from enum import Enum
from pathlib import Path

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
def display_results(results: dict):
    """Display final results in a structured format."""
    if results.get("status") == "failed":
        console.print(Panel(f"[bold red]Error:[/bold red] {results.get('error', 'Unknown error')}", title="Discovery Failed", border_style="red"))
        return

    response = results.get("response", "No response from agent.")
    console.print(Panel(response, title="[bold green]Discovery Report[/bold green]", border_style="green"))

# --- Typer Commands ---

@app.command()
def discover(
    query: str = typer.Argument(..., help="A non-interactive, single-shot materials discovery query."),
):
    """
    Run a single, non-interactive discovery query. Ideal for scripting.
    """
    console.print(f"[cyan]🔍 Starting non-interactive discovery:[/cyan] {query}")
    console.print(f"[dim]Mode: {state['mode']} | Project: {state['project']}[/dim]\n")

    # Set up non-interactive handlers
    state["query"] = query
    workspace_tools.APPROVAL_CALLBACK = approval_callback
    workspace_tools.CLARIFICATION_CALLBACK = non_interactive_clarification

    async def _run():
        agent = EnhancedCrystaLyseAgent(
            config=Config.load(),
            project_name=state['project'],
            mode=state['mode'].value,
            model=state['model'],
        )
        
        # Note: The discover method doesn't accept a progress parameter
        # We can potentially use a trace_handler instead for progress tracking
        results = None
        results = await agent.discover(query)

        if results:
            display_results(results)

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
