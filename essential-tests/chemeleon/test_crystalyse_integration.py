#!/usr/bin/env python3
"""Test integration between Chemeleon and CrystaLyse agents."""

import pytest
import asyncio
import sys
import os
from pathlib import Path

# Add paths
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "openai-agents-python" / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from agents import Agent, Runner
from agents.mcp import MCPServerStdio

class TestCrystaLyseIntegration:
    """Test integration of Chemeleon with CrystaLyse system."""
    
    @pytest.fixture
    def chemeleon_server_params(self):
        """Get Chemeleon server parameters."""
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
    
    @pytest.fixture
    def smact_server_params(self):
        """Get SMACT server parameters."""
        smact_src = Path(__file__).parent.parent.parent / "smact-mcp-server" / "src"
        smact_lib = Path(__file__).parent.parent.parent / "smact"
        
        return {
            "command": sys.executable,
            "args": ["-m", "smact_mcp"],
            "env": {
                **os.environ,
                "PYTHONPATH": f"{smact_src}:{smact_lib}"
            }
        }
    
    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_dual_server_connection(self, chemeleon_server_params, smact_server_params):
        """Test connecting to both Chemeleon and SMACT servers."""
        async with MCPServerStdio(
            name="Chemeleon CSP",
            params=chemeleon_server_params
        ) as chemeleon_server, MCPServerStdio(
            name="SMACT Materials",
            params=smact_server_params
        ) as smact_server:
            
            agent = Agent(
                name="CrystaLyse Agent",
                instructions="You have access to both Chemeleon and SMACT tools.",
                mcp_servers=[chemeleon_server, smact_server]
            )
            
            # Both servers should be connected
            assert agent is not None
    
    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_generate_and_validate_workflow(self, chemeleon_server_params, smact_server_params):
        """Test workflow: generate with Chemeleon, validate with SMACT."""
        async with MCPServerStdio(
            name="Chemeleon CSP",
            params=chemeleon_server_params
        ) as chemeleon_server, MCPServerStdio(
            name="SMACT Materials",
            params=smact_server_params
        ) as smact_server:
            
            agent = Agent(
                name="Materials Discovery Agent",
                instructions="""You are a materials discovery expert with access to:
                - Chemeleon for crystal structure generation
                - SMACT for composition validation
                
                When asked about materials, use both tools appropriately.""",
                mcp_servers=[chemeleon_server, smact_server]
            )
            
            result = await Runner.run(
                starting_agent=agent,
                input="""First check if Li2MnO3 is a valid composition using SMACT,
                then if valid, generate its crystal structure using Chemeleon."""
            )
            
            assert result is not None
            # Should use both tools
            assert "Li2MnO3" in result
    
    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_novel_materials_discovery(self, chemeleon_server_params):
        """Test novel materials discovery with Chemeleon alone."""
        async with MCPServerStdio(
            name="Chemeleon CSP",
            params=chemeleon_server_params
        ) as server:
            
            agent = Agent(
                name="Novel Materials Agent",
                instructions="""You are an expert in discovering novel materials.
                Use Chemeleon's DNG capability to generate new structures and analyze them.""",
                mcp_servers=[server]
            )
            
            result = await Runner.run(
                starting_agent=agent,
                input="""Generate 2 novel crystal structures with 12 atoms each,
                then analyze their symmetries."""
            )
            
            assert result is not None
            # Should mention generation and analysis
            assert "structure" in result.lower()
    
    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_materials_comparison(self, chemeleon_server_params):
        """Test comparing multiple materials."""
        async with MCPServerStdio(
            name="Chemeleon CSP",
            params=chemeleon_server_params
        ) as server:
            
            agent = Agent(
                name="Materials Comparison Agent",
                instructions="""You are an expert in materials analysis.
                Generate and compare crystal structures, focusing on their properties.""",
                mcp_servers=[server]
            )
            
            result = await Runner.run(
                starting_agent=agent,
                input="""Generate crystal structures for TiO2 and SnO2,
                analyze both, and compare their lattice parameters and densities."""
            )
            
            assert result is not None
            # Should mention both materials
            assert "TiO2" in result and "SnO2" in result
    
    @pytest.mark.asyncio
    async def test_error_recovery(self, chemeleon_server_params):
        """Test that the system handles errors gracefully."""
        async with MCPServerStdio(
            name="Chemeleon CSP",
            params=chemeleon_server_params
        ) as server:
            
            agent = Agent(
                name="Test Agent",
                instructions="Generate crystal structures as requested.",
                mcp_servers=[server]
            )
            
            # Mix valid and invalid requests
            result = await Runner.run(
                starting_agent=agent,
                input="""Try to generate structures for:
                1. NaCl (valid)
                2. InvalidFormula123 (invalid)
                3. SiO2 (valid)
                Report what worked and what didn't."""
            )
            
            assert result is not None
            # Should handle both successes and failures
            assert "NaCl" in result and "SiO2" in result

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])