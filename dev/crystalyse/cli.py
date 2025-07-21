

import click
import asyncio
import json
import time
import sys
import logging
from contextlib import nullcontext
from io import StringIO
from pathlib import Path
from prompt_toolkit import prompt
from prompt_toolkit.validation import Validator, ValidationError
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.syntax import Syntax
from rich.live import Live
from rich.logging import RichHandler
from rich.text import Text
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.status import Status
from rich.prompt import Prompt

# Enhanced UI Components - Red theme as default
from crystalyse.ui.themes import ThemeManager, ThemeType
from crystalyse.ui.components import (
    CrystaLyseHeader, 
    StatusBar, 
    ChatDisplay, 
    MaterialDisplay,
    ProgressIndicator
)
from crystalyse.ui.gradients import create_gradient_text, GradientStyle

# Configure logging with a cleaner format first
logging.basicConfig(
    level=logging.WARNING,
    format="%(message)s",
    handlers=[RichHandler(show_level=False, show_time=False)]
)
logger = logging.getLogger(__name__)

# Initialize enhanced UI with red theme
theme_manager = ThemeManager(ThemeType.CRYSTALYSE_RED)
enhanced_console = Console(theme=theme_manager.current_theme.rich_theme)

from crystalyse.config import config
from crystalyse.memory import CrystaLyseMemory

# Import session-based system
try:
    from crystalyse.agents.session_based_agent import (
        CrystaLyseSession, 
        CrystaLyseSessionManager,
        get_session_manager
    )
    SESSION_BASED_AVAILABLE = True
except ImportError as e:
    SESSION_BASED_AVAILABLE = False
    logger.warning(f"Session-based functionality not available: {e}")

# Import legacy agent functionality
try:
    from crystalyse.agents.crystalyse_agent import analyse_materials, CrystaLyse
    LEGACY_AGENT_AVAILABLE = True
except ImportError as e:
    LEGACY_AGENT_AVAILABLE = False
    logger.warning(f"Legacy agent functionality not available: {e}")

# Exception for chat exit
class ChatExit(Exception):
    """Exception to signal chat session should exit."""
    pass

# --- Main CLI Group ---

@click.group(context_settings=dict(help_option_names=['-h', '--help']), invoke_without_command=True)
@click.pass_context
def cli(ctx):
    """
    CrystaLyse.AI: A modern, intuitive CLI for computational materials discovery.
    
    Features:
    • Session-based conversations with automatic history
    • Persistent memory across sessions
    • Multi-turn context understanding
    • Computational validation with live tools
    • SQLiteSession-like behavior for conversation management
    """
    if ctx.invoked_subcommand is None:
        # No subcommand provided - launch unified interface
        from crystalyse.unified_cli import main as unified_main
        unified_main()

# --- New Command ---

class ModeValidator(Validator):
    def validate(self, document):
        text = document.text.lower()
        if text not in ['creative', 'rigorous']:
            raise ValidationError(message='Please enter "creative" or "rigorous".',
                                  cursor_position=len(document.text))

@click.command()
@click.option('--user-id', default='cli_user', help='User ID for the session.')
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose output.')
def new(user_id: str, verbose: bool):
    """Start a new, guided material discovery project."""
    console = enhanced_console  # Use enhanced console with red theme
    
    # Show enhanced header
    header = CrystaLyseHeader(console)
    console.print(header.render("1.0.0"))
    
    # Enhanced project setup panel
    project_text = create_gradient_text(
        "New CrystaLyse.AI Discovery Project",
        GradientStyle.CRYSTALYSE_RED,
        theme_manager.current_theme.get_gradient_colors()
    )
    
    console.print(Panel(
        Text.assemble(
            project_text,
            "\n[dim]Follow the prompts to define your search.[/dim]"
        ),
        expand=False,
        border_style=theme_manager.current_theme.colors.accent_red
    ))
    project_name = prompt("Project Name: ", default="New Material Search")
    target_properties = prompt("Target Properties (e.g., high band gap): ")
    constraints = prompt("Constraints (e.g., must contain Si and O): ")
    mode = prompt("Analysis Mode (creative/rigorous): ", validator=ModeValidator(), default="creative").lower()
    query = (
        f"Project '{project_name}': Find materials with properties: {target_properties}, "
        f"under constraints: {constraints}."
    )
    console.print("\n[bold]Starting analysis...[/bold]")
    _run_and_display_analysis(query, mode, user_id, console, verbose)

cli.add_command(new)

# --- Analyse Command ---

@click.command()
@click.argument('query')
@click.option('--mode', type=click.Choice(['creative', 'rigorous']), default='creative', help='The analysis mode.')
@click.option('--user-id', default='cli_user', help='User ID for the session.')
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose output.')
def analyse(query: str, mode: str, user_id: str, verbose: bool):
    """Run a materials discovery analysis."""
    console = enhanced_console  # Use enhanced console with red theme
    
    # Check if legacy agent functionality is available
    if not LEGACY_AGENT_AVAILABLE:
        # Enhanced error display
        error_text = create_gradient_text(
            "❌ Analysis functionality not available",
            GradientStyle.CRYSTALYSE_RED,
            theme_manager.current_theme.get_gradient_colors()
        )
        
        error_content = Text.assemble(
            error_text,
            "\n\nThe analysis functionality requires the OpenAI Agents SDK "
            "and MCP packages to be properly installed.\n\n"
            "Please install the required dependencies:\n"
            "• pip install mcp\n"
            "• Ensure OpenAI Agents SDK is properly installed\n\n"
            "Or try `crystalyse legacy-chat` for basic memory functionality."
        )
        
        console.print(Panel(
            error_content,
            title="[bold]Analysis Unavailable[/bold]",
            border_style=theme_manager.current_theme.colors.error
        ))
        return
    
    _run_and_display_analysis(query, mode, user_id, console, verbose)

