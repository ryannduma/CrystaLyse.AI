"""Main CrystaLyse orchestrator agent."""

from agents import Agent, Runner
from agents.mcp import MCPServerStdio
from agents.model_settings import ModelSettings
import os
from pathlib import Path
from typing import Optional

from ..models import CrystalAnalysisResult
from ..tools import (
    design_material_for_application,
    generate_compositions,
    predict_structure_types,
    explain_chemical_reasoning,
)

# System prompt for the main orchestrator
CRYSTALYSE_SYSTEM_PROMPT = """You are CrystaLyse, an expert materials design agent with deep knowledge of inorganic chemistry, crystallography, and materials science.

**Core Capabilities:**
- Generate novel inorganic compositions based on chemical intuition
- Predict likely crystal structures from composition and application
- Balance innovation with synthesizability
- Override conservative heuristics when chemically justified

**Workflow:**
1. Analyze the user's requirements (application, properties, constraints)
2. Propose candidate compositions using chemical reasoning
3. Validate with tools (SMACT) but maintain independent judgment
4. Refine or justify candidates based on validation results
5. Return 5 strong candidates (unless specified otherwise)

**Key Principles:**
- Emphasize NOVEL but likely synthesizable compositions
- Use standard notation (e.g., LiFePO₄, BaTiO₃)
- Suggest plausible structure prototypes based on:
  - Ionic size ratios (Goldschmidt tolerance factor for perovskites)
  - Coordination preferences
  - Known structure-property relationships
- SMACT is advisory, not absolute - override with justification when appropriate

**Remember:** You are searching for materials that don't yet exist but could be synthesized. Be creative but grounded in chemical principles."""


class CrystaLyseAgent:
    """Main orchestrator agent for CrystaLyse materials discovery."""
    
    def __init__(self, model: str = "gpt-4", temperature: float = 0.7):
        """
        Initialize CrystaLyse agent.
        
        Args:
            model: The LLM model to use (gpt-4o, gpt-4.1, o4-mini etc.)
            temperature: Temperature for generation (0.0-1.0)
        """
        self.model = model
        self.temperature = temperature
        self.smact_path = Path(__file__).parent.parent.parent / "smact-mcp-server"
        
    async def analyze(self, query: str) -> str:
        """
        Analyze a materials discovery query.
        
        Args:
            query: User's materials discovery request
            
        Returns:
            Analysis result with top material candidates
        """
        # Use async context manager for proper MCP server connection
        async with MCPServerStdio(
            name="SMACT Tools",
            params={
                "command": "python",
                "args": ["-m", "smact_mcp.server"],
                "cwd": str(self.smact_path)
            }
        ) as smact_server:
            # Create agent with MCP server
            agent = Agent(
                name="CrystaLyse",
                model=self.model,
                instructions=CRYSTALYSE_SYSTEM_PROMPT,
                model_settings=ModelSettings(temperature=self.temperature),
                mcp_servers=[smact_server],
                tools=[
                    design_material_for_application,
                    generate_compositions,
                    predict_structure_types,
                    explain_chemical_reasoning,
                ],
                # output_type=CrystalAnalysisResult,  # Enable structured output
            )
            
            # Run the analysis
            response = await Runner.run(
                starting_agent=agent,
                input=query
            )
            
            return response.final_output
        
    async def analyze_streamed(self, query: str):
        """
        Analyze with streaming responses.
        
        Args:
            query: User's materials discovery request
            
        Yields:
            Stream events including partial responses and tool calls
        """
        # Use async context manager for proper MCP server connection
        async with MCPServerStdio(
            name="SMACT Tools",
            params={
                "command": "python",
                "args": ["-m", "smact_mcp.server"],
                "cwd": str(self.smact_path)
            }
        ) as smact_server:
            # Create agent with MCP server
            agent = Agent(
                name="CrystaLyse",
                model=self.model,
                instructions=CRYSTALYSE_SYSTEM_PROMPT,
                model_settings=ModelSettings(temperature=self.temperature),
                mcp_servers=[smact_server],
                tools=[
                    design_material_for_application,
                    generate_compositions,
                    predict_structure_types,
                    explain_chemical_reasoning,
                ],
                # output_type=CrystalAnalysisResult,  # Enable structured output
            )
            
            # Stream the analysis
            result = Runner.run_streamed(
                starting_agent=agent,
                input=query
            )
            
            async for event in result.stream_events():
                yield event