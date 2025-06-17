"""
Three-stage pipeline implementation following Agent Laboratory patterns.
Each stage has a dedicated micro-agent with clear handoffs and compact JSON summaries.
"""

import asyncio
import json
import time
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
from contextlib import AsyncExitStack

from agents import Agent, Runner, function_tool
from agents.mcp import MCPServer, MCPServerStdio
from pydantic import BaseModel

from ..config import config
from ..monitoring.metrics import MetricsCollector


@dataclass
class StageResult:
    """Compact JSON summary passed between pipeline stages"""
    stage: str
    success: bool
    data: Dict[str, Any]
    metadata: Dict[str, Any]
    timestamp: float
    cost_estimate: float = 0.0
    tokens_used: int = 0


class CompositionStage:
    """Stage 1: Composition validation using SMACT"""
    
    def __init__(self, metrics: MetricsCollector):
        self.metrics = metrics
        self.stage_name = "composition"
        
    async def execute(self, query: str, requirements: Dict[str, Any]) -> StageResult:
        """Execute composition validation stage"""
        start_time = time.time()
        
        # Create dedicated micro-agent for composition
        instructions = (
            "You are CompositionBot, a PhD-level materials scientist specializing in "
            "chemical composition validation. Your ONLY job is to:\n"
            "1. Parse the user query for elemental requirements\n"
            "2. Use SMACT tools to generate and validate compositions\n"
            "3. Return a compact JSON summary with valid compositions\n"
            "4. NEVER proceed to structure prediction - that's the next stage\n\n"
            "Always call `smact_validity` before approving any composition."
        )
        
        async with AsyncExitStack() as stack:
            # Connect SMACT server
            smact_server = await stack.enter_async_context(
                MCPServerStdio(
                    name="SMACT Server",
                    params={
                        "command": "python",
                        "args": ["-m", "smact_mcp.server"],
                        "cwd": config.mcp_servers["smact"]["cwd"]
                    }
                )
            )
            
            agent = Agent(
                name="CompositionBot",
                instructions=instructions,
                model="o4-mini",
                mcp_servers=[smact_server],
                tools=[self._composition_checkpoint_tool()],
                max_turns=10
            )
            
            result = await Runner.run(starting_agent=agent, input=query)
            
            # Extract validated compositions from result
            compositions = self._extract_compositions(result)
            
            return StageResult(
                stage=self.stage_name,
                success=len(compositions) > 0,
                data={"compositions": compositions, "query": query},
                metadata={"agent": "CompositionBot", "tools_used": ["smact_validity"]},
                timestamp=time.time(),
                cost_estimate=self._estimate_cost(result),
                tokens_used=self._count_tokens(result)
            )
    
    def _composition_checkpoint_tool(self):
        """Tool for composition stage to submit results"""
        @function_tool
        def submit_compositions(compositions: List[Dict[str, Any]], reasoning: str) -> str:
            """Submit validated compositions to move to next stage"""
            return f"Compositions submitted: {len(compositions)} valid candidates. Reasoning: {reasoning}"
        return submit_compositions
    
    def _extract_compositions(self, result) -> List[Dict[str, Any]]:
        """Extract composition data from agent result"""
        # Implementation would parse agent output for composition data
        return []  # Placeholder
    
    def _estimate_cost(self, result) -> float:
        """Estimate cost of this stage"""
        return 0.05  # Placeholder - would calculate based on tokens/API calls
    
    def _count_tokens(self, result) -> int:
        """Count tokens used in this stage"""
        return 1000  # Placeholder


class StructureStage:
    """Stage 2: Crystal structure prediction using Chemeleon"""
    
    def __init__(self, metrics: MetricsCollector):
        self.metrics = metrics
        self.stage_name = "structure"
        
    async def execute(self, composition_result: StageResult) -> StageResult:
        """Execute structure prediction stage"""
        
        instructions = (
            "You are StructureBot, a Postdoc-level crystallographer. Your job is to:\n"
            "1. Take validated compositions from the previous stage\n"
            "2. Use Chemeleon tools to predict crystal structures\n"
            "3. Generate 3-5 diverse polymorphs per composition\n"
            "4. Return compact JSON with structure files and metadata\n"
            "5. NEVER proceed to energy calculations - that's the next stage\n\n"
            "Focus on structural diversity and known prototype matching."
        )
        
        async with AsyncExitStack() as stack:
            chemeleon_server = await stack.enter_async_context(
                MCPServerStdio(
                    name="Chemeleon Server",
                    params={
                        "command": "python",
                        "args": ["-m", "chemeleon_mcp.server"],
                        "cwd": config.mcp_servers["chemeleon"]["cwd"]
                    }
                )
            )
            
            agent = Agent(
                name="StructureBot",
                instructions=instructions,
                model="o4-mini",
                mcp_servers=[chemeleon_server],
                tools=[self._structure_checkpoint_tool()],
                max_turns=15
            )
            
            # Pass composition data as input
            input_data = f"Predict structures for compositions: {composition_result.data['compositions']}"
            result = await Runner.run(starting_agent=agent, input=input_data)
            
            structures = self._extract_structures(result)
            
            return StageResult(
                stage=self.stage_name,
                success=len(structures) > 0,
                data={"structures": structures, "parent_compositions": composition_result.data["compositions"]},
                metadata={"agent": "StructureBot", "tools_used": ["chemeleon_predict"]},
                timestamp=time.time(),
                cost_estimate=self._estimate_cost(result),
                tokens_used=self._count_tokens(result)
            )
    
    def _structure_checkpoint_tool(self):
        """Tool for structure stage to submit results"""
        @function_tool
        def submit_structures(structures: List[Dict[str, Any]], reasoning: str) -> str:
            """Submit predicted structures to move to next stage"""
            return f"Structures submitted: {len(structures)} candidates. Reasoning: {reasoning}"
        return submit_structures
    
    def _extract_structures(self, result) -> List[Dict[str, Any]]:
        """Extract structure data from agent result"""
        return []  # Placeholder
    
    def _estimate_cost(self, result) -> float:
        return 0.15  # Chemeleon is more expensive
    
    def _count_tokens(self, result) -> int:
        return 2500  # Larger context for structure prediction


