#!/usr/bin/env python3
"""Debug script to test Chemeleon MCP server via OpenAI agents SDK."""

import asyncio
import json
import sys
from pathlib import Path

# Ensure we're using the right paths
sys.path.insert(0, str(Path(__file__).parent.parent / "openai-agents-python" / "src"))

from agents import Agent, Runner, trace
from agents.mcp import MCPServerStdio

async def test_chemeleon_mcp():
    """Test the Chemeleon MCP server with OpenAI agents."""
    
    print("=== Testing Chemeleon MCP Server ===\n")
    
    # Create server connection
    server_params = {
        "command": sys.executable,
        "args": ["-m", "chemeleon_mcp"],
        "env": {
            "PYTHONPATH": str(Path(__file__).parent / "chemeleon-mcp-server" / "src") + ":" + 
                         str(Path(__file__).parent / "chemeleon-dng"),
            "PYTORCH_ENABLE_MPS_FALLBACK": "1"  # For Mac compatibility
        }
    }
    
    print(f"Starting server with command: {server_params['command']} {' '.join(server_params['args'])}")
    
    try:
        async with MCPServerStdio(
            name="Chemeleon CSP",
            params=server_params,
            cache_tools_list=True
        ) as server:
            print("✓ Server started successfully")
            
            # Create agent
            agent = Agent(
                name="Materials Designer",
                instructions="""You are a materials scientist using Chemeleon for crystal structure prediction.
                Use the available tools to:
                1. Generate crystal structures from formulas
                2. Create novel structures
                3. Analyze the generated structures
                """,
                mcp_servers=[server]
            )
            
            # Test 1: Get model info
            print("\n--- Test 1: Get Model Info ---")
            result1 = await Runner.run(
                starting_agent=agent,
                input="Use get_model_info to check what models are available"
            )
            print(f"Result: {result1}")
            
            # Test 2: Generate crystal structure (CSP)
            print("\n--- Test 2: Generate Crystal Structure (CSP) ---")
            result2 = await Runner.run(
                starting_agent=agent,
                input="Generate a crystal structure for NaCl using generate_crystal_csp"
            )
            print(f"Result: {result2}")
            
            # Test 3: Generate novel structure (DNG)
            print("\n--- Test 3: Generate Novel Structure (DNG) ---")
            result3 = await Runner.run(
                starting_agent=agent,
                input="Generate a novel crystal structure with 10 atoms using generate_crystal_dng"
            )
            print(f"Result: {result3}")
            
            # Test 4: Analyze structure
            print("\n--- Test 4: Structure Analysis ---")
            result4 = await Runner.run(
                starting_agent=agent,
                input="Generate a structure for TiO2 and analyze its symmetry"
            )
            print(f"Result: {result4}")
            
            print("\n✅ All tests completed successfully!")
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

async def test_integration_with_crystalyse():
    """Test integration with CrystaLyse agent."""
    
    print("\n=== Testing Integration with CrystaLyse ===\n")
    
    # This would test the full integration
    # For now, we'll create a simple test
    
    server_params = {
        "command": sys.executable,
        "args": ["-m", "chemeleon_mcp"],
        "env": {
            "PYTHONPATH": str(Path(__file__).parent / "chemeleon-mcp-server" / "src") + ":" + 
                         str(Path(__file__).parent / "chemeleon-dng")
        }
    }
    
    try:
        async with MCPServerStdio(
            name="Chemeleon CSP",
            params=server_params
        ) as chemeleon_server:
            
            # Could also add SMACT server here for full integration
            agent = Agent(
                name="CrystaLyse Materials Designer",
                instructions="""You are an advanced materials discovery agent with access to:
                - Chemeleon for crystal structure generation
                - Structure analysis capabilities
                
                Help users discover and design new materials.""",
                mcp_servers=[chemeleon_server]
            )
            
            # Complex task
            print("Testing complex materials design task...")
            result = await Runner.run(
                starting_agent=agent,
                input="""I need help designing a new perovskite material.
                1. Generate crystal structures for CaTiO3 and BaTiO3
                2. Analyze their symmetries
                3. Suggest which might have better ferroelectric properties based on the structure"""
            )
            
            print(f"\nResult: {result}")
            
            return True
            
    except Exception as e:
        print(f"\n❌ Integration test error: {e}")
        return False

async def main():
    """Run all tests."""
    
    # Basic MCP test
    success1 = await test_chemeleon_mcp()
    
    # Integration test
    if success1:
        print("\n" + "="*50 + "\n")
        success2 = await test_integration_with_crystalyse()
    else:
        success2 = False
    
    if success1 and success2:
        print("\n✅ All MCP tests passed!")
        return 0
    else:
        print("\n❌ Some MCP tests failed")
        return 1

if __name__ == "__main__":
    # Run with proper event loop
    try:
        sys.exit(asyncio.run(main()))
    except KeyboardInterrupt:
        print("\nInterrupted by user")
        sys.exit(1)