#!/usr/bin/env python3
"""
Quick test for rigor mode functionality that avoids rate limits.
"""

import asyncio
import sys
import os
import time
from pathlib import Path

# Add the current directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from crystalyse.agents.main_agent import CrystaLyseAgent

async def test_basic_functionality():
    """Test basic agent setup and configuration."""
    print("🔧 Testing Basic Agent Setup...")
    
    agent = CrystaLyseAgent(
        use_chem_tools=True,
        enable_mace=True,
        temperature=0.3
    )
    
    config = agent.get_agent_configuration()
    print(f"✓ Agent mode: {config['integration_mode']}")
    
    # Check all required capabilities
    capabilities = config['capabilities']
    required = ['composition_validation', 'energy_analysis', 'crystal_structure_generation', 'multi_fidelity_routing']
    
    for capability in required:
        if capabilities.get(capability, False):
            print(f"✓ {capability}: enabled")
        else:
            print(f"✗ {capability}: disabled")
            return False
    
    return True

async def test_simple_analysis():
    """Test a very simple analysis to verify MCP connections work."""
    print("\n🧪 Testing Simple Analysis...")
    
    agent = CrystaLyseAgent(
        use_chem_tools=False,  # Start simple without SMACT
        enable_mace=False,     # Without MACE to avoid complexity
        temperature=0.3
    )
    
    # Very simple query to test basic functionality
    simple_query = "Predict the crystal structure of BaTiO3 for ferroelectric applications. Keep the response brief."
    
    try:
        start_time = time.time()
        result = await agent.analyze(simple_query)
        duration = time.time() - start_time
        
        print(f"✓ Analysis completed in {duration:.1f}s")
        print(f"✓ Result length: {len(result)} characters")
        
        # Basic validation
        if isinstance(result, str) and len(result) > 50:
            print("✓ Valid result received")
            return True
        else:
            print("✗ Invalid result")
            return False
            
    except Exception as e:
        print(f"✗ Analysis failed: {e}")
        return False

async def test_method_existence():
    """Test that all consolidated methods exist."""
    print("\n🛠️ Testing Consolidated Methods...")
    
    agent = CrystaLyseAgent(use_chem_tools=True, enable_mace=True)
    
    methods = [
        'predict_structures',
        'validate_compositions', 
        'energy_analysis',
        'batch_screening',
        'get_agent_configuration'
    ]
    
    for method in methods:
        if hasattr(agent, method):
            print(f"✓ {method}: exists")
        else:
            print(f"✗ {method}: missing")
            return False
    
    return True

async def main():
    """Run quick tests."""
    print("🧪 CrystaLyse.AI Quick Rigor Mode Test")
    print("=" * 45)
    
    tests = [
        ("Basic Functionality", test_basic_functionality),
        ("Method Existence", test_method_existence),
        ("Simple Analysis", test_simple_analysis)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n🚀 Running: {test_name}")
        try:
            if await test_func():
                passed += 1
                print(f"✅ {test_name}: PASSED")
            else:
                print(f"❌ {test_name}: FAILED")
        except Exception as e:
            print(f"❌ {test_name}: ERROR - {e}")
    
    print(f"\n📊 RESULTS: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Consolidated agent is working correctly.")
        return True
    else:
        print("⚠️ Some tests failed. Check MCP server configuration.")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)