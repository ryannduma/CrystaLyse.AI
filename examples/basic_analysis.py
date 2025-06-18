"""Basic example of using CrystaLyse Unified Agent for materials discovery."""

import asyncio
import os
from crystalyse import CrystaLyse, AgentConfig


async def main():
    """Run basic material discovery examples using the unified agent."""
    
    # Check for OpenAI API key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("Error: OPENAI_API_KEY environment variable not set!")
        print("Set it with: export OPENAI_API_KEY='your-api-key'")
        return
        
    print("🔬 CrystaLyse.AI Unified Agent - Basic Examples")
    print("=" * 50)
    
    # Example 1: Creative mode for innovative exploration
    print("\n1. Creative Mode - Innovative Battery Materials")
    creative_config = AgentConfig(
        model="o4-mini",
        mode="creative",
        temperature=0.8,
        enable_smact=False,  # Knowledge-based only
        enable_chemeleon=False,
        enable_mace=False
    )
    
    creative_agent = CrystaLyse(creative_config)
    
    query1 = "Design an innovative solid-state electrolyte for sodium-ion batteries"
    print(f"Query: {query1}")
    
    result1 = await creative_agent.discover_materials(query1)
    if result1.get('status') == 'completed':
        print("✅ Success!")
        print(f"Analysis: {result1['discovery_result'][:200]}...")
    else:
        print(f"❌ Error: {result1.get('error', 'Unknown error')}")
    
    # Example 2: Rigorous mode for systematic analysis
    print("\n\n2. Rigorous Mode - Systematic Solar Cell Materials")
    rigorous_config = AgentConfig(
        model="o4-mini", 
        mode="rigorous",
        temperature=0.3,
        enable_smact=False,  # Would enable SMACT if MCP servers configured
        enable_chemeleon=False,
        enable_mace=False
    )
    
    rigorous_agent = CrystaLyse(rigorous_config)
    
    query2 = "Find lead-free perovskite materials for solar cell applications"
    print(f"Query: {query2}")
    
    result2 = await rigorous_agent.discover_materials(query2)
    if result2.get('status') == 'completed':
        print("✅ Success!")
        print(f"Analysis: {result2['discovery_result'][:200]}...")
        
        # Show metrics
        metrics = result2.get('metrics', {})
        print(f"\n📊 Performance: {metrics.get('elapsed_time', 0):.1f}s using {metrics.get('model', 'unknown')}")
    else:
        print(f"❌ Error: {result2.get('error', 'Unknown error')}")

    print("\n" + "=" * 50)
    print("🎯 Examples completed!")
    print("\nTo enable full computational workflow:")
    print("• Set up MCP servers (SMACT, Chemeleon, MACE)")
    print("• Enable tools in AgentConfig")
    print("• Get composition validation, structure generation, and energy calculations")


if __name__ == "__main__":
    asyncio.run(main())