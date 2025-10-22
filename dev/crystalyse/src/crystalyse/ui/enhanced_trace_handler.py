"""
Enhanced Trace Handler with JSONL Provenance Capture
=====================================================
Extends the visual trace handler to capture complete provenance data
including tool calls, timings, materials generated, and model outputs.
"""

import json
import time
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict

from rich.console import Console

try:
    from agents.items import ItemHelpers
except ImportError:
    # Fallback for when SDK is not fully available
    class ItemHelpers:
        @staticmethod
        def text_message_output(item):
            if hasattr(item, 'content'):
                return item.content
            return ""

from .trace_handler import ToolTraceHandler

# Import JSONLLogger with proper path handling
import sys
from pathlib import Path
framework_path = Path(__file__).parent.parent.parent.parent / "new_expt_framework"
if framework_path.exists():
    sys.path.insert(0, str(framework_path))
    from event_logger import JSONLLogger
else:
    # Fallback inline implementation
    import json
    from dataclasses import asdict, dataclass
    from datetime import datetime
    
    @dataclass
    class Event:
        type: str
        ts: str
        data: Dict[str, Any]
    
    class JSONLLogger:
        def __init__(self, path: Path) -> None:
            self.path = path
            self.path.parent.mkdir(parents=True, exist_ok=True)
        
        def log(self, type_: str, data: Dict[str, Any]) -> None:
            evt = Event(type=type_, ts=datetime.utcnow().isoformat(), data=data)
            with self.path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(asdict(evt)) + "\n")


@dataclass
class ToolCall:
    """Tracks a single tool call with timing."""
    tool_name: str
    args: Dict[str, Any]
    start_time: float
    end_time: Optional[float] = None
    output: Optional[Any] = None
    success: bool = True
    call_id: Optional[str] = None
    
    @property
    def duration_ms(self) -> float:
        if self.end_time:
            return (self.end_time - self.start_time) * 1000
        return 0