cli.add_command(analyse)

# --- Session-Based Commands (only available when session system is available) ---

if SESSION_BASED_AVAILABLE:
    
    @cli.command()
    @click.option('--user-id', '-u', default='default', help='User ID for memory system')
    @click.option('--session-id', '-s', default=None, help='Session ID (auto-generated if not provided)')
    @click.option('--mode', '-m', type=click.Choice(['creative', 'rigorous']), default='creative', help='Analysis mode')
    @click.option('--verbose', '-v', is_flag=True, help='Enable verbose logging')
    def chat(user_id: str, session_id: str, mode: str, verbose: bool):
        """
        Start an interactive session-based chat with automatic conversation history.
        
        This provides SQLiteSession-like behavior:
        • Automatic conversation history retrieval
        • Persistent memory across sessions
        • Context continuity between queries
        • Session management with cleanup
        
        Commands:
        • /history - Show conversation history
        • /clear - Clear conversation history
        • /undo - Remove last interaction (like SQLiteSession.pop_item)
        • /sessions - List all sessions
        • /resume <session_id> - Resume a session
        • /help - Show help
        • /exit - Exit chat
        """
        if verbose:
            logging.getLogger().setLevel(logging.DEBUG)
        
        # Generate session ID if not provided
        if session_id is None:
            from datetime import datetime
            session_id = f"{user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Run the async chat session
        asyncio.run(_run_session_chat(user_id, session_id, mode))

    @cli.command()
    @click.option('--user-id', '-u', default='default', help='User ID')
    def sessions(user_id: str):
        """List all sessions for a user."""
        console = Console()
        _show_user_sessions(console, user_id)

    @cli.command()
    @click.argument('session_id')
    @click.option('--user-id', '-u', default='default', help='User ID')
    @click.option('--mode', '-m', type=click.Choice(['creative', 'rigorous']), default='creative', help='Analysis mode')
    def resume(session_id: str, user_id: str, mode: str):
        """Resume a previous session."""
        console = Console()
        console.print(f"[bold]Resuming session: {session_id}[/bold]")
        
        # Resume the session
        asyncio.run(_run_session_chat(user_id, session_id, mode))

    @cli.command()
    @click.option('--user-id', '-u', default='demo_user', help='User ID for demo')
    def demo():
        """Run a demonstration of the session-based system."""
        console = Console()
        console.print("[bold]🎭 CrystaLyse Session-Based Demo[/bold]")
        asyncio.run(_run_session_demo(console))

    # Session-based helper functions
    async def _run_session_chat(user_id: str, session_id: str, mode: str):
        """Run the session-based chat."""
        console = Console()
        
        # Get session manager
        manager = get_session_manager()
        
        # Create session
        session = manager.get_or_create_session(session_id, user_id, max_turns=config.max_turns)
        
        # Display welcome message
        _display_session_welcome(console, user_id, session_id, mode)
        
        # Show existing conversation history if any
        await _show_conversation_history(console, session)
        
        # Setup agent
        console.print("[dim]Setting up CrystaLyse agent...[/dim]")
        await session.setup_agent(mode)
        console.print("[green]✅ Agent ready![/green]")
        
        # Main chat loop
        try:
            while True:
                # Get user input
                user_input = Prompt.ask("\n🔬 You", console=console)
                
                # Handle commands
                if user_input.lower() in ['/exit', '/quit', 'quit', 'bye']:
                    console.print("[green]Goodbye![/green]")
                    break
                
                elif user_input.lower() == '/history':
                    await _show_conversation_history(console, session)
                    continue
                
                elif user_input.lower() == '/clear':
                    session.clear_conversation()
                    console.print("[yellow]Conversation history cleared[/yellow]")
                    continue
                
                elif user_input.lower() == '/undo':
                    last_item = session.pop_last_item()
                    if last_item:
                        console.print(f"[yellow]Removed: {last_item.role}: {last_item.content[:50]}...[/yellow]")
                    else:
                        console.print("[yellow]No items to undo[/yellow]")
                    continue
                
                elif user_input.lower() == '/sessions':
                    _show_user_sessions(console, user_id)
                    continue
                
                elif user_input.startswith('/resume '):
                    resume_session_id = user_input[8:].strip()
                    if resume_session_id:
                        console.print(f"[yellow]Use 'crystalyse chat -s {resume_session_id}' to resume that session[/yellow]")
                    else:
                        console.print("[red]Usage: /resume <session_id>[/red]")
                    continue
                
                elif user_input.lower() == '/help':
                    _show_session_help(console)
                    continue
                
                # Regular query with automatic history
                console.print("\n[cyan]🤖 CrystaLyse is thinking...[/cyan]")
                
                try:
                    # This automatically handles conversation history!
                    result = await session.run_with_history(user_input)
                    
                    if result['status'] == 'success':
                        # Display response
                        console.print(Panel(
                            result['response'],
                            title="[bold green]🔬 CrystaLyse Response[/bold green]",
                            border_style="green"
                        ))
                        
                        # Show session stats
                        if result.get('history_length', 0) > 0:
                            console.print(f"[dim]Session context: {result['history_length']} previous interactions[/dim]")
                    
                    else:
                        console.print(Panel(
                            f"[bold red]Error:[/bold red] {result['error']}",
                            border_style="red"
                        ))
                    
                except Exception as e:
                    console.print(f"[red]Error: {str(e)}[/red]")
                    logger.error(f"Chat error: {e}", exc_info=True)
        
        except KeyboardInterrupt:
            console.print("\n[yellow]Chat interrupted[/yellow]")
        
        finally:
            # Cleanup
            console.print("\n[dim]Cleaning up session...[/dim]")
            await session.cleanup()
            console.print("[green]✅ Session ended successfully[/green]")

    def _display_session_welcome(console: Console, user_id: str, session_id: str, mode: str):
        """Display welcome message for session-based chat with enhanced UI."""
        # Initialize enhanced UI components
        header = CrystaLyseHeader(console)
        
        # Show enhanced header
        header_panel = header.render("1.0.0")
        console.print(header_panel)
        
        # Create enhanced welcome content
        welcome_text = Text()
        welcome_text.append("🔬 CrystaLyse.AI - Session-Based Chat\n\n", style="accent.red")
        welcome_text.append(f"User: {user_id}\n", style="accent.green")
        welcome_text.append(f"Session: {session_id}\n", style="accent.cyan")
        welcome_text.append(f"Mode: {mode.capitalize()}\n\n", style="accent.blue")
        
        welcome_text.append("Key Features:\n", style="title")
        welcome_text.append("✅ Automatic conversation history\n", style="status.success")
        welcome_text.append("✅ Persistent memory across sessions\n", style="status.success")
        welcome_text.append("✅ Multi-turn context understanding\n", style="status.success")
        welcome_text.append("✅ SQLiteSession-like behavior\n", style="status.success")
        welcome_text.append("✅ Computational validation with live tools\n\n", style="status.success")
        
        welcome_text.append("Available Commands:\n", style="title")
        commands = [
            ("• `/history`", "Show conversation history"),
            ("• `/clear`", "Clear conversation history"),
            ("• `/undo`", "Remove last interaction"),
            ("• `/sessions`", "List all sessions"),
            ("• `/help`", "Show detailed help"),
            ("• `/exit`", "Exit chat")
        ]
        
        for cmd, desc in commands:
            welcome_text.append(f"{cmd}", style="accent.cyan")
            welcome_text.append(f" - {desc}\n", style="dim")
        
        welcome_panel = Panel(
            welcome_text,
            title="[bold]Welcome to CrystaLyse Session Chat[/bold]",
            border_style=theme_manager.current_theme.colors.accent_red,
            padding=(1, 2)
        )
        
        console.print(welcome_panel)

    def _show_session_help(console: Console):
        """Show help information for session-based chat."""
        console.print(Panel(
            "[bold]CrystaLyse Session-Based Chat Commands:[/bold]\n\n"
            "[cyan]/history[/cyan] - Show conversation history\n"
            "[cyan]/clear[/cyan] - Clear conversation history\n"
            "[cyan]/undo[/cyan] - Remove last interaction (like SQLiteSession.pop_item)\n"
            "[cyan]/sessions[/cyan] - List all your sessions\n"
            "[cyan]/resume <session_id>[/cyan] - Resume a specific session\n"
            "[cyan]/help[/cyan] - Show this help message\n"
            "[cyan]/exit[/cyan] - Exit chat session\n\n"
            "[bold]Enhanced Workflow Features:[/bold]\n"
            "• Automatic conversation history retrieval and persistence\n"
            "• Context continuity across multi-turn conversations\n"
            "• Memory integration for caching computational results\n"
            "• Session resumption for long-running research projects\n"
            "• Discovery caching to avoid redundant calculations\n\n"
            "[bold]Example Enhanced Workflow:[/bold]\n"
            "1. 'Analyze LiCoO₂ battery properties' (starts research)\n"
            "2. 'What about volume changes during delithiation?' (remembers context)\n"
            "3. 'Compare with experimental values from Materials Project' (builds on analysis)\n"
            "4. Exit and resume later - conversation history is preserved!\n"
            "5. 'How do these results compare to other cathode materials?' (continues research)\n",
            title="Session-Based Chat Help",
            border_style="blue"
        ))

    async def _show_conversation_history(console: Console, session: CrystaLyseSession):
        """Show conversation history for the session."""
        history = session.get_conversation_history()
        
        if not history:
            console.print("[dim]No conversation history[/dim]")
            return
        
        # Create table
        table = Table(title=f"Conversation History - {session.session_id}")
        table.add_column("Role", style="bold")
        table.add_column("Content", style="dim")
        table.add_column("Time", style="cyan")
        
        for item in history[-10:]:  # Show last 10 items
            content = item.content[:80] + "..." if len(item.content) > 80 else item.content
            table.add_row(
                item.role,
                content,
                item.timestamp.strftime("%H:%M:%S")
            )
        
        console.print(table)

    def _show_user_sessions(console: Console, user_id: str):
        """Show all sessions for a user."""
        console.print(f"[bold]Active Sessions for User: {user_id}[/bold]")
        
        # Show sessions from database
        import sqlite3
        
        db_path = Path.home() / ".crystalyse" / "conversations.db"
        
        if not db_path.exists():
            console.print("[dim]No conversation database found[/dim]")
            return
        
        with sqlite3.connect(db_path) as conn:
            cursor = conn.execute('''
                SELECT DISTINCT session_id, COUNT(*) as message_count, 
                       MAX(timestamp) as last_activity
                FROM conversations
                WHERE user_id = ?
                GROUP BY session_id
                ORDER BY last_activity DESC
            ''', (user_id,))
            
            sessions = cursor.fetchall()
            
            if not sessions:
                console.print("[dim]No sessions found[/dim]")
                return
            
            table = Table(title="Your Sessions")
            table.add_column("Session ID", style="bold")
            table.add_column("Messages", style="cyan")
            table.add_column("Last Activity", style="dim")
            
            for session_id, count, last_activity in sessions:
                table.add_row(session_id, str(count), last_activity)
            
            console.print(table)

    async def _run_session_demo(console: Console):
        """Run a demonstration showing SQLiteSession-like behavior."""
        
        console.print("\n[bold cyan]Creating a new session...[/bold cyan]")
        
        # Get session manager
        manager = get_session_manager()
        
        # Create demo session
        session = manager.get_or_create_session("demo_session", "demo_user", max_turns=config.max_turns)
        
        # Setup agent
        console.print("[dim]Setting up agent...[/dim]")
        await session.setup_agent("creative")
        
        # Demo queries showing context persistence
        demo_queries = [
            "What is a perovskite material?",
            "Give me an example of one",
            "What are its typical applications?",
            "How stable is it compared to other materials?"
        ]
        
        for i, query in enumerate(demo_queries, 1):
            console.print(f"\n[bold]Demo Query {i}:[/bold] {query}")
            
            result = await session.run_with_history(query)
            
            if result['status'] == 'success':
                response = result['response'][:200] + "..." if len(result['response']) > 200 else result['response']
                console.print(f"[green]Response:[/green] {response}")
                console.print(f"[dim]Context length: {result['history_length']} previous interactions[/dim]")
            else:
                console.print(f"[red]Error: {result['error']}[/red]")
        
        # Show final conversation history
        console.print("\n[bold]Final Conversation History:[/bold]")
        await _show_conversation_history(console, session)
        
        # Cleanup
        await session.cleanup()
        console.print("\n[green]✅ Demo completed![/green]")

