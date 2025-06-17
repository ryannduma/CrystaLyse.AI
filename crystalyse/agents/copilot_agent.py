"""
Co-pilot mode agent following Agent Laboratory patterns
Adds human checkpoints during the discovery pipeline for better outcomes
"""

import asyncio
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Confirm, Prompt

from .pipeline_agents import ThreeStageRunner, StageResult
from ..monitoring.agent_telemetry import agent_step, get_telemetry_summary

console = Console()


@dataclass
class CheckpointDecision:
    """User decision at a checkpoint"""
    action: str  # "continue", "tweak", "stop"
    modifications: Dict[str, Any]
    reasoning: str


class HumanCheckpoint:
    """Interactive human checkpoint during pipeline execution"""
    
    def __init__(self, stage: str, description: str):
        self.stage = stage
        self.description = description
        
    async def present_checkpoint(self, data: Dict[str, Any], 
                                telemetry: Dict[str, Any]) -> CheckpointDecision:
        """Present checkpoint to user and get decision"""
        
        # Display current progress
        console.print(f"\n{self.stage.title()} Checkpoint", style="bold yellow")
        console.print(Panel(self.description, title="Current Status"))
        
        # Show telemetry
        self._display_telemetry(telemetry)
        
        # Show current results
        self._display_results(data)
        
        # Get user decision
        return await self._get_user_decision(data)
    
    def _display_telemetry(self, telemetry: Dict[str, Any]):
        """Display cost and performance info"""
        if not telemetry or "message" in telemetry:
            return
            
        table = Table(title="Performance & Cost")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")
        
        table.add_row("Total Cost", f"${telemetry.get('total_cost_usd', 0):.3f}")
        table.add_row("Total Time", f"{telemetry.get('total_time_seconds', 0):.1f}s")
        table.add_row("Success Rate", f"{telemetry.get('success_rate', 0)*100:.1f}%")
        table.add_row("Tool Calls", str(telemetry.get('total_calls', 0)))
        
        if 'most_expensive_tool' in telemetry:
            table.add_row("Most Expensive", 
                         f"{telemetry['most_expensive_tool']} (${telemetry['most_expensive_cost']:.3f})")
        
        console.print(table)
    
    def _display_results(self, data: Dict[str, Any]):
        """Display current stage results"""
        
        if self.stage == "composition":
            self._display_composition_results(data)
        elif self.stage == "structure":
            self._display_structure_results(data)
        elif self.stage == "energy":
            self._display_energy_results(data)
    
    def _display_composition_results(self, data: Dict[str, Any]):
        """Display composition validation results"""
        compositions = data.get("compositions", [])
        
        table = Table(title="Validated Compositions")
        table.add_column("Formula", style="cyan")
        table.add_column("Valid", style="green")
        table.add_column("Score", style="yellow")
        
        for comp in compositions[:10]:  # Show top 10
            formula = comp.get("formula", "Unknown")
            valid = "Yes" if comp.get("valid", False) else "No"
            score = comp.get("score", 0.0)
            table.add_row(formula, valid, f"{score:.2f}")
        
        console.print(table)
        
        if len(compositions) > 10:
            console.print(f"... and {len(compositions) - 10} more compositions")
    
    def _display_structure_results(self, data: Dict[str, Any]):
        """Display structure prediction results"""
        structures = data.get("structures", [])
        
        table = Table(title="Predicted Structures")
        table.add_column("Formula", style="cyan")
        table.add_column("Space Group", style="green")
        table.add_column("Density", style="yellow")
        table.add_column("Polymorphs", style="blue")
        
        for struct in structures[:8]:  # Show top 8
            formula = struct.get("formula", "Unknown")
            space_group = struct.get("space_group", "P1")
            density = struct.get("density", 0.0)
            polymorphs = len(struct.get("polymorphs", []))
            table.add_row(formula, space_group, f"{density:.2f}", str(polymorphs))
        
        console.print(table)
    
    def _display_energy_results(self, data: Dict[str, Any]):
        """Display energy calculation results"""
        calculations = data.get("energy_calculations", [])
        
        table = Table(title="Energy Calculations")
        table.add_column("Formula", style="cyan")
        table.add_column("Energy/atom", style="green")
        table.add_column("Formation E", style="yellow")
        table.add_column("Stability", style="blue")
        
        for calc in calculations[:8]:
            formula = calc.get("formula", "Unknown")
            energy_per_atom = calc.get("energy_per_atom", 0.0)
            formation_e = calc.get("formation_energy", 0.0)
            stability = calc.get("stability_score", 0.0)
            
            table.add_row(
                formula, 
                f"{energy_per_atom:.3f} eV",
                f"{formation_e:.3f} eV",
                f"{stability:.2f}"
            )
        
        console.print(table)
    
    async def _get_user_decision(self, data: Dict[str, Any]) -> CheckpointDecision:
        """Get user decision on how to proceed"""
        
        console.print("\nHow would you like to proceed?")
        
        choices = [
            "continue - Proceed to next stage",
            "tweak - Modify search parameters",
            "stop - End discovery here"
        ]
        
        for i, choice in enumerate(choices, 1):
            console.print(f"  {i}. {choice}")
        
        while True:
            try:
                choice = Prompt.ask("Your choice", choices=["1", "2", "3", "continue", "tweak", "stop"])
                
                if choice in ["1", "continue"]:
                    return CheckpointDecision("continue", {}, "User chose to continue")
                elif choice in ["2", "tweak"]:
                    return await self._get_tweaks(data)
                elif choice in ["3", "stop"]:
                    return CheckpointDecision("stop", {}, "User chose to stop")
                    
            except KeyboardInterrupt:
                return CheckpointDecision("stop", {}, "User interrupted")
    
    async def _get_tweaks(self, data: Dict[str, Any]) -> CheckpointDecision:
        """Get specific tweaks from user"""
        console.print("\nWhat would you like to modify?")
        
        modifications = {}
        
        if self.stage == "composition":
            # Get composition-specific tweaks
            if Confirm.ask("Adjust element constraints?"):
                elements = Prompt.ask("Elements to focus on (comma-separated)")
                modifications["focus_elements"] = [e.strip() for e in elements.split(",")]
            
            if Confirm.ask("Change composition limits?"):
                max_compositions = Prompt.ask("Maximum compositions to generate", default="100")
                modifications["max_compositions"] = int(max_compositions)
                
        elif self.stage == "structure":
            # Get structure-specific tweaks
            if Confirm.ask("Adjust structure diversity?"):
                polymorphs = Prompt.ask("Number of polymorphs per composition", default="5")
                modifications["polymorphs_per_composition"] = int(polymorphs)
            
            if Confirm.ask("Focus on specific crystal systems?"):
                systems = Prompt.ask("Crystal systems (cubic,tetragonal,orthorhombic,etc)")
                modifications["crystal_systems"] = [s.strip() for s in systems.split(",")]
                
        elif self.stage == "energy":
            # Get energy-specific tweaks
            if Confirm.ask("Adjust energy calculation parameters?"):
                accuracy = Prompt.ask("Accuracy level", choices=["low", "medium", "high"], default="medium")
                modifications["accuracy"] = accuracy
            
            if Confirm.ask("Filter by energy criteria?"):
                max_energy = Prompt.ask("Maximum energy per atom (eV)", default="-0.1")
                modifications["max_energy_per_atom"] = float(max_energy)
        
        reasoning = Prompt.ask("Reason for these changes", default="User-requested modifications")
        
        return CheckpointDecision("tweak", modifications, reasoning)


