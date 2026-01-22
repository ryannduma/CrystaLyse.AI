#!/usr/bin/env python3
"""
Simple discovery example with provenance capture
"""

import asyncio
import sys
from pathlib import Path

# Add provenance system to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from integration import CrystaLyseWithProvenance
from rich.console import Console


async def main():
    """Run a simple discovery with provenance."""

    console = Console()

    # Initialize CrystaLyse with provenance
    crystalyse = CrystaLyseWithProvenance(
        mode="creative", provenance_dir="./example_provenance", enable_visual=True, console=console
    )

    # Discovery query
    query = "Find stable binary oxides of titanium"

    console.print(f"[bold cyan]Running discovery:[/bold cyan] {query}")
    console.print("[yellow]Mode:[/yellow] creative\n")

    # Run discovery
    result = await crystalyse.discover(query)

    # Check results
    if result.get("status") == "completed":
        provenance = result.get("provenance", {})
        summary = provenance.get("summary", {})

        console.print("\n[bold green]✓ Discovery complete![/bold green]")
        console.print(f"Materials found: {summary.get('materials_found', 0)}")
        console.print(f"Unique compositions: {summary.get('unique_compositions', 0)}")
        console.print(f"Total time: {summary.get('total_time_s', 0):.1f}s")

        # Show MCP tools used
        if summary.get("mcp_tools"):
            console.print("\n[bold]MCP Tools Used:[/bold]")
            for tool, stats in summary["mcp_tools"].items():
                console.print(f"  • {tool}: {stats['count']} calls, {stats['materials']} materials")

        # Show provenance location
        console.print(f"\n[bold]Provenance saved to:[/bold] {provenance.get('output_dir')}")

        # Get materials catalog
        session_id = provenance.get("session_id")
        materials = crystalyse.get_materials_catalog(session_id)

        if materials:
            console.print("\n[bold]Materials Discovered:[/bold]")
            for mat in materials[:5]:  # Show first 5
                energy = mat.get("formation_energy")
                energy_str = f"{energy:.3f} eV/atom" if energy else "N/A"
                console.print(f"  • {mat.get('composition')}: {energy_str}")

            if len(materials) > 5:
                console.print(f"  ... and {len(materials) - 5} more")

    else:
        console.print(f"[red]Discovery failed:[/red] {result.get('error', 'Unknown error')}")


if __name__ == "__main__":
    asyncio.run(main())