# --- Fallback commands for when session system is not available ---

else:
    # Provide fallback commands that show helpful error messages
    
    @cli.command()
    @click.option('--user-id', '-u', default='default', help='User ID for memory system')
    @click.option('--session-id', '-s', default=None, help='Session ID (auto-generated if not provided)')
    @click.option('--mode', '-m', type=click.Choice(['creative', 'rigorous']), default='creative', help='Analysis mode')
    @click.option('--verbose', '-v', is_flag=True, help='Enable verbose logging')
    def chat(user_id: str, session_id: str, mode: str, verbose: bool):
        """Start an interactive session-based chat (requires dependencies)."""
        console = Console()
        console.print(Panel(
            "[bold red]❌ Session-based chat not available[/bold red]\n\n"
            "The session-based chat functionality requires the OpenAI Agents SDK "
            "and MCP packages to be properly installed.\n\n"
            "Please try:\n"
            "• `crystalyse legacy-chat` for basic chat functionality\n"
            "• `crystalyse analyse \"your query\"` for one-shot analysis\n\n"
            "Or install the required dependencies.",
            title="Chat Unavailable",
            border_style="red"
        ))

    @cli.command()
    @click.option('--user-id', '-u', default='default', help='User ID')
    def sessions(user_id: str):
        """List all sessions for a user (requires dependencies)."""
        console = Console()
        console.print(Panel(
            "[bold red]❌ Sessions not available[/bold red]\n\n"
            "Session management requires the OpenAI Agents SDK "
            "and MCP packages to be properly installed.\n\n"
            "Please install the required dependencies.",
            title="Sessions Unavailable",
            border_style="red"
        ))

    @cli.command()
    @click.argument('session_id')
    @click.option('--user-id', '-u', default='default', help='User ID')
    @click.option('--mode', '-m', type=click.Choice(['creative', 'rigorous']), default='creative', help='Analysis mode')
    def resume(session_id: str, user_id: str, mode: str):
        """Resume a previous session (requires dependencies)."""
        console = Console()
        console.print(Panel(
            "[bold red]❌ Resume not available[/bold red]\n\n"
            "Session resumption requires the OpenAI Agents SDK "
            "and MCP packages to be properly installed.\n\n"
            "Please install the required dependencies.",
            title="Resume Unavailable",
            border_style="red"
        ))

    @cli.command()
    @click.option('--user-id', '-u', default='demo_user', help='User ID for demo')
    def demo():
        """Run a demonstration of the session-based system (requires dependencies)."""
        console = Console()
        console.print(Panel(
            "[bold red]❌ Demo not available[/bold red]\n\n"
            "The session-based demo requires the OpenAI Agents SDK "
            "and MCP packages to be properly installed.\n\n"
            "Please install the required dependencies and try again.\n\n"
            "Available commands:\n"
            "• `crystalyse examples` - View example workflows\n"
            "• `crystalyse config show` - Check configuration\n"
            "• `crystalyse legacy-chat` - Basic memory functionality",
            title="Demo Unavailable",
            border_style="red"
        ))