class EnhancedTraceHandler(ToolTraceHandler):
    """
    Enhanced trace handler that captures both visual display and structured provenance.
    Implements the design from your plan:
    - JSONL event logging
    - Tool timing capture
    - Material/energy extraction from outputs
    - CIF artifact tracking
    - Full assistant response capture
    """
    
    def __init__(
        self,
        console: Console,
        output_dir: Optional[Path] = None,
        session_id: Optional[str] = None,
        enable_provenance: bool = True,
        enable_visual: bool = True
    ):
        super().__init__(console)
        
        self.enable_provenance = enable_provenance
        self.enable_visual = enable_visual
        self.session_id = session_id or datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if enable_provenance and output_dir:
            self.output_dir = Path(output_dir) / f"runs/{self.session_id}"
            self.output_dir.mkdir(parents=True, exist_ok=True)
            
            # Initialize loggers
            self.event_logger = JSONLLogger(self.output_dir / "events.jsonl")
            self.provenance_logger = JSONLLogger(self.output_dir / "provenance.jsonl")
            self.artifact_logger = JSONLLogger(self.output_dir / "artifacts.jsonl")
            
            # State tracking
            self.tool_calls: Dict[str, ToolCall] = {}
            self.current_tool_counter = 0
            self.run_start_time = time.time()
            self.first_token_time: Optional[float] = None
            self.assistant_buffer: List[str] = []
            self.materials_found: List[Dict[str, Any]] = []
            
            # Log session start
            self.event_logger.log("session_start", {
                "session_id": self.session_id,
                "timestamp": datetime.now().isoformat(),
                "output_dir": str(self.output_dir)
            })
        else:
            self.output_dir = None
            self.event_logger = None
    
    def on_event(self, event):
        """Enhanced event handler with provenance capture."""
        # Always do visual display if enabled
        if self.enable_visual:
            super().on_event(event)
        
        # Capture provenance if enabled
        if not self.enable_provenance or not self.event_logger:
            return
            
        try:
            if event.type == "run_item_stream_event":
                if event.item.type == "tool_call_item":
                    self._on_tool_call_start_provenance(event.item)
                elif event.item.type == "tool_call_output_item":
                    self._on_tool_call_end_provenance(event.item)
                elif event.item.type == "message_output_item":
                    self._on_message_output_provenance(event.item)
                elif event.item.type == "reasoning_item":
                    self._on_reasoning_provenance(event.item)
        except Exception as e:
            # Log errors but don't crash the stream
            if self.event_logger:
                self.event_logger.log("error", {
                    "error": str(e),
                    "event_type": getattr(event, 'type', 'unknown')
                })
    
    def _on_tool_call_start_provenance(self, item):
        """Track tool call start with timing."""
        tool_name = "unknown_tool"
        tool_args = {}
        call_id = None
        
        # Extract tool info (same logic as parent class)
        try:
            if hasattr(item.raw_item, 'function'):
                func = item.raw_item.function
                if hasattr(func, 'name'):
                    tool_name = func.name
                if hasattr(func, 'arguments'):
                    if isinstance(func.arguments, str):
                        tool_args = json.loads(func.arguments)
                    else:
                        tool_args = func.arguments
            
            # Get call ID if available
            if hasattr(item.raw_item, 'id'):
                call_id = item.raw_item.id
            elif hasattr(item, 'id'):
                call_id = item.id
            else:
                call_id = f"call_{self.current_tool_counter}"
                self.current_tool_counter += 1
        except Exception as e:
            call_id = f"call_{self.current_tool_counter}"
            self.current_tool_counter += 1
        
        # Create tool call tracker
        tool_call = ToolCall(
            tool_name=tool_name,
            args=tool_args,
            start_time=time.time(),
            call_id=call_id
        )
        self.tool_calls[call_id] = tool_call
        
        # Log tool start event
        self.event_logger.log("tool", {
            "phase": "start",
            "tool": tool_name,
            "args": tool_args,
            "call_id": call_id,
            "ts": datetime.now().isoformat()
        })
    
    def _on_tool_call_end_provenance(self, item):
        """Track tool call end with output parsing."""
        # Find the matching tool call
        call_id = None
        if hasattr(item.raw_item, 'tool_call_id'):
            call_id = item.raw_item.tool_call_id
        elif hasattr(item, 'tool_call_id'):
            call_id = item.tool_call_id
        
        # If no ID, use the most recent uncompleted call
        if not call_id:
            for cid, tc in reversed(list(self.tool_calls.items())):
                if tc.end_time is None:
                    call_id = cid
                    break
        
        if call_id and call_id in self.tool_calls:
            tool_call = self.tool_calls[call_id]
            tool_call.end_time = time.time()
            tool_call.output = item.output
            
            # Log tool end event
            self.event_logger.log("tool", {
                "phase": "end",
                "tool": tool_call.tool_name,
                "duration_ms": tool_call.duration_ms,
                "ok": tool_call.success,
                "call_id": call_id,
                "ts": datetime.now().isoformat(),
                "output_summary": self._summarize_output(item.output)
            })
            
            # Extract provenance from tool output
            self._extract_provenance_from_output(tool_call.tool_name, item.output)
    
    def _on_message_output_provenance(self, item):
        """Capture assistant message output."""
        # Track first token time
        if not self.first_token_time:
            self.first_token_time = time.time()
            ttfb = (self.first_token_time - self.run_start_time) * 1000
            self.event_logger.log("ttfb", {
                "time_ms": ttfb,
                "ts": datetime.now().isoformat()
            })
        
        # Extract text content
        try:
            text = ItemHelpers.text_message_output(item)
            if text:
                self.assistant_buffer.append(text)
        except:
            pass
    
    def _on_reasoning_provenance(self, item):
        """Track reasoning tokens (for o-series models)."""
        if hasattr(item, 'content') and item.content:
            # Just log that reasoning occurred, don't persist content
            self.event_logger.log("reasoning", {
                "length": len(item.content),
                "ts": datetime.now().isoformat()
            })
    
    def _extract_provenance_from_output(self, tool_name: str, output: Any):
        """Extract materials, energies, and other provenance from tool outputs."""
        if not output:
            return
            
        try:
            # Parse JSON output if string
            if isinstance(output, str):
                try:
                    output_data = json.loads(output)
                except:
                    return
            else:
                output_data = output
            
            # Extract based on tool type
            if tool_name == "comprehensive_materials_analysis":
                self._extract_materials_data(output_data)
            elif tool_name == "calculate_energy_mace":
                self._extract_energy_data(output_data)
            elif tool_name == "generate_structures":
                self._extract_structure_data(output_data)
                
        except Exception as e:
            self.event_logger.log("extraction_error", {
                "tool": tool_name,
                "error": str(e)
            })
    
    def _extract_materials_data(self, data: Dict):
        """Extract materials from comprehensive_materials_analysis output."""
        if "generated_structures" in data:
            for comp_data in data["generated_structures"]:
                composition = comp_data.get("composition", "")
                
                for struct in comp_data.get("structures", []):
                    material_entry = {
                        "composition": composition,
                        "formula": struct.get("formula", ""),
                        "formation_energy": struct.get("formation_energy", None),
                        "unit": "eV/atom",
                        "space_group": struct.get("space_group", ""),
                        "cif_saved": struct.get("cif_saved", False),
                        "source_tool": "comprehensive_materials_analysis",
                        "ts": datetime.now().isoformat()
                    }
                    
                    self.materials_found.append(material_entry)
                    
                    # Log as provenance tuple
                    key = f"energy.{composition}.{struct.get('structure_id', 'unknown')}"
                    self.provenance_logger.log("tuple", {
                        "key": key,
                        "value": struct.get("formation_energy"),
                        "unit": "eV/atom",
                        "source_tool": "comprehensive_materials_analysis",
                        "composition": composition,
                        "ts": datetime.now().isoformat()
                    })
    
    def _extract_energy_data(self, data: Dict):
        """Extract energy values from MACE calculations."""
        if "formation_energy" in data:
            self.provenance_logger.log("tuple", {
                "key": f"energy.mace.{time.time()}",
                "value": data["formation_energy"],
                "unit": "eV/atom",
                "source_tool": "calculate_energy_mace",
                "ts": datetime.now().isoformat()
            })
    
    def _extract_structure_data(self, data: Dict):
        """Extract structure generation data."""
        if "structures" in data:
            for struct in data["structures"]:
                self.provenance_logger.log("structure", {
                    "composition": struct.get("composition", ""),
                    "space_group": struct.get("space_group", ""),
                    "lattice": struct.get("lattice", {}),
                    "source_tool": "generate_structures",
                    "ts": datetime.now().isoformat()
                })
    
    def _summarize_output(self, output: Any) -> str:
        """Create a brief summary of tool output."""
        if not output:
            return "empty"
            
        try:
            if isinstance(output, str):
                # Try to parse JSON
                try:
                    data = json.loads(output)
                    if isinstance(data, dict):
                        # Summarize key fields
                        summary_parts = []
                        if "generated_structures" in data:
                            n = len(data["generated_structures"])
                            summary_parts.append(f"{n} compositions")
                        if "valid" in data:
                            summary_parts.append(f"valid={data['valid']}")
                        if "formation_energy" in data:
                            summary_parts.append(f"E={data['formation_energy']:.3f}")
                        return " | ".join(summary_parts) if summary_parts else "complex_output"
                except:
                    return f"text[{len(output)}]"
            else:
                return str(type(output).__name__)
        except:
            return "unknown"
    
    def finalize(self):
        """Called at the end of a run to save final outputs."""
        if not self.enable_provenance or not self.event_logger:
            return
            
        # Save full assistant response
        if self.assistant_buffer:
            full_response = "".join(self.assistant_buffer)
            response_file = self.output_dir / "assistant_full.md"
            with open(response_file, 'w') as f:
                f.write(full_response)
            
            # Log summary
            self.event_logger.log("assistant_output", {
                "length": len(full_response),
                "ts": datetime.now().isoformat(),
                "session_id": self.session_id
            })
        
        # Generate summary report
        summary = {
            "session_id": self.session_id,
            "total_time_s": time.time() - self.run_start_time,
            "ttfb_ms": (self.first_token_time - self.run_start_time) * 1000 if self.first_token_time else None,
            "tool_calls": len(self.tool_calls),
            "materials_found": len(self.materials_found),
            "timestamp": datetime.now().isoformat()
        }
        
        # Tool statistics
        tool_stats = {}
        for tc in self.tool_calls.values():
            if tc.tool_name not in tool_stats:
                tool_stats[tc.tool_name] = {
                    "count": 0,
                    "total_ms": 0,
                    "avg_ms": 0
                }
            tool_stats[tc.tool_name]["count"] += 1
            tool_stats[tc.tool_name]["total_ms"] += tc.duration_ms
        
        for tool_name, stats in tool_stats.items():
            stats["avg_ms"] = stats["total_ms"] / stats["count"]
        
        summary["tool_stats"] = tool_stats
        
        # Save summary
        with open(self.output_dir / "summary.json", 'w') as f:
            json.dump(summary, f, indent=2)
        
        # Log session end
        self.event_logger.log("session_end", summary)
        
        return summary


