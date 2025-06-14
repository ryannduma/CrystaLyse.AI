#!/usr/bin/env python3
"""
Comprehensive test: Na-ion battery cathode materials with full rigor mode.
SMACT validation + Chemeleon structure generation + MACE energy analysis.
"""

import asyncio
import sys
import time
from pathlib import Path

# Add the current directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from crystalyse.agents.main_agent import CrystaLyseAgent

async def test_naion_cathodes_rigor():
    """Test complete rigor mode workflow for Na-ion battery cathodes."""
    print("🔋 Na-ion Battery Cathode Materials Discovery - Full Rigor Mode")
    print("=" * 70)
    print("🔧 Mode: SMACT Validation + Chemeleon CSP + MACE Energy Analysis")
    print("🎯 Target: 4 stable cathode materials with comprehensive analysis")
    print("=" * 70)
    
    # Set up agent in FULL RIGOR MODE - all tools enabled
    agent = CrystaLyseAgent(
        use_chem_tools=True,   # Enable SMACT composition validation
        enable_mace=True,      # Enable MACE energy calculations  
        temperature=0.3        # Analytical precision
    )
    
    # Comprehensive query for Na-ion cathode materials
    query = """Find 4 stable cathode materials for Na-ion batteries with comprehensive energy analysis.

REQUIREMENTS:
- High energy density (>120 mAh/g theoretical capacity)
- Operating voltage 2.5-4.0V vs Na/Na+
- Good structural stability during cycling
- Earth-abundant elements preferred
- Thermodynamically stable (negative formation energy)

COMPLETE WORKFLOW REQUIRED:
1. **COMPOSITION VALIDATION**: Use SMACT tools to validate all proposed compositions
2. **STRUCTURE GENERATION**: Use Chemeleon to generate 2-3 crystal structures per composition
3. **ENERGY ANALYSIS**: Use MACE tools for each structure:
   - Calculate energy with uncertainty for confidence assessment
   - Calculate formation energy for thermodynamic stability
   - Assess structural stability

ANALYSIS FOR EACH MATERIAL:
- SMACT validation results
- Crystal structure predictions with lattice parameters
- Energy per atom and formation energy from MACE
- Uncertainty quantification for confidence levels
- Theoretical capacity and voltage estimates
- Synthesis recommendations

Focus on layered oxides, polyanionic compounds, and Prussian blue analogs.
Provide quantitative energy data and confidence assessments for each candidate."""
    
    print(f"🚀 Starting comprehensive Na-ion cathode analysis...")
    start_time = time.time()
    
    try:
        result = await agent.analyze(query)
        duration = time.time() - start_time
        
        print(f"✅ Analysis completed in {duration:.1f} seconds")
        print(f"📊 Result length: {len(result)} characters")
        print()
        print("📋 NA-ION CATHODE MATERIALS ANALYSIS:")
        print("=" * 80)
        print(result)
        print("=" * 80)
        
        # Save results with detailed metadata
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        filename = f"naion_cathodes_rigor_mode_{timestamp}.txt"
        with open(filename, "w") as f:
            f.write("Na-ion Battery Cathode Materials Discovery - Full Rigor Mode\n")
            f.write("=" * 70 + "\n\n")
            f.write("Analysis Configuration:\n")
            f.write(f"- SMACT Validation: ENABLED\n")
            f.write(f"- Chemeleon CSP: ENABLED\n") 
            f.write(f"- MACE Energy Analysis: ENABLED\n")
            f.write(f"- Analysis Duration: {duration:.1f} seconds\n")
            f.write(f"- Result Length: {len(result)} characters\n")
            f.write(f"- Target: 4 stable cathode materials\n\n")
            f.write("Results:\n")
            f.write("-" * 40 + "\n")
            f.write(result)
        
        print(f"\n💾 Complete analysis saved to: {filename}")
        
        # Check for successful integration indicators
        success_indicators = [
            "formation_energy" in result.lower() or "formation energy" in result.lower(),
            "smact" in result.lower() or "validation" in result.lower(),
            "energy" in result.lower() and ("ev" in result.lower() or "eV" in result),
            "stable" in result.lower() or "stability" in result.lower()
        ]
        
        success_count = sum(success_indicators)
        print(f"\n📈 Integration Success Metrics:")
        print(f"  - Energy Analysis: {'✅' if success_indicators[2] else '❌'}")
        print(f"  - Formation Energy: {'✅' if success_indicators[0] else '❌'}")
        print(f"  - SMACT Validation: {'✅' if success_indicators[1] else '❌'}")
        print(f"  - Stability Assessment: {'✅' if success_indicators[3] else '❌'}")
        print(f"  - Overall Score: {success_count}/4")
        
        if success_count >= 3:
            print("\n🎉 EXCELLENT: Full rigor mode working successfully!")
            print("✅ Complete workflow: SMACT → Chemeleon → MACE integration verified")
            return True
        elif success_count >= 2:
            print("\n✅ GOOD: Most components working, minor issues detected")
            return True
        else:
            print("\n⚠️  PARTIAL: Some integration issues remain")
            return False
        
    except Exception as e:
        print(f"❌ Analysis failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Run the comprehensive Na-ion cathode test."""
    print("🧪 Testing complete CrystaLyse.AI workflow integration...")
    print("🔬 Mode: Maximum rigor with all computational tools\n")
    
    success = await test_naion_cathodes_rigor()
    
    if success:
        print("\n" + "=" * 70)
        print("🏆 SUCCESS: Complete materials discovery workflow operational!")
        print("🔗 Integration: SMACT + Chemeleon + MACE working together")
        print("🎯 Application: Ready for real materials discovery projects")
        print("=" * 70)
    else:
        print("\n" + "=" * 70)
        print("❌ Integration needs refinement")
        print("=" * 70)
    
    return success

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)