# --- Dashboard Command ---

async def get_stats():
    if not LEGACY_AGENT_AVAILABLE:
        return {"error": "Agent functionality not available"}
    
    agent = CrystaLyse()
    stats = await agent._get_infrastructure_stats()
    await agent.cleanup()
    return stats

def generate_dashboard_panel(stats: dict) -> Panel:
    main_table = Table.grid(expand=True)
    main_table.add_column(style="cyan")
    main_table.add_column(justify="right")
    status = "[bold green]OPERATIONAL[/bold green]" if not stats.get("error") else "[bold red]ERROR[/bold red]"
    main_table.add_row("System Status:", status)
    return Panel(main_table, title="[bold]CrystaLyse.AI Live Dashboard[/bold]", subtitle=f"[default]{time.ctime()}[/default]")

@click.command()
def dashboard():
    """Display a live dashboard of the CrystaLyse.AI system status."""
    console = Console()
    with Live(console=console, screen=False, redirect_stderr=False) as live:
        while True:
            try:
                stats = _run_stats_async_aware()
                panel = generate_dashboard_panel(stats)
                live.update(panel)
                time.sleep(5)
            except KeyboardInterrupt:
                break
            except Exception as e:
                console.print(Panel(f"[bold red]Error updating dashboard:[bold red]\n{e}"))
                break

cli.add_command(dashboard)

# --- Config Command ---

@click.group(name='config')
def config_cli():
    """View and manage configuration."""
    pass

