#!/usr/bin/env python3
"""
Test FastMCP tool registration directly
"""

import sys
from pathlib import Path

# Add paths
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "smact-mcp-server" / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "chemeleon-mcp-server" / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "mace-mcp-server" / "src"))

from mcp.server.fastmcp import FastMCP

# Test SMACT tools registration
print("Testing SMACT tools registration...")
try:
    from smact_mcp.server import mcp as smact_mcp
    print(f"SMACT MCP object: {smact_mcp}")
    print(f"SMACT MCP name: {smact_mcp.name}")
    
    # Check if tools are registered after import
    import smact_mcp.tools
    
    # Try to get tool count using list_tools
    try:
        tools = smact_mcp.list_tools()
        print(f"SMACT tools registered: {len(tools)}")
        for tool in tools:
            print(f"  - {tool.name}: {tool.description[:80]}...")
    except Exception as e:
        print(f"Error listing SMACT tools: {e}")
    
except Exception as e:
    print(f"SMACT test failed: {e}")
    import traceback
    traceback.print_exc()

# Test CHEMELEON tools registration
print("\nTesting CHEMELEON tools registration...")
try:
    from chemeleon_mcp.server import mcp as chemeleon_mcp
    print(f"CHEMELEON MCP object: {chemeleon_mcp}")
    print(f"CHEMELEON MCP name: {chemeleon_mcp.name}")
    
    # Check if tools are registered after import
    import chemeleon_mcp.tools
    
    # Try to get tool count using list_tools
    try:
        tools = chemeleon_mcp.list_tools()
        print(f"CHEMELEON tools registered: {len(tools)}")
        for tool in tools:
            print(f"  - {tool.name}: {tool.description[:80]}...")
    except Exception as e:
        print(f"Error listing CHEMELEON tools: {e}")
        
except Exception as e:
    print(f"CHEMELEON test failed: {e}")
    import traceback
    traceback.print_exc()

# Test MACE tools registration
print("\nTesting MACE tools registration...")
try:
    from mace_mcp.server import mcp as mace_mcp
    print(f"MACE MCP object: {mace_mcp}")
    print(f"MACE MCP name: {mace_mcp.name}")
    
    # Check if tools are registered after import
    import mace_mcp.tools
    
    # Try to get tool count
    if hasattr(mace_mcp, '_tools'):
        print(f"MACE tools registered: {len(mace_mcp._tools)}")
        for tool_name in mace_mcp._tools:
            print(f"  - {tool_name}")
    else:
        print("No _tools attribute found on MACE MCP")
        
except Exception as e:
    print(f"MACE test failed: {e}")
    import traceback
    traceback.print_exc()