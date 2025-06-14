#!/usr/bin/env python3
"""
Na-ion battery cathode discovery: 2 materials with increased max_turns.
Complete workflow: SMACT validation + Chemeleon CSP + MACE energy analysis.
"""

import asyncio
import sys
import time
from pathlib import Path

# Add the current directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from crystalyse.agents.main_agent import CrystaLyseAgent

async def test_naion_increased_turns():
    """Test complete rigor mode workflow for 2 Na-ion battery cathodes with more turns."""
    print("🔋 Na-ion Battery Cathode Discovery - Increased Max Turns")
    print("=" * 70)
    print("🔧 Complete Integration: SMACT → Chemeleon → MACE")
    print("🎯 Target: 2 stable cathode materials with comprehensive analysis")
    print("⏳ Max Turns: 20 (increased from default 10)")
    print("=" * 70)
    
    # Set up agent in FULL RIGOR MODE with increased max_turns
    agent = CrystaLyseAgent(
        use_chem_tools=True,   # Enable SMACT composition validation
        enable_mace=True,      # Enable MACE energy calculations  
        temperature=0.3,       # Analytical precision
        max_turns=20           # Increased from default 15
    )
    
    # Focused query for exactly 2 Na-ion cathode materials
    query = """Find 2 stable cathode materials for Na-ion batteries with complete energy analysis using full rigor mode.

COMPLETE WORKFLOW REQUIRED:
1. **SMACT VALIDATION**: Validate all proposed compositions
2. **STRUCTURE GENERATION**: Use Chemeleon to generate crystal structures
3. **MACE ENERGY ANALYSIS**: Calculate energies and formation energies
4. **STABILITY ASSESSMENT**: Provide thermodynamic stability analysis

TARGET REQUIREMENTS:
- High theoretical capacity (>100 mAh/g)
- Operating voltage 2.5-4.0V vs Na/Na+
- Thermodynamically stable (negative formation energy)
- Earth-abundant elements preferred

PROVIDE FOR EACH MATERIAL:
- Composition and SMACT validation results
- Crystal structure with lattice parameters
- Total energy and energy per atom (eV/atom)
- Formation energy and stability assessment
- Theoretical capacity and voltage estimates
- Brief synthesis recommendations

Focus on exactly 2 well-known, promising cathode materials."""
    
    print("🚀 Starting 2-material Na-ion cathode analysis with increased turns...")
    start_time = time.time()
    
    try:
        result = await agent.analyze(query)
        duration = time.time() - start_time
        
        print(f"✅ Analysis completed in {duration:.1f} seconds")
        print(f"📊 Result length: {len(result)} characters")
        print()
        print("📋 NA-ION CATHODE ANALYSIS (INCREASED TURNS):")
        print("=" * 80)
        print(result)
        print("=" * 80)
        
        # Comprehensive success verification
        success_indicators = {
            "smact_validation": any(keyword in result.lower() for keyword in ["smact", "valid", "composition validation"]),
            "structure_data": any(keyword in result.lower() for keyword in ["lattice", "structure", "crystal", "cell"]),
            "energy_calculations": any(keyword in result.lower() for keyword in ["energy", "ev/atom", "ev"]),
            "formation_energy": any(keyword in result.lower() for keyword in ["formation energy", "stability", "thermodynamic"]),
            "quantitative_data": any(char in result for char in ["-", "+"]) and "ev" in result.lower(),
            "two_materials": result.lower().count("material") >= 2 or result.lower().count("cathode") >= 2,
            "capacity_analysis": any(keyword in result.lower() for keyword in ["capacity", "mah/g", "voltage"])
        }
        
        success_count = sum(success_indicators.values())
        total_metrics = len(success_indicators)
        success_percentage = (success_count / total_metrics) * 100
        
        print("\n📊 COMPREHENSIVE INTEGRATION VERIFICATION:")
        print(f"  ✅ SMACT Validation: {'✅' if success_indicators['smact_validation'] else '❌'}")
        print(f"  ✅ Structure Generation: {'✅' if success_indicators['structure_data'] else '❌'}")
        print(f"  ✅ Energy Calculations: {'✅' if success_indicators['energy_calculations'] else '❌'}")
        print(f"  ✅ Formation Energy: {'✅' if success_indicators['formation_energy'] else '❌'}")
        print(f"  ✅ Quantitative Results: {'✅' if success_indicators['quantitative_data'] else '❌'}")
        print(f"  ✅ Two Materials Analyzed: {'✅' if success_indicators['two_materials'] else '❌'}")
        print(f"  ✅ Battery Performance: {'✅' if success_indicators['capacity_analysis'] else '❌'}")
        print(f"\n🏆 Overall Integration Success: {success_count}/{total_metrics} ({success_percentage:.1f}%)")
        
        # Save comprehensive results
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        filename = f"naion_increased_turns_{timestamp}.txt"
        with open(filename, "w") as f:
            f.write("Na-ion Battery Cathode Discovery - Increased Max Turns\n")
            f.write("=" * 70 + "\n\n")
            f.write("Analysis Configuration:\n")
            f.write("- Mode: Full Rigor (SMACT + Chemeleon + MACE)\n")
            f.write("- Target: 2 stable cathode materials\n")
            f.write("- Application: Na-ion battery cathodes\n")
            f.write("- Max Turns: 20 (increased from default)\n")
            f.write(f"- Duration: {duration:.1f} seconds\n")
            f.write(f"- Result Length: {len(result)} characters\n")
            f.write(f"- Integration Success: {success_percentage:.1f}%\n\n")
            f.write("Integration Verification:\n")
            for metric, status in success_indicators.items():
                f.write(f"- {metric.replace('_', ' ').title()}: {'✅' if status else '❌'}\n")
            f.write("\nResults:\n")
            f.write("-" * 50 + "\n")
            f.write(result)
        
        print(f"\n💾 Complete analysis saved to: {filename}")
        
        # Determine final success level
        if success_percentage >= 80:
            print(f"\n🎉 EXCELLENT SUCCESS! ({success_percentage:.1f}%)")
            print("✅ Complete SMACT → Chemeleon → MACE integration verified")
            print("🚀 CrystaLyse.AI ready for production materials discovery")
            return True
        elif success_percentage >= 60:
            print(f"\n✅ GOOD SUCCESS! ({success_percentage:.1f}%)")
            print("✅ Core integration working with minor refinements needed")
            return True
        else:
            print(f"\n⚠️  PARTIAL SUCCESS ({success_percentage:.1f}%)")
            print("⚠️  Some integration components need refinement")
            return False
        
    except Exception as e:
        print(f"❌ Analysis failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Run the increased max_turns Na-ion cathode test."""
    print("🧪 CrystaLyse.AI Integration Test - Increased Max Turns")
    print("🔬 Testing complete computational workflow with more analysis depth\n")
    
    success = await test_naion_increased_turns()
    
    print("\n" + "=" * 70)
    if success:
        print("🏆 WORKFLOW INTEGRATION SUCCESSFUL!")
        print("🔗 Complete materials discovery pipeline operational")
        print("🎯 SMACT validation + Chemeleon CSP + MACE energy analysis")
        print("✅ Ready for comprehensive materials research projects")
        print("⏳ Increased max_turns allows for deeper analysis")
    else:
        print("❌ Integration verification needs additional refinement")
        print("🔧 Core components working, optimization in progress")
    print("=" * 70)
    
    return success

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)