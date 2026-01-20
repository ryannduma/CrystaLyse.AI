#!/usr/bin/env python3
"""
Analyze captured provenance data
"""

import json
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

# Add provenance system to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import typer
from rich.console import Console
from rich.table import Table

app = typer.Typer()


def load_session_data(session_dir: Path) -> dict:
    """Load all data for a session."""
    data = {"events": [], "materials": [], "summary": {}, "assistant_response": ""}

    # Load events
    events_file = session_dir / "events.jsonl"
    if events_file.exists():
        with open(events_file) as f:
            for line in f:
                if line.strip():
                    data["events"].append(json.loads(line))

    # Load materials catalog
    catalog_file = session_dir / "materials_catalog.json"
    if catalog_file.exists():
        with open(catalog_file) as f:
            data["materials"] = json.load(f)

    # Load summary
    summary_file = session_dir / "summary.json"
    if summary_file.exists():
        with open(summary_file) as f:
            data["summary"] = json.load(f)

    # Load assistant response
    response_file = session_dir / "assistant_full.md"
    if response_file.exists():
        with open(response_file) as f:
            data["assistant_response"] = f.read()

    return data


@app.command()
def analyze(
    session_path: str = typer.Argument(..., help="Path to session directory"),
    show_timeline: bool = typer.Option(False, "--timeline", help="Show event timeline"),
    show_materials: bool = typer.Option(False, "--materials", help="Show materials details"),
    show_tools: bool = typer.Option(False, "--tools", help="Show tool usage details"),
):
    """Analyze a provenance session."""

    console = Console()
    session_dir = Path(session_path)

    if not session_dir.exists():
        console.print(f"[red]Session directory not found:[/red] {session_path}")
        return

    # Load session data
    console.print(f"[cyan]Loading session:[/cyan] {session_dir.name}\n")
    data = load_session_data(session_dir)

    # Show summary
    summary = data["summary"]
    if summary:
        console.print("[bold]Session Summary:[/bold]")
        console.print(f"  Session ID: {summary.get('session_id', 'unknown')}")
        console.print(f"  Total time: {summary.get('total_time_s', 0):.1f}s")
        console.print(f"  TTFB: {summary.get('ttfb_ms', 'N/A')}ms")
        console.print(f"  Materials found: {summary.get('materials_found', 0)}")
        console.print(f"  Unique compositions: {summary.get('unique_compositions', 0)}")

        # Energy statistics
        mat_summary = summary.get("materials_summary", {})
        if mat_summary.get("avg_energy"):
            console.print(
                f"  Energy range: {mat_summary['min_energy']:.3f} to {mat_summary['max_energy']:.3f} eV/atom"
            )
            console.print(f"  Average energy: {mat_summary['avg_energy']:.3f} eV/atom")

    # Show event timeline
    if show_timeline and data["events"]:
        console.print("\n[bold]Event Timeline:[/bold]")

        table = Table()
        table.add_column("Time (s)", style="cyan")
        table.add_column("Event", style="yellow")
        table.add_column("Details", style="white")

        start_time = None
        for event in data["events"]:
            event_time = datetime.fromisoformat(event["ts"])
            if start_time is None:
                start_time = event_time
                rel_time = 0.0
            else:
                rel_time = (event_time - start_time).total_seconds()

            event_type = event["type"]
            details = ""

            if event_type == "tool_start":
                details = f"Tool: {event['data'].get('wrapper', 'unknown')}"
            elif event_type == "tool_end":
                mcp_tool = event["data"].get("mcp_tool", "unknown")
                duration = event["data"].get("duration_ms", 0)
                materials = event["data"].get("materials_count", 0)
                details = f"MCP: {mcp_tool}, {duration:.1f}ms, {materials} materials"
            elif event_type == "ttfb":
                details = f"Time to first byte: {event['data'].get('time_ms', 0):.1f}ms"

            table.add_row(f"{rel_time:.2f}", event_type, details)

        console.print(table)

    # Show materials details
    if show_materials and data["materials"]:
        console.print("\n[bold]Materials Discovered:[/bold]")

        table = Table()
        table.add_column("Composition", style="cyan")
        table.add_column("Formula", style="yellow")
        table.add_column("Energy (eV/atom)", style="green")
        table.add_column("Space Group", style="magenta")
        table.add_column("Source Tool", style="white")

        for mat in data["materials"]:
            energy = mat.get("formation_energy")
            energy_str = f"{energy:.4f}" if energy else "N/A"

            table.add_row(
                mat.get("composition", ""),
                mat.get("formula", ""),
                energy_str,
                mat.get("space_group", ""),
                mat.get("source_tool", ""),
            )

        console.print(table)

    # Show tool usage
    if show_tools and summary.get("mcp_tools"):
        console.print("\n[bold]MCP Tool Usage:[/bold]")

        table = Table()
        table.add_column("Tool", style="cyan")
        table.add_column("Calls", style="yellow")
        table.add_column("Avg Time (ms)", style="green")
        table.add_column("Materials", style="magenta")

        for tool_name, stats in summary["mcp_tools"].items():
            table.add_row(
                tool_name,
                str(stats.get("count", 0)),
                f"{stats.get('avg_ms', 0):.1f}",
                str(stats.get("materials", 0)),
            )

        console.print(table)

    # Event type distribution
    if data["events"]:
        console.print("\n[bold]Event Distribution:[/bold]")
        event_types = Counter(e["type"] for e in data["events"])
        for event_type, count in event_types.most_common():
            console.print(f"  {event_type}: {count}")


