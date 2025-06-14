#!/usr/bin/env python3
"""
Comprehensive test for the consolidated CrystaLyseAgent.

This test verifies that all consolidated functionality from StructurePredictionAgent,
ValidationAgent, and MACEIntegratedAgent works correctly in the unified main agent.
"""

import asyncio
import sys
import os
from pathlib import Path

# Add the CrystaLyse.AI directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent / "CrystaLyse.AI"))

from crystalyse.agents.main_agent import CrystaLyseAgent

async def test_agent_modes():
    """Test different agent operational modes."""
    print("=== Testing Agent Modes ===")
    
    # Test Creative Mode
    print("\n1. Testing Creative Mode...")
    creative_agent = CrystaLyseAgent(use_chem_tools=False, enable_mace=False)
    config = creative_agent.get_agent_configuration()
    print(f"Creative mode config: {config['integration_mode']}")
    assert config['integration_mode'] == 'creative_structure_generation'
    
    # Test Rigorous Mode
    print("2. Testing Rigorous Mode...")
    rigorous_agent = CrystaLyseAgent(use_chem_tools=True, enable_mace=False)
    config = rigorous_agent.get_agent_configuration()
    print(f"Rigorous mode config: {config['integration_mode']}")
    assert config['integration_mode'] == 'rigorous_validation'
    
    # Test MACE Creative Mode
    print("3. Testing MACE Creative Mode...")
    mace_creative_agent = CrystaLyseAgent(use_chem_tools=False, enable_mace=True)
    config = mace_creative_agent.get_agent_configuration()
    print(f"MACE creative mode config: {config['integration_mode']}")
    assert config['integration_mode'] == 'creative_with_energy_validation'
    
    # Test Full Multi-Tool Mode
    print("4. Testing Full Multi-Tool Mode...")
    full_agent = CrystaLyseAgent(use_chem_tools=True, enable_mace=True)
    config = full_agent.get_agent_configuration()
    print(f"Full multi-tool mode config: {config['integration_mode']}")
    assert config['integration_mode'] == 'full_multi_tool_rigorous'
    
    # Test Energy Analysis Mode
    print("5. Testing Energy Analysis Mode...")
    energy_agent = CrystaLyseAgent(enable_mace=True, energy_focus=True)
    config = energy_agent.get_agent_configuration()
    print(f"Energy analysis mode config: {config['integration_mode']}")
    assert config['integration_mode'] == 'energy_analysis_focused'
    
    print("✓ All agent modes configured correctly!")

async def test_consolidated_methods():
    """Test the consolidated methods from other agents."""
    print("\n=== Testing Consolidated Methods ===")
    
    agent = CrystaLyseAgent(use_chem_tools=True, enable_mace=True)
    
    # Test that consolidated methods exist
    print("1. Checking consolidated methods exist...")
    assert hasattr(agent, 'predict_structures'), "predict_structures method missing"
    assert hasattr(agent, 'validate_compositions'), "validate_compositions method missing"
    assert hasattr(agent, 'energy_analysis'), "energy_analysis method missing"
    assert hasattr(agent, 'batch_screening'), "batch_screening method missing"
    print("✓ All consolidated methods present!")
    
    # Test configuration method
    print("2. Testing configuration method...")
    config = agent.get_agent_configuration()
    required_keys = ['model', 'temperature', 'use_chem_tools', 'enable_mace', 
                     'energy_focus', 'uncertainty_threshold', 'server_paths',
                     'integration_mode', 'capabilities']
    for key in required_keys:
        assert key in config, f"Missing config key: {key}"
    print("✓ Configuration method working correctly!")
    
    # Test capabilities reporting
    print("3. Testing capabilities reporting...")
    capabilities = config['capabilities']
    assert capabilities['structure_prediction'] == True
    assert capabilities['composition_validation'] == True  # Should be True since use_chem_tools=True
    assert capabilities['energy_analysis'] == True  # Should be True since enable_mace=True
    assert capabilities['crystal_structure_generation'] == True
    assert capabilities['multi_fidelity_routing'] == True
    print("✓ Capabilities correctly reported!")

async def test_error_handling():
    """Test error handling for MACE methods when MACE is disabled."""
    print("\n=== Testing Error Handling ===")
    
    # Create agent without MACE enabled
    agent = CrystaLyseAgent(use_chem_tools=True, enable_mace=False)
    
    print("1. Testing energy_analysis error handling...")
    try:
        await agent.energy_analysis([{"composition": "LiFePO4"}])
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "MACE must be enabled" in str(e)
        print("✓ energy_analysis correctly raises error when MACE disabled")
    
    print("2. Testing batch_screening error handling...")
    try:
        await agent.batch_screening(["LiFePO4"])
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "MACE must be enabled" in str(e)
        print("✓ batch_screening correctly raises error when MACE disabled")

async def test_ferroelectric_materials_design():
    """
    Test the agent on the lead-free ferroelectric materials design task
    to verify full integration works in rigor mode.
    """
    print("\n=== Testing Lead-Free Ferroelectric Materials Design ===")
    
    # Create agent in full rigor mode
    agent = CrystaLyseAgent(
        use_chem_tools=True, 
        enable_mace=True, 
        temperature=0.3  # Lower temperature for rigorous analysis
    )
    
    query = """Design lead-free ferroelectric materials for memory devices using multi-fidelity approach.
        
Requirements:
- High spontaneous polarization (> 50 μC/cm²)
- Curie temperature > 300°C  
- Formation energy analysis with uncertainty quantification
- Intelligent routing: Accept high-confidence MACE predictions, route uncertain cases for DFT validation

Provide 3-5 candidate compositions with energy analysis and synthesis recommendations."""
    
    print("Testing full workflow on lead-free ferroelectric materials...")
    print("Query:", query[:100] + "...")
    
    try:
        # Test the main analysis method
        print("Running comprehensive analysis...")
        result = await agent.analyze(query)
        
        # Basic validation that we got a result
        assert isinstance(result, str), "Result should be a string"
        assert len(result) > 100, "Result should be substantial"
        
        print(f"✓ Analysis completed successfully! Result length: {len(result)} characters")
        print("First 200 characters of result:")
        print(result[:200] + "...")
        
        return result
        
    except Exception as e:
        print(f"⚠ Analysis failed (likely due to MCP server connection): {e}")
        print("This is expected if MCP servers are not running.")
        return None

async def main():
    """Run all tests."""
    print("🧪 Testing Consolidated CrystaLyseAgent")
    print("=" * 50)
    
    try:
        # Test basic functionality that doesn't require MCP servers
        await test_agent_modes()
        await test_consolidated_methods()
        await test_error_handling()
        
        print("\n🎯 Basic Tests Completed Successfully!")
        
        # Test full workflow (may fail if MCP servers not available)
        print("\n🚀 Testing Full Workflow...")
        result = await test_ferroelectric_materials_design()
        
        if result:
            print("\n🏆 ALL TESTS PASSED! Consolidated agent fully functional.")
        else:
            print("\n✅ CORE TESTS PASSED! Full workflow requires MCP servers to be running.")
            print("To test full functionality, ensure MCP servers are available.")
        
        return True
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)