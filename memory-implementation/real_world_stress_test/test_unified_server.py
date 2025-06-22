#!/usr/bin/env python3
"""
Test Chemistry Unified Server connectivity
"""

import asyncio
import sys
from pathlib import Path
import json

# Add path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

async def test_unified_server():
    """Test the unified chemistry server works with CrystaLyse."""
    try:
        from crystalyse.agents.unified_agent import CrystaLyse, AgentConfig
        
        print("🔧 Testing Chemistry Unified Server...")
        print("=" * 60)
        
        # Create agent
        config = AgentConfig(mode="rigorous", max_turns=2)
        agent = CrystaLyse(agent_config=config)
        
        # Test query 1: Simple validation
        print("\n1. Testing SMACT validation through unified server...")
        query = "Validate LiFePO4"
        result = await agent.discover_materials(query)
        
        print(f"Status: {result.get('status')}")
        
        tool_validation = result.get('tool_validation', {})
        print(f"Tools called: {tool_validation.get('tools_called', 0)}")
        print(f"Tools used: {tool_validation.get('tools_used', [])}")
        
        if tool_validation.get('tools_called', 0) > 0:
            print("✅ SUCCESS: Tools were called!")
            
            # Check response
            response = result.get('discovery_result', '')
            print(f"\nResponse preview (first 300 chars):")
            print(f"{response[:300]}...")
        else:
            print("❌ FAILURE: No tools called")
            if tool_validation.get('potential_hallucination'):
                print("🚨 HALLUCINATION DETECTED!")
        
        # Test query 2: Full workflow
        print("\n2. Testing full workflow with multiple tools...")
        query = "Find one stable battery material"
        result = await agent.discover_materials(query)
        
        print(f"Status: {result.get('status')}")
        
        tool_validation = result.get('tool_validation', {})
        print(f"Tools called: {tool_validation.get('tools_called', 0)}")
        print(f"Tools used: {tool_validation.get('tools_used', [])}")
        
        if tool_validation.get('tools_called', 0) > 0:
            print("✅ SUCCESS: Tools were called!")
        else:
            print("❌ FAILURE: No tools called")
        
        print("\n" + "=" * 60)
        
        # Overall conclusion
        if any(result.get('tool_validation', {}).get('tools_called', 0) > 0 for result in [result]):
            print("🎉 UNIFIED SERVER TEST: PASSED!")
            print("The chemistry unified server is working correctly.")
        else:
            print("💥 UNIFIED SERVER TEST: FAILED!")
            print("Tools are not being called through the unified server.")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_unified_server())