"""
Core agent logic for CrystaLyse.AI.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional
from contextlib import asynccontextmanager, AsyncExitStack

try:
    from agents import Agent, Runner
    from agents.mcp import MCPServerStdio
    from agents.model_settings import ModelSettings
    from agents.items import ItemHelpers
    
    # Try to import SQLiteSession from different locations
    SQLiteSession = None
    try:
        from agents import SQLiteSession
    except ImportError:
        try:
            from agents.memory import SQLiteSession
        except ImportError:
            try:
                from agents.memory.session import SQLiteSession
            except ImportError:
                logging.warning("SQLiteSession not available - sessions will use in-memory storage")
    
    SDK_AVAILABLE = True
except ImportError as e:
    SDK_AVAILABLE = False
    SQLiteSession = None
    logging.warning(f"OpenAI Agents SDK not available: {e}")

from ..config import Config
from ..ui.trace_handler import ToolTraceHandler
from ..workspace import workspace_tools

logger = logging.getLogger(__name__)

class EnhancedCrystaLyseAgent:
    """
    The backend of CrystaLyse.AI. It processes requests, manages MCP servers,
    and uses tools to fulfill user queries. It is completely UI-agnostic.
    """
    
    def __init__(
        self,
        config: Optional[Config] = None,
        project_name: str = "crystalyse_session",
        mode: str = "adaptive",
        model: Optional[str] = None,
    ):
        self.config = config or Config.load()
        self.project_name = project_name
        self.mode = mode
        self.model = model
        self.session_id = f"{project_name}_{mode}"

    @asynccontextmanager
    async def _managed_mcp_servers(self):
        """Starts, manages, and stops MCP servers."""
        if not SDK_AVAILABLE:
            yield []
            return
        
        servers = []
        stack = AsyncExitStack()
        try:
            server_configs = {
                "creative": "chemistry_creative",
                "rigorous": "chemistry_unified",
                "adaptive": "chemistry_unified",
            }
            chem_server_name = server_configs.get(self.mode, "chemistry_unified")
            
            # Start Servers
            for server_name in [chem_server_name, "visualization"]:
                try:
                    config = self.config.get_server_config(server_name)
                    server = await stack.enter_async_context(MCPServerStdio(
                        name=server_name.replace("_", "").title(),
                        params=config,
                        client_session_timeout_seconds=300
                    ))
                    servers.append(server)
                    logger.info(f"✅ Connected to {server_name} server.")
                except Exception as e:
                    logger.warning(f"⚠️ Could not start {server_name} server: {e}")

            yield servers
        finally:
            await stack.aclose()
            logger.info("✅ All MCP servers shut down.")

    async def discover(
        self,
        query: str,
        history: Optional[List[Dict[str, Any]]] = None,
        trace_handler: Optional[ToolTraceHandler] = None
    ) -> Dict[str, Any]:
        """
        Processes a single discovery request, streaming events to the trace_handler.
        """
        if not SDK_AVAILABLE:
            return {"status": "failed", "error": "OpenAI Agents SDK is not installed."}

        async with self._managed_mcp_servers() as mcp_servers:
            try:
                # Create session if SQLiteSession is available, otherwise use None
                session = SQLiteSession(self.session_id) if SQLiteSession else None
                selected_model = self.model or self._select_model_for_mode(self.mode)
                
                sdk_agent = Agent(
                    name="CrystaLyse",
                    model=selected_model,
                    instructions=self._create_enhanced_instructions(self.mode, history),
                    tools=[
                        workspace_tools.read_file,
                        workspace_tools.write_file,
                        workspace_tools.list_files,
                        workspace_tools.request_user_clarification,
                    ],
                    model_settings=ModelSettings(tool_choice="auto"),
                    mcp_servers=mcp_servers
                )
                
                timeout_seconds = self.config.mode_timeouts.get(self.mode, 180)
                
                final_response = "No response generated."
                async with asyncio.timeout(timeout_seconds):
                    result = Runner.run_streamed(
                        starting_agent=sdk_agent,
                        input=query,
                        session=session,
                        max_turns=20
                    )
                    
                    async for event in result.stream_events():
                        if trace_handler:
                            trace_handler.on_event(event)
                        
                        # Capture any message output (more comprehensive)
                        if hasattr(event, 'item') and hasattr(event.item, 'type'):
                            if event.item.type == "message_output_item":
                                final_response = ItemHelpers.text_message_output(event.item)
                            elif event.item.type == "reasoning_item":
                                # Also capture reasoning as potential final output
                                reasoning_content = getattr(event.item, 'content', '')
                                if reasoning_content and len(reasoning_content) > 50:  # Substantial content
                                    final_response = reasoning_content
                    
                    # Also try to get the final result after streaming
                    try:
                        final_result = await result
                        if hasattr(final_result, 'final_output') and final_result.final_output:
                            final_response = final_result.final_output
                        elif hasattr(final_result, 'items') and final_result.items:
                            # Extract text from the last item
                            last_item = final_result.items[-1]
                            if hasattr(last_item, 'content'):
                                final_response = last_item.content
                    except Exception as e:
                        logger.debug(f"Could not extract final result: {e}")

                return {
                    "status": "completed",
                    "query": query,
                    "response": final_response,
                }
            
            except asyncio.TimeoutError:
                logger.error(f"Discovery timed out after {timeout_seconds} seconds.")
                return {"status": "failed", "error": "The operation timed out.", "query": query}
            except Exception as e:
                logger.error(f"Discovery failed: {e}", exc_info=True)
                return {"status": "failed", "error": str(e), "query": query}

    def _select_model_for_mode(self, mode: str) -> str:
        return {"creative": "o4-mini", "rigorous": "o3", "adaptive": "o4-mini"}.get(mode, "o4-mini")

    def _create_enhanced_instructions(self, mode: str, history: Optional[List[Dict[str, Any]]]) -> str:
        """Creates enhanced system instructions, now including conversation history."""
        try:
            prompt_path = self.config.base_dir / "crystalyse" / "prompts" / "unified_agent_prompt.md"
            with open(prompt_path, 'r') as f:
                base_instructions = f.read()
        except Exception as e:
            logger.warning(f"Could not load unified prompt: {e}, using fallback")
            base_instructions = "You are CrystaLyse, an advanced autonomous materials discovery agent."
        
        mode_enhancements = {
            "creative": "\n## Creative Mode: Focus on rapid exploration and novel ideas.",
            "rigorous": "\n## Rigorous Mode: Focus on comprehensive validation and accuracy.",
            "adaptive": "\n## Adaptive Mode: Balance exploration and validation based on context."
        }
        
        if history:
            history_str = "\n\n## Conversation History\n"
            for msg in history:
                history_str += f"- {msg['role'].title()}: {msg['content']}\n"
            base_instructions += history_str

        return base_instructions + mode_enhancements.get(mode, "")