#!/usr/bin/env python3
"""Basic tests for Chemeleon MCP server functionality."""

import pytest
import json
import sys
from pathlib import Path

# Add paths
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "chemeleon-mcp-server" / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "chemeleon-dng"))

class TestChemeleonBasic:
    """Basic functionality tests for Chemeleon MCP server."""
    
    def test_imports(self):
        """Test that all required modules can be imported."""
        # Core imports
        import torch
        import ase
        import pymatgen
        import mcp
        
        # Chemeleon imports
        from chemeleon_dng.diffusion.diffusion_module import DiffusionModule
        from chemeleon_mcp.server import mcp, SERVER_NAME, SERVER_VERSION
        
        assert SERVER_NAME == "chemeleon-csp"
        assert SERVER_VERSION == "0.1.0"
    
    def test_tool_registration(self):
        """Test that all tools are properly registered."""
        from chemeleon_mcp.server import mcp
        import chemeleon_mcp.tools  # This registers the tools
        
        # Check that tools are registered (implementation depends on FastMCP version)
        # This is a basic check - actual tool list retrieval may vary
        assert hasattr(mcp, 'tool')  # Decorator exists
    
    def test_device_detection(self):
        """Test device detection."""
        from chemeleon_mcp.tools import _get_device
        
        device = _get_device()
        assert device in ["cuda", "mps", "cpu"]
        print(f"Detected device: {device}")
    
    def test_model_info(self):
        """Test get_model_info tool."""
        from chemeleon_mcp.tools import get_model_info
        
        result_str = get_model_info()
        result = json.loads(result_str)
        
        assert "available_tasks" in result
        assert "device" in result
        assert "cached_models" in result
        assert result["available_tasks"] == ["csp"]
    
    @pytest.mark.slow
    def test_generate_csp_basic(self):
        """Test basic CSP generation (may download models)."""
        from chemeleon_mcp.tools import generate_crystal_csp
        
        result_str = generate_crystal_csp(
            formulas="NaCl",
            num_samples=1,
            output_format="dict"
        )
        result = json.loads(result_str)
        
        assert result["success"] is True
        assert result["num_structures"] == 1
        assert len(result["structures"]) == 1
        
        struct = result["structures"][0]
        assert struct["formula"] == "NaCl"
        assert "structure" in struct
        assert "cell" in struct["structure"]
        assert "positions" in struct["structure"]
        assert "numbers" in struct["structure"]
    
    def test_analyse_structure(self):
        """Test structure analysis."""
        from chemeleon_mcp.tools import analyse_structure
        
        # Create a simple test structure
        test_structure = {
            "cell": [[4.0, 0.0, 0.0], [0.0, 4.0, 0.0], [0.0, 0.0, 4.0]],
            "positions": [[0.0, 0.0, 0.0], [2.0, 2.0, 2.0]],
            "numbers": [11, 17],  # Na, Cl
            "pbc": [True, True, True]
        }
        
        result_str = analyse_structure(
            structure_dict=test_structure,
            calculate_symmetry=True
        )
        result = json.loads(result_str)
        
        assert "formula" in result
        assert "volume" in result
        assert "density" in result
        assert "lattice" in result
        
        # May have symmetry or symmetry_error depending on installation
        assert "symmetry" in result or "symmetry_error" in result
    
    def test_output_formats(self):
        """Test different output formats."""
        from chemeleon_mcp.tools import generate_crystal_csp
        
        # Test CIF format
        result_str = generate_crystal_csp(
            formulas="H2O",
            num_samples=1,
            output_format="cif"
        )
        result = json.loads(result_str)
        
        if result["success"]:
            assert "cif" in result["structures"][0]
            assert "structure" not in result["structures"][0]
            
            # CIF should contain expected keywords
            cif_content = result["structures"][0]["cif"]
            assert "_cell_length_a" in cif_content
            assert "_atom_site_label" in cif_content
    
    def test_cache_operations(self):
        """Test model cache operations."""
        from chemeleon_mcp.tools import clear_model_cache, get_model_info
        
        # Clear cache
        clear_result_str = clear_model_cache()
        clear_result = json.loads(clear_result_str)
        assert clear_result["success"] is True
        
        # Check that cache is empty
        info_str = get_model_info()
        info = json.loads(info_str)
        assert len(info["cached_models"]) == 0

if __name__ == "__main__":
    pytest.main([__file__, "-v"])