"""
Enhanced Result Formatter for Crystalyse

Provides beautiful, readable formatting for JSON outputs and tool results,
making complex scientific data easily digestible for users.
"""

import json
from typing import Any

from rich.console import Console
from rich.json import JSON
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table


class EnhancedResultFormatter:
    """
    Formats tool results and JSON data in a beautiful, readable way.

    Features:
    - Intelligent JSON formatting with syntax highlighting
    - Scientific data-aware formatting (energies, structures, etc.)
    - Structured output for chemistry tools
    - Expandable/collapsible large data
    """

    def __init__(self, console: Console):
        self.console = console

    def format_tool_result(
        self, tool_name: str, result: Any, tool_args: dict | None = None
    ) -> None:
        """
        Format and display a tool result in an enhanced way.

        Args:
            tool_name: Name of the tool that was called
            result: The result from the tool
            tool_args: Optional arguments that were passed to the tool
        """
        try:
            # Try to parse JSON if it's a string
            if isinstance(result, str) and result.strip().startswith(("{", "[")):
                try:
                    parsed_result = json.loads(result)
                    self._format_structured_result(tool_name, parsed_result, tool_args)
                    return
                except json.JSONDecodeError:
                    pass

            # Handle already parsed JSON/dict
            if isinstance(result, dict | list):
                self._format_structured_result(tool_name, result, tool_args)
                return

            # Handle plain text results
            self._format_text_result(tool_name, result, tool_args)

        except Exception:
            # Fallback to simple display
            self.console.print(
                Panel(
                    str(result), title=f"[bold][=] {tool_name} Result[/bold]", border_style="cyan"
                )
            )

    def _format_structured_result(
        self, tool_name: str, data: dict | list, tool_args: dict | None = None
    ) -> None:
        """Format structured JSON/dict data with scientific data awareness."""

        # Detect the type of scientific data and format accordingly
        if isinstance(data, dict):
            if self._is_chemistry_result(data):
                self._format_chemistry_result(tool_name, data, tool_args)
            elif self._is_energy_result(data):
                self._format_energy_result(tool_name, data, tool_args)
            elif self._is_structure_result(data):
                self._format_structure_result(tool_name, data, tool_args)
            else:
                self._format_generic_dict(tool_name, data, tool_args)
        elif isinstance(data, list):
            self._format_list_result(tool_name, data, tool_args)
        else:
            self._format_generic_result(tool_name, data, tool_args)

    def _is_chemistry_result(self, data: dict) -> bool:
        """Check if data looks like a chemistry validation result."""
        chemistry_keys = {"composition", "is_valid", "elements", "counts", "formula"}
        return any(key in data for key in chemistry_keys)

    def _is_energy_result(self, data: dict) -> bool:
        """Check if data looks like an energy calculation result."""
        energy_keys = {"formation_energy", "total_energy", "energy_per_atom", "status"}
        return any(key in data for key in energy_keys)

    def _is_structure_result(self, data: dict) -> bool:
        """Check if data looks like a crystal structure result."""
        structure_keys = {"structures", "num_structures", "cell", "positions", "sample_index"}
        return any(key in data for key in structure_keys)

    def _format_chemistry_result(
        self, tool_name: str, data: dict, tool_args: dict | None = None
    ) -> None:
        """Format chemistry validation results beautifully."""
        table = Table(show_header=False, box=None)
        table.add_column("Property", style="cyan", width=20)
        table.add_column("Value", style="white", width=40)

        if "composition" in data:
            table.add_row("Formula", f"[bold]{data['composition']}[/bold]")

        if "is_valid" in data:
            validity = "✓ Valid" if data["is_valid"] else "✗ Invalid"
            style = "green" if data["is_valid"] else "red"
            table.add_row("Validation", f"[{style}]{validity}[/{style}]")

        if "elements" in data and "counts" in data:
            elements = data["elements"]
            counts = data["counts"]
            composition_parts = []
            for element, count in zip(elements, counts, strict=False):
                if count == 1.0:
                    composition_parts.append(element)
                else:
                    composition_parts.append(f"{element}{count}")
            table.add_row("Elements", " + ".join(composition_parts))

        self.console.print(
            Panel(
                table, title=f"[bold cyan][=] {tool_name} Result[/bold cyan]", border_style="cyan"
            )
        )

    def _format_energy_result(
        self, tool_name: str, data: dict, tool_args: dict | None = None
    ) -> None:
        """Format energy calculation results with proper units and precision."""
        table = Table(show_header=False, box=None)
        table.add_column("Property", style="cyan", width=25)
        table.add_column("Value", style="white", width=35)

        if "status" in data:
            status = data["status"]
            if status == "completed":
                table.add_row("Status", "[green]✓ Completed[/green]")
            else:
                table.add_row("Status", f"[yellow]{status}[/yellow]")

        if "formation_energy_per_atom" in data:
            energy = data["formation_energy_per_atom"]
            table.add_row("Formation Energy", f"[bold]{energy:.3f} eV/atom[/bold]")

        if "compound_total_energy" in data:
            energy = data["compound_total_energy"]
            table.add_row("Total Energy", f"{energy:.3f} eV")

        if "num_atoms" in data:
            table.add_row("Atoms", str(data["num_atoms"]))

        # Add thermodynamic stability interpretation
        if "formation_energy_per_atom" in data:
            fe = data["formation_energy_per_atom"]
            if fe < -3.0:
                stability = "[green]Highly Stable[/green]"
            elif fe < -1.0:
                stability = "[yellow]Moderately Stable[/yellow]"
            elif fe < 0:
                stability = "[orange3]Marginally Stable[/orange3]"
            else:
                stability = "[red]Unstable[/red]"
            table.add_row("Stability", stability)

        self.console.print(
            Panel(
                table,
                title=f"[bold green][=] {tool_name} Result[/bold green]",
                border_style="green",
            )
        )

    def _format_structure_result(
        self, tool_name: str, data: dict, tool_args: dict | None = None
    ) -> None:
        """Format crystal structure results with proper scientific formatting."""
        if "structures" in data and data["structures"]:
            # Multiple structures
            self.console.print(
                Panel(
                    f"Generated [bold]{data.get('num_structures', len(data['structures']))}[/bold] crystal structures",
                    title=f"[bold magenta][=] {tool_name} Result[/bold magenta]",
                    border_style="magenta",
                )
            )

            # Show details for each structure
            for i, structure in enumerate(data["structures"][:3]):  # Show first 3
                self._format_single_structure(f"Structure {i + 1}", structure)

            if len(data["structures"]) > 3:
                self.console.print(
                    f"[dim]... and {len(data['structures']) - 3} more structures[/dim]"
                )

        elif "cell" in data and "positions" in data:
            # Single structure
            self._format_single_structure(tool_name, data)

        else:
            # Generic structure data
            self._format_generic_dict(tool_name, data, tool_args)

    def _format_single_structure(self, title: str, structure: dict) -> None:
        """Format a single crystal structure."""
        table = Table(show_header=False, box=None)
        table.add_column("Property", style="cyan", width=20)
        table.add_column("Value", style="white", width=50)

        if "formula" in structure:
            table.add_row("Formula", f"[bold]{structure['formula']}[/bold]")

        if "structure" in structure and "cell" in structure["structure"]:
            cell = structure["structure"]["cell"]
            if len(cell) >= 3:
                table.add_row("Cell a", f"{cell[0]:.3f} Å")
                table.add_row("Cell b", f"{cell[1]:.3f} Å")
                table.add_row("Cell c", f"{cell[2]:.3f} Å")

        if "sample_index" in structure:
            table.add_row("Sample", str(structure["sample_index"]))

        self.console.print(
            Panel(table, title=f"[bold blue]{title}[/bold blue]", border_style="blue")
        )

    def _format_generic_dict(
        self, tool_name: str, data: dict, tool_args: dict | None = None
    ) -> None:
        """Format generic dictionary data with beautiful JSON syntax highlighting."""

        # Create readable JSON
        json_str = json.dumps(data, indent=2, ensure_ascii=False)

        # Use Rich's JSON formatter for syntax highlighting
        try:
            json_obj = JSON(json_str)
            self.console.print(
                Panel(
                    json_obj,
                    title=f"[bold][=] {tool_name} Result[/bold]",
                    border_style="cyan",
                    expand=False,
                )
            )
        except Exception:
            # Fallback to syntax highlighting
            syntax = Syntax(json_str, "json", theme="monokai", line_numbers=False)
            self.console.print(
                Panel(syntax, title=f"[bold][=] {tool_name} Result[/bold]", border_style="cyan")
            )

    def _format_list_result(
        self, tool_name: str, data: list, tool_args: dict | None = None
    ) -> None:
        """Format list results appropriately."""
        if len(data) == 0:
            self.console.print(
                Panel(
                    "[dim]Empty result[/dim]",
                    title=f"[bold][=] {tool_name} Result[/bold]",
                    border_style="cyan",
                )
            )
            return

        # Show first few items and count
        preview_items = data[:5]

        table = Table(show_header=True, header_style="bold cyan")
        table.add_column("Index", style="dim", width=8)
        table.add_column("Value", style="white")

        for i, item in enumerate(preview_items):
            if isinstance(item, dict):
                # Show a summary of dict items
                summary = ", ".join(f"{k}: {v}" for k, v in list(item.items())[:3])
                if len(item) > 3:
                    summary += "..."
                table.add_row(str(i), summary)
            else:
                table.add_row(str(i), str(item))

        if len(data) > 5:
            table.add_row("...", f"[dim]and {len(data) - 5} more items[/dim]")

        self.console.print(
            Panel(
                table,
                title=f"[bold][=] {tool_name} Result[/bold] ([cyan]{len(data)} items[/cyan])",
                border_style="cyan",
            )
        )

    def _format_text_result(
        self, tool_name: str, result: Any, tool_args: dict | None = None
    ) -> None:
        """Format plain text results."""
        self.console.print(
            Panel(str(result), title=f"[bold][=] {tool_name} Result[/bold]", border_style="cyan")
        )

    def _format_generic_result(
        self, tool_name: str, data: Any, tool_args: dict | None = None
    ) -> None:
        """Fallback formatter for unknown data types."""
        self.console.print(
            Panel(str(data), title=f"[bold][=] {tool_name} Result[/bold]", border_style="cyan")
        )
