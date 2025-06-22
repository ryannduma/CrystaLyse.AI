#!/usr/bin/env python3
"""
Test MCP servers directly by running them and sending ListToolsRequest
"""

import asyncio
import json
import sys
from pathlib import Path

# Add paths
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
sys.path.append("/home/ryan/crystalyseai/python-sdk/src")

from mcp.client.stdio import StdioServerParameters, stdio_client


async def test_mcp_server_direct(server_name: str, server_path: str, module: str):
    """Test an MCP server directly."""
    print(f"\nTesting {server_name} server directly...")
    
    server_params = StdioServerParameters(
        command="python",
        args=["-m", module],
        cwd=server_path
    )
    
    async with stdio_client(server_params) as (read, write):
        # Initialize connection
        await write({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name": "test-client", "version": "1.0"}}})
        
        # Read response
        response = await read()
        print(f"Initialize response: {json.dumps(response, indent=2)}")
        
        # List tools
        await write({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})
        
        # Read tools response
        tools_response = await read()
        print(f"Tools response: {json.dumps(tools_response, indent=2)}")
        
        if "result" in tools_response and "tools" in tools_response["result"]:
            tools = tools_response["result"]["tools"]
            print(f"Found {len(tools)} tools:")
            for tool in tools:
                print(f"  - {tool.get('name', 'Unknown')}: {tool.get('description', 'No description')[:80]}...")
        else:
            print("No tools found or error in response")


async def main():
    """Test all MCP servers."""
    print("🔧 Direct MCP Server Testing")
    print("=" * 60)
    
    # Test SMACT
    try:
        await test_mcp_server_direct(
            "SMACT",
            "/home/ryan/crystalyseai/CrystaLyse.AI/smact-mcp-server/src",
            "smact_mcp.server"
        )
    except Exception as e:
        print(f"SMACT test failed: {e}")
        import traceback
        traceback.print_exc()
    
    # Test Chemeleon
    try:
        await test_mcp_server_direct(
            "CHEMELEON",
            "/home/ryan/crystalyseai/CrystaLyse.AI/chemeleon-mcp-server/src",
            "chemeleon_mcp.server"
        )
    except Exception as e:
        print(f"CHEMELEON test failed: {e}")
        import traceback
        traceback.print_exc()
    
    # Test MACE
    try:
        await test_mcp_server_direct(
            "MACE",
            "/home/ryan/crystalyseai/CrystaLyse.AI/mace-mcp-server/src",
            "mace_mcp.server"
        )
    except Exception as e:
        print(f"MACE test failed: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    asyncio.run(main())