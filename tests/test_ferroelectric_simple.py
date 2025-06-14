#!/usr/bin/env python3
"""
Simplified ferroelectric materials test focusing on composition and structure.
"""

import asyncio
import sys
import time
from pathlib import Path

# Add the current directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from crystalyse.agents.main_agent import CrystaLyseAgent

async def test_ferroelectric_materials_simple():
    """Test lead-free ferroelectric materials design with SMACT + structure generation only."""
    print("🔬 Lead-Free Ferroelectric Materials Discovery (Simplified)")
    print("=" * 60)
    
    # Set up agent without MACE to avoid integration issues
    agent = CrystaLyseAgent(
        use_chem_tools=True,  # Enable SMACT validation
        enable_mace=False,    # Disable MACE to avoid integration issues
        temperature=0.3       # Analytical precision
    )
    
    # Focused query for ferroelectric materials
    query = """Design lead-free ferroelectric materials for memory devices.

Requirements:
- High spontaneous polarization (> 50 μC/cm²)
- Curie temperature > 300°C
- Lead-free compositions for environmental safety
- Suitable crystal structures for ferroelectric behavior

Please provide 3-5 candidate compositions with:
1. SMACT validation results
2. Crystal structure predictions with space group and lattice parameters
3. Analysis of why these materials should be ferroelectric
4. Synthesis recommendations

Focus on well-known ferroelectric structure types like perovskites, layered structures, and tungsten bronzes."""
    
    print(f"🚀 Starting simplified analysis...")
    start_time = time.time()
    
    try:
        result = await agent.analyze(query)
        duration = time.time() - start_time
        
        print(f"✅ Analysis completed in {duration:.1f} seconds")
        print(f"📊 Result length: {len(result)} characters")
        print()
        print("📋 FERROELECTRIC MATERIALS ANALYSIS RESULTS:")
        print("=" * 70)
        print(result)
        print("=" * 70)
        
        # Save results
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        filename = f"ferroelectric_materials_simple_{timestamp}.txt"
        with open(filename, "w") as f:
            f.write("Lead-Free Ferroelectric Materials Discovery (Simplified)\n")
            f.write("=" * 60 + "\n\n")
            f.write(f"Analysis Duration: {duration:.1f} seconds\n")
            f.write(f"Result Length: {len(result)} characters\n")
            f.write(f"Agent Mode: SMACT + Chemeleon (Structure Generation)\n\n")
            f.write("Results:\n")
            f.write("-" * 30 + "\n")
            f.write(result)
        
        print(f"\n💾 Results saved to: {filename}")
        
        return result
        
    except Exception as e:
        print(f"❌ Analysis failed: {e}")
        import traceback
        traceback.print_exc()
        return None

async def main():
    """Run the simplified ferroelectric materials test."""
    result = await test_ferroelectric_materials_simple()
    return result is not None

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)