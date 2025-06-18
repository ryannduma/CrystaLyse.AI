"""
CrystaLyse.AI Tools Module

All tools have been consolidated into MCP servers and unified agent.
This module is kept for backward compatibility but all functionality
is now provided through the unified agent and MCP servers:

- SMACT MCP Server: Composition validation and generation
- Chemeleon MCP Server: Crystal structure generation  
- MACE MCP Server: Energy calculations
- Chemistry Unified Server: Integrated workflow

Use the unified agent for all materials discovery tasks.
"""

# Backward compatibility placeholders
def generate_compositions(*args, **kwargs):
    """Use CrystaLyse with SMACT MCP server instead."""
    raise NotImplementedError(
        "This function has been replaced by the unified agent with SMACT MCP server. "
        "Use CrystaLyse for materials discovery."
    )

def validate_composition_batch(*args, **kwargs):
    """Use CrystaLyse with SMACT MCP server instead."""
    raise NotImplementedError(
        "This function has been replaced by the unified agent with SMACT MCP server. "
        "Use CrystaLyse for materials discovery."
    )

__all__ = []  # No public tools - use unified agent instead