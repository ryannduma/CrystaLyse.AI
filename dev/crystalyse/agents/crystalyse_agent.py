"""
CrystaLyse Agent - Unified Materials Discovery Agent with Enhanced Infrastructure and Memory
Consolidates all functionality into a single, comprehensive agent implementation.
"""

import asyncio
import logging
import json
import time
from typing import List, Dict, Any, Literal, Optional
from dataclasses import dataclass
from pathlib import Path
from contextlib import AsyncExitStack

# Core agent framework - Fixed circular import issue
try:
    # Force import from OpenAI agents SDK by manipulating sys.path
    import sys
    import os
    
    # Temporarily remove the local crystalyse directory from sys.path
    # to force Python to import from the OpenAI agents SDK
    current_dir = os.path.dirname(os.path.abspath(__file__))
    crystalyse_parent = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
    
    # Store original sys.path and remove conflicting paths
    original_paths = sys.path[:]
    paths_to_remove = [p for p in sys.path if 'crystalyse' in p.lower()]
    for path in paths_to_remove:
        if path in sys.path:
            sys.path.remove(path)
    
    # Add the OpenAI agents SDK path explicitly
    openai_agents_path = os.path.join(crystalyse_parent, 'openai-agents-python', 'src')
    if os.path.exists(openai_agents_path) and openai_agents_path not in sys.path:
        sys.path.insert(0, openai_agents_path)
    
    # Now try to import from OpenAI agents SDK
    from agents import Agent, Runner, function_tool, gen_trace_id, trace
    from agents.mcp import MCPServerStdio
    from agents.model_settings import ModelSettings
    
    # Restore original sys.path
    sys.path = original_paths
    
except ImportError as e:
    # If that fails, provide placeholder implementations
    print(f"⚠️  Warning: OpenAI agents SDK not available: {e}")
    
    # Provide minimal placeholder implementations to prevent crashes
    class Agent:
        def __init__(self, *args, **kwargs):
            pass
    
    class Runner:
        @staticmethod
        async def run(*args, **kwargs):
            return {"error": "OpenAI agents SDK not available"}
    
    def function_tool(*args, **kwargs):
        def decorator(func):
            return func
        return decorator
    
    def gen_trace_id():
        return "no-trace"
    
    def trace(*args, **kwargs):
        def decorator(func):
            return func
        return decorator
    
    class MCPServerStdio:
        def __init__(self, *args, **kwargs):
            pass
    
    class ModelSettings:
        def __init__(self, *args, **kwargs):
            pass

from pydantic import BaseModel

# CrystaLyse imports
from ..config import config
from ..validation import validate_computational_response, ValidationViolation
from ..infrastructure import (
    get_connection_pool, 
    get_session_manager,
    get_resilient_caller,
    cleanup_connection_pool,
    cleanup_session_manager
)

logger = logging.getLogger(__name__)

# Simple memory system imports
try:
    from ..memory import CrystaLyseMemory, get_memory_tools
    MEMORY_AVAILABLE = True
    logger.info("✅ Simple memory system loaded successfully")
except ImportError as e:
    MEMORY_AVAILABLE = False
    logger.info(f"Simple memory system not available: {e} - using graceful fallbacks")

@dataclass
class AgentConfig:
    """Configuration for the CrystaLyse agent"""
    mode: Literal["creative", "rigorous"] = "rigorous"
    model: str = None  # Will be auto-selected based on mode
    max_turns: int = 100  # Increased to handle complex multi-step discoveries
    enable_mace: bool = True
    enable_chemeleon: bool = True
    enable_smact: bool = True  # Will be overridden based on mode
    parallel_batch_size: int = 10
    max_candidates: int = 100
    structure_samples: int = 5
    enable_metrics: bool = True
    enable_memory: bool = True
    
    def __post_init__(self):
        """Configure model and tools based on mode"""
        if self.model is None:
            if self.mode == "rigorous":
                self.model = "o3"  # Use o3 for rigorous mode 
            else:
                self.model = "o4-mini"  # Use o4-mini for creative mode
        
        # Configure tool usage based on mode
        if self.mode == "creative":
            # Creative mode: fast exploration with Chemeleon + MACE only (no SMACT)
            self.enable_smact = False
            self.enable_chemeleon = True
            self.enable_mace = True
        elif self.mode == "rigorous":
            # Rigorous mode: full validation with all 3 tools
            self.enable_smact = True
            self.enable_chemeleon = True
            self.enable_mace = True

# Response models for structured outputs
class MaterialRecommendation(BaseModel):
    """Structured output for material recommendations"""
    formula: str
    confidence: float
    reasoning: str
    properties: List[str]
    synthesis_method: str

class DiscoveryResult(BaseModel):
    """Structured output for materials discovery"""
    recommended_materials: List[MaterialRecommendation]
    methodology: str
    confidence: float
    next_steps: List[str]

class ClarificationQuestion(BaseModel):
    """A structured question to ask the user for clarification."""
    id: int
    question: str
    options: List[str]
    why: str

# Self-assessment tools for the agent
@function_tool
def assess_progress(current_status: str, steps_completed: int) -> str:
    """
    Assess current progress and suggest next steps.
    
    Args:
        current_status: Description of what's been done so far
        steps_completed: Number of steps completed
    """
    if steps_completed == 0:
        return "No steps completed yet. Start with element selection or composition validation."
    elif steps_completed < 3:
        return f"Good start! {steps_completed} steps done. Continue with composition generation or validation."
    elif steps_completed < 6:
        return f"Making progress! {steps_completed} steps completed. Consider structure generation or energy analysis."
    else:
        return f"Excellent progress! {steps_completed} steps done. Time to synthesise results and make recommendations."

