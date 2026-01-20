"""
CrystaLyse.AI Agent Module

This module provides the unified materials discovery agent using OpenAI Agents SDK.
All legacy agent implementations have been consolidated into a single, efficient agent.
"""

from .openai_agents_bridge import EnhancedCrystaLyseAgent

__all__ = ["EnhancedCrystaLyseAgent"]
