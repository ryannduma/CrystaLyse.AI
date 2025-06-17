#!/usr/bin/env python3
"""
Simple CrystaLyse.AI Query Script
Usage: python simple_query.py "your query here" [mode]
"""

import asyncio
import sys
from crystalyse.unified_agent import CrystaLyseUnifiedAgent, AgentConfig

async def query_agent(query_text, mode="rigorous"):
    """Query the CrystaLyse.AI agent"""
    
    print(f"🔬 CrystaLyse.AI {mode.upper()} Mode")
    print(f"❓ Query: {query_text}")
    print("=" * 60)
    
    try:
        # Create agent
        config = AgentConfig(mode=mode)
        agent = CrystaLyseUnifiedAgent(config)
        
        # Run query
        result = await agent.discover_materials(query_text)
        
        # Display results
        print(f"⏱️  Response Time: {result['metrics']['elapsed_time']:.1f}s")
        print(f"🤖 Model Used: {result['metrics']['model']}")
        print(f"📊 Status: {result['status']}")
        print("\n📋 Response:")
        print("-" * 60)
        print(result['discovery_result'])
        print("-" * 60)
        
        return result
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return None

def main():
    # Get command line arguments
    if len(sys.argv) < 2:
        print("Usage: python simple_query.py \"your query here\" [creative|rigorous]")
        print("\nExample queries:")
        print('python simple_query.py "Find lithium battery cathodes" rigorous')
        print('python simple_query.py "Use SMACT to validate NaFePO4" rigorous')
        print('python simple_query.py "Suggest 2D materials" creative')
        return
    
    query = sys.argv[1]
    mode = sys.argv[2] if len(sys.argv) > 2 else "rigorous"
    
    if mode not in ["creative", "rigorous"]:
        print("Mode must be 'creative' or 'rigorous'")
        return
    
    # Run query
    asyncio.run(query_agent(query, mode))

if __name__ == "__main__":
    main()