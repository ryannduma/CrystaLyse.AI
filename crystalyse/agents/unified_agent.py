"""
Unified CrystaLyse Agent - Uses OpenAI Agents SDK with o4-mini model.
This replaces the 5 redundant agent classes with one truly agentic implementation.
"""

import asyncio
import logging
from typing import List, Dict, Any, Literal, Optional
from dataclasses import dataclass
from pathlib import Path
import json
import time
from contextlib import AsyncExitStack

# Use OpenAI Agents SDK instead of Anthropic
from agents import Agent, Runner, function_tool, gen_trace_id, trace
from agents.mcp import MCPServer, MCPServerStdio
from pydantic import BaseModel

from ..config import config
from ..validation import validate_computational_response, ValidationViolation

logger = logging.getLogger(__name__)

@dataclass
class AgentConfig:
    """Configuration for the unified agent"""
    mode: Literal["creative", "rigorous"] = "rigorous"
    model: str = None  # Will be auto-selected based on mode
    temperature: float = 0.7
    max_turns: int = 15
    enable_mace: bool = True
    enable_chemeleon: bool = True
    enable_smact: bool = True
    parallel_batch_size: int = 10
    max_candidates: int = 100
    structure_samples: int = 5
    enable_metrics: bool = True
    
    def __post_init__(self):
        """Auto-select model based on mode if not specified"""
        if self.model is None:
            if self.mode == "rigorous":
                self.model = "o3"  # Use o3 for rigorous mode with MDG API key
                # o3 doesn't support temperature parameter
                self.temperature = None
            else:
                self.model = "o4-mini"  # Use o4-mini for creative mode
                # o4-mini doesn't support temperature parameter
                self.temperature = None

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

