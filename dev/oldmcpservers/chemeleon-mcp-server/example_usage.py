#!/usr/bin/env python3
"""Example usage of Chemeleon MCP server with CrystaLyse."""

import asyncio
import sys
from pathlib import Path

# Add OpenAI agents to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "openai-agents-python" / "src"))

from agents import Agent, Runner
from agents.mcp import MCPServerStdio

async def main():
    """Example of using Chemeleon MCP server."""
    
    # Server configuration
    server_params = {
        "command": "python",
        "args": ["-m", "chemeleon_mcp"],
        "env": {
            "PYTHONPATH": str(Path(__file__).parent / "src") + ":" + 
                         str(Path(__file__).parent.parent / "chemeleon-dng")
        }
    }
    
    # Create server connection
    async with MCPServerStdio(
        name="Chemeleon CSP",
        params=server_params
    ) as server:
        
        # Create agent with Chemeleon capabilities
        agent = Agent(
            name="Crystal Designer",
            instructions="""You are a crystal structure designer with access to Chemeleon.
            
            Available tools:
            - generate_crystal_csp: Generate structures from formulas
            - analyse_structure: Analyse crystal properties
            - get_model_info: Check available models
            
            Help users design and analyse crystal structures.""",
            mcp_servers=[server]
        )
        
        # Example 1: Generate a simple structure
        print("=== Example 1: Generate NaCl structure ===")
        result = await Runner.run(
            starting_agent=agent,
            input="Generate a crystal structure for NaCl"
        )
        print(result)
        
        # Example 2: Generate and analyse
        print("\n=== Example 2: Generate and analyse TiO2 ===")
        result = await Runner.run(
            starting_agent=agent,
            input="Generate a crystal structure for TiO2 and analyse its symmetry"
        )
        print(result)
        
        # Example 3: Multiple structures
        print("\n=== Example 3: Compare structures ===")
        result = await Runner.run(
            starting_agent=agent,
            input="Generate structures for both MgO and CaO, then compare their lattice parameters"
        )
        print(result)

if __name__ == "__main__":
    print("Chemeleon MCP Server Example")
    print("Note: First run will download the CSP model file (~1GB)\n")
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nInterrupted by user")
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()