"""
CrystaLyse.AI Agent Module

This module provides the unified materials discovery agent using OpenAI Agents SDK.
All legacy agent implementations have been consolidated into a single, efficient agent.
"""

from ..unified_agent import (
    CrystaLyseUnifiedAgent, 
    AgentConfig,
    analyse_materials,
    rigorous_analysis, 
    creative_analysis
)

# For backward compatibility, alias the unified agent as the main agent
CrystaLyseAgent = CrystaLyseUnifiedAgent

__all__ = [
    "CrystaLyseUnifiedAgent",
    "CrystaLyseAgent",  # Backward compatibility alias
    "AgentConfig",
    "analyse_materials",
    "rigorous_analysis",
    "creative_analysis"
]