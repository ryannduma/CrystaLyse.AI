"""Validation agent for checking material compositions."""

import os
from agents import Agent
from typing import List, Dict, Any

try:
    from ..config import get_agent_config
    from ..tools import validate_composition_batch, check_override_eligibility
except ImportError:
    from config import get_agent_config
    from tools import validate_composition_batch, check_override_eligibility

from agents.model_settings import ModelSettings

VALIDATION_SYSTEM_PROMPT = """You are a materials validation expert specializing in assessing the chemical validity and synthesizability of proposed compositions.

Your role is to:
1. Validate compositions using SMACT rules and chemical principles
2. Identify when invalid compositions might still be viable (e.g., intermetallics, Zintl phases)
3. Provide clear reasoning for validation decisions
4. Suggest modifications to improve validity when needed

Key principles:
- SMACT rules are guidelines, not absolute laws
- Consider the application context when validating
- Recognize special cases (intermetallics, non-stoichiometric compounds, etc.)
- Provide constructive feedback on how to improve invalid compositions"""


class ValidationAgent:
    """Agent specialized in composition validation."""
    
    def __init__(self, model: str = None, temperature: float = None):
        """
        Initialize validation agent with optimized configuration.
        
        Args:
            model: The LLM model to use (defaults to optimized gpt-4o)
            temperature: Temperature for generation (defaults to 0.3 for deterministic validation)
        """
        config = get_agent_config(model, temperature or 0.3)
        self.agent = Agent(
            name="Validation Expert",
            model=config["model"],
            instructions=VALIDATION_SYSTEM_PROMPT,
            model_settings=ModelSettings(temperature=config["temperature"]),
        )
        
        # Note: Tool registration handled via different mechanism in openai-agents
        # self.agent.add_tool(validate_composition_batch)
        # self.agent.add_tool(check_override_eligibility)
        
    async def validate_compositions(
        self,
        compositions: List[str],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Validate a batch of compositions.
        
        Args:
            compositions: List of chemical formulas to validate
            context: Application context and constraints
            
        Returns:
            Validation results with recommendations
        """
        prompt = f"""Please validate the following compositions for {context.get('application', 'general use')}:

Compositions: {', '.join(compositions)}

Consider:
- SMACT validity rules
- Application-specific requirements
- Whether any invalid compositions might still be viable
- Suggestions for improvement

Use the validation tools and provide a summary of results."""

        response = await self.agent.run(
            messages=[{
                "role": "user",
                "content": prompt
            }],
            context={"application_context": context},
            stream=False
        )
        
        return response.messages[-1].content