@click.command(name='show')
def show_config():
    """Display the current configuration."""
    console = Console()
    table = Table(title="[bold]CrystaLyse.AI Runtime Configuration[/bold]")
    table.add_column("Setting", style="cyan")
    table.add_column("Value", style="magenta")
    table.add_row("Default Model", config.default_model)
    table.add_row("Max Turns", str(config.max_turns))
    console.print(table)
    server_data = json.dumps(config.mcp_servers, indent=2)
    console.print(Panel(server_data, title="[bold]MCP Server Configurations[/bold]", border_style="green"))

@click.command(name='path')
def config_path():
    """Display the path to the configuration file (if any)."""
    console = Console()
    console.print("[yellow]CrystaLyse.AI is configured via environment variables, not a file.[/yellow]")

config_cli.add_command(show_config)
config_cli.add_command(config_path)
cli.add_command(config_cli)

# --- Examples Command ---

@click.command()
def examples():
    """Show example queries and enhanced workflow patterns."""
    console = Console()
    
    # Basic examples
    table = Table(title="Basic Example Queries")
    table.add_column("Category", style="cyan")
    table.add_column("Query", style="green")
    table.add_row("Basic Discovery", "Find a new material for solar cells")
    table.add_row("Property-driven", "Design a material with high thermal conductivity")
    table.add_row("Battery Analysis", "Analyze LiCoO₂ battery properties and delithiation")
    table.add_row("Structural Analysis", "Compare perovskite stability under pressure")
    console.print(table)
    
    # Enhanced workflow examples
    console.print("\n")
    console.print(Panel(
        "[bold]Enhanced Session-Based Workflow Examples:[/bold]\n\n"
        "[cyan]1. Battery Research Session:[/cyan]\n"
        "   • crystalyse chat -u battery_researcher\n"
        "   • 'Analyze LiCoO₂ cathode material properties'\n"
        "   • 'What happens during delithiation to CoO₂?'\n"
        "   • 'Calculate volume changes and energy density'\n"
        "   • 'Compare with Materials Project mp-552024_Li data'\n"
        "   • Exit and resume later - all context preserved!\n\n"
        "[cyan]2. Perovskite Discovery Session:[/cyan]\n"
        "   • crystalyse chat -u perovskite_researcher -m rigorous\n"
        "   • 'Find stable perovskite materials for solar cells'\n"
        "   • 'What about their band gaps and optical properties?'\n"
        "   • 'How do they perform under different conditions?'\n"
        "   • 'Compare computational predictions with experiments'\n\n"
        "[cyan]3. Multi-Day Research Project:[/cyan]\n"
        "   • Day 1: crystalyse chat -s project_2024 -u researcher\n"
        "   • Day 2: crystalyse resume project_2024 -u researcher\n"
        "   • All conversation history and discoveries preserved\n"
        "   • Memory system caches computational results\n"
        "   • Context continuity across sessions\n",
        title="Session-Based Workflow Examples",
        border_style="green"
    ))

cli.add_command(examples)

# --- Legacy Memory-Based Chat (for backward compatibility) ---

@cli.command(name='legacy-chat')
@click.option('--user-id', '-u', default='default', help='User ID for personalized memory')
@click.option('--mode', '-m', type=click.Choice(['creative', 'rigorous']), default='creative', help='Analysis mode')
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose output')
def legacy_chat(user_id: str, mode: str, verbose: bool):
    """
    Legacy chat mode using the old memory system (for backward compatibility).
    
    Note: Consider using the new 'chat' command for better session management.
    """
    console = Console()
    
    if verbose:
        logging.getLogger().setLevel(logging.INFO)
    
    # Initialize memory system
    memory = CrystaLyseMemory(user_id=user_id)
    
    # Display welcome message
    console.print(Panel(
        f"[bold yellow]🔬 CrystaLyse.AI Legacy Chat Mode[/bold yellow]\n\n"
        f"Mode: {mode.capitalize()}\n"
        f"User ID: {user_id}\n"
        f"Memory Directory: {memory.memory_dir}\n\n"
        f"[bold red]⚠️ This is the legacy chat mode.[/bold red]\n"
        f"[bold green]Consider using 'crystalyse chat' for better session management.[/bold green]\n\n"
        f"Available commands:\n"
        f"• Type your materials science questions naturally\n"
        f"• Use `/save <fact>` to save important information\n"
        f"• Use `/search <query>` to search your memory\n"
        f"• Use `/discoveries <query>` to search cached discoveries\n"
        f"• Use `/summary` to generate weekly research summary\n"
        f"• Use `/memory` to view memory statistics\n"
        f"• Use `/help` to see all commands\n"
        f"• Use `/exit` to quit\n",
        title="Legacy Chat Mode",
        border_style="yellow"
    ))
    
    # Show memory context if available
    context = memory.get_context_for_agent()
    if context != "No previous context available.":
        console.print(Panel(
            context,
            title="[bold blue]Your Research Context[/bold blue]",
            border_style="blue"
        ))
    
    # Check if legacy agent is available
    if not LEGACY_AGENT_AVAILABLE:
        console.print(Panel(
            "[bold red]❌ Legacy chat agent not available[/bold red]\n\n"
            "The legacy chat functionality requires the OpenAI Agents SDK "
            "and MCP packages to be properly installed.\n\n"
            "Only basic memory functionality is available.",
            title="Limited Functionality",
            border_style="red"
        ))
        return
    
    # Initialize agent and run chat loop in single async context
    from crystalyse.agents.crystalyse_agent import AgentConfig
    agent_config = AgentConfig(mode=mode, enable_memory=True)
    console.print("[dim]Initializing CrystaLyse agent...[/dim]")
    
    # Run the chat session with proper memory integration
    _run_chat_session_sync(agent_config, user_id, memory, console, verbose)

# --- Helper Functions ---

