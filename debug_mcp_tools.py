#!/usr/bin/env python3
"""Debug MCP tool availability and calling."""

import os
import asyncio
from pathlib import Path

# Set up environment
os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_MDG_API_KEY", "")

from agents import Agent, Runner
from agents.mcp import MCPServerStdio
from agents.model_settings import ModelSettings


async def debug_mcp_tools():
    """Debug MCP tool availability."""
    
    print("🔍 Debugging MCP Tool Availability...")
    print("=" * 50)
    
    # Set up path to SMACT MCP server
    smact_path = Path(__file__).parent / "smact-mcp-server"
    
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
            
            # Create minimal agent
            agent = Agent(
                name="Debug Agent",
                model="gpt-4o",
                instructions="""You are a debug agent. When asked about tools, list ALL available tools.
                When asked to use a specific tool, you MUST call it immediately, not just show the code.""",
                model_settings=ModelSettings(temperature=0.0),
                mcp_servers=[smact_server],
            )
            
            print("✅ Agent created!")
            
            # Test 1: List available tools
            print("\n🔧 Asking agent to list all available tools...")
            
            response1 = await Runner.run(
                starting_agent=agent,
                input="What tools do you have available? List them all with their descriptions."
            )
            
            print("📋 Available tools response:")
            print(response1.final_output)
            
            # Test 2: Force one specific tool call
            print("\n🎯 Forcing specific tool call...")
            
            response2 = await Runner.run(
                starting_agent=agent,
                input='Call the check_smact_validity tool RIGHT NOW with the argument "H2O". Do not explain, just call it.'
            )
            
            print("🔧 Tool call response:")
            print(response2.final_output)
            
            print("\n✅ Debug tests completed!")
            
    except Exception as e:
        print(f"❌ Debug Error: {e}")
        import traceback
        traceback.print_exc()


async def main():
    """Main debug function."""
    try:
        await debug_mcp_tools()
        print("\n🎉 Debug completed!")
    except Exception as e:
        print(f"\n💥 Debug failed with error: {e}")


if __name__ == "__main__":
    asyncio.run(main())