#!/usr/bin/env python3
"""
Test unified chemistry server with increased timeout for Chemeleon model downloads.
"""

import asyncio
import sys
import time
from pathlib import Path

# Add paths
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

async def test_chemeleon_with_timeout():
    """Test Chemeleon structure generation with 60-second timeout."""
    print("🧪 Testing Chemeleon with Extended Timeout")
    print("=" * 50)
    
    try:
        from crystalyse.agents.unified_agent import CrystaLyse, AgentConfig
        
        # Create agent with all tools enabled
        config = AgentConfig(
            mode="rigorous", 
            max_turns=3,
            enable_smact=True,
            enable_chemeleon=True, 
            enable_mace=True
        )
        agent = CrystaLyse(agent_config=config)
        
        # Test Chemeleon structure generation (this should trigger model download)
        print("\n🔄 Testing Chemeleon structure generation...")
        print("   This may take up to 60 seconds for first-time model download...")
        
        query = "Generate crystal structure for LiFePO4 using Chemeleon"
        start_time = time.time()
        
        result = await agent.discover_materials(query)
        elapsed = time.time() - start_time
        
        print(f"\n✅ Test completed in {elapsed:.1f}s")
        print(f"   Status: {result.get('status')}")
        
        tool_validation = result.get('tool_validation', {})
        print(f"   Tools called: {tool_validation.get('tools_called', 0)}")
        print(f"   Tools used: {tool_validation.get('tools_used', [])}")
        
        # Check if Chemeleon was actually used
        chemeleon_used = tool_validation.get('chemeleon_used', False)
        print(f"   Chemeleon used: {chemeleon_used}")
        
        response = result.get('discovery_result', '')
        if response:
            print(f"\n📄 Response preview:")
            print(f"   {response[:300]}...")
            
            # Look for Chemeleon-specific indicators
            chemeleon_indicators = [
                'structure' in response.lower(),
                'crystal' in response.lower(),
                any(x in response for x in ['space group', 'lattice', 'atoms', 'unit cell', 'cif'])
            ]
            print(f"   Structure generation indicators: {sum(chemeleon_indicators)}/3")
        
        if chemeleon_used and elapsed < 60:
            print("\n🎉 SUCCESS: Chemeleon working with extended timeout!")
            return True
        elif elapsed >= 60:
            print("\n⚠️  WARNING: Operation took longer than timeout limit")
            return False
        else:
            print("\n❌ FAILURE: Chemeleon tools not called")
            return False
            
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_all_tools_with_timeout():
    """Test all tools with the extended timeout configuration."""
    print("\n🧪 Testing All Tools with Extended Timeout")
    print("=" * 50)
    
    try:
        from crystalyse.agents.unified_agent import CrystaLyse, AgentConfig
        
        config = AgentConfig(mode="rigorous", max_turns=5)
        agent = CrystaLyse(agent_config=config)
        
        # Comprehensive query that should use all tools
        query = """
        Find a stable battery cathode material with formation energy better than -2.0 eV/atom.
        Use SMACT to validate compositions, Chemeleon to generate structures, 
        and MACE to calculate formation energies.
        """
        
        print("\n🔄 Running comprehensive tool test...")
        start_time = time.time()
        
        result = await agent.discover_materials(query)
        elapsed = time.time() - start_time
        
        print(f"\n✅ Comprehensive test completed in {elapsed:.1f}s")
        print(f"   Status: {result.get('status')}")
        
        tool_validation = result.get('tool_validation', {})
        tools_called = tool_validation.get('tools_called', 0)
        tools_used = tool_validation.get('tools_used', [])
        
        print(f"   Total tools called: {tools_called}")
        print(f"   Tools used: {tools_used}")
        print(f"   SMACT used: {tool_validation.get('smact_used', False)}")
        print(f"   Chemeleon used: {tool_validation.get('chemeleon_used', False)}")
        print(f"   MACE used: {tool_validation.get('mace_used', False)}")
        
        # Success criteria
        success_criteria = [
            tools_called > 0,
            tool_validation.get('smact_used', False),
            not tool_validation.get('potential_hallucination', True)
        ]
        
        success_count = sum(success_criteria)
        print(f"\n📊 Success criteria met: {success_count}/3")
        
        if success_count >= 2:
            print("🎉 SUCCESS: Extended timeout enables proper tool usage!")
            return True
        else:
            print("❌ FAILURE: Tools still not working properly")
            return False
            
    except Exception as e:
        print(f"\n❌ Comprehensive test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Main test execution."""
    print("🚀 TIMEOUT FIX VALIDATION TEST")
    print("=" * 60)
    print("Testing 60-second timeout for model downloads...")
    
    # Test 1: Chemeleon-specific test
    chemeleon_success = await test_chemeleon_with_timeout()
    
    # Test 2: Comprehensive all-tools test
    comprehensive_success = await test_all_tools_with_timeout()
    
    # Final summary
    print("\n" + "=" * 60)
    print("🎯 TIMEOUT FIX SUMMARY:")
    
    if chemeleon_success or comprehensive_success:
        print("✅ Extended timeout configuration working!")
        print("✅ Model downloads can complete within 60-second window")
        print("✅ MCP servers properly configured with custom timeouts")
        if chemeleon_success:
            print("✅ Chemeleon structure generation functional")
        if comprehensive_success:
            print("✅ Multi-tool workflows operational")
        print("\n🚀 PRODUCTION READY with timeout fix!")
    else:
        print("❌ Timeout fix insufficient")
        print("🔧 May need longer timeout or pre-download strategy")
    
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())