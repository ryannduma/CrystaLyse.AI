#!/usr/bin/env python3
"""
Simple MACE integration test with manually formatted data.
"""

import asyncio
import sys
import time
from pathlib import Path

# Add the current directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from crystalyse.agents.main_agent import CrystaLyseAgent

async def test_mace_simple():
    """Test MACE with a simple, correctly formatted structure."""
    print("🔬 MACE Simple Integration Test")
    print("=" * 40)
    
    # Set up agent in MACE energy mode only
    agent = CrystaLyseAgent(
        use_chem_tools=False,  # No SMACT
        enable_mace=True,      # Enable MACE only
        energy_focus=True,     # Focus on energy analysis
        temperature=0.3
    )
    
    # Simple query with manual structure
    query = """Please analyze the energy and stability of this BaTiO3 structure:

Structure data (in correct MACE format):
{
  "numbers": [56, 22, 8, 8, 8],
  "positions": [
    [0.0, 0.0, 0.0],
    [2.0, 2.0, 2.0], 
    [2.0, 2.0, 0.0],
    [2.0, 0.0, 2.0],
    [0.0, 2.0, 2.0]
  ],
  "cell": [
    [4.0, 0.0, 0.0],
    [0.0, 4.0, 0.0],
    [0.0, 0.0, 4.0]
  ],
  "pbc": [true, true, true]
}

Please use MACE tools to:
1. Calculate energy with uncertainty
2. Calculate formation energy
3. Assess stability

Focus only on energy analysis."""
    
    print(f"🚀 Starting MACE energy analysis...")
    start_time = time.time()
    
    try:
        result = await agent.analyze(query)
        duration = time.time() - start_time
        
        print(f"✅ Analysis completed in {duration:.1f} seconds")
        print(f"📊 Result length: {len(result)} characters")
        print()
        print("📋 MACE ENERGY ANALYSIS RESULTS:")
        print("=" * 50)
        print(result)
        print("=" * 50)
        
        # Save results
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        filename = f"mace_simple_test_{timestamp}.txt"
        with open(filename, "w") as f:
            f.write("MACE Simple Integration Test Results\n")
            f.write("=" * 40 + "\n\n")
            f.write(f"Analysis Duration: {duration:.1f} seconds\n")
            f.write(f"Result Length: {len(result)} characters\n\n")
            f.write("Results:\n")
            f.write("-" * 20 + "\n")
            f.write(result)
        
        print(f"\n💾 Results saved to: {filename}")
        return result
        
    except Exception as e:
        print(f"❌ Analysis failed: {e}")
        import traceback
        traceback.print_exc()
        return None

async def main():
    """Run the simple MACE test."""
    result = await test_mace_simple()
    return result is not None

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)