def _run_stats_async_aware():
    """
    Run get_stats() in either sync or async context.
    Detects if there's already an event loop running and handles accordingly.
    """
    try:
        # Check if there's already an event loop running
        loop = asyncio.get_running_loop()
        # Run in a separate thread with its own event loop
        import concurrent.futures
        
        def run_in_thread():
            new_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(new_loop)
            try:
                return new_loop.run_until_complete(get_stats())
            finally:
                new_loop.close()
        
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(run_in_thread)
            return future.result()
            
    except RuntimeError:
        # No running event loop, safe to use asyncio.run()
        return asyncio.run(get_stats())

def _run_analysis_async_aware(query: str, mode: str, user_id: str):
    """
    Run analysis in either sync or async context.
    Detects if there's already an event loop running and handles accordingly.
    """
    try:
        # Check if there's already an event loop running
        loop = asyncio.get_running_loop()
        # If we're in an async context, we need to use create_task or similar
        # But since we're in a sync function, we'll use a different approach
        import concurrent.futures
        import threading
        
        # Run the async function in a separate thread with its own event loop
        def run_in_thread():
            new_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(new_loop)
            try:
                return new_loop.run_until_complete(analyse_materials(query=query, mode=mode, user_id=user_id))
            finally:
                new_loop.close()
        
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(run_in_thread)
            return future.result()
            
    except RuntimeError:
        # No running event loop, safe to use asyncio.run()
        return asyncio.run(analyse_materials(query=query, mode=mode, user_id=user_id))

def _run_and_display_analysis(query: str, mode: str, user_id: str, console: Console, verbose: bool = False):
    """
    Runs analysis with enhanced UI and improved progress display.
    """
    # Show enhanced header for analysis
    header = CrystaLyseHeader(console)
    console.print(header.render("1.0.0"))
    
    start_time = time.time()
    
    # Capture stderr for cleaner output
    stderr_capture = StringIO()
    original_stderr = sys.stderr
    
    if not verbose:
        # Redirect stderr to capture noisy output
        sys.stderr = stderr_capture
        
        # Set logging to INFO so we can track progress, but suppress noisy loggers
        logging.getLogger().setLevel(logging.INFO)
        
        # Suppress the really noisy loggers
        noisy_loggers = [
            'openai', 'httpx', 'urllib3', 'httpcore', 'mcp.server.lowlevel.server',
            'e3nn', 'torch', 'torchaudio'
        ]
        for logger_name in noisy_loggers:
            logging.getLogger(logger_name).setLevel(logging.ERROR)
            
        # Remove Rich handler temporarily to avoid interference
        rich_handler = None
        for handler in logging.getLogger().handlers[:]:
            if isinstance(handler, RichHandler):
                rich_handler = handler
                logging.getLogger().removeHandler(handler)
                break
    else:
        # Verbose mode - show everything
        logging.getLogger().setLevel(logging.DEBUG)
        rich_handler = None
    
    # Progress tracking
    current_stage = "Initialising analysis..."
    last_update_time = time.time()
    
    def update_progress_stage(message: str) -> str:
        """Update progress stage based on log message content"""
        nonlocal current_stage, last_update_time
        
        msg_lower = message.lower()
        now = time.time()
        
        # Rate limit updates to prevent spam
        if now - last_update_time < 1.0:
            return current_stage
            
        new_stage = None
        
        # Match actual log messages from your output
        if any(keyword in msg_lower for keyword in ['tools loaded successfully', 'tools module imported', 'mcp server']):
            new_stage = "Loading computational tools..."
        elif any(keyword in msg_lower for keyword in ['generating 3 structures', 'generating structures for', 'sampling:']):
            new_stage = "Generating candidate structures..."
        elif any(keyword in msg_lower for keyword in ['calculating formation energy', 'formation energies']):
            new_stage = "Calculating formation energies..."
        elif any(keyword in msg_lower for keyword in ['stability', 'validation', 'band gap']):
            new_stage = "Evaluating stability and properties..."
        elif any(keyword in msg_lower for keyword in ['analysis complete', 'ranking', 'recommended']):
            new_stage = "Finalising results..."
        
        if new_stage and new_stage != current_stage:
            current_stage = new_stage
            last_update_time = now
            
        return current_stage
    
    # Custom logging handler that directly updates the Status widget
    class ProgressLoggingHandler(logging.Handler):
        def __init__(self, status_widget):
            super().__init__()
            self.status_widget = status_widget
            self.setLevel(logging.INFO)
            
        def emit(self, record):
            if verbose:
                return  # Don't interfere with verbose output
                
            try:
                msg = record.getMessage()
                # Update progress and status widget
                stage = update_progress_stage(msg)
                self.status_widget.update(f"[bold cyan]{stage}")
            except Exception:
                pass  # Ignore any errors in progress tracking
    
    try:
        if not verbose:
            # Use Rich Status for clean progress display
            with Status("[bold cyan]Initialising analysis...", console=console, spinner="dots") as status:
                # Create and add progress handler
                progress_handler = ProgressLoggingHandler(status)
                root_logger = logging.getLogger()
                root_logger.addHandler(progress_handler)
                
                try:
                    # Run the analysis - handle both sync and async contexts
                    result = _run_analysis_async_aware(query=query, mode=mode, user_id=user_id)
                finally:
                    # Always remove the handler
                    root_logger.removeHandler(progress_handler)
        else:
            # Verbose mode - show all logs
            console.print("[dim]Running analysis in verbose mode...[/dim]")
            result = _run_analysis_async_aware(query=query, mode=mode, user_id=user_id)
        
    except Exception as e:
        _display_error(console, f"Analysis failed: {str(e)}", verbose, stderr_capture)
        return
    finally:
        # Restore stderr and logging
        sys.stderr = original_stderr
        if not verbose and rich_handler:
            # Restore Rich handler
            logging.getLogger().addHandler(rich_handler)
    
    # Display results
    elapsed_time = time.time() - start_time
    _display_results(console, result, elapsed_time, verbose, stderr_capture)

