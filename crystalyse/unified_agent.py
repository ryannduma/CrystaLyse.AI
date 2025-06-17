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

from .config import config

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

class CrystaLyseUnifiedAgent:
    """
    Unified agent using OpenAI Agents SDK.
    
    This consolidates all functionality into a single, truly agentic implementation.
    """
    
    instructions = (
        "You are CrystaLyse.AI, a world-class materials science research agent. "
        "Your purpose is to accelerate the discovery of new crystalline materials using a suite of computational tools. "
        "You have access to three powerful toolsets, accessible via a unified MCP (Materials Computation Platform):\n"
        "1. `smact_tools`: For generating and validating novel chemical compositions using chemical principles.\n"
        "2. `chemeleon_tools`: For performing crystal structure prediction (CSP) to find stable structures for a given composition.\n"
        "3. `mace_tools`: For running high-accuracy, machine-learning-based potential calculations to determine material properties like energy and forces.\n\n"
        "**Your Operational Workflow: Clarify, Plan, Execute**\n\n"
        "1.  **Analyze and Clarify:** First, critically assess the user's request. If it is broad, ambiguous, or lacks specific constraints (e.g., 'find a new battery material'), your primary and immediate action MUST be to use the `ask_clarifying_questions` tool. Do not guess or proceed with a flawed premise. Wait for the user to provide the necessary details.\n\n"
        "2.  **Formulate a Plan:** Once the query is specific and actionable (e.g., 'find a sodium-ion conductor with high stability and a band gap over 2 eV'), formulate a multi-step plan. Announce this plan to the user clearly. For example: 'Plan: First, I will use `smact_tools.generate_compositions` to find candidate materials. Second, I will predict their structures with `chemeleon_tools.predict_structure`. Finally, I will validate their stability using `mace_tools.calculate_energy`.'\n\n"
        "3.  **Execute Autonomously:** After stating your plan, **immediately execute the first step** by calling the appropriate tool. Do not ask for permission or wait for confirmation. Continue executing the plan, step-by-step, analyzing the output of each tool call to inform the next, until you have a final answer or encounter a definitive failure.\n\n"
        "Your goal is to be a proactive, autonomous research partner. Never ask a question if you can find the answer with a tool. Clarify ambiguity, then plan and execute with relentless forward momentum."
    )

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

    async def discover_materials(self, query: str, session: Optional[Agent] = None, trace_workflow: bool = True) -> dict:
        """
        Asynchronously discovers materials based on a query, managing MCP server lifecycles.
        """
        if session:
            self.agent = session
        
        self.metrics["start_time"] = time.time()
        
        try:
            async with AsyncExitStack() as stack:
                mcp_servers = []
                extra_tools = [assess_progress, explore_alternatives, ask_clarifying_questions]

                if self.agent_config.enable_smact:
                    smact_config = self.system_config.get_server_config("smact")
                    smact_server = await stack.enter_async_context(
                        MCPServerStdio(
                            name="SMACT",
                            params={
                                "command": smact_config["command"],
                                "args": smact_config["args"],
                                "cwd": smact_config["cwd"],
                                "env": smact_config.get("env", {})
                            }
                        )
                    )
                    mcp_servers.append(smact_server)

                if self.agent_config.enable_chemeleon:
                    chemeleon_config = self.system_config.get_server_config("chemeleon")
                    chemeleon_server = await stack.enter_async_context(
                        MCPServerStdio(
                            name="Chemeleon",
                            params={
                                "command": chemeleon_config["command"],
                                "args": chemeleon_config["args"],
                                "cwd": chemeleon_config["cwd"],
                                "env": chemeleon_config.get("env", {})
                            }
                        )
                    )
                    mcp_servers.append(chemeleon_server)

                if self.agent_config.enable_mace:
                    mace_config = self.system_config.get_server_config("mace")
                    mace_server = await stack.enter_async_context(
                        MCPServerStdio(
                            name="MACE",
                            params={
                                "command": mace_config["command"],
                                "args": mace_config["args"],
                                "cwd": mace_config["cwd"],
                                "env": mace_config.get("env", {})
                            }
                        )
                    )
                    mcp_servers.append(mace_server)

                logger.info(f"Initialised agent with {len(mcp_servers)} MCP servers in {self.mode} mode.")

                if not self.agent:
                    # Create model settings with temperature (only if temperature is not None)
                    from agents.model_settings import ModelSettings
                    model_settings = ModelSettings()
                    if self.temperature is not None:
                        model_settings = ModelSettings(temperature=self.temperature)
                    
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
                    input=query, 
                    max_turns=self.max_turns,
                    run_config=run_config
                )
                
                # Simplified result preparation
                elapsed_time = time.time() - self.metrics["start_time"]
                
                # Extract final output
                final_content = str(result.final_output) if result.final_output else "No discovery result found."
                
                # Count tool calls from new_items
                tool_call_count = sum(1 for item in result.new_items if hasattr(item, 'tool_calls') and item.tool_calls)

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

async def analyse_materials(query: str, mode: str = "creative", **kwargs) -> Dict[str, Any]:
    """Top-level analysis function for unified agent."""
    config = AgentConfig(mode=mode, **kwargs)
    agent = CrystaLyseUnifiedAgent(agent_config=config)
    return await agent.discover_materials(query)


async def rigorous_analysis(query: str, **kwargs) -> Dict[str, Any]:
    """Rigorous analysis mode with lower temperature."""
    return await analyse_materials(query, mode="rigorous", temperature=0.3, **kwargs)


async def creative_analysis(query: str, **kwargs) -> Dict[str, Any]:
    """Creative analysis mode with higher temperature."""
    return await analyse_materials(query, mode="creative", temperature=0.8, **kwargs)