"""
Crystalyse Agent Module V2

This module provides the skills-based materials discovery agent.
Two modes are supported:
- Creative (default): Fast exploration with gpt-5-mini
- Rigorous: Thorough analysis with gpt-5.2
"""

from .agent import MaterialsAgent

# Backward compatibility alias
EnhancedCrystaLyseAgent = MaterialsAgent

__all__ = ["MaterialsAgent", "EnhancedCrystaLyseAgent"]
