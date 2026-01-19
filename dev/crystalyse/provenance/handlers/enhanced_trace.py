"""
Enhanced Trace Handler with Complete Provenance Capture
"""

import time
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict

from rich.console import Console

# Import core components - use relative imports within crystalyse.provenance
from ..core import JSONLLogger, MaterialsTracker, MCPDetector
from ..core.pydantic_serializer import (
    serialize_pydantic_model,
    create_enhanced_material_record
)
from ..value_registry import ProvenanceValueRegistry, get_global_registry

# Base class for trace handling (using duck typing to avoid circular import)
class ToolTraceHandler:
    """Minimal base class for trace handling (duck typing interface)."""
    def __init__(self, console: Console):
        self.console = console

    def on_event(self, event):
        """Handle trace event."""
        pass

try:
    from agents.items import ItemHelpers
except ImportError:
    class ItemHelpers:
        @staticmethod
        def text_message_output(item):
            if hasattr(item, 'content'):
                return item.content
            return ""

logger = logging.getLogger(__name__)


@dataclass
class EnhancedToolCall:
    """Enhanced tool call tracking with MCP detection."""
    call_id: str
    wrapper_name: str  # SDK wrapper name (often "unknown_tool")
    mcp_tool: Optional[str] = None  # Actual MCP tool detected
    args: Dict[str, Any] = None
    start_time: float = 0
    end_time: Optional[float] = None
    output: Optional[Any] = None
    materials_extracted: List[Any] = None
    success: bool = True
    
    @property
    def duration_ms(self) -> float:
        if self.end_time:
            return (self.end_time - self.start_time) * 1000
        return 0
    
    @property
    def tool_name(self) -> str:
        """Return MCP tool if detected, otherwise wrapper."""
        return self.mcp_tool or self.wrapper_name


