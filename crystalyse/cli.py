

import click
import asyncio
import json
import time
from prompt_toolkit import prompt
from prompt_toolkit.validation import Validator, ValidationError
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.syntax import Syntax
from rich.live import Live

from crystalyse.agents.crystalyse_agent import analyse_materials, CrystaLyse
from crystalyse.config import config

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
def new(user_id: str):
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
    _run_and_display_analysis(query, mode, user_id, console)

cli.add_command(new)

# --- Analyse Command ---

@click.command()
@click.argument('query')
@click.option('--mode', type=click.Choice(['creative', 'rigorous']), default='creative', help='The analysis mode.')
@click.option('--user-id', default='cli_user', help='User ID for the session.')
def analyse(query: str, mode: str, user_id: str):
    """Run a materials discovery analysis."""
    console = Console()
    _run_and_display_analysis(query, mode, user_id, console)

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
    # Add more stats display here if needed
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
    # Add other config values...
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

# --- Helper Function for Analysis ---

def _run_and_display_analysis(query: str, mode: str, user_id: str, console: Console):
    """
    Sets up a clean, live progress display and runs the analysis,
    translating verbose logs into a user-friendly status.
    """
    import logging
    import sys
    from io import StringIO
    from rich.panel import Panel
    from rich.text import Text

    # --- Live Progress Display Setup ---
    progress_panel = Panel("Initializing...", title="[bold cyan]Analysis Progress[/bold cyan]", border_style="green")
    live = Live(progress_panel, console=console, refresh_per_second=10)

    # --- Custom Logging Handler to Update the Live Display ---
    class RichProgressHandler(logging.Handler):
        def __init__(self, live_display):
            super().__init__()
            self.live_display = live_display
            self.last_message = "Initializing..."

        def emit(self, record):
            msg = record.getMessage()
            new_message = self.last_message

            # Define key stages and update message
            if "Generating structures" in msg:
                new_message = "Stage 1/3: Generating candidate structures..."
            elif "Calculating energies" in msg or "Calculating formation energy" in msg:
                new_message = "Stage 2/3: Calculating energies and stability..."
            elif "Creative pipeline complete" in msg or "Analysis complete" in msg:
                new_message = "Stage 3/3: Finalizing results..."

            if new_message != self.last_message:
                self.last_message = new_message
                self.live_display.update(Panel(Text(new_message, justify="left"),
                                               title="[bold cyan]Analysis Progress[/bold cyan]",
                                               border_style="green"))

    # --- Main Execution Logic ---
    original_stderr = sys.stderr
    log_capture_string = StringIO()
    
    try:
        with live:
            # 1. Set up our custom handler
            handler = RichProgressHandler(live)
            logging.basicConfig(level=logging.INFO, handlers=[handler], force=True)
            
            # 2. Redirect stderr to hide other warnings (like from e3nn)
            sys.stderr = log_capture_string

            # 3. Run the analysis
            result = asyncio.run(analyse_materials(query=query, mode=mode, user_id=user_id))

            # 4. Stop the live display and show final results
            live.stop()

            if result.get("status") == "completed":
                console.print(Panel("[bold green]Analysis Complete[/bold green]", expand=False))
                discovery_result = result.get("discovery_result", "No result found.")
                try:
                    parsed_result = json.loads(discovery_result)
                    pretty_result = json.dumps(parsed_result, indent=2)
                    console.print(Syntax(pretty_result, "json", theme="default", line_numbers=True))
                except (json.JSONDecodeError, TypeError):
                    console.print(Panel(discovery_result, title="Discovery Result", border_style="cyan"))
                metrics = result.get("metrics", {})
                if metrics:
                    table = Table(title="Performance Metrics")
                    table.add_column("Metric", style="cyan")
                    table.add_column("Value", style="magenta")
                    table.add_row("Elapsed Time", f"{metrics.get('elapsed_time', 0):.2f}s")
                    table.add_row("Tool Calls", str(metrics.get('tool_calls', 0)))
                    console.print(table)
            else:
                error_message = result.get("error", "An unknown error occurred.")
                console.print(Panel(f"[bold red]Analysis Failed[/bold red]\n\n{error_message}", expand=False))

    except Exception as e:
        live.stop()
        console.print(Panel(f"[bold red]An unexpected error occurred in the CLI[/bold red]\n\n{e}", expand=False))
    finally:
        # Restore logging and stderr
        logging.basicConfig(level=logging.WARNING, handlers=[logging.StreamHandler()], force=True)
        sys.stderr = original_stderr

def main():
    cli()

if __name__ == '__main__':
    main()

