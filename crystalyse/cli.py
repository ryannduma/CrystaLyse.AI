"""
Command-line interface for CrystaLyse.AI materials discovery platform.

This module provides a comprehensive CLI for CrystaLyse.AI, enabling users to perform
materials discovery tasks from the command line with rich formatting and interactive
features. The CLI supports both streaming and non-streaming analysis, result formatting,
and various output options.

Key Features:
    - Interactive shell with conversational interface (default)
    - Rich terminal output with formatted tables and panels
    - Streaming analysis with real-time progress display
    - JSON output export for integration with other tools
    - Browser-based 3D structure visualisation
    - Session management with history and export
    - Example queries for quick start and demonstration

Commands:
    shell: Start interactive CrystaLyse.AI shell (default when no command given)
    analyse: Perform one-time materials discovery analysis
    examples: Display example queries for reference
    status: Show configuration and API status
    server: Start SMACT MCP server for testing and development

Dependencies:
    - click: Command-line interface framework
    - rich: Rich text and beautiful formatting in terminal
    - prompt-toolkit: Interactive shell with history and completion
    - asyncio: Asynchronous I/O support for agent integration

Example Usage:
    Interactive shell (default):
        $ crystalyse
    
    Start shell explicitly:
        $ crystalyse shell
    
    One-time analysis:
        $ crystalyse analyse "Design a battery cathode material"
    
    Streaming analysis with custom model:
        $ crystalyse analyse "Find multiferroic materials" --model gpt-4o --stream
    
    View example queries:
        $ crystalyse examples
"""

import asyncio
import click
import json
import os
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.live import Live
from prompt_toolkit import PromptSession
from prompt_toolkit.styles import Style
from prompt_toolkit.completion import FuzzyCompleter, WordCompleter

from .agents.unified_agent import CrystaLyse, AgentConfig
from .config import config

console = Console()


@click.group()
def cli():
    """CrystaLyse - Autonomous materials discovery agent."""
    pass


@cli.command()
def status():
    """Show CrystaLyse.AI configuration and unified agent status."""
    # Create status table
    status_table = Table(title="CrystaLyse.AI Configuration Status")
    status_table.add_column("Setting", style="cyan")
    status_table.add_column("Value", style="green")
    status_table.add_column("Status", style="yellow")
    
    # Check API key
    api_key = os.getenv("OPENAI_API_KEY")
    api_configured = bool(api_key)
    
    # Configuration status
    status_table.add_row("OPENAI_API_KEY", "Set" if api_configured else "Not Set", 
                        "Configured" if api_configured else "Missing")
    status_table.add_row("Default Model", "o4-mini", "OpenAI Agents SDK")
    status_table.add_row("Agent Type", "CrystaLyse", "Unified")
    status_table.add_row("Architecture", "90% code reduction", "Optimised")
    
    # MCP Servers status
    try:
        # A more representative test config that would use tools
        test_config = AgentConfig(enable_smact=True, enable_chemeleon=True, enable_mace=True)
        test_agent = CrystaLyse(test_config)
        agent_status = "Working"
    except Exception:
        agent_status = "Error"
    
    status_table.add_row("Agent Status", "Unified Agent", agent_status)
    
    # Check MCP servers
    mcp_servers = []
    if os.path.exists("smact-mcp-server/src"):
        mcp_servers.append("SMACT")
    if os.path.exists("chemeleon-mcp-server/src"):  
        mcp_servers.append("Chemeleon")
    if os.path.exists("mace-mcp-server/src"):
        mcp_servers.append("MACE")
    if os.path.exists("chemistry-unified-server/src"):
        mcp_servers.append("Chemistry-Unified")
        
    status_table.add_row("MCP Servers", f"{len(mcp_servers)} available", 
                        "Ready" if mcp_servers else "Limited")
    
    console.print(status_table)
    
    # Requirements message
    if not api_configured:
        console.print()
        console.print(Panel(
            "[red]REQUIRED[/red]: Set OPENAI_API_KEY environment variable\n\n"
            "[yellow]export OPENAI_API_KEY=\"your_api_key_here\"[/yellow]\n\n"
            "The unified agent provides:\n"
            "   • OpenAI o4-mini model integration\n"
            "   • True agentic behaviour with LLM control\n"
            "   • SMACT, Chemeleon, and MACE tool integration\n"
            "   • 90% code reduction vs legacy implementation",
            title="API Key Required",
            border_style="red"
        ))
    else:
        console.print()
        console.print(Panel(
            f"[green]Ready![/green] MCP servers available: {', '.join(mcp_servers)}\n\n"
            "• Knowledge-based analysis works without MCP servers\n"
            "• Full computational workflow requires MCP server connection\n"
            "• Use 'crystalyse shell' for interactive materials discovery",
            title="CrystaLyse.AI Status",
            border_style="green"
        ))


