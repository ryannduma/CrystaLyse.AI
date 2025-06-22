#!/usr/bin/env python3
"""
Simple test to verify tool calling is working.
"""

import asyncio
import sys
import time
from pathlib import Path

# Add paths
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

async def test_simple_smact_call():
    """Test direct SMACT validation call."""
    print("🧪 Testing Simple SMACT Tool Call")
    print("=" * 40)
    
    try:
        from crystalyse.agents.unified_agent import CrystaLyse, AgentConfig
        
        # Minimal configuration
        config = AgentConfig(
            mode="rigorous", 
            max_turns=2,
            enable_smact=True,
            enable_chemeleon=False, 
            enable_mace=False
        )
        agent = CrystaLyse(agent_config=config)
        
        # Very direct query
        query = "Use SMACT tools to validate LiFePO4"
        
        print(f"Query: {query}")
        print("Running agent...")
        
        start_time = time.time()
        result = await agent.discover_materials(query)
        elapsed = time.time() - start_time
        
        print(f"\n✅ Completed in {elapsed:.1f}s")
        print(f"Status: {result.get('status')}")
        
        # Check tool usage
        tool_validation = result.get('tool_validation', {})
        tools_called = tool_validation.get('tools_called', 0)
        tools_used = tool_validation.get('tools_used', [])
        smact_used = tool_validation.get('smact_used', False)
        
        print(f"Tools called: {tools_called}")
        print(f"Tools used: {tools_used}")
        print(f"SMACT used: {smact_used}")
        
        # Check for hallucination
        potential_hallucination = tool_validation.get('potential_hallucination', False)
        print(f"Potential hallucination: {potential_hallucination}")
        
        # Response analysis
        response = result.get('discovery_result', '')
        if response:
            print(f"\nResponse preview: {response[:200]}...")
            
            # Look for validation results
            validation_indicators = [
                'valid' in response.lower(),
                'confidence' in response.lower(),
                'smact' in response.lower(),
                any(x in response for x in ['0.9', '95%', 'charge', 'electronegativity'])
            ]
            print(f"Validation indicators: {sum(validation_indicators)}/4")
        
        # Success assessment
        if tools_called > 0 and smact_used:
            print("\n🎉 SUCCESS: SMACT tools are being called!")
            return True
        elif not potential_hallucination and 'valid' in response.lower():
            print("\n⚠️  UNCLEAR: Response looks realistic but no tool calls detected")
            return False
        else:
            print("\n❌ FAILURE: No tools called or clear hallucination")
            return False
            
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_tool_listing():
    """Test that tools are properly registered."""
    print("\n🔧 Testing Tool Registration")
    print("=" * 40)
    
    try:
        from crystalyse.agents.unified_agent import CrystaLyse, AgentConfig
        
        config = AgentConfig(enable_smact=True)
        agent = CrystaLyse(agent_config=config)
        
        # This should force MCP connection
        query = "What tools are available?"
        result = await agent.discover_materials(query)
        
        print(f"Status: {result.get('status')}")
        
        # Look for tool mentions in response
        response = result.get('discovery_result', '')
        tool_mentions = [
            'smact' in response.lower(),
            'tool' in response.lower(),
            'available' in response.lower(),
            'chemistry' in response.lower()
        ]
        print(f"Tool mentions in response: {sum(tool_mentions)}/4")
        
        return sum(tool_mentions) >= 2
        
    except Exception as e:
        print(f"Tool listing test failed: {e}")
        return False

async def main():
    """Main test execution."""
    print("🚀 SIMPLE TOOL CALL TEST")
    print("=" * 50)
    
    # Test 1: Tool registration
    tools_registered = await test_tool_listing()
    
    # Test 2: Actual SMACT call
    smact_working = await test_simple_smact_call()
    
    # Summary
    print("\n" + "=" * 50)
    print("🎯 TOOL CALL TEST SUMMARY:")
    
    if tools_registered:
        print("✅ Tools appear to be registered")
    else:
        print("❌ Tool registration unclear")
    
    if smact_working:
        print("✅ SMACT tools being called successfully!")
        print("🚀 Ready to test other tools")
    else:
        print("❌ SMACT tools not being called")
        print("🔧 Need to investigate tool calling mechanism")
    
    print("=" * 50)

if __name__ == "__main__":
    asyncio.run(main())