@app.command()
def compare(
    session1: str = typer.Argument(..., help="First session directory"),
    session2: str = typer.Argument(..., help="Second session directory"),
):
    """Compare two provenance sessions."""

    console = Console()

    # Load both sessions
    data1 = load_session_data(Path(session1))
    data2 = load_session_data(Path(session2))

    s1 = data1["summary"]
    s2 = data2["summary"]

    console.print("[bold]Session Comparison:[/bold]\n")

    table = Table()
    table.add_column("Metric", style="cyan")
    table.add_column(Path(session1).name, style="yellow")
    table.add_column(Path(session2).name, style="green")
    table.add_column("Difference", style="magenta")

    # Compare metrics
    metrics = [
        ("Total Time (s)", "total_time_s", lambda x: f"{x:.1f}"),
        ("TTFB (ms)", "ttfb_ms", lambda x: f"{x:.1f}" if x else "N/A"),
        ("Materials Found", "materials_found", str),
        ("Unique Compositions", "unique_compositions", str),
        ("Tool Calls", "tool_calls_total", str),
    ]

    for metric_name, key, formatter in metrics:
        val1 = s1.get(key, 0)
        val2 = s2.get(key, 0)

        if isinstance(val1, int | float) and isinstance(val2, int | float):
            diff = val2 - val1
            if diff > 0:
                diff_str = f"+{formatter(diff)}"
            else:
                diff_str = formatter(diff)
        else:
            diff_str = "-"

        table.add_row(
            metric_name,
            formatter(val1) if val1 else "N/A",
            formatter(val2) if val2 else "N/A",
            diff_str,
        )

    console.print(table)

    # Compare materials
    mats1 = {m["composition"] for m in data1["materials"]}
    mats2 = {m["composition"] for m in data2["materials"]}

    unique_to_1 = mats1 - mats2
    unique_to_2 = mats2 - mats1
    common = mats1 & mats2

    console.print("\n[bold]Materials Comparison:[/bold]")
    console.print(f"  Common: {len(common)}")
    console.print(f"  Unique to session 1: {len(unique_to_1)}")
    console.print(f"  Unique to session 2: {len(unique_to_2)}")

    if unique_to_1:
        console.print(f"\n  Session 1 only: {', '.join(sorted(unique_to_1))}")
    if unique_to_2:
        console.print(f"  Session 2 only: {', '.join(sorted(unique_to_2))}")


if __name__ == "__main__":
    app()