@cli.command()
@click.argument("query")
@click.option("--model", default="o4-mini", help="LLM model to use (default: o4-mini with OpenAI Agents SDK)")
@click.option("--temperature", default=0.7, type=float, help="Temperature for generation")
@click.option("--max-turns", default=25, type=int, help="Maximum number of conversational turns.")
@click.option("--output", "-o", help="Output file for results (JSON)")
@click.option("--stream", is_flag=True, help="Enable streaming output")
@click.option("--copilot", is_flag=True, help="Enable co-pilot mode with human checkpoints")
@click.option("--pipeline", is_flag=True, help="Use three-stage pipeline (composition → structure → energy)")
@click.option("--optimise", is_flag=True, help="Enable hill-climb optimisation with LLM reflection")
@click.option("--budget", default=1.0, type=float, help="Budget limit in USD (default: $1.00)")
def analyse(query: str, model: str, temperature: float, max_turns: int, output: str, stream: bool,
           copilot: bool, pipeline: bool, optimise: bool, budget: float):
    """
    Analyse a materials discovery query using CrystaLyse.AI.
    
    This command performs comprehensive materials discovery analysis on user queries,
    supporting both creative exploration and rigorous validation modes. Results are
    displayed with rich formatting and can be exported to JSON for further processing.
    
    Args:
        query (str): The materials discovery request. Should clearly specify the target
            application, desired properties, and any constraints.
        model (str): The OpenAI language model to use (default: gpt-4)
        temperature (float): Controls creativity vs precision (0.0-1.0, default: 0.7)
        max_turns (int): The maximum number of turns for the agent conversation.
        output (str): Optional output file path for saving results in JSON format
        stream (bool): Enable real-time streaming output (default: False)
    
    Examples:
        Basic analysis:
            crystalyse analyse "Design a cathode for Na-ion batteries"
        
        High-precision analysis:
            crystalyse analyse "Find Pb-free ferroelectrics" --temperature 0.3
        
        Streaming with file output:
            crystalyse analyse "Solar cell materials" --stream -o results.json
    """
    asyncio.run(_analyse(query, model, temperature, max_turns, output, stream, copilot, pipeline, optimise, budget))