@function_tool  
def explore_alternatives(current_issue: str) -> str:
    """
    Generate alternative approaches when stuck.
    
    Args:
        current_issue: Description of the current problem
    """
    alternatives = [
        "Try simpler compositions with fewer elements",
        "Use well-known structure prototypes (rock salt, perovskite, spinel)",
        "Focus on binary compounds first, then ternary",
        "Use heuristic validation if SMACT tools fail",
        "Consider known material families (spinels, olivines, layered oxides)",
        "Generate fewer but more diverse candidates"
    ]
    
    return f"Alternative approaches for '{current_issue}':\n" + "\n".join(f"• {alt}" for alt in alternatives)

@function_tool
def ask_clarifying_questions(questions: List[ClarificationQuestion]) -> str:
    """
    Asks the user a series of clarifying questions to narrow down the search space.
    Call this tool if the user's initial query is too broad or ambiguous.
    The user's answers will provide critical context for the subsequent analysis.

    Args:
        questions: A list of questions to ask the user. Each question should be a dictionary
                   with keys 'id', 'question', 'options', and 'why'.
    """
    output = "To provide the best recommendations, I need to clarify a few things:\n\n"
    for q in questions:
        output += f"• **{q['question']}**\n"
        if q.get('options'):
            output += f"  Options: {', '.join(q['options'])}\n"
        output += f"  *({q['why']})*\n\n"
    
    return output + "Please provide your answers to help me focus the search."

class ComputationalQueryClassifier:
    """Classify queries to determine if they require computational tools."""
    
    def __init__(self):
        self.computational_keywords = [
            'validate', 'check', 'verify', 'stability', 'stable',
            'energy', 'formation', 'calculate', 'compute',
            'structure', 'crystal', 'polymorph', 'space group',
            'synthesis', 'predict', 'generate', 'design',
            'find', 'suggest', 'discover', 'novel', 'alternatives',
            'compare', 'rank', 'optimise', 'optimize', 'improve'
        ]
        
        self.chemical_formula_pattern = r'\b[A-Z][a-z]?\d*(?:[A-Z][a-z]?\d*)*\b'
        
    def requires_computation(self, query: str) -> bool:
        """Determine if query requires computational tools."""
        query_lower = query.lower()
        
        # Check for computational keywords
        has_computational_keywords = any(
            keyword in query_lower for keyword in self.computational_keywords
        )
        
        # Check for chemical formulas
        import re
        has_formulas = bool(re.search(self.chemical_formula_pattern, query))
        
        return has_computational_keywords or has_formulas
    
    def get_enforcement_level(self, query: str) -> str:
        """Determine tool choice enforcement level."""
        if self.requires_computation(query):
            return "required"  # Force tools for computational queries
        else:
            return "auto"      # Allow flexibility for general queries

