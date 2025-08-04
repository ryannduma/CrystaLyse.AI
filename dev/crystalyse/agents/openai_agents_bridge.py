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
from .mode_injector import GlobalModeManager, inject_mode_into_mcp_servers, create_mode_aware_instructions

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
        
        # Set global mode for automatic injection
        GlobalModeManager.set_mode(mode, lock_mode=True)
        logger.info(f"Agent initialized with mode='{mode}' - Mode injection active")

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

            # Inject mode into MCP servers
            servers_with_mode = inject_mode_into_mcp_servers(servers, self.mode)
            yield servers_with_mode
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
                
                # Create mode-aware instructions
                base_instructions = self._create_enhanced_instructions(self.mode, history)
                mode_aware_instructions = create_mode_aware_instructions(base_instructions, self.mode)
                
                sdk_agent = Agent(
                    name="CrystaLyse",
                    model=selected_model,
                    instructions=mode_aware_instructions,
                    tools=[
                        workspace_tools.read_file,
                        workspace_tools.write_file,
                        workspace_tools.list_files,
                        # NOTE: request_user_clarification removed - queries are pre-processed
                    ],
                    model_settings=ModelSettings(tool_choice="auto"),
                    mcp_servers=mcp_servers
                )
                
                timeout_seconds = self.config.mode_timeouts.get(self.mode, 180)
                
                # Create run config with MDG API key for o3 access
                try:
                    from agents import RunConfig
                    from agents.models.openai_provider import OpenAIProvider
                    import os
                    
                    mdg_api_key = os.getenv("OPENAI_MDG_API_KEY") or os.getenv("OPENAI_API_KEY")
                    if mdg_api_key:
                        model_provider = OpenAIProvider(api_key=mdg_api_key)
                        run_config = RunConfig(
                            trace_id=f"crystalyse_{self.session_id}_{asyncio.get_event_loop().time()}",
                            model_provider=model_provider
                        )
                    else:
                        run_config = RunConfig(trace_id=f"crystalyse_{self.session_id}_{asyncio.get_event_loop().time()}")
                except (ImportError, TypeError) as e:
                    # SDK compatibility fallback
                    run_config = None
                    logger.warning(f"Could not create RunConfig with API key: {e}")
                
                final_response = "No response generated."
                async with asyncio.timeout(timeout_seconds):
                    # Use non-streaming mode for o3 model to avoid organization verification requirement
                    if selected_model == "o3":
                        run_args = {
                            "starting_agent": sdk_agent,
                            "input": query,
                            "session": session,
                            "max_turns": 1000
                        }
                        if run_config:
                            run_args["run_config"] = run_config
                            
                        result = await Runner.run(**run_args)
                        
                        # Extract response from non-streaming result
                        if hasattr(result, 'final_output') and result.final_output:
                            final_response = result.final_output
                        elif hasattr(result, 'items') and result.items:
                            # Extract text from the last item
                            last_item = result.items[-1]
                            if hasattr(last_item, 'content'):
                                final_response = last_item.content
                    else:
                        # Use streaming for other models
                        stream_args = {
                            "starting_agent": sdk_agent,
                            "input": query,
                            "session": session,
                            "max_turns": 1000
                        }
                        if run_config:
                            stream_args["run_config"] = run_config
                            
                        result = Runner.run_streamed(**stream_args)
                        
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
            "creative": f"\n## Creative Mode: Focus on rapid exploration and novel ideas.\n**CRITICAL ERROR PREVENTION**: comprehensive_materials_analysis REQUIRES mode=\"creative\" - the tool will FAIL without it!",
            "rigorous": f"\n## Rigorous Mode: Focus on comprehensive validation and accuracy.\n**CRITICAL ERROR PREVENTION**: comprehensive_materials_analysis REQUIRES mode=\"rigorous\" - the tool will FAIL without it!",
            "adaptive": f"\n## Adaptive Mode: Balance exploration and validation based on context.\n**CRITICAL ERROR PREVENTION**: comprehensive_materials_analysis REQUIRES mode=\"adaptive\" - the tool will FAIL without it!"
        }
        
        if history:
            history_str = "\n\n## Conversation History\n"
            for msg in history:
                history_str += f"- {msg['role'].title()}: {msg['content']}\n"
            base_instructions += history_str

        return base_instructions + mode_enhancements.get(mode, "")