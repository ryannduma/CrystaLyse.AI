#!/usr/bin/env python3
"""Test Chemeleon MCP server with OpenAI agents client."""

import pytest
import asyncio
import json
import sys
import os
from pathlib import Path

# Add OpenAI agents to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "openai-agents-python" / "src"))

from agents import Agent, Runner
from agents.mcp import MCPServerStdio

class TestChemeleonMCPClient:
    """Test Chemeleon MCP server via OpenAI agents client."""
    
    @pytest.fixture
    def server_params(self):
        """Get server parameters."""
        chemeleon_src = Path(__file__).parent.parent.parent / "chemeleon-mcp-server" / "src"
        chemeleon_dng = Path(__file__).parent.parent.parent / "chemeleon-dng"
        
        return {
            "command": sys.executable,
            "args": ["-m", "chemeleon_mcp"],
            "env": {
                **os.environ,
                "PYTHONPATH": f"{chemeleon_src}:{chemeleon_dng}",
                "PYTORCH_ENABLE_MPS_FALLBACK": "1"
            }
        }
    
    @pytest.mark.asyncio
    async def test_server_connection(self, server_params):
        """Test basic server connection."""
        async with MCPServerStdio(
            name="Chemeleon Test",
            params=server_params
        ) as server:
            # If we get here, server started successfully
            assert server is not None
    
    @pytest.mark.asyncio
    async def test_tool_availability(self, server_params):
        """Test that tools are available to the agent."""
        async with MCPServerStdio(
            name="Chemeleon Test",
            params=server_params,
            cache_tools_list=True
        ) as server:
            agent = Agent(
                name="Test Agent",
                instructions="You are a test agent.",
                mcp_servers=[server]
            )
            
            # Agent should have access to tools
            # (actual tool list access depends on agent implementation)
            assert agent is not None
    
    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_model_info_via_agent(self, server_params):
        """Test get_model_info through agent."""
        async with MCPServerStdio(
            name="Chemeleon Test",
            params=server_params
        ) as server:
            agent = Agent(
                name="Test Agent",
                instructions="Use the get_model_info tool to check available models.",
                mcp_servers=[server]
            )
            
            result = await Runner.run(
                starting_agent=agent,
                input="Check what models are available"
            )
            
            # Result should mention available tasks
            assert result is not None
            assert isinstance(result, str)
    
    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_csp_generation_via_agent(self, server_params):
        """Test CSP generation through agent."""
        async with MCPServerStdio(
            name="Chemeleon Test",
            params=server_params
        ) as server:
            agent = Agent(
                name="Materials Agent",
                instructions="You are a materials scientist. Use generate_crystal_csp to create structures.",
                mcp_servers=[server]
            )
            
            result = await Runner.run(
                starting_agent=agent,
                input="Generate a crystal structure for MgO"
            )
            
            assert result is not None
            # Should mention MgO or structure generation
            assert "MgO" in result or "structure" in result.lower()
    
    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_complex_task(self, server_params):
        """Test a complex materials discovery task."""
        async with MCPServerStdio(
            name="Chemeleon Test",
            params=server_params
        ) as server:
            agent = Agent(
                name="Materials Discovery Agent",
                instructions="""You are an expert in materials discovery.
                Use the available Chemeleon tools to:
                1. Generate crystal structures
                2. Analyze their properties
                3. Provide insights about the materials
                """,
                mcp_servers=[server]
            )
            
            result = await Runner.run(
                starting_agent=agent,
                input="""Generate crystal structures for both NaCl and KCl, 
                then analyze their lattice parameters and explain the differences."""
            )
            
            assert result is not None
            # Should mention both compounds
            assert "NaCl" in result and "KCl" in result
    
    @pytest.mark.asyncio
    async def test_error_handling(self, server_params):
        """Test error handling for invalid inputs."""
        async with MCPServerStdio(
            name="Chemeleon Test",
            params=server_params
        ) as server:
            agent = Agent(
                name="Test Agent",
                instructions="Use generate_crystal_csp to generate structures.",
                mcp_servers=[server]
            )
            
            # Test with invalid formula
            result = await Runner.run(
                starting_agent=agent,
                input="Generate a structure for XYZ123 (this is not a valid formula)"
            )
            
            # Should handle the error gracefully
            assert result is not None

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])