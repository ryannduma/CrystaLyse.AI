#!/usr/bin/env python3
"""
Test provenance capture across all CrystaLyse modes
"""

import asyncio
import sys
import json
from pathlib import Path
from datetime import datetime

# Add provenance system to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from integration import CrystaLyseWithProvenance
from rich.console import Console
from rich.table import Table


async def test_mode(mode: str, query: str, console: Console) -> dict:
    """Test a single mode."""
    
    console.print(f"\n[cyan]Testing {mode} mode...[/cyan]")
    
    # Initialize with provenance
    crystalyse = CrystaLyseWithProvenance(
        mode=mode,
        provenance_dir=f"./test_provenance_{mode}",
        enable_visual=False,  # Disable visual for cleaner output
        console=console
    )
    
    # Run discovery
    start_time = datetime.now()
    result = await crystalyse.discover(query, timeout=300)
    end_time = datetime.now()
    
    # Extract metrics
    provenance = result.get("provenance", {})
    summary = provenance.get("summary", {})
    
    test_result = {
        "mode": mode,
        "status": result.get("status"),
        "duration_s": (end_time - start_time).total_seconds(),
        "materials_found": summary.get("materials_found", 0),
        "unique_compositions": summary.get("unique_compositions", 0),
        "materials_with_energy": summary.get("materials_summary", {}).get("with_energy", 0),
        "mcp_tools": list(summary.get("mcp_tools", {}).keys()),
        "session_id": provenance.get("session_id"),
        "output_dir": provenance.get("output_dir")
    }
    
    # Check energy capture rate
    if test_result["materials_found"] > 0:
        test_result["energy_capture_rate"] = (
            test_result["materials_with_energy"] / test_result["materials_found"] * 100
        )
    else:
        test_result["energy_capture_rate"] = 0
    
    return test_result


async def main():
    """Test all modes and compare results."""
    
    console = Console()
    
    console.print("[bold cyan]CrystaLyse Provenance System Test[/bold cyan]")
    console.print("Testing provenance capture across all discovery modes\n")
    
    # Test query
    query = "Predict five new stable quaternary compositions formed of K, Y, Zr and O"
    console.print(f"[bold]Query:[/bold] {query}")
    
    # Test each mode
    modes = ["creative", "balanced", "rigorous"]
    results = []
    
    for mode in modes:
        try:
            result = await test_mode(mode, query, console)
            results.append(result)
            
            if result["status"] == "completed":
                console.print(f"[green]✓ {mode}: {result['materials_found']} materials, "
                            f"{result['energy_capture_rate']:.0f}% with energies[/green]")
            else:
                console.print(f"[red]✗ {mode}: {result['status']}[/red]")
                
        except Exception as e:
            console.print(f"[red]✗ {mode}: Error - {str(e)}[/red]")
            results.append({
                "mode": mode,
                "status": "error",
                "error": str(e)
            })
    
    # Display comparison table
    console.print("\n[bold]Mode Comparison:[/bold]")
    
    table = Table(title="Provenance Capture Results")
    table.add_column("Mode", style="cyan")
    table.add_column("Status", style="green")
    table.add_column("Duration (s)", style="yellow")
    table.add_column("Materials", style="magenta")
    table.add_column("With Energy", style="magenta")
    table.add_column("Energy %", style="blue")
    table.add_column("MCP Tools", style="white")
    
    for result in results:
        table.add_row(
            result["mode"],
            result.get("status", "unknown"),
            f"{result.get('duration_s', 0):.1f}",
            str(result.get("materials_found", 0)),
            str(result.get("materials_with_energy", 0)),
            f"{result.get('energy_capture_rate', 0):.0f}%",
            ", ".join(result.get("mcp_tools", []))[:40]
        )
    
    console.print(table)
    
    # Save test results
    test_summary = {
        "test_timestamp": datetime.now().isoformat(),
        "query": query,
        "results": results
    }
    
    with open("provenance_test_results.json", "w") as f:
        json.dump(test_summary, f, indent=2)
    
    console.print("\n[bold]Test results saved to:[/bold] provenance_test_results.json")
    
    # Verify provenance completeness
    console.print("\n[bold]Provenance Completeness Check:[/bold]")
    
    all_complete = True
    for result in results:
        if result.get("status") == "completed":
            mode = result["mode"]
            output_dir = Path(result.get("output_dir", ""))
            
            # Check for expected files
            expected_files = [
                "events.jsonl",
                "materials.jsonl", 
                "materials_catalog.json",
                "summary.json",
                "assistant_full.md"
            ]
            
            missing = []
            for file_name in expected_files:
                if not (output_dir / file_name).exists():
                    missing.append(file_name)
            
            if missing:
                console.print(f"  [yellow]⚠ {mode}: Missing {', '.join(missing)}[/yellow]")
                all_complete = False
            else:
                # Check energy capture
                if result.get("energy_capture_rate", 0) < 100:
                    console.print(f"  [yellow]⚠ {mode}: Only {result['energy_capture_rate']:.0f}% materials have energies[/yellow]")
                else:
                    console.print(f"  [green]✓ {mode}: Complete provenance with all energies[/green]")
    
    if all_complete:
        console.print("\n[bold green]✓ All modes have complete provenance capture![/bold green]")
    else:
        console.print("\n[bold yellow]⚠ Some modes have incomplete provenance[/bold yellow]")


if __name__ == "__main__":
    asyncio.run(main())