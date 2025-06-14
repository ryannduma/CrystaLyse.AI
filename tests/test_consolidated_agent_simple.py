#!/usr/bin/env python3
"""
Simple test for the consolidated CrystaLyseAgent without MCP server dependencies.
"""

import sys
import os
from pathlib import Path

# Add the CrystaLyse.AI directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent / "CrystaLyse.AI"))

def test_agent_modes():
    """Test different agent operational modes."""
    print("=== Testing Agent Modes ===")
    
    from crystalyse.agents.main_agent import CrystaLyseAgent
    
    # Test Creative Mode
    print("1. Testing Creative Mode...")
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

def test_consolidated_methods():
    """Test the consolidated methods from other agents."""
    print("\n=== Testing Consolidated Methods ===")
    
    from crystalyse.agents.main_agent import CrystaLyseAgent
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

def main():
    """Run all tests."""
    print("🧪 Testing Consolidated CrystaLyseAgent (Simple Mode)")
    print("=" * 50)
    
    try:
        # Test basic functionality that doesn't require MCP servers
        test_agent_modes()
        test_consolidated_methods()
        
        print("\n🏆 ALL TESTS PASSED! Consolidated agent core functionality verified.")
        print("Note: Full workflow testing requires MCP servers to be running.")
        
        return True
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)