class EnergyStage:
    """Stage 3: Energy calculations and final report using MACE"""
    
    def __init__(self, metrics: MetricsCollector):
        self.metrics = metrics
        self.stage_name = "energy"
        
    async def execute(self, structure_result: StageResult) -> StageResult:
        """Execute energy calculation and reporting stage"""
        
        instructions = (
            "You are ProfessorBot, a Professor-level computational materials scientist. "
            "Your job is to:\n"
            "1. Take predicted structures from the previous stage\n"
            "2. Use MACE tools to calculate formation energies and stability\n"
            "3. Rank materials by stability and target properties\n"
            "4. Generate a comprehensive final report with recommendations\n"
            "5. Include uncertainty estimates and experimental suggestions\n\n"
            "You are the final authority - make definitive recommendations."
        )
        
        async with AsyncExitStack() as stack:
            mace_server = await stack.enter_async_context(
                MCPServerStdio(
                    name="MACE Server",
                    params={
                        "command": "python",
                        "args": ["-m", "mace_mcp.server"],
                        "cwd": config.mcp_servers["mace"]["cwd"]
                    }
                )
            )
            
            agent = Agent(
                name="ProfessorBot",
                instructions=instructions,
                model="o4-mini",
                mcp_servers=[mace_server],
                tools=[self._report_checkpoint_tool()],
                max_turns=20
            )
            
            # Pass structure data as input
            input_data = f"Calculate energies and generate report for: {structure_result.data['structures']}"
            result = await Runner.run(starting_agent=agent, input=input_data)
            
            report = self._generate_final_report(result, structure_result)
            
            return StageResult(
                stage=self.stage_name,
                success=True,
                data={"final_report": report, "energy_calculations": []},
                metadata={"agent": "ProfessorBot", "tools_used": ["mace_calculate"]},
                timestamp=time.time(),
                cost_estimate=self._estimate_cost(result),
                tokens_used=self._count_tokens(result)
            )
    
    def _report_checkpoint_tool(self):
        """Tool for energy stage to submit final report"""
        @function_tool
        def submit_final_report(recommendations: List[Dict[str, Any]], confidence: float, reasoning: str) -> str:
            """Submit final materials recommendations"""
            return f"Final report submitted: {len(recommendations)} recommendations, confidence: {confidence:.2f}"
        return submit_final_report
    
    def _generate_final_report(self, result, structure_result) -> Dict[str, Any]:
        """Generate comprehensive final report"""
        return {
            "summary": "Materials discovery complete",
            "recommendations": [],
            "methodology": "Three-stage pipeline: Composition → Structure → Energy",
            "confidence": 0.85
        }
    
    def _estimate_cost(self, result) -> float:
        return 0.25  # MACE calculations are most expensive
    
    def _count_tokens(self, result) -> int:
        return 3500  # Largest context for final report


class ThreeStageRunner:
    """Orchestrates the three-stage pipeline"""
    
    def __init__(self, metrics: MetricsCollector = None):
        self.metrics = metrics or MetricsCollector()
        self.composition_stage = CompositionStage(self.metrics)
        self.structure_stage = StructureStage(self.metrics)
        self.energy_stage = EnergyStage(self.metrics)
        
    async def run_pipeline(self, query: str, requirements: Dict[str, Any] = None) -> Dict[str, Any]:
        """Run the complete three-stage pipeline"""
        
        self.metrics.start_workflow(query, "three_stage_pipeline")
        
        try:
            # Stage 1: Composition
            composition_result = await self.composition_stage.execute(query, requirements or {})
            if not composition_result.success:
                return {"error": "Composition stage failed", "stage": "composition"}
            
            # Stage 2: Structure
            structure_result = await self.structure_stage.execute(composition_result)
            if not structure_result.success:
                return {"error": "Structure stage failed", "stage": "structure"}
            
            # Stage 3: Energy & Report
            final_result = await self.energy_stage.execute(structure_result)
            
            # Compile final output
            pipeline_result = {
                "success": final_result.success,
                "stages": {
                    "composition": asdict(composition_result),
                    "structure": asdict(structure_result),
                    "energy": asdict(final_result)
                },
                "total_cost": (composition_result.cost_estimate + 
                              structure_result.cost_estimate + 
                              final_result.cost_estimate),
                "total_tokens": (composition_result.tokens_used + 
                               structure_result.tokens_used + 
                               final_result.tokens_used),
                "final_report": final_result.data["final_report"]
            }
            
            return pipeline_result
            
        finally:
            self.metrics.end_workflow() 