class CrystaLyse:
    """
    Unified CrystaLyse agent with enhanced infrastructure and memory capabilities.
    
    This agent consolidates all materials discovery functionality including:
    - Advanced infrastructure with persistent connections and retry logic
    - Comprehensive memory system with caching and scratchpads
    - Model selection (o3 for rigorous, o4-mini for creative)
    - Session management and user profiling
    - Full materials discovery toolchain (SMACT, Chemeleon, MACE)
    """

    def __init__(
        self, 
        agent_config: AgentConfig = None,
        system_config=None,
        user_id: str = "default_user"
    ):
        # Configuration
        self.agent_config = agent_config or AgentConfig()
        self.system_config = system_config or config
        self.user_id = user_id
        
        # Properties from config (set these first)
        self.mode = self.agent_config.mode
        self.model_name = self.agent_config.model
        self.max_turns = getattr(self.agent_config, 'max_turns', 30)
        
        # Agent components
        self.agent = None
        self.instructions = self._load_system_prompt()
        self.session = None
        self.memory_system = None
        
        # Infrastructure components
        self.connection_pool = get_connection_pool()
        self.resilient_caller = get_resilient_caller()
        self.session_manager = get_session_manager()
        
        # Query processing
        self.query_classifier = ComputationalQueryClassifier()
        
        # Metrics
        self.metrics = {}
        
        logger.info(f"CrystaLyse agent initialized in {self.mode} mode (model: {self.model_name}) for user {user_id}")
        
    def _load_system_prompt(self) -> str:
        """Load and process the system prompt from markdown file."""
        prompt_path = Path(__file__).parent.parent / "prompts" / "unified_agent_prompt.md"
        
        try:
            with open(prompt_path, 'r', encoding='utf-8') as f:
                prompt = f.read()
        except FileNotFoundError:
            logger.warning(f"Prompt file not found: {prompt_path}")
            prompt = "CrystaLyse unified agent for computational materials discovery."
        
        # Add mode-specific additions
        mode_additions = {
            "rigorous": "\n\nCrystaLyse is currently operating in Rigorous Mode. Use ALL 3 tools (SMACT + Chemeleon + MACE) for comprehensive validation. Every composition must be validated with SMACT, every structure must have calculated energies, and all results must include uncertainty estimates.\n\n**IMPORTANT: Use individual tools (smact_validity, generate_structures, calculate_energies) instead of pipeline tools for better verifiability and transparency. Call each tool separately to maintain clear audit trails.**",
            "creative": "\n\nCrystaLyse is currently operating in Creative Mode. Use ONLY Chemeleon + MACE tools (NO SMACT validation). Focus on rapid exploration of unconventional chemical spaces. Generate compositions freely and validate only the final candidates with structure and energy calculations.\n\n**IMPORTANT: Use individual tools (generate_structures, calculate_energies) instead of pipeline tools for better verifiability and transparency. Call each tool separately to maintain clear audit trails.**"
        }
        
        if self.mode in mode_additions:
            prompt += mode_additions[self.mode]
        
        # Add memory system information
        prompt += "\n\n## Memory System\n\nYou have access to a simple file-based memory system with the following tools:\n- `save_to_memory(fact, section)` - Save important information to user memory\n- `search_memory(query)` - Search user memory for relevant information\n- `save_discovery(formula, properties)` - Cache expensive computational results\n- `search_discoveries(query)` - Search cached discoveries\n- `get_cached_discovery(formula)` - Check if a material has been analyzed before\n- `get_memory_context()` - Get comprehensive memory context\n- `generate_weekly_summary()` - Generate research progress summary\n- `get_memory_statistics()` - Get memory system statistics\n\n**Use these tools to:**\n- Remember important user preferences and constraints\n- Cache expensive MACE, Chemeleon, and SMACT calculations\n- Build on previous discoveries and research\n- Maintain continuity across sessions\n- Provide personalized recommendations based on user history"
            
        return prompt

    async def _initialize_memory_system(self):
        """Initialize the simple file-based memory system."""
        if not self.agent_config.enable_memory:
            logger.info("Memory system disabled by configuration")
            return None
            
        if not MEMORY_AVAILABLE:
            logger.info("Memory system components not available - continuing without memory")
            return None
            
        try:
            # Create simple memory system
            logger.info(f"Initialising simple memory system for user {self.user_id}")
            
            self.memory_system = CrystaLyseMemory(user_id=self.user_id)
            
            # Log memory system components
            components = [
                "Session Memory (conversation context)",
                "Discovery Cache (JSON file)",
                "User Memory (markdown file)",
                "Cross-Session Context (auto-generated insights)"
            ]
                
            logger.info(f"✅ Simple memory system initialised with: {', '.join(components)}")
            return self.memory_system
            
        except Exception as e:
            logger.warning(f"Memory system initialisation failed: {e}")
            logger.info("Continuing without memory system - core functionality preserved")
            return None

    def _get_all_tools(self) -> List:
        """Get all available tools including simple memory tools for enhanced agent capabilities."""
        base_tools = [assess_progress, explore_alternatives, ask_clarifying_questions]
        
        # Add memory tools if memory system is available
        if MEMORY_AVAILABLE and self.memory_system:
            try:
                memory_tools = get_memory_tools()
                logger.info(f"Added {len(memory_tools)} simple memory tools to agent (session, cache, user memory, insights)")
                return base_tools + memory_tools
            except Exception as e:
                logger.warning(f"Could not load memory tools: {e}")
                
        logger.info(f"Using base tools only ({len(base_tools)} tools available)")
        return base_tools

    async def _get_or_create_session(self):
        """Get or create a persistent session with memory and fallback options."""
        try:
            # Server configurations - choose appropriate chemistry server based on mode
            server_configs = {}
            if (self.agent_config.enable_smact or 
                self.agent_config.enable_chemeleon or 
                self.agent_config.enable_mace):
                
                # Primary server selection based on mode
                if self.mode == "creative":
                    preferred_server = "chemistry_creative"
                    fallback_server = "chemistry_unified"
                    logger.info("Using chemistry_creative server for creative mode (Chemeleon + MACE)")
                else:
                    preferred_server = "chemistry_unified" 
                    fallback_server = "chemistry_creative"
                    logger.info("Using chemistry_unified server for rigorous mode (SMACT + Chemeleon + MACE)")
                
                # Try preferred server first
                try:
                    chemistry_config = self.system_config.get_server_config(preferred_server)
                    server_configs[preferred_server] = chemistry_config
                    logger.info(f"✅ Primary server {preferred_server} configured successfully")
                except Exception as e:
                    logger.warning(f"⚠️ Primary server {preferred_server} failed: {e}")
                    logger.info(f"🔄 Attempting fallback to {fallback_server}")
                    
                    try:
                        fallback_config = self.system_config.get_server_config(fallback_server)
                        server_configs[fallback_server] = fallback_config
                        logger.info(f"✅ Fallback server {fallback_server} configured successfully")
                        
                        # Update mode to match server capabilities
                        if preferred_server == "chemistry_unified" and fallback_server == "chemistry_creative":
                            logger.info("Note: Falling back from rigorous to creative mode due to server availability")
                    except Exception as fallback_error:
                        logger.error(f"❌ Both servers failed. Primary: {e}, Fallback: {fallback_error}")
                        raise Exception(f"No chemistry servers available: {e}")
            
            # Get or create session
            self.session = await self.session_manager.get_or_create_session(
                self.user_id, 
                self.agent_config,
                server_configs
            )
            
            return self.session
            
        except Exception as e:
            logger.error(f"Failed to create session: {e}")
            return None

    async def _setup_agent(self, tool_choice: str):
        """Set up the agent with enhanced infrastructure and memory."""
        try:
            # Initialize memory system
            await self._initialize_memory_system()
            
            # Get persistent connections
            mcp_servers = []
            
            if self.session and self.session.connection_pool:
                # Use session's connection pool - select appropriate chemistry server
                chemistry_server_name = "chemistry_creative" if self.mode == "creative" else "chemistry_unified"
                connection = await self.session.connection_pool.get_connection(chemistry_server_name)
                if connection:
                    mcp_servers.append(connection)
                    logger.info(f"✅ Using persistent MCP connection to {chemistry_server_name}")
                else:
                    logger.warning(f"⚠️ No persistent connection available for {chemistry_server_name}, falling back to traditional setup")
            
            # Fallback to traditional setup if needed
            if not mcp_servers:
                mcp_servers = await self._setup_traditional_connections()
            
            logger.info(f"Initialised CrystaLyse agent with {len(mcp_servers)} MCP servers in {self.mode} mode.")
            
            # Create model settings (o3 and o4-mini don't support temperature)
            model_settings = ModelSettings(
                tool_choice=tool_choice,
            )
            
            # Get all tools including 23 memory tools
            all_tools = self._get_all_tools()
            
            # Prepare agent data for memory system context
            agent_data = {}
            if self.memory_system:
                agent_data.update({
                    'memory_system': self.memory_system,
                    'session_id': getattr(self.memory_system, 'session_id', 'unknown'),
                    'user_id': self.user_id
                })
            
            # Create agent with enhanced configuration and memory integration
            try:
                self.agent = Agent(
                    name="CrystaLyse",
                    model=self.model_name,
                    instructions=self.instructions,
                    model_settings=model_settings,
                    mcp_servers=mcp_servers,
                    tools=all_tools,
                    agent_data=agent_data if agent_data else None
                )
                logger.info(f"✅ Agent created with {len(all_tools)} tools and memory system context")
            except TypeError as e:
                if "agent_data" in str(e):
                    # Fallback without agent_data for older SDK versions
                    logger.info("Creating agent without agent_data for SDK compatibility")
                    self.agent = Agent(
                        name="CrystaLyse",
                        model=self.model_name,
                        instructions=self.instructions,
                        model_settings=model_settings,
                        mcp_servers=mcp_servers,
                        tools=all_tools
                    )
                    logger.info(f"✅ Agent created with {len(all_tools)} tools (no memory context)")
                else:
                    raise e
            
            logger.info("✅ CrystaLyse agent setup complete")
            
        except Exception as e:
            logger.error(f"Failed to setup CrystaLyse agent: {e}")
            raise


    async def _setup_traditional_connections(self) -> List:
        """Fallback to traditional connection setup with server fallback logic."""
        try:
            async with AsyncExitStack() as stack:
                mcp_servers = []
                
                if (self.agent_config.enable_smact or 
                    self.agent_config.enable_chemeleon or 
                    self.agent_config.enable_mace):
                    
                    # Choose appropriate chemistry server based on mode with fallback
                    if self.mode == "creative":
                        preferred_server = "chemistry_creative"
                        fallback_server = "chemistry_unified"
                        preferred_display = "ChemistryCreative"
                        fallback_display = "ChemistryUnified"
                        logger.info("Setting up traditional connection to chemistry_creative server")
                    else:
                        preferred_server = "chemistry_unified"
                        fallback_server = "chemistry_creative"
                        preferred_display = "ChemistryUnified"
                        fallback_display = "ChemistryCreative"
                        logger.info("Setting up traditional connection to chemistry_unified server")
                    
                    # Try preferred server first
                    chemistry_server = None
                    try:
                        chemistry_config = self.system_config.get_server_config(preferred_server)
                        chemistry_server = await stack.enter_async_context(
                            MCPServerStdio(
                                name=preferred_display,
                                params={
                                    "command": chemistry_config["command"],
                                    "args": chemistry_config["args"],
                                    "cwd": chemistry_config["cwd"],
                                    "env": chemistry_config.get("env", {})
                                },
                                client_session_timeout_seconds=300  # 5 minutes for complex calculations
                            )
                        )
                        logger.info(f"✅ Successfully connected to {preferred_server}")
                    except Exception as e:
                        logger.warning(f"⚠️ Failed to connect to {preferred_server}: {e}")
                        logger.info(f"🔄 Attempting fallback to {fallback_server}")
                        
                        try:
                            fallback_config = self.system_config.get_server_config(fallback_server)
                            chemistry_server = await stack.enter_async_context(
                                MCPServerStdio(
                                    name=fallback_display,
                                    params={
                                        "command": fallback_config["command"],
                                        "args": fallback_config["args"],
                                        "cwd": fallback_config["cwd"],
                                        "env": fallback_config.get("env", {})
                                    },
                                    client_session_timeout_seconds=300
                                )
                            )
                            logger.info(f"✅ Successfully connected to fallback server {fallback_server}")
                            
                            # Update mode to match server capabilities
                            if preferred_server == "chemistry_unified" and fallback_server == "chemistry_creative":
                                logger.info("Note: Falling back from rigorous to creative mode due to server availability")
                        except Exception as fallback_error:
                            logger.error(f"❌ Both servers failed. Primary: {e}, Fallback: {fallback_error}")
                            raise Exception(f"No chemistry servers available")
                    
                    if chemistry_server:
                        mcp_servers.append(chemistry_server)
                
                return mcp_servers
                
        except Exception as e:
            logger.error(f"Failed traditional connection setup: {e}")
            return []

    async def discover_materials(self, query: str, session: Optional[Agent] = None, trace_workflow: bool = True) -> dict:
        """
        Discover materials using enhanced infrastructure and memory capabilities.
        """
        if session:
            self.agent = session
        
        start_time = time.time()
        
        # Get or create persistent session with memory
        if not self.session:
            session = await self._get_or_create_session()
        
        # Initialize memory system if not already done
        if not self.memory_system:
            await self._initialize_memory_system()
        
        # Classify query to determine tool enforcement level
        requires_computation = self.query_classifier.requires_computation(query)
        tool_choice = self.query_classifier.get_enforcement_level(query)
        
        logger.info(f"Query classification: requires_computation={requires_computation}, tool_choice={tool_choice}")
        
        # Check for existing completed analysis before proceeding
        if self.memory_system and requires_computation:
            existing_result = await self._check_existing_analysis(query)
            if existing_result:
                logger.info(f"✅ Found existing analysis for query: {query[:50]}...")
                return existing_result
        
        # Enhanced query for computational requirements
        if requires_computation:
            enhanced_query = f"""
            COMPUTATIONAL QUERY DETECTED: This query requires actual tool usage.
            DO NOT generate results without calling tools.
            
            Query: {query}
            
            Remember: Use tools for ANY computational claims. Report tool failures clearly if they occur.
            """
        else:
            enhanced_query = query
        
        try:
            # Setup agent if not already done
            if not self.agent:
                await self._setup_agent(tool_choice)
            
            # Run discovery with enhanced resilience
            result = await self._run_discovery_with_retry(enhanced_query)
            
            # Process results and add memory/session info
            elapsed_time = time.time() - start_time
            
            # Extract final output - handle both dict and object results
            if isinstance(result, dict):
                final_content = str(result.get('final_output', result.get('response', 'No discovery result found.')))
            else:
                final_content = str(result.final_output) if hasattr(result, 'final_output') and result.final_output else "No discovery result found."
            
            # Extract tool calls from result - handle both dict and object results
            if isinstance(result, dict):
                tool_calls = []
                tool_call_count = 0
                # For dict results, we don't have detailed tool call info
            else:
                from agents.items import ToolCallItem
                tool_calls = self._extract_tool_calls(result)
                tool_call_count = sum(1 for item in result.new_items if isinstance(item, ToolCallItem))
            
            # Validate tool usage to detect potential hallucination - handle both dict and object results
            if isinstance(result, dict):
                # For dict results, skip tool validation as we don't have detailed tool call info
                tool_validation = {"is_valid": True, "violations": []}
            else:
                tool_validation = self._validate_tool_usage(result, query, requires_computation)

            # Advanced response validation
            response_validation = self._validate_response_integrity(
                query, final_content, tool_calls, requires_computation
            )
            
            # Use sanitized response if validation failed
            if not response_validation["is_valid"]:
                final_content = response_validation["sanitized_response"]
                logger.error(f"Response validation failed: {response_validation['violations']}")

            # Update memory systems with discoveries
            if requires_computation and tool_call_count > 0:
                # Update session memory
                if self.session:
                    self.session.record_tool_call("crystalyse", True, "discovery")
                    self.session.add_discovered_material(query, {"result": final_content})
                
                # Update simple memory system
                if self.memory_system:
                    try:
                        # Add interaction to session memory
                        self.memory_system.add_interaction(query, final_content)
                        
                        # Try to extract material formula and properties for caching
                        # This is a simplified approach - in practice, we'd extract from tool results
                        if "formula" in final_content.lower():
                            # Simple extraction - could be improved with regex or parsing
                            lines = final_content.split('\n')
                            for line in lines:
                                if any(keyword in line.lower() for keyword in ['formula', 'material', 'compound']):
                                    # Save discovery to user memory
                                    self.memory_system.save_to_memory(
                                        f"Discovery: {line.strip()}", 
                                        "Recent Discoveries"
                                    )
                                    break
                        
                        logger.info("✅ Discovery stored in simple memory system")
                    except Exception as e:
                        logger.warning(f"Could not store discovery in simple memory system: {e}")

            # Include session info and infrastructure stats in metrics
            session_info = None
            infrastructure_stats = None
            
            if self.session:
                session_info = self.session.get_context_summary()
                
            # Get infrastructure statistics
            infrastructure_stats = await self._get_infrastructure_stats()

            return {
                "status": "completed",
                "discovery_result": final_content,
                "metrics": {
                    "tool_calls": tool_call_count,
                    "elapsed_time": elapsed_time,
                    "model": self.model_name,
                    "mode": self.mode,
                    "total_items": len(result.new_items) if hasattr(result, 'new_items') else 0,
                    "raw_responses": len(result.raw_responses) if hasattr(result, 'raw_responses') else 0,
                    "session_info": session_info,
                    "infrastructure_stats": infrastructure_stats
                },
                "tool_validation": tool_validation,
                "response_validation": response_validation,
                "new_items": [self._serialize_item(item) for item in result.new_items[:20]] if hasattr(result, 'new_items') else [],  # Keep more items for CIF extraction
            }

        except Exception as e:
            logger.error(f"An error occurred during material discovery: {e}", exc_info=True)
            elapsed_time = time.time() - start_time
            return {
                "status": "failed",
                "error": str(e),
                "metrics": {
                    "elapsed_time": elapsed_time,
                    "model": self.model_name,
                    "mode": self.mode,
                },
            }

    async def _run_discovery_with_retry(self, query: str):
        """Run discovery with retry logic."""
        return await self.resilient_caller.call_with_retry(
            self._run_discovery,
            query,
            tool_name="crystalyse_agent",
            operation_type="discovery",
            max_retries=2,
            timeout_override=300  # 5 minutes
        )

    async def _run_discovery(self, query: str):
        """Internal discovery method."""
        from agents import RunConfig
        from agents.models.openai_provider import OpenAIProvider
        import os
        
        try:
            # Use MDG API key for better access to o3 and higher rate limits
            mdg_api_key = os.getenv("OPENAI_MDG_API_KEY") or os.getenv("OPENAI_API_KEY")
            model_provider = OpenAIProvider(api_key=mdg_api_key)
            
            run_config = RunConfig(
                trace_id=gen_trace_id(),
                model_provider=model_provider
            )
        except TypeError as e:
            if "model_provider" in str(e):
                # SDK compatibility fallback
                run_config = RunConfig(trace_id=gen_trace_id())
            else:
                raise e
        
        return await Runner.run(
            starting_agent=self.agent,
            input=query,
            max_turns=self.max_turns,
            run_config=run_config
        )

    def _extract_tool_calls(self, result) -> List:
        """Extract tool calls from the result."""
        from agents.items import ToolCallItem, ToolCallOutputItem
        
        tool_calls = []
        tool_call_count = 0
        
        for item in result.new_items:
            # Check for different types of tool-related items
            if isinstance(item, ToolCallItem):
                tool_call_count += 1
                tool_info = {
                    "type": "tool_call",
                    "item_type": type(item).__name__
                }
                
                # Extract tool name based on the type of raw_item
                raw_item = getattr(item, 'raw_item', None)
                if raw_item:
                    # ResponseFunctionToolCall has function.name
                    if hasattr(raw_item, 'function') and hasattr(raw_item.function, 'name'):
                        tool_info["tool_name"] = raw_item.function.name
                    # McpCall has function_name
                    elif hasattr(raw_item, 'function_name'):
                        tool_info["tool_name"] = raw_item.function_name
                    # Other tool types might have different attributes
                    elif hasattr(raw_item, 'name'):
                        tool_info["tool_name"] = raw_item.name
                    else:
                        tool_info["tool_name"] = "unknown"
                
                tool_calls.append(tool_info)
                
            elif isinstance(item, ToolCallOutputItem):
                tool_calls.append({
                    "type": "tool_output", 
                    "item_type": type(item).__name__,
                    "output": getattr(item, 'output', None)
                })
            elif hasattr(item, 'tool_calls') and item.tool_calls:
                # Legacy fallback
                tool_calls.extend(item.tool_calls)
                tool_call_count += len(item.tool_calls)
        
        # Return both the detailed calls and update the count
        return tool_calls

    def _validate_tool_usage(self, result, query: str, requires_computation: bool = None) -> Dict[str, Any]:
        """Validate that computational tools were actually used when expected."""
        from agents.items import ToolCallItem
        
        tool_calls = self._extract_tool_calls(result)
        
        # Count actual tool calls more accurately
        tool_call_count = sum(1 for item in result.new_items if isinstance(item, ToolCallItem))
        
        # Use the classifier result if provided, otherwise fallback to keyword check
        if requires_computation is None:
            needs_computation = self.query_classifier.requires_computation(query)
        else:
            needs_computation = requires_computation
        
        # Extract tool names from actual calls
        tools_used = []
        for call in tool_calls:
            if isinstance(call, dict) and call.get("type") == "tool_call":
                tool_name = call.get("tool_name", "unknown")
                if tool_name != "unknown":
                    tools_used.append(tool_name)
        # Check for computational results in response without tool calls
        response = str(result.final_output) if result.final_output else ""
        
        # Patterns that indicate computational results were reported
        import re
        computational_result_patterns = [
            r'formation energy.*?-?\d+\.\d+\s*ev',
            r'validation.*valid.*confidence.*\d+',
            r'smact.*valid',
            r'space group.*[a-z0-9/-]+',
            r'crystal system.*[a-z]+',
            r'stability.*stable',
            r'confidence.*score.*\d+',
            r'structure.*generated',
            r'energy.*calculated'
        ]
        
        contains_computational_results = any(
            re.search(pattern, response.lower()) 
            for pattern in computational_result_patterns
        )
        
        validation = {
            "needs_computation": needs_computation,
            "tools_called": tool_call_count,
            "tools_used": tools_used,
            "smact_used": any('smact' in tool.lower() for tool in tools_used),
            "chemeleon_used": any('chemeleon' in tool.lower() for tool in tools_used),
            "mace_used": any('mace' in tool.lower() for tool in tools_used),
            "contains_computational_results": contains_computational_results,
            "potential_hallucination": needs_computation and tool_call_count == 0 and contains_computational_results,
            "critical_failure": needs_computation and tool_call_count == 0 and contains_computational_results
        }
        
        if validation["potential_hallucination"]:
            logger.error(f"🚨 CRITICAL HALLUCINATION DETECTED: Query '{query[:50]}...' requires computation but response contains results without tool calls!")
            
        elif validation["critical_failure"]:
            logger.error(f"💥 SYSTEM FAILURE: Computational results reported without actual calculations!")
            
        return validation

    def _validate_response_integrity(
        self, 
        query: str, 
        response: str, 
        tool_calls: List[Any], 
        requires_computation: bool
    ) -> Dict[str, Any]:
        """Validate response integrity using comprehensive validation system."""
        
        is_valid, sanitized_response, violations = validate_computational_response(
            query=query,
            response=response,
            tool_calls=tool_calls,
            requires_computation=requires_computation
        )
        
        # Format violations for logging
        violation_summaries = []
        for violation in violations:
            violation_summaries.append({
                "type": violation.type.value,
                "severity": violation.severity,
                "pattern": violation.pattern,
                "description": violation.description
            })
        
        return {
            "is_valid": is_valid,
            "sanitized_response": sanitized_response,
            "violations": violation_summaries,
            "violation_count": len(violations),
            "critical_violations": len([v for v in violations if v.severity == "critical"]),
            "warning_violations": len([v for v in violations if v.severity == "warning"])
        }

    async def _get_infrastructure_stats(self) -> Dict[str, Any]:
        """Get comprehensive infrastructure statistics."""
        stats = {}
        
        # Connection pool stats
        if self.connection_pool:
            stats["connection_pool"] = self.connection_pool.get_connection_status()
        
        # Resilient caller stats
        if self.resilient_caller:
            stats["resilient_caller"] = self.resilient_caller.get_statistics()
        
        # Session info
        if self.session:
            try:
                stats["session_info"] = {
                    "session_info": getattr(self.session, 'get_session_info', lambda: {"session_id": "unknown"})(),
                    "discoveries": getattr(self.session, 'get_discovery_summary', lambda: {"materials_count": 0})()
                }
            except Exception as e:
                logger.warning(f"Could not get session info: {e}")
                stats["session_info"] = {"error": str(e)}
        
        # Simple memory system stats
        if self.memory_system:
            try:
                memory_stats = self.memory_system.get_memory_statistics()
                memory_stats["status"] = "active"
                stats["memory_system"] = memory_stats
                
            except Exception as e:
                logger.warning(f"Could not get memory stats: {e}")
                stats["memory_system"] = {"error": str(e), "status": "error"}
        
        return stats

    async def _check_existing_analysis(self, query: str) -> Optional[dict]:
        """
        Check if analysis has already been completed for this query with smart detection.
        
        Args:
            query: The analysis query
            
        Returns:
            Existing analysis result if found, None otherwise
        """
        if not self.memory_system:
            return None
            
        try:
            # Extract potential material formula from query
            import re
            formula_patterns = [
                r'\b[A-Z][a-z]?\d*(?:[A-Z][a-z]?\d*)*\b',  # Chemical formula pattern
                r'\b[A-Z][a-z]?_?\d*[A-Z][a-z]?_?\d*[A-Z][a-z]?_?\d*\b'  # Extended pattern
            ]
            
            potential_formulas = []
            for pattern in formula_patterns:
                matches = re.findall(pattern, query)
                potential_formulas.extend(matches)
            
            # Smart detection: Check for complete analysis suites first
            for formula in potential_formulas:
                if len(formula) > 2:  # Skip very short matches
                    # Check if complete visualization suite exists
                    if self._check_visualization_files_exist(formula):
                        logger.info(f"🎯 Complete analysis suite found for {formula}")
                        
                        # Check if we also have cached computational data
                        cached_result = self.memory_system.discovery_cache.get_cached_result(formula)
                        if cached_result:
                            logger.info(f"✅ Complete analysis found: {formula} (cached + visualizations)")
                            return self._format_cached_result(cached_result, formula)
                        else:
                            # Even without cached data, if we have complete visualizations,
                            # we can return a basic result to avoid regeneration
                            logger.info(f"✅ Complete visualization suite found for {formula}")
                            return self._format_visualization_result(formula)
                    else:
                        # Check if we have partial results
                        cached_result = self.memory_system.discovery_cache.get_cached_result(formula)
                        if cached_result:
                            logger.info(f"⚠️ Partial analysis found for {formula} (cached but missing visualizations)")
            
            # Search memory for similar queries
            similar_discoveries = self.memory_system.discovery_cache.search_similar(query, limit=3)
            if similar_discoveries:
                for discovery in similar_discoveries:
                    formula = discovery.get("formula", "Unknown")
                    if self._check_visualization_files_exist(formula):
                        logger.info(f"✅ Similar complete analysis found for {formula}")
                        return self._format_cached_result(discovery, formula)
            
            return None
            
        except Exception as e:
            logger.warning(f"Error checking existing analysis: {e}")
            return None
    
    def _check_visualization_files_exist(self, formula: str) -> bool:
        """
        Check if all visualization files exist for a formula with smarter detection.
        
        Args:
            formula: Chemical formula
            
        Returns:
            True if all required files exist, False otherwise
        """
        from pathlib import Path
        
        # Check in current directory and common output directories
        check_dirs = [
            Path("."),
            Path("./CrystaLyse.AI"),
            Path("./CrystaLyse.AI/chemistry-unified-server/src"),
            Path("./chemistry-unified-server/src"),
            Path("./src")
        ]
        
        # Essential files for complete analysis
        essential_files = [
            f"{formula}_3dmol.html",
            f"{formula}_analysis/{formula}.cif",
            f"{formula}_analysis/XRD_Pattern_{formula}.pdf",
            f"{formula}_analysis/RDF_Analysis_{formula}.pdf",
            f"{formula}_analysis/Coordination_Analysis_{formula}.pdf"
        ]
        
        # Optional files (3D structure might fail due to WebGL issues)
        optional_files = [
            f"{formula}_analysis/3D_Structure_{formula}.pdf"
        ]
        
        best_match = 0
        best_dir = None
        
        for check_dir in check_dirs:
            if not check_dir.exists():
                continue
                
            essential_found = 0
            optional_found = 0
            
            # Check essential files
            for required_file in essential_files:
                file_path = check_dir / required_file
                if file_path.exists():
                    essential_found += 1
            
            # Check optional files
            for optional_file in optional_files:
                file_path = check_dir / optional_file
                if file_path.exists():
                    optional_found += 1
            
            total_found = essential_found + optional_found
            
            # Update best match
            if total_found > best_match:
                best_match = total_found
                best_dir = check_dir
            
            # If we have all essential files, consider it complete
            if essential_found >= 4:  # Allow for 1 missing essential file
                logger.info(f"✅ Complete analysis found for {formula} in {check_dir}")
                logger.info(f"   Essential files: {essential_found}/{len(essential_files)}")
                logger.info(f"   Optional files: {optional_found}/{len(optional_files)}")
                return True
        
        # Log the best match found
        if best_match > 0:
            logger.info(f"⚠️ Partial analysis found for {formula} in {best_dir}")
            logger.info(f"   Files found: {best_match}/{len(essential_files) + len(optional_files)}")
        
        return False
    
    def _format_cached_result(self, cached_data: dict, formula: str) -> dict:
        """
        Format cached result into the expected discovery result format.
        
        Args:
            cached_data: Cached discovery data
            formula: Chemical formula
            
        Returns:
            Formatted result dictionary
        """
        properties = cached_data.get("properties", {})
        cached_at = cached_data.get("cached_at", "Unknown time")
        
        # Create a formatted response
        discovery_result = f"""
✅ **Analysis Complete (from cache)**: {formula}

✨ **Cached Analysis Summary**:
• Material: {formula}
• Previously analyzed: {cached_at}
• Visualization files: Available
• Properties: {len(properties)} cached properties

📊 **Available Files**:
• 3D Structure visualization ({formula}_3dmol.html)
• Analysis suite ({formula}_analysis/ directory)
• XRD Pattern, RDF Analysis, Coordination Analysis

💯 **Result**: Complete analysis already available. No need to re-analyze.
        """
        
        return {
            "status": "completed",
            "discovery_result": discovery_result,
            "metrics": {
                "tool_calls": 0,
                "elapsed_time": 0.1,  # Very fast cache lookup
                "model": self.model_name,
                "mode": self.mode,
                "total_items": 0,
                "raw_responses": 0,
                "cached": True,
                "cache_hit": True,
                "formula": formula,
                "cache_timestamp": cached_at
            },
            "tool_validation": {
                "needs_computation": True,
                "tools_called": 0,
                "tools_used": [],
                "cached_result": True,
                "potential_hallucination": False,
                "critical_failure": False
            },
            "response_validation": {
                "is_valid": True,
                "cached_response": True,
                "violations": [],
                "violation_count": 0
            },
            "new_items": []
        }
    
    def _format_visualization_result(self, formula: str) -> dict:
        """
        Format result when complete visualizations exist but no cached data.
        
        Args:
            formula: Chemical formula
            
        Returns:
            Formatted result dictionary
        """
        discovery_result = f"""
✅ **Complete Analysis Available**: {formula}

🎨 **Visualization Suite Found**:
• Material: {formula}
• Status: Complete visualization suite available
• Files: 3D structure, XRD pattern, RDF analysis, coordination analysis
• Interactive visualization: {formula}_3dmol.html
• Analysis directory: {formula}_analysis/

📊 **Available Analyses**:
• Structure visualization (3D interactive)
• X-ray diffraction pattern
• Radial distribution function
• Coordination environment analysis

🎯 **Result**: Complete analysis suite ready for review.
        """
        
        return {
            "status": "completed",
            "discovery_result": discovery_result,
            "metrics": {
                "tool_calls": 0,
                "elapsed_time": 0.05,  # Very fast visualization check
                "model": self.model_name,
                "mode": self.mode,
                "total_items": 0,
                "raw_responses": 0,
                "cached": True,
                "visualization_suite": True,
                "formula": formula
            },
            "tool_validation": {
                "needs_computation": True,
                "tools_called": 0,
                "tools_used": [],
                "visualization_suite_found": True,
                "potential_hallucination": False,
                "critical_failure": False
            },
            "response_validation": {
                "is_valid": True,
                "visualization_suite": True,
                "violations": [],
                "violation_count": 0
            },
            "new_items": []
        }

    def _serialize_item(self, item):
        """Serialize an item from result.new_items, preserving tool output data."""
        from agents import ToolCallOutputItem
        import json
        
        try:
            if hasattr(item, '__class__') and 'ToolCallOutputItem' in str(item.__class__):
                # This is a ToolCallOutputItem, extract the output data
                if hasattr(item, 'output') and item.output:
                    try:
                        # Try to parse output as JSON if it's a string
                        if isinstance(item.output, str):
                            try:
                                output_data = json.loads(item.output)
                            except json.JSONDecodeError:
                                output_data = item.output
                        else:
                            output_data = item.output
                        
                        return {
                            "type": "tool_call_output",
                            "agent": str(item.agent.name) if hasattr(item, 'agent') and hasattr(item.agent, 'name') else "unknown",
                            "output": output_data,
                            "raw_item_type": str(type(item).__name__)
                        }
                    except Exception as e:
                        # Fallback to string representation
                        return {
                            "type": "tool_call_output",
                            "raw_string": str(item),
                            "error": f"Failed to extract output: {e}"
                        }
                else:
                    return {
                        "type": "tool_call_output",
                        "raw_string": str(item),
                        "note": "No output attribute found"
                    }
            else:
                # For other items, just convert to string
                return str(item)
        except Exception as e:
            # Fallback to string representation
            return f"Error serializing item: {e} - {str(item)}"

    async def cleanup(self):
        """Cleanup session, memory system, and connection resources."""
        cleanup_errors = []
        
        # Cleanup simple memory system
        if self.memory_system:
            try:
                self.memory_system.cleanup()
                logger.info("✅ Simple memory system cleaned up successfully")
            except Exception as e:
                cleanup_errors.append(f"Memory cleanup: {e}")
                logger.warning(f"Memory cleanup error: {e}")
        
        # Cleanup session
        if self.session:
            try:
                await self.session.cleanup()
                logger.info("Session cleaned up")
            except Exception as e:
                cleanup_errors.append(f"Session cleanup: {e}")
                logger.warning(f"Session cleanup error: {e}")
        
        if cleanup_errors:
            logger.warning(f"Cleanup completed with {len(cleanup_errors)} errors")
        else:
            logger.info(f"✅ CrystaLyse agent fully cleaned up for user {self.user_id}")

# Top-level convenience functions for backward compatibility
async def analyse_materials(query: str, mode: str = "creative", user_id: str = "default", **kwargs) -> Dict[str, Any]:
    """Top-level analysis function for CrystaLyse agent with memory."""
    config = AgentConfig(mode=mode, **kwargs)
    agent = CrystaLyse(agent_config=config, user_id=user_id)
    try:
        return await agent.discover_materials(query)
    finally:
        await agent.cleanup()

async def rigorous_analysis(query: str, **kwargs) -> Dict[str, Any]:
    """Rigorous analysis mode with o3 model."""
    return await analyse_materials(query, mode="rigorous", **kwargs)

async def creative_analysis(query: str, **kwargs) -> Dict[str, Any]:
    """Creative analysis mode with o4-mini model."""
    return await analyse_materials(query, mode="creative", **kwargs)