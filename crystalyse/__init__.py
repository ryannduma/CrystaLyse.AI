"""
CrystaLyse.AI - Unified Materials Discovery with OpenAI Agents SDK

CrystaLyse.AI enables researchers to discover and design materials using a unified 
agent architecture powered by OpenAI o4-mini model with true agentic behaviour.

Key Features:
    - Unified Agent Architecture: Single agent replaces 5+ redundant implementations
    - OpenAI Agents SDK: True agentic behaviour with LLM-controlled workflows
    - SMACT Integration: Proper chemistry validation using established libraries
    - Chemeleon CSP: Crystal structure prediction with up to 10 polymorphs
    - MACE Integration: Formation energy calculations for stability ranking
    - 90% Code Reduction: Streamlined, maintainable codebase
    - Natural Language Tools: Simple tools that LLMs can easily use
"""

__version__ = "0.2.0"

# Import unified agent
from .agents.unified_agent import (
    CrystaLyse,
    AgentConfig,
    analyse_materials,
    rigorous_analysis,
    creative_analysis
)

# Configuration
from .config import config

# Define exports
__all__ = [
    "CrystaLyse",
    "AgentConfig",
    "analyse_materials",
    "rigorous_analysis", 
    "creative_analysis",
    "config"
]