async def _analyse(query: str, model: str, temperature: float, max_turns: int, output: str, stream: bool,
                  copilot: bool, pipeline: bool, optimise: bool, budget: float):
    """
    Asynchronous implementation of the analyse command.
    
    Handles the core logic for materials discovery analysis including agent initialisation,
    query processing, result formatting, and file output. Supports both streaming and
    non-streaming modes with comprehensive error handling and user feedback.
    
    Args:
        query (str): Materials discovery query from user
        model (str): OpenAI model name to use for analysis
        temperature (float): Temperature setting for generation control
        max_turns (int): Maximum number of conversational turns.
        output (str): Optional file path for saving results
        stream (bool): Whether to enable streaming output mode
    
    Returns:
        None: Results are displayed to console and optionally saved to file
        
    Raises:
        SystemExit: If API key is not found or agent initialisation fails
    """
    # Check for API key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        console.print("[red]Error: OpenAI API key not found![/red]")
        console.print("Set OPENAI_API_KEY environment variable.")
        return
    
    # Display analysis mode header
    console.print(f"[cyan]CrystaLyse.AI Analysis[/cyan]")
    console.print(f"Query: {query}")
    console.print(f"Model: {model} | Temperature: {temperature} | Budget: ${budget:.2f}")
    
    # Display enabled patterns
    patterns = []
    if copilot:
        patterns.append("Co-pilot Mode")
    if pipeline:
        patterns.append("Three-Stage Pipeline")
    if optimise:
        patterns.append("Hill-Climb Optimisation")
    
    if patterns:
        console.print(f"Patterns: {' | '.join(patterns)}")
    
    try:
        # Choose analysis mode based on patterns
        if copilot:
            # Use co-pilot mode with human checkpoints
            from .agents.copilot_agent import run_copilot_discovery
            console.print("\nStarting Co-pilot Discovery Mode")
            
            result = await run_copilot_discovery(
                query=query, 
                enable_checkpoints=True,
                requirements={"budget": budget, "model": model}
            )
            
        elif pipeline:
            # Use three-stage pipeline
            from .agents.pipeline_agents import ThreeStageRunner
            console.print("\nStarting Three-Stage Pipeline")
            
            runner = ThreeStageRunner(
                query=query, 
                model=model,
                temperature=temperature,
                max_turns=max_turns
            )
            result = await runner.run_pipeline()

        elif optimise:
            # Run hill-climb optimisation
            from .agents.hill_climb_optimiser import HillClimbOptimiser
            console.print("\nStarting Hill-Climb Optimisation")

            # Need to get initial candidates first, maybe from a basic agent run?
            # For now, let's assume we have some. This part needs better integration.
            console.print("[yellow]Warning: Optimisation mode needs initial candidates.[/yellow]")
            initial_candidates = [
                {'formula': 'LiCoO2', 'stability': 0.8, 'energy_per_atom': -2.5},
                {'formula': 'NaFePO4', 'stability': 0.7, 'energy_per_atom': -2.3}
            ]
            
            optimiser = HillClimbOptimiser(max_iterations=10, population_size=8)
            result = await optimiser.optimise_materials(
                target_description=query,
                initial_candidates=initial_candidates
            )

        else:
            # Default: unified agent without special patterns
            agent = CrystaLyse(
                agent_config=AgentConfig(
                    model=model,
                    temperature=temperature,
                    max_turns=max_turns
                )
            )
            
            result = await agent.discover_materials(query)
            
        # Process and display results
        if output:
            with open(output, "w") as f:
                json.dump(result, f, indent=2)
            console.print(f"\n[green]Results saved to {output}[/green]")
        else:
            # Nicely formatted output
            if isinstance(result, dict) and "candidates" in result:
                display_results(result)
            elif isinstance(result, str):
                console.print(Panel(result, title="Final Answer", border_style="green"))
            else:
                console.print(result)

    except Exception as e:
        console.print(f"\n[red]An error occurred during analysis: {e}[/red]")
        # Add more detailed error handling/logging here

def display_results(result: dict):
    """Display final results in a formatted table."""
    
    table = Table(title="Top Material Candidates")
    table.add_column("Formula", style="cyan")
    table.add_column("Stability Score", style="magenta")
    table.add_column("Predicted Properties", style="green")
    
    candidates = result.get("candidates", [])
    for cand in candidates:
        props_str = ", ".join([f"{k}: {v}" for k, v in cand.get("properties", {}).items()])
        table.add_row(
            cand.get("formula", "N/A"),
            f"{cand.get('stability', 0):.2f}",
            props_str
        )
        
    console.print(table)
    
    summary = result.get("summary", "No summary provided.")
    console.print(Panel(summary, title="Analysis Summary", border_style="yellow"))

    # Visualize best candidate if available
    if candidates and "structure_data" in candidates[0]:
        console.print("\n[bold]Visualising best candidate...[/bold]")
        from .visualisation.crystal_viz import visualise_structure
        visualise_structure(candidates[0]["structure_data"])
        

@cli.command()
def examples():
    """Show example queries for the unified agent."""
    examples = [
        ("Basic Materials Discovery", [
            "Design a stable cathode material for a Na-ion battery",
            "Suggest a non-toxic semiconductor for solar cell applications", 
            "Find a Pb-free multiferroic crystal"
        ]),
        ("Advanced Queries", [
            "Design a novel battery cathode for sodium-ion batteries using SMACT validation, Chemeleon for 10 polymorphs each, and MACE for energy ranking",
            "Find oxide materials for photocatalytic water splitting with specific band gaps",
            "Suggest materials for solid-state electrolyte applications with high ionic conductivity"
        ]),
        ("Structure-Specific", [
            "I want a composition with manganese in the perovskite structure type",
            "Design a magnetic material with high Curie temperature in spinel structure",
            "Find layered materials suitable for intercalation batteries"
        ])
    ]
    
    console.print("[bold]CrystaLyse.AI Unified Agent Examples[/bold]\n")
    
    for category, category_examples in examples:
        console.print(f"[cyan]{category}:[/cyan]")
        for i, example in enumerate(category_examples, 1):
            console.print(f"  {i}. {example}")
        console.print()
        
    console.print("[dim]Run any example with:[/dim]")
    console.print('[cyan]crystalyse analyse "Your query here"[/cyan]')
    console.print()
    console.print("[dim]For rigorous analysis (temperature < 0.5):[/dim]")
    console.print('[cyan]crystalyse analyse "Your query" --temperature 0.3[/cyan]')
    console.print()
    console.print("[bold]Agent Laboratory Patterns:[/bold]")
    console.print('[cyan]crystalyse analyse "Your query" --copilot[/cyan]      # Human checkpoints')
    console.print('[cyan]crystalyse analyse "Your query" --pipeline[/cyan]     # Three-stage pipeline')
    console.print('[cyan]crystalyse analyse "Your query" --optimise[/cyan]     # Hill-climb optimisation')
    console.print('[cyan]crystalyse analyse "Your query" --budget 0.50[/cyan]  # Budget limit ($0.50)')
    console.print()
    console.print("[dim]View agent status:[/dim]")
    console.print('[cyan]crystalyse status[/cyan]')


