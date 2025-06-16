"""
Command-line interface for CrystaLyse.AI materials discovery platform.

This module provides a comprehensive CLI for CrystaLyse.AI, enabling users to perform
materials discovery tasks from the command line with rich formatting and interactive
features. The CLI supports both streaming and non-streaming analysis, result formatting,
and various output options.

Key Features:
    - Rich terminal output with formatted tables and panels
    - Streaming analysis with real-time progress display
    - JSON output export for integration with other tools
    - Example queries for quick start and demonstration
    - Built-in SMACT MCP server management for testing

Commands:
    analyze: Perform materials discovery analysis on user queries
    examples: Display example queries for reference
    server: Start SMACT MCP server for testing and development

Dependencies:
    - click: Command-line interface framework
    - rich: Rich text and beautiful formatting in terminal
    - asyncio: Asynchronous I/O support for agent integration

Example Usage:
    Basic analysis:
        $ crystalyse analyze "Design a battery cathode material"
    
    Streaming analysis with custom model:
        $ crystalyse analyze "Find multiferroic materials" --model gpt-4o --stream
    
    Save results to file:
        $ crystalyse analyze "Photovoltaic semiconductors" -o results.json
    
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

from .agents import CrystaLyseAgent
from .config import get_agent_config, verify_rate_limits, DEFAULT_MODEL
try:
    from .models import CrystalAnalysisResult
except ImportError:
    # Handle case where models module might not exist
    CrystalAnalysisResult = None

console = Console()


@click.group()
def cli():
    """CrystaLyse - Autonomous materials discovery agent."""
    pass


@cli.command()
def status():
    """Show CrystaLyse.AI configuration and rate limits status."""
    rate_limits = verify_rate_limits()
    
    # Create status table
    status_table = Table(title="🚀 CrystaLyse.AI Configuration Status")
    status_table.add_column("Setting", style="cyan")
    status_table.add_column("Value", style="green")
    status_table.add_column("Status", style="yellow")
    
    # API Configuration
    api_status = "✅ Configured" if rate_limits["mdg_api_configured"] else "❌ Missing"
    api_key_status = "MDG API Key" if rate_limits["mdg_api_configured"] else "Not Set"
    
    status_table.add_row("OPENAI_MDG_API_KEY", api_key_status, api_status)
    status_table.add_row("Default Model", DEFAULT_MODEL, "✅ Optimized")
    
    # Rate Limits
    if rate_limits["mdg_api_configured"]:
        status_table.add_row("Tokens/Minute", "2,000,000", "🚀 High Performance")
        status_table.add_row("Requests/Minute", "10,000", "🚀 High Performance")
        status_table.add_row("Tokens/Day", "200,000,000", "🚀 High Performance")
        status_table.add_row("Batch Size", str(rate_limits["recommended_batch_size"]), "🚀 Optimized")
    else:
        status_table.add_row("Status", "API Key Required", "❌ Cannot operate")
        status_table.add_row("Batch Size", str(rate_limits["recommended_batch_size"]), "❌ Disabled")
    
    console.print(status_table)
    
    # Requirements message
    if not rate_limits["mdg_api_configured"]:
        console.print()
        console.print(Panel(
            "🔑 [red]REQUIRED[/red]: Set OPENAI_MDG_API_KEY environment variable\n\n"
            "[yellow]export OPENAI_MDG_API_KEY=\"your_mdg_key_here\"[/yellow]\n\n"
            "This provides:\n"
            "   • 2,000,000 tokens per minute\n"
            "   • 10,000 requests per minute\n"
            "   • 200,000,000 tokens per day\n"
            "   • Optimized batch processing for materials discovery",
            title="API Key Required",
            border_style="red"
        ))


@cli.command()
@click.argument("query")
@click.option("--model", default=DEFAULT_MODEL, help="LLM model to use (optimized default: gpt-4o)")
@click.option("--temperature", default=0.7, type=float, help="Temperature for generation")
@click.option("--output", "-o", help="Output file for results (JSON)")
@click.option("--stream", is_flag=True, help="Enable streaming output")
def analyze(query: str, model: str, temperature: float, output: str, stream: bool):
    """
    Analyze a materials discovery query using CrystaLyse.AI.
    
    This command performs comprehensive materials discovery analysis on user queries,
    supporting both creative exploration and rigorous validation modes. Results are
    displayed with rich formatting and can be exported to JSON for further processing.
    
    Args:
        query (str): The materials discovery request. Should clearly specify the target
            application, desired properties, and any constraints.
        model (str): The OpenAI language model to use (default: gpt-4)
        temperature (float): Controls creativity vs precision (0.0-1.0, default: 0.7)
        output (str): Optional output file path for saving results in JSON format
        stream (bool): Enable real-time streaming output (default: False)
    
    Examples:
        Basic analysis:
            crystalyse analyze "Design a cathode for Na-ion batteries"
        
        High-precision analysis:
            crystalyse analyze "Find Pb-free ferroelectrics" --temperature 0.3
        
        Streaming with file output:
            crystalyse analyze "Solar cell materials" --stream -o results.json
    """
    asyncio.run(_analyze(query, model, temperature, output, stream))


async def _analyze(query: str, model: str, temperature: float, output: str, stream: bool):
    """
    Asynchronous implementation of the analyze command.
    
    Handles the core logic for materials discovery analysis including agent initialization,
    query processing, result formatting, and file output. Supports both streaming and
    non-streaming modes with comprehensive error handling and user feedback.
    
    Args:
        query (str): Materials discovery query from user
        model (str): OpenAI model name to use for analysis
        temperature (float): Temperature setting for generation control
        output (str): Optional file path for saving results
        stream (bool): Whether to enable streaming output mode
    
    Returns:
        None: Results are displayed to console and optionally saved to file
        
    Raises:
        SystemExit: If API key is not found or agent initialization fails
    """
    # Check for API key
    api_key = os.getenv("OPENAI_MDG_API_KEY") or os.getenv("OPENAI_API_KEY")
    if not api_key:
        console.print("[red]Error: OpenAI API key not found![/red]")
        console.print("Set OPENAI_MDG_API_KEY or OPENAI_API_KEY environment variable.")
        return
        
    # Initialize agent
    console.print(f"[cyan]Initializing CrystaLyse with {model}...[/cyan]")
    
    try:
        agent = CrystaLyseAgent(model=model, temperature=temperature)
    except Exception as e:
        console.print(f"[red]Error initializing agent: {e}[/red]")
        return
        
    # Display query
    console.print(Panel(query, title="Query", border_style="blue"))
    
    # Run analysis
    if stream:
        console.print("[cyan]Streaming analysis...[/cyan]\n")
        result = await _analyze_streamed(agent, query)
    else:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Analyzing...", total=None)
            result = await agent.analyze(query)
            progress.remove_task(task)
    
    # Parse and display results
    try:
        if isinstance(result, str):
            # Try to parse as JSON
            try:
                result_data = json.loads(result)
                _display_results(result_data)
            except json.JSONDecodeError:
                # Display as text
                console.print(Panel(result, title="Analysis Result", border_style="green"))
        else:
            _display_results(result)
            
        # Save to file if requested
        if output:
            with open(output, "w") as f:
                if isinstance(result, str):
                    f.write(result)
                else:
                    json.dump(result, f, indent=2)
            console.print(f"\n[green]Results saved to {output}[/green]")
            
    except Exception as e:
        console.print(f"[red]Error displaying results: {e}[/red]")
        console.print(result)


async def _analyze_streamed(agent: CrystaLyseAgent, query: str):
    """Handle streamed analysis."""
    full_response = ""
    current_tool = None
    
    async for event in agent.analyze_streamed(query):
        if event.type == "agent_update":
            if event.data.get("tool_name"):
                current_tool = event.data["tool_name"]
                console.print(f"\n[yellow]Using tool: {current_tool}[/yellow]")
        elif event.type == "text":
            text = event.data.get("text", "")
            console.print(text, end="")
            full_response += text
        elif event.type == "tool_result":
            if current_tool:
                console.print(f"[dim]Tool {current_tool} completed[/dim]")
                current_tool = None
                
    return full_response


def _display_results(result_data: dict):
    """Display analysis results in a formatted way."""
    if "top_candidates" in result_data:
        # Display candidates table
        table = Table(title="Top Material Candidates", show_header=True)
        table.add_column("Rank", style="cyan", width=6)
        table.add_column("Formula", style="magenta")
        table.add_column("Validation", style="green")
        table.add_column("Novelty", style="yellow")
        table.add_column("Structure", style="blue")
        table.add_column("Family", style="dim")
        
        for candidate in result_data["top_candidates"]:
            structures = candidate.get("proposed_structures", [])
            structure_str = structures[0]["structure_type"] if structures else "unknown"
            
            validation_style = "green" if candidate["validation"] == "valid" else "yellow"
            
            table.add_row(
                str(candidate["rank"]),
                candidate["formula"],
                f"[{validation_style}]{candidate['validation']}[/{validation_style}]",
                candidate["novelty"],
                structure_str,
                candidate.get("chemical_family", "")
            )
            
        console.print("\n")
        console.print(table)
        
        # Display summary
        if "generation_summary" in result_data:
            summary = result_data["generation_summary"]
            console.print("\n[bold]Generation Summary:[/bold]")
            console.print(f"  Total generated: {summary['total_generated']}")
            console.print(f"  Valid: {summary['valid']}")
            console.print(f"  Overridden: {summary['overridden']}")
            console.print(f"  Selected: {summary['selected']}")
            
        # Display detailed info for top candidate
        if result_data["top_candidates"]:
            top = result_data["top_candidates"][0]
            console.print(f"\n[bold]Top Candidate Details:[/bold]")
            console.print(f"  Formula: [magenta]{top['formula']}[/magenta]")
            if top.get("reasoning"):
                console.print(f"  Reasoning: {top['reasoning']}")
            if top.get("synthesis_notes"):
                console.print(f"  Synthesis: {top['synthesis_notes']}")
                
    else:
        # Generic display
        console.print(Panel(json.dumps(result_data, indent=2), title="Analysis Result"))


@cli.command()
def examples():
    """Show example queries."""
    examples = [
        "Design a stable cathode material for a Na-ion battery",
        "Suggest a non-toxic semiconductor for solar cell applications",
        "Find a Pb-free multiferroic crystal",
        "I want a composition with manganese in the perovskite structure type",
        "Design a magnetic material with high Curie temperature",
        "Suggest materials for solid-state electrolyte applications",
        "Find oxide materials for photocatalytic water splitting"
    ]
    
    console.print("[bold]Example Queries:[/bold]\n")
    for i, example in enumerate(examples, 1):
        console.print(f"  {i}. {example}")
        
    console.print("\n[dim]Run any example with:[/dim]")
    console.print('[cyan]crystalyse analyze "Your query here"[/cyan]')


@cli.command()
def server():
    """Start the SMACT MCP server (for testing)."""
    console.print("[cyan]Starting SMACT MCP server...[/cyan]")
    smact_path = os.path.join(os.path.dirname(__file__), "..", "..", "smact-mcp-server")
    os.system(f"cd {smact_path} && python -m smact_mcp.server")


def main():
    """Main entry point."""
    cli()


if __name__ == "__main__":
    main()