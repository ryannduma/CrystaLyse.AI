"""
LLM-scored hill-climb optimiser following patterns
Implements iterative optimisation with self-reflection and reward scoring
"""

import asyncio
import json
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from agents import Agent, Runner, function_tool

from ..monitoring.agent_telemetry import agent_step


@dataclass
class MaterialCandidate:
    """Single material candidate with score"""
    formula: str
    structure_data: Dict[str, Any]
    energy_per_atom: float
    stability_score: float
    target_properties: Dict[str, float]
    generation: int
    parent_id: Optional[str] = None
    
    def get_reward(self) -> float:
        """Calculate reward score"""
        # Simple heuristic: +1 if stable and good energy, 0 otherwise
        stable = self.stability_score > 0.5
        good_energy = self.energy_per_atom < -0.3
        return 1.0 if (stable and good_energy) else 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "formula": self.formula,
            "energy_per_atom": self.energy_per_atom,
            "stability_score": self.stability_score,
            "target_properties": self.target_properties,
            "reward": self.get_reward(),
            "generation": self.generation
        }


class LLMReflector:
    """LLM-powered self-reflection agent"""
    
    def __init__(self):
        self.reflection_agent = None
        
    async def reflect_on_results(self, candidates: List[MaterialCandidate], 
                                target: str, iteration: int) -> Dict[str, Any]:
        """Generate reflection and next steps"""
        
        if not self.reflection_agent:
            instructions = (
                "You are a materials science researcher analyzing optimisation results. "
                "Your job is to:\n"
                "1. Analyze the current batch of materials candidates\n"
                "2. Identify what's working and what's not\n" 
                "3. Suggest specific edits to improve the next generation\n"
                "4. Focus on single, high-impact changes\n\n"
                "Be specific about compositional or structural modifications."
            )
            
            self.reflection_agent = Agent(
                name="ReflectionBot",
                instructions=instructions,
                model="o4-mini",
                tools=[self._create_reflection_tool()],
                max_turns=5
            )
        
        # Prepare candidate summary for analysis
        candidate_summary = self._summarize_candidates(candidates, target)
        
        reflection_input = (
            f"Iteration {iteration} results for target: {target}\n\n"
            f"Current candidates:\n{candidate_summary}\n\n"
            "What single edit would most increase the reward? Be specific."
        )
        
        result = await Runner.run(starting_agent=self.reflection_agent, input=reflection_input)
        
        # Extract reflection insights
        return self._parse_reflection(result)
    
    def _create_reflection_tool(self):
        """Tool for reflection agent to submit analysis"""
        @function_tool
        def submit_reflection(
            best_candidate: str,
            key_issue: str, 
            specific_edit: str,
            reasoning: str,
            confidence: float
        ) -> str:
            """Submit reflection analysis with specific improvement suggestion"""
            return f"Reflection: Best={best_candidate}, Issue={key_issue}, Edit={specific_edit}, Confidence={confidence}"
        
        return submit_reflection
    
    def _summarize_candidates(self, candidates: List[MaterialCandidate], target: str) -> str:
        """Create summary of candidates for reflection"""
        summary = []
        for i, candidate in enumerate(candidates[:5]):  # Top 5
            summary.append(
                f"{i+1}. {candidate.formula}: "
                f"E={candidate.energy_per_atom:.3f} eV/atom, "
                f"Stability={candidate.stability_score:.2f}, "
                f"Reward={candidate.get_reward():.1f}"
            )
        return "\n".join(summary)
    
    def _parse_reflection(self, result) -> Dict[str, Any]:
        """Parse reflection result into actionable insights"""
        # Placeholder - would parse agent output for structured insights
        return {
            "key_issue": "Unknown",
            "suggested_edit": "Try different composition",
            "confidence": 0.7,
            "reasoning": "Placeholder reflection"
        }


