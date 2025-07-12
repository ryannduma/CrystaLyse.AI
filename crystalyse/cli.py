

import click
import asyncio
import json
import time
import sys
import logging
from contextlib import nullcontext
from io import StringIO
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

from crystalyse.agents.crystalyse_agent import analyse_materials, CrystaLyse
from crystalyse.config import config

# Configure logging with a cleaner format
logging.basicConfig(
    level=logging.WARNING,
    format="%(message)s",
    handlers=[RichHandler(show_level=False, show_time=False)]
)
logger = logging.getLogger(__name__)

# --- Main CLI Group ---

@click.group(context_settings=dict(help_option_names=['-h', '--help']))
def cli():
    """
    CrystaLyse.AI: A modern, intuitive CLI for computational materials discovery.
    """
    pass

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
    console = Console()
    console.print(Panel("[bold cyan]New CrystaLyse.AI Discovery Project[/bold cyan]", 
                      subtitle="Follow the prompts to define your search.",
                      expand=False))
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
    console = Console()
    _run_and_display_analysis(query, mode, user_id, console, verbose)

cli.add_command(analyse)

# --- Dashboard Command ---

async def get_stats():
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
                stats = asyncio.run(get_stats())
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
    """Show example queries."""
    console = Console()
    table = Table(title="Example Queries")
    table.add_column("Category", style="cyan")
    table.add_column("Query", style="green")
    table.add_row("Basic Discovery", "Find a new material for solar cells")
    table.add_row("Property-driven", "Design a material with high thermal conductivity")
    console.print(table)

cli.add_command(examples)

# --- Improved Helper Function for Analysis ---

def _run_and_display_analysis(query: str, mode: str, user_id: str, console: Console, verbose: bool = False):
    """
    Runs analysis with improved progress display and cleaner output.
    """
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
                    # Run the analysis
                    result = asyncio.run(analyse_materials(query=query, mode=mode, user_id=user_id))
                finally:
                    # Always remove the handler
                    root_logger.removeHandler(progress_handler)
        else:
            # Verbose mode - show all logs
            console.print("[dim]Running analysis in verbose mode...[/dim]")
            result = asyncio.run(analyse_materials(query=query, mode=mode, user_id=user_id))
        
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
    """Display analysis results in a clean format."""
    
    # Clear any remaining status
    console.print()
    
    if result.get("status") == "completed":
        # Success banner
        console.print(Panel(
            f"[bold green]✅ Analysis Complete[/bold green]\n"
            f"[dim]Completed in {elapsed_time:.1f}s[/dim]",
            expand=False,
            border_style="green"
        ))
        
        # Main results
        discovery_result = result.get("discovery_result", "No result found.")
        
        # Try to parse and format as JSON
        try:
            parsed_result = json.loads(discovery_result)
            console.print(Panel(
                Syntax(json.dumps(parsed_result, indent=2), "json", theme="monokai", line_numbers=False),
                title="[bold cyan]Discovery Results[/bold cyan]",
                border_style="cyan"
            ))
        except (json.JSONDecodeError, TypeError):
            console.print(Panel(
                discovery_result,
                title="[bold cyan]Discovery Results[/bold cyan]",
                border_style="cyan"
            ))
        
        # Compact metrics table
        metrics = result.get("metrics", {})
        if metrics:
            table = Table(show_header=False, box=None, padding=(0, 2))
            table.add_column("Metric", style="dim cyan", width=15)
            table.add_column("Value", style="white")
            
            table.add_row("Time", f"{metrics.get('elapsed_time', elapsed_time):.1f}s")
            table.add_row("Tool Calls", str(metrics.get('tool_calls', 0)))
            table.add_row("Model", str(metrics.get('model', 'Unknown')))
            table.add_row("Mode", str(metrics.get('mode', 'Unknown')))
            
            console.print(Panel(table, title="[bold]Performance Metrics[/bold]", border_style="blue"))
        
        # Only show validation issues if there are any
        validation = result.get("response_validation", {})
        if validation and not validation.get("is_valid", True):
            console.print(Panel(
                f"[bold yellow]⚠️  Validation Issues[/bold yellow]\n"
                f"Issues found: {validation.get('violation_count', 0)}",
                border_style="yellow"
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
                title="[bold yellow]Debug Output[/bold yellow]",
                border_style="yellow"
            ))

def _display_error(console: Console, error_message: str, verbose: bool, stderr_capture: StringIO):
    """Display error information in a user-friendly way."""
    
    console.print(Panel(
        f"[bold red]❌ Analysis Failed[/bold red]\n\n{error_message}",
        expand=False,
        border_style="red"
    ))
    
    if verbose and stderr_capture and stderr_capture.getvalue().strip():
        console.print(Panel(
            stderr_capture.getvalue().strip(),
            title="[bold red]Error Details[/bold red]",
            border_style="red"
        ))

def main():
    cli()

if __name__ == '__main__':
    main()

