#!/usr/bin/env python3
"""Test script to verify MCP server connection and SMACT tools."""

import os
import asyncio
from pathlib import Path

# Set up environment
os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_MDG_API_KEY", "")

from agents import Agent, Runner
from agents.mcp import MCPServerStdio
from agents.model_settings import ModelSettings


async def test_mcp_connection():
    """Test MCP server connection and available tools."""
    
    print("🔬 Testing CrystaLyse MCP Connection...")
    print("=" * 50)
    
    # Set up path to SMACT MCP server
    smact_path = Path(__file__).parent / "smact-mcp-server"
    print(f"📁 SMACT MCP Server Path: {smact_path}")
    
    try:
        # Test MCP server connection
        async with MCPServerStdio(
            name="SMACT Tools",
            params={
                "command": "python",
                "args": ["-m", "smact_mcp.server"],
                "cwd": str(smact_path)
            }
        ) as smact_server:
            print("✅ MCP Server connection established!")
            
            # Create test agent
            agent = Agent(
                name="SMACT Test Agent",
                model="gpt-4o",
                instructions="You are a materials science assistant with access to SMACT tools. Use the available tools to validate chemical compositions and test their functionality.",
                model_settings=ModelSettings(temperature=0.3),
                mcp_servers=[smact_server],
            )
            
            print("✅ Agent created with MCP server!")
            
            # Test 1: List available tools
            print("\n🔧 Testing tool availability...")
            test_query = "What SMACT tools are available? List them and briefly describe what each one does."
            
            response = await Runner.run(
                starting_agent=agent,
                input=test_query
            )
            
            print("📋 Available Tools Response:")
            print(response.final_output)
            
            # Test 2: Validate a simple composition
            print("\n🧪 Testing composition validation...")
            test_query2 = "Use the SMACT tools to check if NaCl is a valid composition. Show me the detailed results."
            
            response2 = await Runner.run(
                starting_agent=agent,
                input=test_query2
            )
            
            print("🧂 NaCl Validation Response:")
            print(response2.final_output)
            
            # Test 3: Parse a formula
            print("\n🔬 Testing formula parsing...")
            test_query3 = "Parse the chemical formula LiFePO4 using SMACT tools and show me the element breakdown."
            
            response3 = await Runner.run(
                starting_agent=agent,
                input=test_query3
            )
            
            print("🔋 LiFePO4 Parsing Response:")
            print(response3.final_output)
            
            print("\n✅ All MCP tests completed successfully!")
            
    except Exception as e:
        print(f"❌ MCP Connection Error: {e}")
        print(f"📝 Make sure the SMACT MCP server is properly set up at: {smact_path}")
        raise


async def main():
    """Main test function."""
    try:
        await test_mcp_connection()
        print("\n🎉 CrystaLyse MCP integration is working!")
    except Exception as e:
        print(f"\n💥 Test failed with error: {e}")
        print("\n🔧 Troubleshooting suggestions:")
        print("1. Ensure Python environment has required packages:")
        print("   - openai-agents")
        print("   - smact")
        print("   - pymatgen")
        print("2. Check that SMACT MCP server is in the correct location")
        print("3. Verify OPENAI_MDG_API_KEY environment variable is set")


if __name__ == "__main__":
    asyncio.run(main())