def hook_workspace_writes(output_dir: Path, session_id: str):
    """
    Hook into workspace writes to capture CIF artifacts.
    This should be called before running the agent.
    """
    artifact_logger = JSONLLogger(output_dir / f"runs/{session_id}/artifacts.jsonl")
    
    # Import workspace tools with proper path handling
    import sys
    from pathlib import Path
    dev_path = Path(__file__).parent.parent.parent
    if str(dev_path) not in sys.path:
        sys.path.insert(0, str(dev_path))
    from crystalyse.workspace import workspace_tools
    
    # Store original write function
    original_write = workspace_tools.write_file
    
    def write_with_tracking(file_path: str, content: str) -> str:
        """Wrapped write function that tracks artifacts."""
        result = original_write(file_path, content)
        
        # Compute hash
        content_bytes = content.encode('utf-8')
        file_hash = hashlib.sha256(content_bytes).hexdigest()
        
        # Check if it's a CIF file
        is_cif = file_path.endswith('.cif')
        
        # Log artifact
        artifact_logger.log("artifact", {
            "path": file_path,
            "sha256": file_hash,
            "size": len(content_bytes),
            "is_cif": is_cif,
            "ts": datetime.now().isoformat()
        })
        
        # If CIF, compute canonical hash
        if is_cif:
            try:
                from pymatgen.core import Structure
                struct = Structure.from_str(content, fmt='cif')
                # Sort sites and round coordinates for canonical form
                sorted_sites = sorted(struct.sites, key=lambda s: (s.species_string, tuple(s.frac_coords)))
                canonical_str = str(sorted_sites)
                canonical_hash = hashlib.sha256(canonical_str.encode()).hexdigest()[:16]
                
                artifact_logger.log("cif_canonical", {
                    "path": file_path,
                    "canonical_hash": canonical_hash,
                    "composition": str(struct.composition),
                    "ts": datetime.now().isoformat()
                })
            except:
                pass
        
        return result
    
    # Replace the function
    workspace_tools.write_file = write_with_tracking
    
    return original_write  # Return original for restoration later