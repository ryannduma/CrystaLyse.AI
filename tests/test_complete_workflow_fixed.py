#!/usr/bin/env python3
"""
Complete workflow test: Discovery → Structure → Energy with MACE integration.
"""

import asyncio
import sys
import time
from pathlib import Path

# Add the current directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from crystalyse.agents.main_agent import CrystaLyseAgent

async def test_complete_workflow():
    """Test complete workflow with MACE integration."""
    print("🔬 Complete Workflow Test: Discovery → Structure → Energy")
    print("=" * 60)
    
    # Set up agent with ALL tools enabled
    agent = CrystaLyseAgent(
        use_chem_tools=True,   # Enable SMACT validation
        enable_mace=True,      # Enable MACE energy calculations
        temperature=0.3        # Analytical precision
    )
    
    # Focused query for one ferroelectric material
    query = """Design and analyze lead-free ferroelectric materials.

Target: BaTiO3 (barium titanate) - a well-known ferroelectric perovskite

Requirements:
1. Validate composition using SMACT
2. Generate crystal structure using Chemeleon
3. Calculate energy and formation energy using MACE
4. Assess stability and synthesizability

Please follow the complete workflow:
1. SMACT validation of BaTiO3
2. Generate 1-2 crystal structures
3. For each structure, extract the correct structure data and calculate:
   - Energy with uncertainty using MACE
   - Formation energy for stability assessment
4. Provide synthesis recommendations

Keep the analysis focused on BaTiO3 only to avoid hitting turn limits."""
    
    print(f"🚀 Starting complete workflow analysis...")
    start_time = time.time()
    
    try:
        result = await agent.analyze(query)
        duration = time.time() - start_time
        
        print(f"✅ Analysis completed in {duration:.1f} seconds")
        print(f"📊 Result length: {len(result)} characters")
        print()
        print("📋 COMPLETE WORKFLOW RESULTS:")
        print("=" * 70)
        print(result)
        print("=" * 70)
        
        # Save results
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        filename = f"complete_workflow_test_{timestamp}.txt"
        with open(filename, "w") as f:
            f.write("Complete Workflow Test: Discovery → Structure → Energy\n")
            f.write("=" * 60 + "\n\n")
            f.write(f"Analysis Duration: {duration:.1f} seconds\n")
            f.write(f"Result Length: {len(result)} characters\n")
            f.write(f"Agent Mode: SMACT + Chemeleon + MACE (Full Integration)\n\n")
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
    """Run the complete workflow test."""
    result = await test_complete_workflow()
    return result is not None

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)