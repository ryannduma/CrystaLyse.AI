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

__version__ = "2.0.0-alpha"

# Import unified agent
try:
    from .agents.openai_agents_bridge import EnhancedCrystaLyseAgent
except ImportError as e:
    import warnings
    warnings.warn(f"Agent functionality not available: {e}")
    EnhancedCrystaLyseAgent = None

# Configuration
from .config import CrystaLyseConfig

# Define exports
__all__ = [
    "EnhancedCrystaLyseAgent",
    "CrystaLyseConfig"
]