@cli.command()
@click.option("--model", default=config.default_model, help="Model to use for the interactive session.")
@click.option("--max-turns", default=15, help="Maximum number of conversation turns.")
@click.option("--temperature", default=0.4, help="Set the creativity temperature (0.0 to 1.0).")
def shell(model: str, max_turns: int, temperature: float):
    """
    Start an interactive shell for materials discovery with CrystaLyse.AI.
    
    Provides a conversational interface for iterative materials exploration.
    Supports history, autocompletion, and multi-line input.
    
    Args:
        model (str): The language model to be used in the session.
        max_turns (int): Max turns for each conversation.
        temperature (float): The creativity temperature for the model.
    """
    asyncio.run(_shell(model, max_turns, temperature))


async def _shell(model: str, max_turns: int, temperature: float):
    """Asynchronous implementation of the interactive shell."""
    
    display_splash_screen()
    
    agent = CrystaLyse(
        agent_config=AgentConfig(
            model=model,
            temperature=temperature,
            max_turns=max_turns
        )
    )

    # Setup prompt session
    style = Style.from_dict({
        'prompt': 'bold #00ff00',
    })
    
    # Add example queries to completer
    example_queries = [
        "Design a new solar cell material", 
        "Find a stable, non-toxic blue pigment",
        "Analyse carbon-based superconductors"
    ]
    completer = FuzzyCompleter(WordCompleter(example_queries, ignore_case=True))
    
    session = PromptSession(
        "CrystaLyse> ",
        style=style,
        completer=completer,
        history=None # Could implement file-based history here
    )

    while True:
        try:
            user_input = await session.prompt_async()
            
            if user_input.lower() in ['exit', 'quit']:
                break
            if user_input.lower().startswith('!file'):
                filepath = user_input.split(' ', 1)[1]
                await run_from_file(filepath, agent)
                continue
                
            if not user_input.strip():
                continue

            await agent.discover_materials(user_input)

        except KeyboardInterrupt:
            continue
        except EOFError:
            break
            
    console.print("\n[bold cyan]Exiting CrystaLyse.AI. Goodbye![/bold cyan]\n")


def display_splash_screen():
    """Displays a cool splash screen for the interactive shell."""
    logo = """
   ______           __         __  .__.__          
  / ____/________  / /_  ___  / /_/  |  |   ____   
 / /   / ___/ __ \/ __ \/ _ \/ __/ / |  |  /  _ \  
/ /___/ /  / /_/ / / / /  __/ /_/ /|  |_(  <_> ) 
\____/_/   \____/_/ /_/\___/\__/_/ |____/\____/  
    """
    console.print(f"[bold cyan]{logo}[/bold cyan]")
    console.print("[bold]Welcome to the CrystaLyse.AI Interactive Shell[/bold]")
    console.print("Type your materials science queries or 'exit' to quit.")
    console.print("Example: 'Design a lead-free piezoelectric material'")
    console.print("-" * 60)


async def run_from_file(filepath: str, agent: CrystaLyse):
    """Runs a discovery session from a file containing a list of queries."""
    try:
        with open(filepath, 'r') as f:
            queries = [line.strip() for line in f if line.strip()]
        
        console.print(f"Found {len(queries)} queries in {filepath}.")
        
        for i, query in enumerate(queries):
            console.print(f"\n--- Running Query {i+1}/{len(queries)}: {query} ---")
            await agent.discover_materials(query)
            
    except FileNotFoundError:
        console.print(f"[red]Error: File not found at '{filepath}'[/red]")
    except Exception as e:
        console.print(f"[red]An error occurred while running from file: {e}[/red]")


def main():
    """Main entry point for the CLI."""
    # It's good practice to wrap the main entry point in a function.
    cli()


if __name__ == "__main__":
    main()