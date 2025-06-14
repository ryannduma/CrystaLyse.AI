#!/usr/bin/env python3
"""
Focused test for lead-free ferroelectric materials discovery.
"""

import asyncio
import sys
import time
from pathlib import Path

# Add the current directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from crystalyse.agents.main_agent import CrystaLyseAgent

async def test_ferroelectric_materials():
    """Test lead-free ferroelectric materials design."""
    print("🔬 Lead-Free Ferroelectric Materials Discovery")
    print("=" * 50)
    
    # Set up agent in full rigor mode
    agent = CrystaLyseAgent(
        use_chem_tools=True,  # Enable SMACT validation
        enable_mace=True,     # Enable MACE energy calculations
        temperature=0.3       # Analytical precision
    )
    
    # Focused query for ferroelectric materials
    query = """Design lead-free ferroelectric materials for memory devices.

Requirements:
- High spontaneous polarization (> 50 μC/cm²)
- Curie temperature > 300°C
- Lead-free compositions
- Formation energy analysis

Please provide 3 candidate compositions with:
1. SMACT validation
2. Crystal structure prediction
3. Formation energy analysis
4. Synthesis recommendations

Keep analysis focused and concise."""
    
    print(f"🚀 Starting analysis...")
    start_time = time.time()
    
    try:
        result = await agent.analyze(query)
        duration = time.time() - start_time
        
        print(f"✅ Analysis completed in {duration:.1f} seconds")
        print(f"📊 Result length: {len(result)} characters")
        print()
        print("📋 FERROELECTRIC MATERIALS ANALYSIS RESULTS:")
        print("=" * 60)
        print(result)
        print("=" * 60)
        
        # Save results
        with open("ferroelectric_materials_analysis.txt", "w") as f:
            f.write("Lead-Free Ferroelectric Materials Discovery Results\n")
            f.write("=" * 50 + "\n\n")
            f.write(f"Analysis Duration: {duration:.1f} seconds\n")
            f.write(f"Result Length: {len(result)} characters\n\n")
            f.write("Results:\n")
            f.write("-" * 20 + "\n")
            f.write(result)
        
        print(f"\n💾 Results saved to: ferroelectric_materials_analysis.txt")
        
        return result
        
    except Exception as e:
        print(f"❌ Analysis failed: {e}")
        return None

async def main():
    """Run the ferroelectric materials test."""
    result = await test_ferroelectric_materials()
    return result is not None

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)