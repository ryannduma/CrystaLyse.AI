"""
Enhanced Trace Handler V2 with Proper MCP Tool Detection
=========================================================
Fixes the issues with tool name detection and materials extraction
by parsing the MCP server responses.
"""

import json
import logging
import re
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from rich.console import Console

try:
    from agents.items import ItemHelpers
except ImportError:

    class ItemHelpers:
        @staticmethod
        def text_message_output(item):
            if hasattr(item, "content"):
                return item.content
            return ""


# Import JSONLLogger
import sys

from .trace_handler import ToolTraceHandler

framework_path = Path(__file__).parent.parent.parent.parent / "new_expt_framework"
if framework_path.exists() and str(framework_path) not in sys.path:
    sys.path.insert(0, str(framework_path))
    from event_logger import JSONLLogger
else:
    # Fallback implementation
    from dataclasses import dataclass
    from datetime import datetime

    @dataclass
    class Event:
        type: str
        ts: str
        data: dict[str, Any]

    class JSONLLogger:
        def __init__(self, path: Path) -> None:
            self.path = path
            self.path.parent.mkdir(parents=True, exist_ok=True)

        def log(self, type_: str, data: dict[str, Any]) -> None:
            evt = Event(type=type_, ts=datetime.utcnow().isoformat(), data=data)
            with self.path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(asdict(evt)) + "\n")


@dataclass
class EnhancedToolCall:
    """Enhanced tool call tracking with MCP awareness."""

    wrapper_name: str  # SDK wrapper name
    mcp_tool: str | None = None  # Actual MCP tool name
    args: dict[str, Any] = None
    start_time: float = 0
    end_time: float | None = None
    output: Any | None = None
    success: bool = True
    call_id: str | None = None
    materials_extracted: list[dict] = None

    def __post_init__(self):
        if self.args is None:
            self.args = {}
        if self.materials_extracted is None:
            self.materials_extracted = []

    @property
    def duration_ms(self) -> float:
        if self.end_time:
            return (self.end_time - self.start_time) * 1000
        return 0

    @property
    def tool_name(self) -> str:
        """Return the best available tool name."""
        return self.mcp_tool or self.wrapper_name


