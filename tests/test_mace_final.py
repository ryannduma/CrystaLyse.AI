#!/usr/bin/env python3
"""
Final MACE integration test with explicit data extraction examples.
"""

import asyncio
import sys
import time
from pathlib import Path

# Add the current directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from crystalyse.agents.main_agent import CrystaLyseAgent

async def test_mace_final():
    """Test complete MACE integration with explicit instructions."""
    print("🔬 Final MACE Integration Test")
    print("=" * 50)
    
    # Set up agent with MACE + Chemeleon only (no SMACT to reduce complexity)
    agent = CrystaLyseAgent(
        use_chem_tools=False,  # Disable SMACT for simplicity
        enable_mace=True,      # Enable MACE energy calculations
        temperature=0.2        # Very focused
    )
    
    # Explicit query with step-by-step instructions
    query = """Please analyze BaTiO3 (barium titanate) using Chemeleon and MACE tools.

STEP 1: Generate crystal structure
Use generate_crystal_csp with formula="BaTiO3" and num_structures=1

STEP 2: Extract structure data correctly
From the Chemeleon result, you will get something like:
{
  "structures": [
    {
      "formula": "BaTiO3", 
      "structure": {
        "numbers": [...],
        "positions": [...],
        "cell": [...],
        "pbc": [...]
      }
    }
  ]
}

STEP 3: Use MACE tools
Extract ONLY the inner "structure" dictionary and use it with MACE:
- calculate_energy_with_uncertainty(structure_dict=structure["structure"])  
- calculate_formation_energy(structure_dict=structure["structure"])

STEP 4: Results
Provide energy, formation energy, and stability assessment.

Please follow these steps exactly and show each tool call result."""
    
    print(f"🚀 Starting final MACE test...")
    start_time = time.time()
    
    try:
        result = await agent.analyze(query)
        duration = time.time() - start_time
        
        print(f"✅ Analysis completed in {duration:.1f} seconds")
        print(f"📊 Result length: {len(result)} characters")
        print()
        print("📋 FINAL MACE TEST RESULTS:")
        print("=" * 60)
        print(result)
        print("=" * 60)
        
        # Save results
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        filename = f"mace_final_test_{timestamp}.txt"
        with open(filename, "w") as f:
            f.write("Final MACE Integration Test Results\n")
            f.write("=" * 50 + "\n\n")
            f.write(f"Analysis Duration: {duration:.1f} seconds\n")
            f.write(f"Result Length: {len(result)} characters\n")
            f.write(f"Agent Mode: Chemeleon + MACE (Explicit Instructions)\n\n")
            f.write("Results:\n")
            f.write("-" * 30 + "\n")
            f.write(result)
        
        print(f"\n💾 Results saved to: {filename}")
        
        # Check if MACE tools were actually used
        if "calculate_energy" in result or "formation_energy" in result:
            print("✅ MACE tools were successfully used!")
            return True
        else:
            print("❌ MACE tools were not used - still having integration issues")
            return False
        
    except Exception as e:
        print(f"❌ Analysis failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Run the final MACE test."""
    success = await test_mace_final()
    if success:
        print("\n🎉 MACE INTEGRATION SUCCESSFUL!")
        print("The complete loop from material discovery → structure → energy is working.")
    else:
        print("\n❌ MACE integration still needs work.")
    return success

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)