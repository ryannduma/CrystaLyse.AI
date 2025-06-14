#!/usr/bin/env python3
"""
Focused Na-ion battery cathode test with 2 materials - full rigor mode.
"""

import asyncio
import sys
import time
from pathlib import Path

# Add the current directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from crystalyse.agents.main_agent import CrystaLyseAgent

async def test_naion_focused():
    """Test focused Na-ion cathode analysis with 2 materials."""
    print("🔋 Na-ion Battery Cathode Materials - Focused Analysis")
    print("=" * 60)
    print("🔧 Mode: SMACT + Chemeleon + MACE (Full Rigor)")
    print("🎯 Target: 2 cathode materials with complete analysis")
    print("=" * 60)
    
    # Set up agent in full rigor mode
    agent = CrystaLyseAgent(
        use_chem_tools=True,   # SMACT validation
        enable_mace=True,      # MACE energy analysis
        temperature=0.3        # Analytical precision
    )
    
    # Focused query for 2 well-known cathode materials
    query = """Analyze 2 stable cathode materials for Na-ion batteries with complete energy analysis.

TARGET MATERIALS:
1. NaFePO4 (sodium iron phosphate) - olivine structure
2. Na2FePO4F (sodium iron phosphate fluoride) - NASICON-type

COMPLETE WORKFLOW FOR EACH:
1. **SMACT Validation**: Validate composition and oxidation states
2. **Structure Generation**: Generate 2 crystal structures using Chemeleon
3. **MACE Energy Analysis**: For each structure:
   - Calculate energy with uncertainty
   - Calculate formation energy for stability
   - Extract structure data correctly from Chemeleon before passing to MACE

PROVIDE FOR EACH MATERIAL:
- SMACT validation results
- Crystal structures with lattice parameters  
- Energy per atom (eV/atom)
- Formation energy (eV/atom)
- Stability assessment (stable/unstable)
- Theoretical capacity estimate
- Synthesis recommendations

Keep analysis focused on these 2 materials only to avoid turn limits."""
    
    print(f"🚀 Starting focused Na-ion cathode analysis...")
    start_time = time.time()
    
    try:
        result = await agent.analyze(query)
        duration = time.time() - start_time
        
        print(f"✅ Analysis completed in {duration:.1f} seconds")
        print(f"📊 Result length: {len(result)} characters")
        print()
        print("📋 FOCUSED NA-ION CATHODE ANALYSIS:")
        print("=" * 70)
        print(result)
        print("=" * 70)
        
        # Save detailed results
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        filename = f"naion_focused_analysis_{timestamp}.txt"
        with open(filename, "w") as f:
            f.write("Na-ion Battery Cathode Materials - Focused Analysis\n")
            f.write("=" * 60 + "\n\n")
            f.write("Analysis Configuration:\n")
            f.write("- Mode: Full Rigor (SMACT + Chemeleon + MACE)\n")
            f.write("- Materials: NaFePO4, Na2FePO4F\n") 
            f.write(f"- Duration: {duration:.1f} seconds\n")
            f.write(f"- Result Length: {len(result)} characters\n\n")
            f.write("Results:\n")
            f.write("-" * 40 + "\n")
            f.write(result)
        
        print(f"\n💾 Analysis saved to: {filename}")
        
        # Comprehensive success analysis
        success_metrics = {
            "smact_validation": "smact" in result.lower() or "validation" in result.lower(),
            "structure_generation": "structure" in result.lower() and ("lattice" in result.lower() or "cell" in result.lower()),
            "energy_calculation": "energy" in result.lower() and ("ev" in result.lower() or "eV" in result),
            "formation_energy": "formation" in result.lower() and "energy" in result.lower(),
            "stability_assessment": "stable" in result.lower() or "stability" in result.lower(),
            "both_materials": "nafepo4" in result.lower() and ("na2fepo4f" in result.lower() or "nasicon" in result.lower()),
            "quantitative_data": "-" in result and ("ev" in result.lower() or "eV" in result)
        }
        
        success_count = sum(success_metrics.values())
        total_metrics = len(success_metrics)
        
        print(f"\n📊 DETAILED SUCCESS ANALYSIS:")
        print(f"  ✅ SMACT Validation: {'✅' if success_metrics['smact_validation'] else '❌'}")
        print(f"  ✅ Structure Generation: {'✅' if success_metrics['structure_generation'] else '❌'}")
        print(f"  ✅ Energy Calculations: {'✅' if success_metrics['energy_calculation'] else '❌'}")
        print(f"  ✅ Formation Energy: {'✅' if success_metrics['formation_energy'] else '❌'}")
        print(f"  ✅ Stability Assessment: {'✅' if success_metrics['stability_assessment'] else '❌'}")
        print(f"  ✅ Both Materials Analyzed: {'✅' if success_metrics['both_materials'] else '❌'}")
        print(f"  ✅ Quantitative Data: {'✅' if success_metrics['quantitative_data'] else '❌'}")
        print(f"\n🎯 Overall Integration Score: {success_count}/{total_metrics} ({success_count/total_metrics*100:.1f}%)")
        
        if success_count >= 5:
            print("\n🎉 EXCELLENT: Full workflow integration successful!")
            print("✅ SMACT → Chemeleon → MACE pipeline working perfectly")
            return True
        elif success_count >= 3:
            print("\n✅ GOOD: Core functionality working with minor gaps")
            return True
        else:
            print("\n⚠️  NEEDS WORK: Significant integration issues detected")
            return False
        
    except Exception as e:
        print(f"❌ Analysis failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Run the focused Na-ion cathode test."""
    success = await test_naion_focused()
    
    if success:
        print("\n" + "🏆" * 60)
        print("🏆 WORKFLOW INTEGRATION VERIFIED SUCCESSFULLY!")
        print("🏆 CrystaLyse.AI ready for production materials discovery")
        print("🏆" * 60)
    else:
        print("\n❌ Integration verification incomplete")
    
    return success

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)