class EnhancedTraceHandlerV2(ToolTraceHandler):
    """
    Version 2 of the enhanced trace handler with proper MCP tool detection.

    Key improvements:
    - Detects actual MCP tool names from output structure
    - Extracts materials data from tool responses
    - Captures real operation timing from logs
    - Links materials to CIF files
    """

    def __init__(
        self,
        console: Console,
        output_dir: Path | None = None,
        session_id: str | None = None,
        enable_provenance: bool = True,
        enable_visual: bool = True,
        capture_mcp_logs: bool = True,
    ):
        super().__init__(console)

        self.enable_provenance = enable_provenance
        self.enable_visual = enable_visual
        self.capture_mcp_logs = capture_mcp_logs
        self.session_id = session_id or datetime.now().strftime("%Y%m%d_%H%M%S")

        if enable_provenance and output_dir:
            self.output_dir = Path(output_dir) / f"runs/{self.session_id}"
            self.output_dir.mkdir(parents=True, exist_ok=True)

            # Initialize loggers
            self.event_logger = JSONLLogger(self.output_dir / "events.jsonl")
            self.provenance_logger = JSONLLogger(self.output_dir / "provenance.jsonl")
            self.artifact_logger = JSONLLogger(self.output_dir / "artifacts.jsonl")
            self.materials_logger = JSONLLogger(self.output_dir / "materials.jsonl")

            # State tracking
            self.tool_calls: dict[str, EnhancedToolCall] = {}
            self.current_tool_counter = 0
            self.run_start_time = time.time()
            self.first_token_time: float | None = None
            self.assistant_buffer: list[str] = []
            self.materials_found: list[dict[str, Any]] = []
            self.mcp_operations: list[dict[str, Any]] = []

            # Set up MCP log capture if enabled
            if capture_mcp_logs:
                self._setup_mcp_log_capture()

            # Log session start
            self.event_logger.log(
                "session_start",
                {
                    "session_id": self.session_id,
                    "timestamp": datetime.now().isoformat(),
                    "output_dir": str(self.output_dir),
                    "capture_mcp_logs": capture_mcp_logs,
                },
            )
        else:
            self.output_dir = None
            self.event_logger = None

    def _setup_mcp_log_capture(self):
        """Set up logging to capture MCP server operations."""

        # Create a custom handler to capture MCP logs
        class MCPLogCapture(logging.Handler):
            def __init__(self, handler):
                super().__init__()
                self.handler = handler

            def emit(self, record):
                # Capture logs from MCP servers
                if record.name in ["__main__", "chemeleon_mcp.tools", "mace_mcp.tools"]:
                    self.handler._capture_mcp_log(record)

        # Add handler to capture MCP logs
        self.mcp_log_handler = MCPLogCapture(self)
        logging.getLogger("__main__").addHandler(self.mcp_log_handler)
        logging.getLogger("chemeleon_mcp.tools").addHandler(self.mcp_log_handler)
        logging.getLogger("mace_mcp.tools").addHandler(self.mcp_log_handler)

    def _capture_mcp_log(self, record):
        """Capture and parse MCP server log entries."""
        if not self.event_logger:
            return

        msg = record.getMessage()
        timestamp = datetime.fromtimestamp(record.created).isoformat()

        # Parse different types of MCP operations
        operation = None

        # Chemeleon generation
        if "Generating" in msg and "structures for" in msg:
            match = re.search(r"Generating (\d+) structures for ([A-Za-z0-9]+)", msg)
            if match:
                operation = {
                    "type": "chemeleon_start",
                    "count": int(match.group(1)),
                    "composition": match.group(2),
                }

        # MACE calculation
        elif "Calculated energy for" in msg:
            match = re.search(r"Calculated energy for ([^:]+): ([-\d.]+) eV/atom", msg)
            if match:
                operation = {
                    "type": "mace_result",
                    "structure": match.group(1),
                    "energy": float(match.group(2)),
                }

        # CIF save
        elif "Saved CIF file" in msg:
            match = re.search(r"Saved CIF file for ([^:]+): (.+)", msg)
            if match:
                operation = {
                    "type": "cif_saved",
                    "composition": match.group(1),
                    "path": match.group(2),
                }

        # Progress bars (for timing)
        elif "Sampling: 100%" in msg:
            match = re.search(r"\[(\d+:\d+)<.*?, ([\d.]+)it/s\]", msg)
            if match:
                operation = {
                    "type": "sampling_complete",
                    "duration": match.group(1),
                    "rate": float(match.group(2)),
                }

        if operation:
            self.mcp_operations.append(
                {"timestamp": timestamp, "operation": operation, "raw_msg": msg}
            )

            # Log to events
            self.event_logger.log("mcp_operation", operation)

    def on_event(self, event):
        """Enhanced event handler with MCP tool detection."""
        # Visual display if enabled
        if self.enable_visual:
            super().on_event(event)

        # Capture provenance if enabled
        if not self.enable_provenance or not self.event_logger:
            return

        try:
            if event.type == "run_item_stream_event":
                if event.item.type == "tool_call_item":
                    self._on_tool_call_start_enhanced(event.item)
                elif event.item.type == "tool_call_output_item":
                    self._on_tool_call_end_enhanced(event.item)
                elif event.item.type == "message_output_item":
                    self._on_message_output_provenance(event.item)
                elif event.item.type == "reasoning_item":
                    self._on_reasoning_provenance(event.item)
        except Exception as e:
            if self.event_logger:
                self.event_logger.log(
                    "error", {"error": str(e), "event_type": getattr(event, "type", "unknown")}
                )

    def _on_tool_call_start_enhanced(self, item):
        """Track tool call start with MCP awareness."""
        # Get wrapper name (might be generic for MCP)
        wrapper_name = self._extract_wrapper_name(item)

        # Get call ID
        call_id = self._extract_call_id(item)

        # Create enhanced tool call
        tool_call = EnhancedToolCall(
            wrapper_name=wrapper_name,
            args=self._extract_arguments(item),
            start_time=time.time(),
            call_id=call_id,
        )
        self.tool_calls[call_id] = tool_call

        # Log start event
        self.event_logger.log(
            "tool_start",
            {"wrapper": wrapper_name, "call_id": call_id, "timestamp": datetime.now().isoformat()},
        )

    def _on_tool_call_end_enhanced(self, item):
        """Track tool call end with MCP tool detection and materials extraction."""
        # Find matching tool call
        call_id = self._find_matching_call(item)
        if not call_id or call_id not in self.tool_calls:
            return

        tool_call = self.tool_calls[call_id]
        tool_call.end_time = time.time()
        tool_call.output = item.output

        # Save raw output for debugging
        if self.output_dir and item.output:
            raw_file = self.output_dir / f"raw_output_{call_id[:8]}.json"
            try:
                import json

                if isinstance(item.output, str):
                    with open(raw_file, "w") as f:
                        f.write(item.output)
                else:
                    with open(raw_file, "w") as f:
                        json.dump(item.output, f, indent=2)
            except Exception:
                pass

        # Detect actual MCP tool from output
        mcp_tool = self._detect_mcp_tool(item.output)
        if mcp_tool:
            tool_call.mcp_tool = mcp_tool

        # Extract materials if present
        materials = self._extract_materials_comprehensive(item.output, mcp_tool)
        if materials:
            tool_call.materials_extracted = materials
            self.materials_found.extend(materials)

            # Log each material
            for material in materials:
                self.materials_logger.log("material", material)

        # Log end event with full details
        self.event_logger.log(
            "tool_end",
            {
                "wrapper": tool_call.wrapper_name,
                "mcp_tool": tool_call.mcp_tool,
                "duration_ms": tool_call.duration_ms,
                "materials_count": len(tool_call.materials_extracted),
                "call_id": call_id,
                "timestamp": datetime.now().isoformat(),
            },
        )

    def _detect_mcp_tool(self, output: Any) -> str | None:
        """Detect the actual MCP tool from output structure."""
        if not output:
            return None

        try:
            # Parse output if string
            if isinstance(output, str):
                # Check if it's a wrapped response
                if output.startswith('{"type":'):
                    wrapper = json.loads(output)
                    if wrapper.get("type") == "text":
                        output = wrapper.get("text", "")

                # Try to parse the actual content
                if output.strip().startswith("{"):
                    data = json.loads(output)
                else:
                    return None
            else:
                data = output

            # Detect tool by output structure
            if isinstance(data, dict):
                # Comprehensive materials analysis
                if "generated_structures" in data:
                    if data.get("mode") == "creative":
                        return "creative_discovery_pipeline"
                    return "comprehensive_materials_analysis"

                # SMACT validation
                elif "valid" in data and "oxidation_states" in data:
                    return "validate_composition_smact"

                # Chemeleon generation
                elif "structures" in data and "cif_strings" in data:
                    return "generate_structures"

                # MACE calculation
                elif "formation_energy" in data or "total_energy" in data:
                    return "calculate_energy_mace"

                # PyMatgen analysis
                elif "space_group" in data or "crystal_system" in data:
                    return "analyze_structure_pymatgen"

                # Generic success response
                elif "success" in data and "composition" in data:
                    if "mode" in data:
                        return "comprehensive_materials_analysis"

        except Exception as e:
            # Log parsing error but don't crash
            if self.event_logger:
                self.event_logger.log(
                    "parse_error", {"error": str(e), "output_preview": str(output)[:200]}
                )

        return None

    def _extract_materials_comprehensive(self, output: Any, tool_name: str | None) -> list[dict]:
        """Extract materials data from tool output."""
        materials = []

        if not output:
            return materials

        try:
            # Parse output - handle SDK wrapper structure
            if isinstance(output, dict):
                # Check if it's wrapped in SDK response format
                if output.get("type") == "text" and "text" in output:
                    # Extract the actual JSON from the text field
                    content = output["text"]
                    if isinstance(content, str):
                        data = json.loads(content)
                    else:
                        data = content
                else:
                    data = output
            elif isinstance(output, str):
                # Handle string responses
                try:
                    parsed = json.loads(output)
                    # Check if wrapped
                    if parsed.get("type") == "text" and "text" in parsed:
                        data = json.loads(parsed["text"])
                    else:
                        data = parsed
                except Exception:
                    return materials
            else:
                data = output

            # Extract based on tool type
            if tool_name in ["comprehensive_materials_analysis", "creative_discovery_pipeline"]:
                # Build energy lookup from energy_calculations
                energy_lookup = {}
                if "energy_calculations" in data:
                    for calc in data["energy_calculations"]:
                        struct_id = calc.get("structure_id")
                        if struct_id:
                            energy_lookup[struct_id] = calc.get("formation_energy")

                # Extract from generated_structures
                if "generated_structures" in data:
                    for comp_data in data["generated_structures"]:
                        composition = comp_data.get("composition", "")

                        for idx, struct in enumerate(comp_data.get("structures", [])):
                            # Generate structure_id if not present
                            struct_id = f"{composition}_struct_{idx + 1}"

                            # Get energy from lookup
                            formation_energy = energy_lookup.get(struct_id)

                            material = {
                                "composition": composition,
                                "formula": struct.get("formula", ""),
                                "formation_energy": formation_energy,
                                "unit": "eV/atom" if formation_energy else None,
                                "space_group": struct.get("space_group", ""),
                                "structure_id": struct_id,
                                "cif_saved": struct.get("cif_saved", False),
                                "source_tool": tool_name,
                                "timestamp": datetime.now().isoformat(),
                            }
                            materials.append(material)

            elif tool_name == "calculate_energy_mace":
                # Single energy calculation
                if "formation_energy" in data:
                    material = {
                        "composition": data.get("composition", "unknown"),
                        "formation_energy": data["formation_energy"],
                        "unit": "eV/atom",
                        "source_tool": tool_name,
                        "timestamp": datetime.now().isoformat(),
                    }
                    materials.append(material)

        except Exception as e:
            # Log extraction error
            if self.event_logger:
                self.event_logger.log("extraction_error", {"error": str(e), "tool": tool_name})

        return materials

    def _extract_wrapper_name(self, item) -> str:
        """Extract the wrapper function name from the item."""
        try:
            if hasattr(item.raw_item, "function"):
                func = item.raw_item.function
                if hasattr(func, "name"):
                    return func.name
            elif hasattr(item.raw_item, "tool_name"):
                return item.raw_item.tool_name
            elif hasattr(item.raw_item, "name"):
                return item.raw_item.name
        except Exception:
            pass
        return "mcp_wrapper"

    def _extract_call_id(self, item) -> str:
        """Extract or generate a call ID."""
        try:
            if hasattr(item.raw_item, "id"):
                return item.raw_item.id
            elif hasattr(item, "id"):
                return item.id
        except Exception:
            pass

        call_id = f"call_{self.current_tool_counter}"
        self.current_tool_counter += 1
        return call_id

    def _extract_arguments(self, item) -> dict:
        """Extract tool arguments."""
        try:
            if hasattr(item.raw_item, "function"):
                func = item.raw_item.function
                if hasattr(func, "arguments"):
                    if isinstance(func.arguments, str):
                        return json.loads(func.arguments)
                    return func.arguments
        except Exception:
            pass
        return {}

    def _find_matching_call(self, item) -> str | None:
        """Find the matching tool call for an output item."""
        try:
            if hasattr(item.raw_item, "tool_call_id"):
                return item.raw_item.tool_call_id
            elif hasattr(item, "tool_call_id"):
                return item.tool_call_id
        except Exception:
            pass

        # Use most recent uncompleted call
        for call_id, tc in reversed(list(self.tool_calls.items())):
            if tc.end_time is None:
                return call_id

        return None

    def _on_message_output_provenance(self, item):
        """Capture assistant message output."""
        if not self.first_token_time:
            self.first_token_time = time.time()
            ttfb = (self.first_token_time - self.run_start_time) * 1000
            self.event_logger.log(
                "ttfb", {"time_ms": ttfb, "timestamp": datetime.now().isoformat()}
            )

        try:
            text = ItemHelpers.text_message_output(item)
            if text:
                self.assistant_buffer.append(text)
        except Exception:
            pass

    def _on_reasoning_provenance(self, item):
        """Track reasoning tokens."""
        if hasattr(item, "content") and item.content:
            self.event_logger.log(
                "reasoning", {"length": len(item.content), "timestamp": datetime.now().isoformat()}
            )

    def finalize(self):
        """Finalize and save all outputs with enhanced metrics."""
        if not self.enable_provenance or not self.event_logger:
            return {}

        # Save assistant response
        if self.assistant_buffer:
            full_response = "".join(self.assistant_buffer)
            response_file = self.output_dir / "assistant_full.md"
            with open(response_file, "w") as f:
                f.write(full_response)

            self.event_logger.log(
                "assistant_output",
                {
                    "length": len(full_response),
                    "timestamp": datetime.now().isoformat(),
                    "session_id": self.session_id,
                },
            )

        # Enhanced summary with MCP tool breakdown
        summary = {
            "session_id": self.session_id,
            "total_time_s": time.time() - self.run_start_time,
            "ttfb_ms": (self.first_token_time - self.run_start_time) * 1000
            if self.first_token_time
            else None,
            "tool_calls_total": len(self.tool_calls),
            "materials_found": len(self.materials_found),
            "unique_compositions": len({m["composition"] for m in self.materials_found}),
            "mcp_operations": len(self.mcp_operations),
            "timestamp": datetime.now().isoformat(),
        }

        # MCP tool statistics
        mcp_tools = {}
        for tc in self.tool_calls.values():
            tool_name = tc.tool_name
            if tool_name not in mcp_tools:
                mcp_tools[tool_name] = {"count": 0, "total_ms": 0, "materials": 0}
            mcp_tools[tool_name]["count"] += 1
            mcp_tools[tool_name]["total_ms"] += tc.duration_ms
            mcp_tools[tool_name]["materials"] += len(tc.materials_extracted)

        # Calculate averages
        for _tool_name, stats in mcp_tools.items():
            if stats["count"] > 0:
                stats["avg_ms"] = stats["total_ms"] / stats["count"]

        summary["mcp_tools"] = mcp_tools

        # Materials summary
        if self.materials_found:
            energies = [
                m["formation_energy"] for m in self.materials_found if m.get("formation_energy")
            ]
            summary["materials_summary"] = {
                "total": len(self.materials_found),
                "with_energy": len(energies),
                "min_energy": min(energies) if energies else None,
                "max_energy": max(energies) if energies else None,
                "avg_energy": sum(energies) / len(energies) if energies else None,
            }

        # Save enhanced summary
        with open(self.output_dir / "summary.json", "w") as f:
            json.dump(summary, f, indent=2)

        # Save materials catalog
        if self.materials_found:
            with open(self.output_dir / "materials_catalog.json", "w") as f:
                json.dump(self.materials_found, f, indent=2)

        # Log session end
        self.event_logger.log("session_end", summary)

        # Clean up MCP log handler
        if hasattr(self, "mcp_log_handler"):
            logging.getLogger("__main__").removeHandler(self.mcp_log_handler)
            logging.getLogger("chemeleon_mcp.tools").removeHandler(self.mcp_log_handler)
            logging.getLogger("mace_mcp.tools").removeHandler(self.mcp_log_handler)

        return summary