class HillClimbOptimiser:
    """Hill-climb optimiser with LLM scoring and reflection"""
    
    def __init__(self, max_iterations: int = 10, population_size: int = 8):
        self.max_iterations = max_iterations
        self.population_size = population_size
        self.reflector = LLMReflector()
        self.optimisation_history = []
        
    @agent_step(stage="optimisation")
    async def optimise_materials(self, target_description: str, 
                               initial_candidates: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Run hill-climb optimisation with LLM reflection"""
        
        # Convert initial candidates to MaterialCandidate objects
        population = self._initialise_population(initial_candidates)
        
        best_candidate = None
        best_reward = -1.0
        
        for iteration in range(self.max_iterations):
            print(f"Running hill-climb iteration {iteration + 1}/{self.max_iterations}")
            
            # Evaluate current population
            population = await self._evaluate_population(population, iteration)
            
            # Track best candidate
            current_best = max(population, key=lambda x: x.get_reward())
            if current_best.get_reward() > best_reward:
                best_candidate = current_best
                best_reward = current_best.get_reward()
            
            # Self-reflection
            reflection = await self.reflector.reflect_on_results(
                population, target_description, iteration
            )
            
            self.optimisation_history.append({
                "iteration": iteration,
                "best_reward": best_reward,
                "best_formula": best_candidate.formula if best_candidate else "None",
                "reflection": reflection,
                "population_size": len(population)
            })
            
            # Early stopping if we find a good solution
            if best_reward >= 0.9:
                print(f"✅ Found excellent candidate: {best_candidate.formula}")
                break
            
            # Generate next population based on reflection
            if iteration < self.max_iterations - 1:
                population = await self._generate_next_population(
                    population, reflection, iteration + 1
                )
        
        return {
            "best_candidate": best_candidate.to_dict() if best_candidate else None,
            "best_reward": best_reward,
            "total_iterations": iteration + 1,
            "optimisation_history": self.optimisation_history,
            "final_population": [c.to_dict() for c in population]
        }
    
    def _initialise_population(self, initial_data: List[Dict[str, Any]]) -> List[MaterialCandidate]:
        """Initialise population from initial candidates"""
        population = []
        for i, data in enumerate(initial_data):
            candidate = MaterialCandidate(
                formula=data.get("formula", f"Unknown_{i}"),
                structure_data=data.get("structure", {}),
                energy_per_atom=data.get("energy_per_atom", 0.0),
                stability_score=data.get("stability", 0.5),
                target_properties=data.get("properties", {}),
                generation=0
            )
            population.append(candidate)
        
        return population
    
    async def _evaluate_population(self, population: List[MaterialCandidate], 
                                 iteration: int) -> List[MaterialCandidate]:
        """Evaluate population (placeholder - would use MACE for real scoring)"""
        
        # In real implementation, this would:
        # 1. Run MACE calculations for each candidate
        # 2. Update energy_per_atom and stability_score
        # 3. Calculate target properties
        
        # For now, simulate with some noise
        import random
        for candidate in population:
            # Add some random variation to simulate real calculations
            noise = random.uniform(-0.1, 0.1)
            candidate.energy_per_atom += noise
            candidate.stability_score = max(0, min(1, candidate.stability_score + noise/2))
        
        return population
    
    async def _generate_next_population(self, current_population: List[MaterialCandidate],
                                      reflection: Dict[str, Any], generation: int) -> List[MaterialCandidate]:
        """Generate next population based on reflection"""
        
        # Select top performers
        sorted_pop = sorted(current_population, key=lambda x: x.get_reward(), reverse=True)
        survivors = sorted_pop[:self.population_size // 2]
        
        next_population = []
        
        # Keep best candidates
        for candidate in survivors:
            next_population.append(candidate)
        
        # Generate variants based on reflection
        suggested_edit = reflection.get("suggested_edit", "Try different composition")
        
        for i, parent in enumerate(survivors):
            if len(next_population) >= self.population_size:
                break
                
            # Create variant (placeholder - would implement real structural/compositional edits)
            variant = MaterialCandidate(
                formula=self._mutate_formula(parent.formula, suggested_edit),
                structure_data=parent.structure_data.copy(),
                energy_per_atom=parent.energy_per_atom,
                stability_score=parent.stability_score,
                target_properties=parent.target_properties.copy(),
                generation=generation,
                parent_id=parent.formula
            )
            
            next_population.append(variant)
        
        return next_population
    
    def _mutate_formula(self, formula: str, edit_suggestion: str) -> str:
        # Placeholder - would implement real logic based on LLM suggestion
        # e.g., using a chemistry toolkit to parse and modify the formula
        if "add" in edit_suggestion.lower() and len(formula) < 10:
            return formula + "O"
        elif "remove" in edit_suggestion.lower() and "O" in formula:
            return formula.replace("O", "", 1)
        return formula + "Si"
    
    def get_optimisation_summary(self) -> str:
        """Get summary of the optimisation run"""
        if not self.optimisation_history:
            return "No optimisation run yet."

        summary = "Optimisation Summary:\n"
        for record in self.optimisation_history:
            summary += (
                f"  Iter {record['iteration']}: "
                f"Best Reward={record['best_reward']:.2f}, "
                f"Formula='{record['best_formula']}', "
                f"Reflection='{record['reflection']['suggested_edit']}'\n"
            )
        return summary 