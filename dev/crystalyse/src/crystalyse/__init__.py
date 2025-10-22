"""
Crystalyse - AI-Powered Materials Design

Crystalyse enables researchers to discover and design materials using a unified
agent architecture powered by OpenAI Agents SDK with true agentic behaviour.

Key Features:
    - Unified Agent Architecture: Single agent with intelligent tool coordination
    - OpenAI Agents SDK: True agentic behaviour with LLM-controlled workflows
    - SMACT Integration: Chemistry validation using established libraries
    - Chemeleon CSP: Crystal structure prediction with up to 10 polymorphs
    - MACE Integration: Formation energy calculations for stability ranking
    - Complete Provenance: Always-on audit trails for reproducibility
    - UV Workspace: Fast, reproducible dependency management
"""

__version__ = "1.0.0"

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