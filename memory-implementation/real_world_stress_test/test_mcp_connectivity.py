#!/usr/bin/env python3
"""
Test MCP Server Connectivity

Verify that MCP servers can be reached and tools are available.
"""

import asyncio
import sys
from pathlib import Path
import json
import logging
from contextlib import AsyncExitStack

# Set up logging to see detailed info
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from agents import Agent
from agents.mcp import MCPServerStdio
from crystalyse.config import config

async def test_mcp_server_connection():
    """Test individual MCP server connections."""
    
    print("🔍 Testing MCP Server Connectivity...")
    print("=" * 60)
    
    async with AsyncExitStack() as stack:
        # Test SMACT server
        print("\n1. Testing SMACT MCP Server...")
        try:
            smact_config = config.get_server_config("smact")
            print(f"   Command: {smact_config['command']}")
            print(f"   Args: {smact_config['args']}")
            print(f"   CWD: {smact_config['cwd']}")
            
            smact_server = await stack.enter_async_context(
                MCPServerStdio(
                    name="SMACT",
                    params={
                        "command": smact_config["command"],
                        "args": smact_config["args"],
                        "cwd": smact_config["cwd"],
                        "env": smact_config.get("env", {})
                    }
                )
            )
            
            # Try to list tools
            print("   ✅ SMACT server started successfully")
            
            # Create a simple agent to test tool availability
            test_agent = Agent(
                name="TestAgent",
                model="openai/gpt-4",
                instructions="Test agent for MCP connectivity",
                mcp_servers=[smact_server]
            )
            
            tools = await test_agent.get_all_tools()
            smact_tools = [t for t in tools if 'smact' in t.name.lower()]
            print(f"   Found {len(smact_tools)} SMACT tools:")
            for tool in smact_tools:
                print(f"     - {tool.name}")
            
        except Exception as e:
            print(f"   ❌ SMACT server failed: {e}")
            logger.exception("SMACT server error")
        
        # Test Chemeleon server
        print("\n2. Testing CHEMELEON MCP Server...")
        try:
            chemeleon_config = config.get_server_config("chemeleon")
            print(f"   Command: {chemeleon_config['command']}")
            print(f"   Args: {chemeleon_config['args']}")
            print(f"   CWD: {chemeleon_config['cwd']}")
            
            chemeleon_server = await stack.enter_async_context(
                MCPServerStdio(
                    name="Chemeleon",
                    params={
                        "command": chemeleon_config["command"],
                        "args": chemeleon_config["args"],
                        "cwd": chemeleon_config["cwd"],
                        "env": chemeleon_config.get("env", {})
                    }
                )
            )
            
            print("   ✅ CHEMELEON server started successfully")
            
            # Test with agent
            test_agent = Agent(
                name="TestAgent",
                model="openai/gpt-4",
                instructions="Test agent for MCP connectivity",
                mcp_servers=[chemeleon_server]
            )
            
            tools = await test_agent.get_all_tools()
            chemeleon_tools = [t for t in tools if 'chemeleon' in t.name.lower()]
            print(f"   Found {len(chemeleon_tools)} CHEMELEON tools:")
            for tool in chemeleon_tools:
                print(f"     - {tool.name}")
                
        except Exception as e:
            print(f"   ❌ CHEMELEON server failed: {e}")
            logger.exception("CHEMELEON server error")
        
        # Test MACE server
        print("\n3. Testing MACE MCP Server...")
        try:
            mace_config = config.get_server_config("mace")
            print(f"   Command: {mace_config['command']}")
            print(f"   Args: {mace_config['args']}")
            print(f"   CWD: {mace_config['cwd']}")
            
            mace_server = await stack.enter_async_context(
                MCPServerStdio(
                    name="MACE",
                    params={
                        "command": mace_config["command"],
                        "args": mace_config["args"],
                        "cwd": mace_config["cwd"],
                        "env": mace_config.get("env", {})
                    }
                )
            )
            
            print("   ✅ MACE server started successfully")
            
            # Test with agent
            test_agent = Agent(
                name="TestAgent",
                model="openai/gpt-4",
                instructions="Test agent for MCP connectivity",
                mcp_servers=[mace_server]
            )
            
            tools = await test_agent.get_all_tools()
            mace_tools = [t for t in tools if 'mace' in t.name.lower()]
            print(f"   Found {len(mace_tools)} MACE tools:")
            for tool in mace_tools:
                print(f"     - {tool.name}")
                
        except Exception as e:
            print(f"   ❌ MACE server failed: {e}")
            logger.exception("MACE server error")
        
        # Test all servers together
        print("\n4. Testing all MCP servers together...")
        try:
            mcp_servers = []
            
            # Start all servers
            smact_server = await stack.enter_async_context(
                MCPServerStdio(
                    name="SMACT",
                    params={
                        "command": config.get_server_config("smact")["command"],
                        "args": config.get_server_config("smact")["args"],
                        "cwd": config.get_server_config("smact")["cwd"],
                        "env": config.get_server_config("smact").get("env", {})
                    }
                )
            )
            mcp_servers.append(smact_server)
            
            chemeleon_server = await stack.enter_async_context(
                MCPServerStdio(
                    name="Chemeleon",
                    params={
                        "command": config.get_server_config("chemeleon")["command"],
                        "args": config.get_server_config("chemeleon")["args"],
                        "cwd": config.get_server_config("chemeleon")["cwd"],
                        "env": config.get_server_config("chemeleon").get("env", {})
                    }
                )
            )
            mcp_servers.append(chemeleon_server)
            
            mace_server = await stack.enter_async_context(
                MCPServerStdio(
                    name="MACE",
                    params={
                        "command": config.get_server_config("mace")["command"],
                        "args": config.get_server_config("mace")["args"],
                        "cwd": config.get_server_config("mace")["cwd"],
                        "env": config.get_server_config("mace").get("env", {})
                    }
                )
            )
            mcp_servers.append(mace_server)
            
            print("   ✅ All servers started successfully")
            
            # Create agent with all servers
            test_agent = Agent(
                name="CrystaLyseTest",
                model="openai/gpt-4",
                instructions="Test agent with all MCP servers",
                mcp_servers=mcp_servers
            )
            
            tools = await test_agent.get_all_tools()
            print(f"   Total tools available: {len(tools)}")
            
            # Categorize tools
            smact_tools = [t for t in tools if 'smact' in t.name.lower()]
            chemeleon_tools = [t for t in tools if 'chemeleon' in t.name.lower()]
            mace_tools = [t for t in tools if 'mace' in t.name.lower()]
            
            print(f"   - SMACT tools: {len(smact_tools)}")
            print(f"   - CHEMELEON tools: {len(chemeleon_tools)}")
            print(f"   - MACE tools: {len(mace_tools)}")
            
            # List all tools
            print("\n   All available tools:")
            for tool in tools:
                print(f"     - {tool.name}: {tool.description[:80]}...")
            
            if len(tools) > 0:
                print("\n✅ MCP CONNECTIVITY TEST PASSED!")
                print("All servers are reachable and tools are available.")
            else:
                print("\n❌ MCP CONNECTIVITY TEST FAILED!")
                print("Servers started but no tools are available.")
                
        except Exception as e:
            print(f"   ❌ Combined server test failed: {e}")
            logger.exception("Combined server error")
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    asyncio.run(test_mcp_server_connection())