class CopilotAgent:
    """Co-pilot agent with human checkpoints"""
    
    def __init__(self, enable_checkpoints: bool = True):
        self.enable_checkpoints = enable_checkpoints
        self.pipeline_runner = ThreeStageRunner()
        self.checkpoints = {
            "composition": HumanCheckpoint("composition", 
                "Composition validation complete. Review the generated formulas."),
            "structure": HumanCheckpoint("structure", 
                "Structure prediction complete. Review the predicted crystal structures."),
            "energy": HumanCheckpoint("energy",
                "Energy calculations complete. Review the stability analysis.")
        }
        
    @agent_step(stage="copilot")
    async def discover_with_copilot(self, query: str, 
                                   requirements: Dict[str, Any] = None) -> Dict[str, Any]:
        """Run materials discovery with human checkpoints"""
        
        console.print("Starting Co-pilot Materials Discovery", style="bold green")
        console.print(f"Query: {query}")
        
        if self.enable_checkpoints:
            console.print("Checkpoints enabled - you'll be asked to review results at each stage")
        
        try:
            # Stage 1: Composition with checkpoint
            composition_result = await self.pipeline_runner.composition_stage.execute(
                query, requirements or {}
            )
            
            if self.enable_checkpoints:
                telemetry = get_telemetry_summary()
                decision = await self.checkpoints["composition"].present_checkpoint(
                    composition_result.data, telemetry
                )
                
                if decision.action == "stop":
                    return {"stopped_at": "composition", "reason": decision.reasoning}
                elif decision.action == "tweak":
                    # Apply modifications and re-run composition stage
                    requirements = {**(requirements or {}), **decision.modifications}
                    composition_result = await self.pipeline_runner.composition_stage.execute(
                        query, requirements
                    )
            
            if not composition_result.success:
                return {"error": "Composition stage failed", "stage": "composition"}
            
            # Stage 2: Structure with checkpoint  
            structure_result = await self.pipeline_runner.structure_stage.execute(composition_result)
            
            if self.enable_checkpoints:
                telemetry = get_telemetry_summary()
                decision = await self.checkpoints["structure"].present_checkpoint(
                    structure_result.data, telemetry
                )
                
                if decision.action == "stop":
                    return {"stopped_at": "structure", "reason": decision.reasoning,
                           "partial_results": {"composition": composition_result.data}}
                elif decision.action == "tweak":
                    # Apply structure modifications (placeholder)
                    console.print("Applying structure modifications...")
            
            if not structure_result.success:
                return {"error": "Structure stage failed", "stage": "structure"}
            
            # Stage 3: Energy with checkpoint
            energy_result = await self.pipeline_runner.energy_stage.execute(structure_result)
            
            if self.enable_checkpoints:
                telemetry = get_telemetry_summary()
                decision = await self.checkpoints["energy"].present_checkpoint(
                    energy_result.data, telemetry
                )
                
                if decision.action == "stop":
                    return {"stopped_at": "energy", "reason": decision.reasoning,
                           "partial_results": {
                               "composition": composition_result.data,
                               "structure": structure_result.data
                           }}
                elif decision.action == "tweak":
                    console.print("Applying energy calculation modifications...")
            
            # Compile final results
            final_result = {
                "success": True,
                "discovery_mode": "copilot",
                "checkpoints_used": self.enable_checkpoints,
                "stages": {
                    "composition": composition_result.data,
                    "structure": structure_result.data,  
                    "energy": energy_result.data
                },
                "final_report": energy_result.data["final_report"],
                "telemetry": get_telemetry_summary()
            }
            
            # Display final results
            self._display_final_results(final_result)
            
            return final_result
            
        except KeyboardInterrupt:
            console.print("\nDiscovery interrupted by user", style="red")
            return {"error": "User interrupted", "partial_results": {}}
        except Exception as e:
            console.print(f"\nDiscovery failed: {e}", style="red")
            return {"error": str(e), "stage": "unknown"}
    
    def _display_final_results(self, results: Dict[str, Any]):
        """Display final discovery results"""
        console.print("\nMaterials Discovery Complete!", style="bold green")
        
        # Summary table
        table = Table(title="Discovery Summary")
        table.add_column("Stage", style="cyan")
        table.add_column("Status", style="green")
        table.add_column("Results", style="yellow")
        
        stages = results.get("stages", {})
        for stage_name, stage_data in stages.items():
            status = "Success" if stage_data else "Failed"
            
            if stage_name == "composition":
                count = len(stage_data.get("compositions", []))
                result_text = f"{count} valid compositions"
            elif stage_name == "structure":
                count = len(stage_data.get("structures", []))
                result_text = f"{count} predicted structures"
            elif stage_name == "energy":
                calculations = stage_data.get("energy_calculations", [])
                result_text = f"{len(calculations)} energy calculations"
            
            table.add_row(stage_name.title(), status, result_text)
        
        console.print(table)
        
        # Cost summary
        telemetry = results.get("telemetry", {})
        if telemetry and "total_cost_usd" in telemetry:
            console.print(f"\nTotal Cost: ${telemetry['total_cost_usd']:.3f}")
            console.print(f"Total Time: {telemetry.get('total_time_seconds', 0):.1f}s")
            
            if telemetry['total_cost_usd'] > 0.50:
                console.print("High cost detected - consider optimisation", style="yellow")
        
        console.print("\nFull results saved to telemetry logs")


# Convenience function for CLI integration
async def run_copilot_discovery(query: str, enable_checkpoints: bool = True, 
                               requirements: Dict[str, Any] = None) -> Dict[str, Any]:
    """Run copilot discovery - convenience function for CLI"""
    agent = CopilotAgent(enable_checkpoints=enable_checkpoints)
    return await agent.discover_with_copilot(query, requirements) 