# Pydantic model for the clarification question structure
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
    # In a real interactive session, this would present the questions to the user
    # and wait for their input. For this simulation, we will just print them.
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
    Unified agent using OpenAI Agents SDK.
    
    This consolidates all functionality into a single, truly agentic implementation.
    """

    def __init__(self, agent_config: AgentConfig = None, system_config=None):
        self.agent_config = agent_config or AgentConfig()
        # Use the global config if a specific one isn't provided
        self.system_config = system_config or config
        self.metrics = {"tool_calls": 0, "start_time": None, "errors": []}
        
        self.temperature = self.agent_config.temperature
        self.mode = self.agent_config.mode  # Use the mode from config directly
        self.model_name = self.agent_config.model
        self.max_turns = self.agent_config.max_turns
        self.agent = None
        self.instructions = self._load_system_prompt()
        
        # Initialize query classifier for tool enforcement
        self.query_classifier = ComputationalQueryClassifier()
        
    def _load_system_prompt(self) -> str:
        """Load and process the system prompt from markdown file."""
        # Get the path to the prompt file
        prompt_path = Path(__file__).parent.parent / "prompts" / "unified_agent_prompt.md"
        
        # Read the prompt
        with open(prompt_path, 'r', encoding='utf-8') as f:
            prompt = f.read()
        
        # Add mode-specific additions
        mode_additions = {
            "rigorous": "\n\nCrystaLyse is currently operating in Rigorous Mode. Every composition must be validated, every structure must have calculated energies, and all results must include uncertainty estimates.",
            "creative": "\n\nCrystaLyse is currently operating in Creative Mode. Explore boldly, validate the most promising candidates, and encourage novel thinking."
        }
        
        if self.mode in mode_additions:
            prompt += mode_additions[self.mode]
            
        return prompt

    async def discover_materials(self, query: str, session: Optional[Agent] = None, trace_workflow: bool = True) -> dict:
        """
        Asynchronously discovers materials based on a query, managing MCP server lifecycles.
        """
        if session:
            self.agent = session
        
        self.metrics["start_time"] = time.time()
        
        # Classify query to determine tool enforcement level
        requires_computation = self.query_classifier.requires_computation(query)
        tool_choice = self.query_classifier.get_enforcement_level(query)
        
        logger.info(f"Query classification: requires_computation={requires_computation}, tool_choice={tool_choice}")
        
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
            async with AsyncExitStack() as stack:
                mcp_servers = []
                extra_tools = [assess_progress, explore_alternatives, ask_clarifying_questions]

                # Use unified chemistry server that combines all tools
                if (self.agent_config.enable_smact or 
                    self.agent_config.enable_chemeleon or 
                    self.agent_config.enable_mace):
                    
                    chemistry_config = self.system_config.get_server_config("chemistry_unified")
                    chemistry_server = await stack.enter_async_context(
                        MCPServerStdio(
                            name="ChemistryUnified",
                            params={
                                "command": chemistry_config["command"],
                                "args": chemistry_config["args"],
                                "cwd": chemistry_config["cwd"],
                                "env": chemistry_config.get("env", {})
                            },
                            client_session_timeout_seconds=60  # Allow 60s for model downloads
                        )
                    )
                    mcp_servers.append(chemistry_server)

                logger.info(f"Initialised agent with {len(mcp_servers)} MCP servers in {self.mode} mode.")

                if not self.agent:
                    # Create model settings with dynamic tool choice based on query classification
                    from agents.model_settings import ModelSettings
                    model_settings = ModelSettings(tool_choice=tool_choice)
                    if self.temperature is not None:
                        model_settings = ModelSettings(temperature=self.temperature, tool_choice=tool_choice)
                    
                    self.agent = Agent(
                        name="CrystaLyse",
                        model=self.model_name,
                        instructions=self.instructions,
                        tools=extra_tools,
                        mcp_servers=mcp_servers,
                        model_settings=model_settings,
                    )

                # Run the agent with max_turns using MDG API key
                from agents.run import RunConfig
                from agents.models.openai_provider import OpenAIProvider
                import os
                
                # Use MDG API key for better access to o3 and higher rate limits
                mdg_api_key = os.getenv("OPENAI_MDG_API_KEY") or os.getenv("OPENAI_API_KEY")
                model_provider = OpenAIProvider(api_key=mdg_api_key)
                
                run_config = RunConfig(
                    trace_id=gen_trace_id(),
                    model_provider=model_provider
                )
                
                result = await Runner.run(
                    starting_agent=self.agent, 
                    input=enhanced_query, 
                    max_turns=self.max_turns,
                    run_config=run_config
                )
                
                # Simplified result preparation
                elapsed_time = time.time() - self.metrics["start_time"]
                
                # Extract final output
                final_content = str(result.final_output) if result.final_output else "No discovery result found."
                
                # Extract tool calls from result
                tool_calls = []
                for item in result.new_items:
                    if hasattr(item, 'tool_calls') and item.tool_calls:
                        tool_calls.extend(item.tool_calls)
                
                tool_call_count = len(tool_calls)
                
                # Validate tool usage to detect potential hallucination
                tool_validation = self._validate_tool_usage(result, query, requires_computation)

                # Advanced response validation
                response_validation = self._validate_response_integrity(
                    query, final_content, tool_calls, requires_computation
                )
                
                # Use sanitized response if validation failed
                if not response_validation["is_valid"]:
                    final_content = response_validation["sanitized_response"]
                    logger.error(f"Response validation failed: {response_validation['violations']}")

                return {
                    "status": "completed",
                    "discovery_result": final_content,
                    "metrics": {
                        "tool_calls": tool_call_count,
                        "elapsed_time": elapsed_time,
                        "model": self.model_name,
                        "mode": self.mode,
                        "total_items": len(result.new_items),
                        "raw_responses": len(result.raw_responses)
                    },
                    "tool_validation": tool_validation,
                    "response_validation": response_validation,
                    "new_items": [str(item) for item in result.new_items[:5]],  # Sample of items
                }

        except Exception as e:
            logger.error(f"An error occurred during material discovery: {e}", exc_info=True)
            self.metrics["errors"].append(str(e))
            elapsed_time = time.time() - self.metrics["start_time"]
            return {
                "status": "failed",
                "error": str(e),
                "metrics": {
                    "elapsed_time": elapsed_time,
                    "model": self.model_name,
                },
            }
    
    def _validate_tool_usage(self, result, query: str, requires_computation: bool = None) -> Dict[str, Any]:
        """Validate that computational tools were actually used when expected."""
        tool_calls = getattr(result, 'tool_calls', []) or []
        
        # Use the classifier result if provided, otherwise fallback to keyword check
        if requires_computation is None:
            needs_computation = self.query_classifier.requires_computation(query)
        else:
            needs_computation = requires_computation
        
        # Extract tool names from actual calls
        tools_used = []
        for call in tool_calls:
            if hasattr(call, 'function') and hasattr(call.function, 'name'):
                tools_used.append(call.function.name)
        
        # Check for computational results in response without tool calls
        response = str(result.final_output) if result.final_output else ""
        
        # Patterns that indicate computational results were reported
        import re
        computational_result_patterns = [
            r'formation energy:.*-?\d+\.\d+\s*ev',
            r'validation.*valid.*confidence.*\d+',
            r'smact.*valid',
            r'space group:.*[a-z0-9/-]+',
            r'crystal system:.*[a-z]+',
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
            "tools_called": len(tool_calls),
            "tools_used": tools_used,
            "smact_used": any('smact' in tool.lower() for tool in tools_used),
            "chemeleon_used": any('chemeleon' in tool.lower() for tool in tools_used),
            "mace_used": any('mace' in tool.lower() for tool in tools_used),
            "contains_computational_results": contains_computational_results,
            "potential_hallucination": needs_computation and len(tool_calls) == 0 and contains_computational_results,
            "critical_failure": needs_computation and len(tool_calls) == 0 and contains_computational_results
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

async def analyse_materials(query: str, mode: str = "creative", **kwargs) -> Dict[str, Any]:
    """Top-level analysis function for unified agent."""
    config = AgentConfig(mode=mode, **kwargs)
    agent = CrystaLyse(agent_config=config)
    return await agent.discover_materials(query)


async def rigorous_analysis(query: str, **kwargs) -> Dict[str, Any]:
    """Rigorous analysis mode with lower temperature."""
    return await analyse_materials(query, mode="rigorous", temperature=0.3, **kwargs)


async def creative_analysis(query: str, **kwargs) -> Dict[str, Any]:
    """Creative analysis mode with higher temperature."""
    return await analyse_materials(query, mode="creative", temperature=0.8, **kwargs)