def _display_results(console: Console, result: dict, elapsed_time: float, verbose: bool, stderr_capture: StringIO):
    """Display analysis results with enhanced UI."""
    
    # Clear any remaining status
    console.print()
    
    if result.get("status") == "completed":
        # Enhanced success banner with gradient
        success_text = create_gradient_text(
            "✅ Analysis Complete",
            GradientStyle.CRYSTALYSE_RED,
            theme_manager.current_theme.get_gradient_colors()
        )
        
        success_panel = Panel(
            Text.assemble(
                success_text,
                f"\n[dim]Completed in {elapsed_time:.1f}s[/dim]"
            ),
            expand=False,
            border_style=theme_manager.current_theme.colors.success
        )
        console.print(success_panel)
        
        # Main results with enhanced formatting
        discovery_result = result.get("discovery_result", "No result found.")
        
        # Try to parse and format as JSON or display as enhanced text
        try:
            parsed_result = json.loads(discovery_result)
            console.print(Panel(
                Syntax(json.dumps(parsed_result, indent=2), "json", theme="monokai", line_numbers=False),
                title="[bold]Discovery Results[/bold]",
                border_style=theme_manager.current_theme.colors.accent_cyan
            ))
        except (json.JSONDecodeError, TypeError):
            # Enhanced text display for discovery results
            result_text = Text()
            result_text.append(discovery_result, style="foreground")
            
            console.print(Panel(
                result_text,
                title="[bold]Discovery Results[/bold]",
                border_style=theme_manager.current_theme.colors.accent_cyan,
                padding=(1, 2)
            ))
        
        # Enhanced metrics table
        metrics = result.get("metrics", {})
        if metrics:
            table = Table(show_header=False, box=None, padding=(0, 2))
            table.add_column("Metric", style="material.property", width=15)
            table.add_column("Value", style="material.value")
            
            table.add_row("Time", f"{metrics.get('elapsed_time', elapsed_time):.1f}s")
            table.add_row("Tool Calls", str(metrics.get('tool_calls', 0)))
            table.add_row("Model", str(metrics.get('model', 'Unknown')))
            table.add_row("Mode", str(metrics.get('mode', 'Unknown')))
            
            console.print(Panel(
                table, 
                title="[bold]Performance Metrics[/bold]", 
                border_style=theme_manager.current_theme.colors.accent_blue
            ))
        
        # Enhanced validation issues display
        validation = result.get("response_validation", {})
        if validation and not validation.get("is_valid", True):
            warning_text = Text()
            warning_text.append("⚠️  Validation Issues\n", style="status.warning")
            warning_text.append(f"Issues found: {validation.get('violation_count', 0)}", style="dim")
            
            console.print(Panel(
                warning_text,
                border_style=theme_manager.current_theme.colors.warning
            ))
    
    else:
        # Error display
        error_message = result.get("error", "An unknown error occurred.")
        _display_error(console, error_message, verbose, stderr_capture)
    
    # Show debug output only if verbose and there are actual errors
    if verbose and stderr_capture and stderr_capture.getvalue().strip():
        stderr_content = stderr_capture.getvalue().strip()
        # Only show if it contains actual error information
        if any(keyword in stderr_content.lower() for keyword in ['error', 'exception', 'traceback', 'warning']):
            console.print(Panel(
                stderr_content,
                title="[bold]Debug Output[/bold]",
                border_style=theme_manager.current_theme.colors.warning
            ))

def _display_error(console: Console, error_message: str, verbose: bool, stderr_capture: StringIO):
    """Display error information with enhanced UI."""
    
    # Enhanced error display with gradient
    error_text = create_gradient_text(
        "❌ Analysis Failed",
        GradientStyle.CRYSTALYSE_RED,
        theme_manager.current_theme.get_gradient_colors()
    )
    
    error_panel = Panel(
        Text.assemble(
            error_text,
            f"\n\n{error_message}"
        ),
        expand=False,
        border_style=theme_manager.current_theme.colors.error
    )
    console.print(error_panel)
    
    if verbose and stderr_capture and stderr_capture.getvalue().strip():
        console.print(Panel(
            stderr_capture.getvalue().strip(),
            title="[bold]Error Details[/bold]",
            border_style=theme_manager.current_theme.colors.error
        ))

