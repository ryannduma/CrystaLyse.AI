#!/usr/bin/env python3
"""Test the main CrystaLyse agent with MCP integration."""

import os
import asyncio

# Set up environment
# Verify MDG API key is set
if not os.getenv("OPENAI_MDG_API_KEY"):
    print("❌ OPENAI_MDG_API_KEY not set. Please set this environment variable.")
    sys.exit(1)

from crystalyse.agents.main_agent import CrystaLyseAgent


async def test_main_agent():
    """Test the main CrystaLyse agent with MCP."""
    
    print("Testing Testing CrystaLyse Main Agent with MCP...")
    print("=" * 50)
    
    try:
        # Initialize CrystaLyse agent
        agent = CrystaLyseAgent(model="gpt-4o", temperature=0.3)
        print("SUCCESS CrystaLyse agent initialized!")
        
        # Test query for battery materials
        query = """I need novel cathode materials for lithium-ion batteries. 
        The material should have high energy density and good stability.
        Please use SMACT tools to validate any compositions you propose.
        Provide 3 strong candidates with proper chemical validation."""
        
        print(f"\n🔋 Query: {query}")
        print("\nResults Agent Response:")
        
        # Run analysis
        response = await agent.analyze(query)
        print(response)
        
        print("\nSUCCESS Test completed successfully!")
        
    except Exception as e:
        print(f"ERROR Test Error: {e}")
        import traceback
        traceback.print_exc()


async def main():
    """Main test function."""
    try:
        await test_main_agent()
        print("\n🎉 CrystaLyse main agent test completed!")
    except Exception as e:
        print(f"\nERROR Test failed with error: {e}")


if __name__ == "__main__":
    asyncio.run(main())