class ProvenanceTraceHandler(ToolTraceHandler):
    """
    Complete provenance trace handler for CrystaLyse.
    
    Features:
    - Detects actual MCP tool names (not SDK wrappers)
    - Extracts materials with energies
    - Captures complete event stream in JSONL
    - Saves raw tool outputs for debugging
    - Generates comprehensive summaries
    """
    
    def __init__(
        self,
        console: Optional[Console] = None,
        output_dir: Optional[Path] = None,
        session_id: Optional[str] = None,
        enable_provenance: bool = True,
        enable_visual: bool = True,
        capture_mcp_logs: bool = False,
        save_raw_outputs: bool = True
    ):
        """
        Initialize provenance handler.
        
        Args:
            console: Rich console for visual output
            output_dir: Directory for provenance files
            session_id: Unique session identifier
            enable_provenance: Enable provenance capture
            enable_visual: Show visual trace output
            capture_mcp_logs: Attempt to capture MCP server logs
            save_raw_outputs: Save raw tool outputs for debugging
        """
        super().__init__(console or Console())
        
        self.enable_provenance = enable_provenance
        self.enable_visual = enable_visual
        self.capture_mcp_logs = capture_mcp_logs
        self.save_raw_outputs = save_raw_outputs
        
        # Session management
        self.session_id = session_id or datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if enable_provenance and output_dir:
            # Set up output directory
            self.output_dir = Path(output_dir) / f"runs/{self.session_id}"
            self.output_dir.mkdir(parents=True, exist_ok=True)
            
            # Initialize loggers
            self.event_logger = JSONLLogger(self.output_dir / "events.jsonl")
            self.materials_logger = JSONLLogger(self.output_dir / "materials.jsonl")
            
            # Initialize trackers
            self.materials_tracker = MaterialsTracker()
            self.mcp_detector = MCPDetector()
            
            # State tracking
            self.tool_calls: Dict[str, EnhancedToolCall] = {}
            self.tool_counter = 0
            self.run_start_time = time.time()
            self.first_token_time: Optional[float] = None
            self.assistant_buffer: List[str] = []

            # Conversation tracking (user queries, clarifications, responses)
            self.conversation_log: List[Dict[str, Any]] = []
            self.user_query: Optional[str] = None
            self.clarification_exchanges: List[Dict[str, Any]] = []
            
            # Log session start
            self.event_logger.log_session_start(
                self.session_id,
                {"output_dir": str(self.output_dir), "capture_mcp_logs": capture_mcp_logs}
            )
        else:
            self.output_dir = None
            self.event_logger = None
    
    def on_event(self, event):
        """Process SDK events with provenance capture."""
        # Visual display if enabled
        if self.enable_visual:
            super().on_event(event)

        # Provenance capture
        if not self.enable_provenance or not self.event_logger:
            return

        # DEBUG: Log all event types
        logger.debug(f"Event received: type={event.type}, has_item={hasattr(event, 'item')}")
        if hasattr(event, 'item'):
            logger.debug(f"  Item type: {event.item.type if hasattr(event.item, 'type') else 'no type'}")

        try:
            if event.type == "run_item_stream_event":
                self._process_stream_event(event.item)
        except Exception as e:
            logger.error(f"Error processing event: {e}")
            if self.event_logger:
                self.event_logger.log("error", {
                    "error": str(e),
                    "event_type": getattr(event, 'type', 'unknown')
                })
    
    def _process_stream_event(self, item):
        """Process different types of stream events."""
        if item.type == "tool_call_item":
            self._on_tool_call_start(item)
        elif item.type == "tool_call_output_item":
            self._on_tool_call_end(item)
        elif item.type == "message_output_item":
            self._on_message_output(item)
        elif item.type == "reasoning_item":
            self._on_reasoning(item)
    
    def _on_tool_call_start(self, item):
        """Track tool call start."""
        # Extract basic info
        wrapper_name = self._extract_tool_name(item)
        args = self._extract_tool_args(item)
        call_id = self._get_call_id(item)
        
        # Create tool call tracker
        tool_call = EnhancedToolCall(
            call_id=call_id,
            wrapper_name=wrapper_name,
            args=args,
            start_time=time.time()
        )
        self.tool_calls[call_id] = tool_call
        
        # Log event
        self.event_logger.log("tool_start", {
            "wrapper": wrapper_name,
            "call_id": call_id,
            "timestamp": datetime.now().isoformat()
        })
    
    def _on_tool_call_end(self, item):
        """Track tool call end with MCP detection and Pydantic serialization."""
        call_id = self._find_matching_call(item)
        if not call_id or call_id not in self.tool_calls:
            return

        tool_call = self.tool_calls[call_id]
        tool_call.end_time = time.time()
        tool_call.output = item.output

        # Serialize Pydantic models if present
        serialized_output = serialize_pydantic_model(item.output)

        # Save raw output if enabled
        if self.save_raw_outputs and self.output_dir and serialized_output:
            self._save_raw_output(call_id, serialized_output)

        # Detect actual MCP tool
        mcp_tool = self.mcp_detector.detect_tool(serialized_output)
        if mcp_tool:
            tool_call.mcp_tool = mcp_tool

        # Extract materials with enhanced tracking
        materials = self.materials_tracker.extract_from_output(
            serialized_output,
            mcp_tool or tool_call.wrapper_name
        )
        if materials:
            tool_call.materials_extracted = materials
            # Log each material with enhanced metadata
            for material in materials:
                self.materials_logger.log("material", material.to_dict())

        # Register with value registry for render gate
        registry = get_global_registry()
        if registry and mcp_tool:
            registry.register_tool_output(
                tool_name=mcp_tool,
                tool_call_id=call_id,
                input_data={},  # Could extract from tool_call.args if needed
                output_data=serialized_output,
                timestamp=datetime.now().isoformat()
            )

        # Create enhanced material record for Phase 1.5 tools
        if mcp_tool and mcp_tool.startswith(('validate_', 'calculate_', 'analyze_', 'predict_', 'generate_')):
            enhanced_record = create_enhanced_material_record(
                mcp_tool,
                serialized_output,
                datetime.now().isoformat()
            )
            self.event_logger.log("enhanced_material", enhanced_record)

        # Log tool end with serialized data
        self.event_logger.log("tool_end", {
            "wrapper": tool_call.wrapper_name,
            "mcp_tool": tool_call.mcp_tool,
            "duration_ms": tool_call.duration_ms,
            "materials_count": len(materials),
            "call_id": call_id,
            "has_pydantic": hasattr(item.output, 'model_dump') or hasattr(item.output, 'dict'),
            "timestamp": datetime.now().isoformat()
        })
    
    def _on_message_output(self, item):
        """Capture assistant message output."""
        # Track first token time
        if not self.first_token_time:
            self.first_token_time = time.time()
            ttfb = (self.first_token_time - self.run_start_time) * 1000
            self.event_logger.log("ttfb", {
                "time_ms": ttfb,
                "timestamp": datetime.now().isoformat()
            })
        
        # Extract text
        try:
            text = ItemHelpers.text_message_output(item)
            if text:
                self.assistant_buffer.append(text)
        except:
            pass
    
    def _on_reasoning(self, item):
        """Track reasoning tokens."""
        if hasattr(item, 'content') and item.content:
            self.event_logger.log("reasoning", {
                "length": len(item.content),
                "timestamp": datetime.now().isoformat()
            })
    
    def _extract_tool_name(self, item) -> str:
        """Extract tool name from item."""
        try:
            if hasattr(item.raw_item, 'function'):
                func = item.raw_item.function
                if hasattr(func, 'name'):
                    return func.name
        except:
            pass
        return "unknown_tool"
    
    def _extract_tool_args(self, item) -> Dict:
        """Extract tool arguments."""
        try:
            if hasattr(item.raw_item, 'function'):
                func = item.raw_item.function
                if hasattr(func, 'arguments'):
                    if isinstance(func.arguments, str):
                        return json.loads(func.arguments)
                    return func.arguments
        except:
            pass
        return {}
    
    def _get_call_id(self, item) -> str:
        """Get or generate call ID."""
        if hasattr(item.raw_item, 'id'):
            return item.raw_item.id
        elif hasattr(item, 'id'):
            return item.id
        else:
            self.tool_counter += 1
            return f"call_{self.tool_counter}"
    
    def _find_matching_call(self, item) -> Optional[str]:
        """Find matching tool call for output."""
        # Try to get ID from item
        if hasattr(item.raw_item, 'tool_call_id'):
            return item.raw_item.tool_call_id
        elif hasattr(item, 'tool_call_id'):
            return item.tool_call_id
        
        # Find most recent uncompleted call
        for call_id, tc in reversed(list(self.tool_calls.items())):
            if tc.end_time is None:
                return call_id
        
        return None
    
    def _save_raw_output(self, call_id: str, output: Any):
        """Save raw tool output for debugging."""
        try:
            raw_file = self.output_dir / f"raw_output_{call_id[:8]}.json"

            if isinstance(output, str):
                with open(raw_file, 'w') as f:
                    f.write(output)
            else:
                with open(raw_file, 'w') as f:
                    json.dump(output, f, indent=2)
        except Exception as e:
            logger.debug(f"Failed to save raw output: {e}")

    def set_user_query(self, query: str):
        """
        Record the user's original query.

        Args:
            query: The user's original query text
        """
        if not self.enable_provenance:
            return

        # Avoid duplicate entries if query already set
        if self.user_query is not None:
            return

        self.user_query = query
        self.conversation_log.append({
            "role": "user",
            "content": query,
            "timestamp": datetime.now().isoformat(),
            "type": "query"
        })

        if self.event_logger:
            self.event_logger.log("user_query", {
                "query": query,
                "timestamp": datetime.now().isoformat()
            })

    def add_clarification_exchange(
        self,
        question: str,
        answer: str,
        question_id: Optional[str] = None,
        options: Optional[List[str]] = None
    ):
        """
        Record a clarification question and answer.

        Args:
            question: The clarification question asked
            answer: The user's response
            question_id: Optional identifier for the question
            options: Optional list of options presented to user
        """
        if not self.enable_provenance:
            return

        exchange = {
            "question": question,
            "answer": answer,
            "question_id": question_id,
            "options": options,
            "timestamp": datetime.now().isoformat()
        }
        self.clarification_exchanges.append(exchange)

        # Add to conversation log
        self.conversation_log.append({
            "role": "assistant",
            "content": question,
            "timestamp": datetime.now().isoformat(),
            "type": "clarification_question",
            "options": options
        })
        self.conversation_log.append({
            "role": "user",
            "content": answer,
            "timestamp": datetime.now().isoformat(),
            "type": "clarification_answer",
            "question_id": question_id
        })

        if self.event_logger:
            self.event_logger.log("clarification", exchange)

    def add_enriched_query(self, enriched_query: str):
        """
        Record the enriched/processed query sent to the agent.

        Args:
            enriched_query: The processed query with context
        """
        if not self.enable_provenance:
            return

        self.conversation_log.append({
            "role": "system",
            "content": enriched_query,
            "timestamp": datetime.now().isoformat(),
            "type": "enriched_query"
        })

        if self.event_logger:
            self.event_logger.log("enriched_query", {
                "query": enriched_query,
                "timestamp": datetime.now().isoformat()
            })

    def _save_conversation_log(self):
        """Save the complete conversation as a formatted markdown file."""
        if not self.conversation_log and not self.user_query:
            return

        conv_file = self.output_dir / "conversation_full.md"

        lines = [
            f"# Crystalyse Conversation Log",
            f"",
            f"**Session ID:** {self.session_id}",
            f"**Timestamp:** {datetime.now().isoformat()}",
            f"",
            f"---",
            f""
        ]

        for entry in self.conversation_log:
            role = entry.get("role", "unknown")
            content = entry.get("content", "")
            entry_type = entry.get("type", "message")
            timestamp = entry.get("timestamp", "")

            if entry_type == "query":
                lines.append(f"## User Query")
                lines.append(f"")
                lines.append(f"> {content}")
                lines.append(f"")
            elif entry_type == "clarification_question":
                lines.append(f"### Clarification Question")
                lines.append(f"")
                lines.append(f"**Crystalyse:** {content}")
                options = entry.get("options")
                if options:
                    lines.append(f"")
                    lines.append(f"*Options: {', '.join(options)}*")
                lines.append(f"")
            elif entry_type == "clarification_answer":
                lines.append(f"**User:** {content}")
                lines.append(f"")
            elif entry_type == "enriched_query":
                lines.append(f"### Processed Query (sent to agent)")
                lines.append(f"")
                lines.append(f"```")
                lines.append(content)
                lines.append(f"```")
                lines.append(f"")
            elif entry_type == "response":
                lines.append(f"## Crystalyse Response")
                lines.append(f"")
                lines.append(content)
                lines.append(f"")
            else:
                # Generic message
                if role == "user":
                    lines.append(f"**User:** {content}")
                elif role == "assistant":
                    lines.append(f"**Crystalyse:** {content}")
                else:
                    lines.append(f"**{role}:** {content}")
                lines.append(f"")

        lines.append(f"---")
        lines.append(f"")
        lines.append(f"*End of conversation log*")

        with open(conv_file, 'w') as f:
            f.write("\n".join(lines))
    
    def finalize(self) -> Dict[str, Any]:
        """Generate final summary and save outputs."""
        if not self.enable_provenance or not self.event_logger:
            return {}

        # Save assistant response (legacy file for backwards compatibility)
        full_response = ""
        if self.assistant_buffer:
            full_response = "".join(self.assistant_buffer)
            response_file = self.output_dir / "assistant_full.md"
            with open(response_file, 'w') as f:
                f.write(full_response)

            self.event_logger.log("assistant_output", {
                "length": len(full_response),
                "timestamp": datetime.now().isoformat(),
                "session_id": self.session_id
            })

        # Add assistant response to conversation log (avoid duplicates)
        if full_response:
            # Check if response already exists in conversation log
            has_response = any(
                entry.get("type") == "response" and entry.get("role") == "assistant"
                for entry in self.conversation_log
            )
            if not has_response:
                self.conversation_log.append({
                    "role": "assistant",
                    "content": full_response,
                    "timestamp": datetime.now().isoformat(),
                    "type": "response"
                })

        # Save complete conversation log as markdown
        self._save_conversation_log()

        # Save conversation log as JSON for programmatic access
        if self.conversation_log:
            conv_json_file = self.output_dir / "conversation.json"
            with open(conv_json_file, 'w') as f:
                json.dump(self.conversation_log, f, indent=2)
        
        # Save materials catalog with enhanced metadata
        self.materials_tracker.save_catalog(
            self.output_dir / "materials_catalog.json",
            enhanced=True
        )
        
        # Generate summary
        materials_summary = self.materials_tracker.get_summary()
        
        # Tool statistics
        mcp_tools = {}
        for tc in self.tool_calls.values():
            tool_name = tc.mcp_tool or tc.wrapper_name
            if tool_name not in mcp_tools:
                mcp_tools[tool_name] = {
                    "count": 0,
                    "total_ms": 0,
                    "materials": 0
                }
            mcp_tools[tool_name]["count"] += 1
            mcp_tools[tool_name]["total_ms"] += tc.duration_ms
            if tc.materials_extracted:
                mcp_tools[tool_name]["materials"] += len(tc.materials_extracted)
        
        # Calculate averages
        for tool_stats in mcp_tools.values():
            if tool_stats["count"] > 0:
                tool_stats["avg_ms"] = tool_stats["total_ms"] / tool_stats["count"]
        
        summary = {
            "session_id": self.session_id,
            "total_time_s": time.time() - self.run_start_time,
            "ttfb_ms": (self.first_token_time - self.run_start_time) * 1000 if self.first_token_time else None,
            "tool_calls_total": len(self.tool_calls),
            "materials_found": materials_summary["total_materials"],
            "unique_compositions": materials_summary["unique_compositions"],
            "mcp_operations": sum(1 for tc in self.tool_calls.values() if tc.mcp_tool),
            "timestamp": datetime.now().isoformat(),
            "mcp_tools": mcp_tools,
            "materials_summary": {
                "total": materials_summary["total_materials"],
                "with_energy": materials_summary["materials_with_energy"],
                "min_energy": materials_summary.get("min_energy"),
                "max_energy": materials_summary.get("max_energy"),
                "avg_energy": materials_summary.get("avg_energy")
            }
        }
        
        # Save summary
        with open(self.output_dir / "summary.json", 'w') as f:
            json.dump(summary, f, indent=2)
        
        # Log session end
        self.event_logger.log_session_end(self.session_id, summary)
        
        return summary