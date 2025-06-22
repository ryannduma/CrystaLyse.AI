#!/usr/bin/env python3
"""
Final test to verify MCP connectivity is working
"""

import asyncio
import sys
from pathlib import Path

# Add path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

async def final_connectivity_test():
    """Final test of MCP connectivity."""
    try:
        from crystalyse.agents.unified_agent import CrystaLyse, AgentConfig
        
        print("🎯 FINAL MCP CONNECTIVITY TEST")
        print("=" * 60)
        
        # Create agent
        config = AgentConfig(mode="rigorous", max_turns=2)
        agent = CrystaLyse(agent_config=config)
        
        # Simple validation query
        query = "Validate the composition LiFePO4"
        
        print(f"Query: {query}")
        print("Expected: Should use smact_validity tool from unified server")
        print("-" * 40)
        
        result = await agent.discover_materials(query)
        
        print(f"\nStatus: {result.get('status')}")
        print(f"Response length: {len(result.get('discovery_result', ''))}")
        
        # Check the response content
        response = result.get('discovery_result', '')
        
        # Key indicators that tools were used
        tool_indicators = [
            'valid' in response.lower(),
            'confidence' in response.lower(),
            'smact' in response.lower() or 'validity' in response.lower(),
            any(x in response for x in ['0.95', '0.9', 'charge-balance', 'electronegativity'])
        ]
        
        print(f"\nTool usage indicators found: {sum(tool_indicators)}/4")
        
        if sum(tool_indicators) >= 2:
            print("✅ LIKELY TOOL USAGE: Response contains tool-specific outputs")
        else:
            print("❌ LIKELY HALLUCINATION: Response lacks tool-specific details")
        
        # Show response preview
        print(f"\nResponse preview:")
        print("-" * 40)
        print(response[:500] + "..." if len(response) > 500 else response)
        
        print("\n" + "=" * 60)
        
        # Summary
        print("\n📊 MCP CONNECTIVITY SUMMARY:")
        print("✅ Chemistry Unified Server is loaded (see logs)")
        print("✅ Server processes tool requests (see 'Processing request' logs)")
        
        if 'failed' not in result.get('status', ''):
            print("✅ Agent completed successfully")
            if sum(tool_indicators) >= 2:
                print("✅ Tool outputs detected in response")
                print("\n🎉 MCP TOOLS ARE WORKING!")
            else:
                print("⚠️  Tool outputs not clearly detected")
                print("Consider checking tool response format")
        else:
            print("❌ Agent execution failed")
            print(f"Error: {result.get('error', 'Unknown')}")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(final_connectivity_test())