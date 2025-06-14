"""Structure prediction agent for crystal structure analysis."""

import os
from agents import Agent
from typing import List, Optional

try:
    from ..config import get_agent_config
    from ..tools import predict_structure_types, analyze_structure_stability
except ImportError:
    from config import get_agent_config
    from tools import predict_structure_types, analyze_structure_stability

from agents.model_settings import ModelSettings

STRUCTURE_SYSTEM_PROMPT = """You are a crystal structure prediction expert with deep knowledge of crystallography and structure-property relationships.

Your expertise includes:
1. Predicting likely crystal structures from composition
2. Understanding structure types (perovskite, spinel, layered, etc.)
3. Relating structures to properties and applications
4. Assessing structural stability and phase transitions

Key principles:
- Consider ionic size ratios and coordination preferences
- Apply tolerance factors and stability rules
- Recognize when multiple structures are possible
- Connect structure to desired properties"""


class StructurePredictionAgent:
    """Agent specialized in crystal structure prediction."""
    
    def __init__(self, model: str = None, temperature: float = None):
        """
        Initialize structure prediction agent with optimized configuration.
        
        Args:
            model: The LLM model to use (defaults to optimized gpt-4o)
            temperature: Temperature for generation (defaults to optimized)
        """
        config = get_agent_config(model, temperature or 0.5)
        self.agent = Agent(
            name="Structure Expert",
            model=config["model"],
            instructions=STRUCTURE_SYSTEM_PROMPT,
            model_settings=ModelSettings(temperature=config["temperature"]),
        )
        
        # Note: Tool registration handled via different mechanism in openai-agents
        # self.agent.add_tool(predict_structure_types)
        # self.agent.add_tool(analyze_structure_stability)
        
    async def predict_structures(
        self,
        composition: str,
        application: Optional[str] = None
    ) -> str:
        """
        Predict likely crystal structures for a composition.
        
        Args:
            composition: Chemical formula
            application: Target application (optional)
            
        Returns:
            Structure predictions with confidence and reasoning
        """
        prompt = f"Predict the most likely crystal structures for {composition}"
        if application:
            prompt += f" for {application} applications"
            
        prompt += """

Consider:
- Stoichiometry and likely structure types
- Ionic size ratios and coordination
- Application requirements
- Multiple possible structures

Use the structure prediction tools and explain your reasoning."""

        response = await self.agent.run(
            messages=[{
                "role": "user",
                "content": prompt
            }],
            stream=False
        )
        
        return response.messages[-1].content