# Legacy chat functions for backward compatibility
if LEGACY_AGENT_AVAILABLE:
    async def _run_chat_session(agent_config, user_id: str, memory: CrystaLyseMemory, console: Console, verbose: bool):
        """Run the entire chat session in a single async context to maintain MCP connections."""
        from crystalyse.agents.crystalyse_agent import CrystaLyse
        
        # Initialize agent once for the entire session
        agent = CrystaLyse(agent_config=agent_config, user_id=user_id)
        console.print("[dim]Agent initialized successfully![/dim]")
        
        # Chat loop
        console.print("[dim]Starting chat loop...[/dim]")
        try:
            while True:
                try:
                    # Get user input (synchronous)
                    user_input = prompt("\n🔬 You: ", validator=None)
                    
                    if not user_input.strip():
                        continue
                    
                    # Handle special commands
                    if user_input.startswith('/'):
                        try:
                            _handle_chat_command(user_input, memory, console)
                        except ChatExit:
                            console.print("\n[green]Exiting chat session...[/green]")
                            break
                        continue
                    
                    # Regular materials science query
                    console.print(f"\n[bold cyan]🤖 CrystaLyse is thinking...[/bold cyan]")
                    
                    with console.status("[bold green]Analyzing materials...", spinner="dots"):
                        # Use await instead of asyncio.run to maintain async context
                        result = await agent.discover_materials(user_input)
                    
                    if result['status'] == 'completed':
                        response = result['discovery_result']
                        
                        # Display response
                        console.print(Panel(
                            response,
                            title="[bold green]🔬 CrystaLyse Analysis[/bold green]",
                            border_style="green"
                        ))
                        
                        # Show memory statistics if verbose
                        if verbose:
                            memory_stats = result.get('metrics', {}).get('infrastructure_stats', {}).get('memory_system', {})
                            if memory_stats:
                                console.print(f"\n[dim]Memory: {memory_stats.get('cache', {}).get('total_entries', 0)} cached discoveries, "
                                            f"{memory_stats.get('session', {}).get('total_interactions', 0)} session interactions[/dim]")
                        
                        # Auto-generate insights if needed
                        memory.auto_generate_insights()
                        
                    else:
                        console.print(Panel(
                            f"[bold red]❌ Analysis Failed[/bold red]\n\n{result.get('error', 'Unknown error')}",
                            border_style="red"
                        ))
                    
                except KeyboardInterrupt:
                    console.print("\n[yellow]Use /exit to quit properly[/yellow]")
                    continue
                except Exception as e:
                    console.print(f"[red]Error: {str(e)}[/red]")
                    
        except KeyboardInterrupt:
            console.print("\n[yellow]Chat session interrupted[/yellow]")
        finally:
            # Cleanup
            await agent.cleanup()
            console.print("\n[green]✅ Chat session ended. Your memory has been saved.[/green]")

    def _run_chat_session_sync(agent_config, user_id: str, memory: CrystaLyseMemory, console: Console, verbose: bool):
        """Synchronous wrapper for the async chat session."""
        try:
            # Check if there's already an event loop running
            loop = asyncio.get_running_loop()
            # If we're in an async context, we need to use a different approach
            import concurrent.futures
            
            def run_in_thread():
                new_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(new_loop)
                try:
                    return new_loop.run_until_complete(_run_chat_session(agent_config, user_id, memory, console, verbose))
                finally:
                    new_loop.close()
            
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(run_in_thread)
                return future.result()
                
        except RuntimeError:
            # No running event loop, safe to use asyncio.run()
            return asyncio.run(_run_chat_session(agent_config, user_id, memory, console, verbose))

    def _handle_chat_command(command: str, memory: CrystaLyseMemory, console: Console):
        """Handle special chat commands."""
        command = command.strip()
        
        if command == '/exit':
            raise ChatExit()
        
        elif command == '/help':
            console.print(Panel(
                "[bold]Available Commands:[/bold]\n\n"
                "• `/save <fact>` - Save important information to memory\n"
                "• `/search <query>` - Search your memory\n"
                "• `/discoveries <query>` - Search cached discoveries\n"
                "• `/summary` - Generate weekly research summary\n"
                "• `/memory` - View memory statistics\n"
                "• `/context` - View current memory context\n"
                "• `/help` - Show this help message\n"
                "• `/exit` - Exit chat mode\n",
                title="Chat Commands",
                border_style="blue"
            ))
        
        elif command.startswith('/save '):
            fact = command[6:].strip()
            if fact:
                memory.save_to_memory(fact)
                console.print(f"[green]✅ Saved to memory: {fact[:50]}{'...' if len(fact) > 50 else ''}[/green]")
            else:
                console.print("[red]Usage: /save <fact to save>[/red]")
        
        elif command.startswith('/search '):
            query = command[8:].strip()
            if query:
                results = memory.search_memory(query)
                if results:
                    console.print(Panel(
                        "\n".join(f"• {result}" for result in results[:10]),
                        title=f"Memory Search Results for '{query}'",
                        border_style="blue"
                    ))
                else:
                    console.print(f"[yellow]No memory entries found for '{query}'[/yellow]")
            else:
                console.print("[red]Usage: /search <query>[/red]")
        
        elif command.startswith('/discoveries '):
            query = command[13:].strip()
            if query:
                results = memory.search_discoveries(query)
                if results:
                    discovery_lines = []
                    for result in results:
                        formula = result.get('formula', 'Unknown')
                        cached_at = result.get('cached_at', 'Unknown time')
                        discovery_lines.append(f"• {formula} (cached: {cached_at})")
                    
                    console.print(Panel(
                        "\n".join(discovery_lines),
                        title=f"Discovery Search Results for '{query}'",
                        border_style="cyan"
                    ))
                else:
                    console.print(f"[yellow]No cached discoveries found for '{query}'[/yellow]")
            else:
                console.print("[red]Usage: /discoveries <query>[/red]")
        
        elif command == '/summary':
            console.print("[cyan]Generating weekly research summary...[/cyan]")
            summary = memory.generate_weekly_summary()
            console.print(Panel(
                summary,
                title="Weekly Research Summary",
                border_style="green"
            ))
        
        elif command == '/memory':
            stats = memory.get_memory_statistics()
            stats_text = f"""[bold]Memory Statistics:[/bold]

User ID: {stats['user_id']}
Memory Directory: {stats['memory_directory']}
Session Interactions: {stats['session']['total_interactions']}
Cached Discoveries: {stats['cache']['total_entries']}
User Preferences: {stats['user_preferences']}
Research Interests: {stats['research_interests']}
Recent Discoveries: {stats['recent_discoveries']}
Insights Available: {stats['insights_available']}
"""
            console.print(Panel(
                stats_text,
                title="Memory System Status",
                border_style="blue"
            ))
        
        elif command == '/context':
            context = memory.get_context_for_agent()
            console.print(Panel(
                context,
                title="Current Memory Context",
                border_style="blue"
            ))
        
        else:
            console.print(f"[red]Unknown command: {command}[/red]")
            console.print("[yellow]Type /help for available commands[/yellow]")

def main():
    cli()

if __name__ == '__main__':
    main()

