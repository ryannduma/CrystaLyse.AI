"""
CrystaLyse Agent wrapper with automatic provenance capture
"""

import asyncio
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime

# Add paths for imports
import sys
dev_path = Path(__file__).parent.parent.parent / "dev"
if str(dev_path) not in sys.path:
    sys.path.insert(0, str(dev_path))

provenance_path = Path(__file__).parent.parent
if str(provenance_path) not in sys.path:
    sys.path.insert(0, str(provenance_path))

from crystalyse.agents.openai_agents_bridge import EnhancedCrystaLyseAgent
from handlers import ProvenanceTraceHandler
from rich.console import Console


class CrystaLyseWithProvenance:
    """
    CrystaLyse agent with integrated provenance capture.
    
    This wrapper automatically captures complete provenance for all discoveries,
    including MCP tool calls, materials found, and performance metrics.
    """
    
    def __init__(
        self,
        mode: str = "balanced",
        project_name: Optional[str] = None,
        provenance_dir: str = "./provenance_output",
        enable_visual: bool = True,
        save_raw_outputs: bool = True,
        console: Optional[Console] = None
    ):
        """
        Initialize CrystaLyse with provenance.
        
        Args:
            mode: Discovery mode (creative, balanced, rigorous)
            project_name: Optional project name
            provenance_dir: Directory for provenance files
            enable_visual: Show visual trace output
            save_raw_outputs: Save raw tool outputs
            console: Rich console for output
        """
        self.mode = mode
        self.project_name = project_name or f"crystalyse_{mode}"
        self.provenance_dir = Path(provenance_dir)
        self.enable_visual = enable_visual
        self.save_raw_outputs = save_raw_outputs
        self.console = console or Console()
        
        # Initialize agent
        self.agent = EnhancedCrystaLyseAgent(
            mode=mode,
            project_name=self.project_name
        )
        
        # Track sessions
        self.sessions = []
    
    async def discover(
        self,
        query: str,
        session_id: Optional[str] = None,
        timeout: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Run discovery with automatic provenance capture.
        
        Args:
            query: Discovery query
            session_id: Optional session identifier
            timeout: Optional timeout in seconds
            
        Returns:
            Discovery result with provenance summary
        """
        # Generate session ID
        if not session_id:
            session_id = f"{self.mode}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Set timeout based on mode if not specified
        if timeout is None:
            timeout = {
                "creative": 180,
                "balanced": 300,
                "rigorous": 600
            }.get(self.mode, 300)
        
        # Initialize trace handler
        trace_handler = ProvenanceTraceHandler(
            console=self.console,
            output_dir=self.provenance_dir,
            session_id=session_id,
            enable_provenance=True,
            enable_visual=self.enable_visual,
            capture_mcp_logs=True,
            save_raw_outputs=self.save_raw_outputs
        )
        
        # Log query
        if trace_handler.event_logger:
            trace_handler.event_logger.log("discovery_start", {
                "query": query,
                "mode": self.mode,
                "timeout": timeout,
                "timestamp": datetime.now().isoformat()
            })
        
        try:
            # Run discovery with timeout
            result = await asyncio.wait_for(
                self.agent.discover(query, trace_handler=trace_handler),
                timeout=timeout
            )
            
            # Get provenance summary
            provenance_summary = trace_handler.finalize()
            
            # Track session
            session_info = {
                "session_id": session_id,
                "query": query,
                "mode": self.mode,
                "status": result.get("status", "unknown"),
                "materials_found": provenance_summary.get("materials_found", 0),
                "duration_s": provenance_summary.get("total_time_s", 0),
                "timestamp": datetime.now().isoformat()
            }
            self.sessions.append(session_info)
            
            # Add provenance to result
            result["provenance"] = {
                "session_id": session_id,
                "output_dir": str(trace_handler.output_dir),
                "summary": provenance_summary
            }
            
            # Log success
            if trace_handler.event_logger:
                trace_handler.event_logger.log("discovery_complete", {
                    "status": "success",
                    "materials_found": provenance_summary.get("materials_found", 0),
                    "duration_s": provenance_summary.get("total_time_s", 0)
                })
            
            return result
            
        except asyncio.TimeoutError:
            # Log timeout
            if trace_handler.event_logger:
                trace_handler.event_logger.log("discovery_timeout", {
                    "timeout_s": timeout,
                    "timestamp": datetime.now().isoformat()
                })
            
            # Still finalize to save partial results
            provenance_summary = trace_handler.finalize()
            
            return {
                "status": "timeout",
                "error": f"Discovery timed out after {timeout}s",
                "provenance": {
                    "session_id": session_id,
                    "output_dir": str(trace_handler.output_dir),
                    "summary": provenance_summary
                }
            }
            
        except Exception as e:
            # Log error
            if trace_handler.event_logger:
                trace_handler.event_logger.log("discovery_error", {
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                })
            
            # Finalize to save partial results
            provenance_summary = trace_handler.finalize()
            
            return {
                "status": "error",
                "error": str(e),
                "provenance": {
                    "session_id": session_id,
                    "output_dir": str(trace_handler.output_dir),
                    "summary": provenance_summary
                }
            }
    
    def get_session_summary(self, session_id: str) -> Optional[Dict]:
        """Get summary for a specific session."""
        for session in self.sessions:
            if session["session_id"] == session_id:
                return session
        return None
    
    def get_all_sessions(self) -> list:
        """Get all session summaries."""
        return self.sessions
    
    def get_materials_catalog(self, session_id: str) -> Optional[list]:
        """Get materials catalog for a session."""
        session_dir = self.provenance_dir / f"runs/{session_id}"
        catalog_file = session_dir / "materials_catalog.json"
        
        if catalog_file.exists():
            import json
            with open(catalog_file) as f:
                return json.load(f)
        return None
    
    def get_provenance_events(self, session_id: str) -> Optional[list]:
        """Get all provenance events for a session."""
        session_dir = self.provenance_dir / f"runs/{session_id}"
        events_file = session_dir / "events.jsonl"
        
        if events_file.exists():
            events = []
            import json
            with open(events_file) as f:
                for line in f:
                    if line.strip():
                        events.append(json.loads(line))
            return events
        return None