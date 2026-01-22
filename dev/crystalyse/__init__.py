"""
Crystalyse -- Intelligent Scientific Agent for Materials Design

Crystalyse enables researchers to discover and design materials using a skills-based
agent architecture powered by OpenAI models with true agentic behaviour.

Key Features:
    - Skills-Based Architecture: SKILL.md files provide procedural knowledge
    - Two Modes: Creative (o4-mini) for fast exploration, Rigorous (o3) for thorough analysis
    - Direct Tool Imports: No MCP overhead, direct Python integrations
    - SMACT Integration: Proper chemistry validation using established libraries
    - Chemeleon CSP: Crystal structure prediction with up to 10 polymorphs
    - MACE Integration: Formation energy calculations for stability ranking
    - OPTIMADE: Cross-database structure search and grounding
"""

__version__ = "2.0.0-dev"

# Import new agent
try:
    from .agents.agent import MaterialsAgent

    # Backward compatibility alias
    EnhancedCrystaLyseAgent = MaterialsAgent
except ImportError as e:
    import warnings

    warnings.warn(f"Agent functionality not available: {e}", stacklevel=2)
    MaterialsAgent = None
    EnhancedCrystaLyseAgent = None

# Configuration
from .config import CREATIVE_MODEL, RIGOROUS_MODEL, CrystaLyseConfig

# Define exports
__all__ = [
    "MaterialsAgent",
    "EnhancedCrystaLyseAgent",
    "CrystaLyseConfig",
    "CREATIVE_MODEL",
    "RIGOROUS_MODEL",
]
