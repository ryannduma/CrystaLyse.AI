"""
Handles the real-time tracing of agent events for a rich CLI experience.
"""

import json

# Corrected imports based on the local SDK version
from agents.items import (
    ToolCallItem,
    ToolCallOutputItem,  # Used to know when to stop the spinner
)
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.text import Text

from .enhanced_result_formatter import EnhancedResultFormatter


class ToolTraceHandler:
    """
    Processes the event stream from the agent runner and displays a
    rich, real-time view of the agent's operations.
    """

    def __init__(self, console: Console):
        self.console = console
        self.live = None
        self.current_tool_call = None
        self.current_tool_args = {}
        self.result_formatter = EnhancedResultFormatter(console)

    def _start_live_display(self, text: Text):
        self._stop_live_display()  # Ensure any previous display is stopped
        self.live = Live(text, console=self.console, transient=True, refresh_per_second=10)
        self.live.start()

    def _stop_live_display(self):
        if self.live:
            self.live.stop()
            self.live = None

    def on_event(self, event):
        """Main event handler to dispatch stream events."""
        if event.type == "run_item_stream_event":
            if event.item.type == "tool_call_item":
                self.on_tool_call_start(event.item)
            elif event.item.type == "tool_call_output_item":
                self.on_tool_call_end(event.item)
            elif event.item.type == "message_output_item":
                # A new message from the assistant means the tool calls are done for now.
                self._stop_live_display()

    def on_tool_call_start(self, item: ToolCallItem):
        """Called when the agent decides to call a tool."""
        tool_name = "unknown_tool"
        tool_args = {}

        # Extract tool name and arguments safely - try multiple approaches
        try:
            # Approach 1: Direct function attribute
            if hasattr(item.raw_item, "function") and hasattr(item.raw_item.function, "name"):
                tool_name = item.raw_item.function.name
                if hasattr(item.raw_item.function, "arguments"):
                    try:
                        if isinstance(item.raw_item.function.arguments, str):
                            tool_args = json.loads(item.raw_item.function.arguments)
                        else:
                            tool_args = item.raw_item.function.arguments
                    except Exception:
                        tool_args = {"raw_arguments": str(item.raw_item.function.arguments)}

            # Approach 2: Tool name attribute
            elif hasattr(item.raw_item, "tool_name"):
                tool_name = item.raw_item.tool_name
                if hasattr(item.raw_item, "arguments"):
                    tool_args = item.raw_item.arguments

            # Approach 3: Name attribute
            elif hasattr(item.raw_item, "name"):
                tool_name = item.raw_item.name

            # Approach 4: If it's a dict-like object
            elif hasattr(item.raw_item, "__dict__"):
                # Try to find a name-like field
                for attr in ["function", "tool_name", "name"]:
                    if attr in item.raw_item.__dict__:
                        val = getattr(item.raw_item, attr)
                        if hasattr(val, "name"):
                            tool_name = val.name
                            if hasattr(val, "arguments"):
                                try:
                                    if isinstance(val.arguments, str):
                                        tool_args = json.loads(val.arguments)
                                    else:
                                        tool_args = val.arguments
                                except Exception:
                                    tool_args = {"raw_arguments": str(val.arguments)}
                            break
                        elif isinstance(val, str):
                            tool_name = val
                            break

        except Exception as e:
            # Log for debugging but don't crash
            print(f"[DEBUG] Error extracting tool info: {e}")

        self.current_tool_call = tool_name
        self.current_tool_args = tool_args

        text = Text()
        text.append("[*] ", style="yellow")  # Clean indicator
        text.append("Calling ", style="dim")
        text.append(f"{tool_name}", style="bold yellow")

        # Show key arguments for transparency
        if tool_args:
            key_args = self._format_key_arguments(tool_args)
            if key_args:
                text.append(f" ({key_args})", style="dim cyan")

        self._start_live_display(text)

    def on_tool_call_end(self, item: ToolCallOutputItem):
        """Called when a tool finishes execution."""
        self._stop_live_display()

        tool_name = self.current_tool_call or "unknown_tool"

        # Use the enhanced result formatter for beautiful output
        try:
            # Parse the output if it's a string
            if isinstance(item.output, str) and item.output.strip():
                try:
                    output_data = json.loads(item.output)
                except json.JSONDecodeError:
                    output_data = item.output
            else:
                output_data = item.output

            # Use the enhanced formatter
            self.result_formatter.format_tool_result(
                tool_name=tool_name, result=output_data, tool_args=self.current_tool_args
            )

        except Exception as e:
            # Fallback to simple display if formatting fails
            self.console.print(
                Panel(
                    f"[red]Error formatting result: {e}[/red]\n\nRaw output:\n{item.output}",
                    title=f"[bold][!] {tool_name} Result[/bold]",
                    border_style="red",
                )
            )

        # Reset state
        self.current_tool_call = None
        self.current_tool_args = {}

    def _format_key_arguments(self, args: dict) -> str:
        """Format key arguments for display."""
        if not args:
            return ""

        # Show only the most important arguments to keep display clean
        key_params = []

        # Common important parameters across different tools
        important_keys = [
            "composition",
            "formula",
            "structure",
            "energy_type",
            "material",
            "query",
            "search_term",
            "file_path",
            "content",
        ]

        for key in important_keys:
            if key in args:
                value = args[key]
                if isinstance(value, str) and len(value) > 30:
                    value = value[:30] + "..."
                key_params.append(f"{key}={value}")

        # If no important keys found, show first few parameters
        if not key_params and args:
            for key, value in list(args.items())[:2]:
                if isinstance(value, str) and len(value) > 20:
                    value = value[:20] + "..."
                key_params.append(f"{key}={value}")

        return ", ".join(key_params)

    def _extract_result_summary(self, output_data: dict, tool_name: str) -> str:
        """Extract a summary of key results for transparency."""
        summary_parts = []

        # Tool-specific result extraction
        if tool_name == "validate_composition_smact":
            if "valid_compositions" in output_data:
                count = len(output_data["valid_compositions"])
                summary_parts.append(f"Validated {count} compositions")

        elif tool_name == "generate_structures":
            if "structures" in output_data:
                count = len(output_data["structures"])
                summary_parts.append(f"Generated {count} crystal structures")

        elif tool_name == "calculate_energy_mace":
            if "formation_energy" in output_data:
                energy = output_data["formation_energy"]
                summary_parts.append(f"Formation energy: {energy:.3f} eV/atom")
            if "total_energy" in output_data:
                energy = output_data["total_energy"]
                summary_parts.append(f"Total energy: {energy:.3f} eV")

        elif "count" in output_data:
            summary_parts.append(f"Found {output_data['count']} items")

        elif "results" in output_data and isinstance(output_data["results"], list):
            summary_parts.append(f"Returned {len(output_data['results'])} results")

        return " | ".join(summary_parts) if summary_parts else ""
