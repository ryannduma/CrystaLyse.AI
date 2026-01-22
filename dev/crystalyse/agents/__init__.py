"""
Crystalyse Agent Module V2

This module provides the skills-based materials discovery agent.
Two modes are supported:
- Creative (default): Fast exploration with o4-mini
- Rigorous: Thorough analysis with o3
"""

from .agent import MaterialsAgent

# Backward compatibility alias
EnhancedCrystaLyseAgent = MaterialsAgent

__all__ = ["MaterialsAgent", "EnhancedCrystaLyseAgent"]
