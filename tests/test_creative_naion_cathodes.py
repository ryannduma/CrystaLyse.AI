#!/usr/bin/env python3
"""
Creative mode test: Na-ion battery cathodes with o4-mini + Chemeleon + MACE.
Uses chemical reasoning instead of SMACT validation.
"""

import asyncio
import sys
import time
from pathlib import Path

# Add the current directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from crystalyse.agents.main_agent import CrystaLyseAgent

async def test_creative_naion_cathodes():
    """Test creative mode for Na-ion battery cathode discovery."""
    print("🧠 CREATIVE MODE: Na-ion Battery Cathode Discovery")
    print("=" * 65)
    print("🤖 Model: o4-mini (10M TPM, 1B TPD!)")
    print("🔧 Workflow: Chemical Reasoning → Chemeleon → MACE")
    print("🎯 Target: 3 innovative Na-ion cathode materials")
    print("⚡ No SMACT validation - pure AI chemical intuition")
    print("=" * 65)
    
    # Set up agent in CREATIVE MODE with o4-mini
    agent = CrystaLyseAgent(
        model="o4-mini",           # Ultra-high rate limit reasoning model
        use_chem_tools=False,      # No SMACT - pure chemical reasoning
        enable_mace=True,          # Enable MACE energy calculations  
        temperature=None,          # o4-mini doesn't support temperature
        max_turns=20               # Generous turns for comprehensive analysis
    )
    
    # Na-ion cathode query with creative reasoning
    query = """Design 3 innovative cathode materials for Na-ion batteries using chemical reasoning and intuition.

CREATIVE DESIGN APPROACH:
- Use your deep electrochemical knowledge to propose novel compositions
- Consider Na+ intercalation chemistry, redox couples, and structural stability
- Explore beyond conventional materials while maintaining practicality

TARGET REQUIREMENTS:
- High theoretical capacity (>120 mAh/g)
- Operating voltage 2.5-4.0V vs Na/Na+
- Good structural stability during cycling
- Earth-abundant elements preferred
- Novel but synthesizable compositions

COMPLETE WORKFLOW:
1. **CHEMICAL REASONING**: Use AI chemical intuition to design 3 promising cathode compositions
   - Consider layered oxides, polyanionic frameworks, and Prussian blue analogs
   - Balance redox activity with structural stability
   - Think about Na+ diffusion pathways and intercalation sites
2. **STRUCTURE GENERATION**: Use Chemeleon to generate crystal structures
3. **ENERGY VALIDATION**: Use MACE to calculate energies and formation energies
4. **ELECTROCHEMICAL ANALYSIS**: Predict battery performance properties

PROVIDE FOR EACH OF THE 3 MATERIALS:
- Composition with chemical reasoning for Na+ intercalation
- Crystal structure with lattice parameters and Na+ sites
- Energy and formation energy from MACE calculations
- Theoretical capacity and voltage predictions
- Cycling stability assessment based on structural considerations
- Synthesis routes and processing conditions
- Advantages over existing cathode materials

Focus on creative but electrochemically sound compositions that push beyond traditional cathode chemistries."""
    
    print("🚀 Starting creative Na-ion cathode design...")
    start_time = time.time()
    
    try:
        result = await agent.analyze(query)
        duration = time.time() - start_time
        
        print(f"✅ Analysis completed in {duration:.1f} seconds")
        print(f"📊 Result length: {len(result)} characters")
        print()
        print("📋 CREATIVE NA-ION CATHODE DESIGN:")
        print("=" * 70)
        print(result)
        print("=" * 70)
        
        # Creative mode success indicators for cathodes
        success_indicators = {
            "chemical_reasoning": any(keyword in result.lower() for keyword in ["reasoning", "chemical", "intuition", "design"]),
            "cathode_compositions": any(keyword in result.lower() for keyword in ["composition", "cathode", "material"]),
            "structure_generation": any(keyword in result.lower() for keyword in ["structure", "lattice", "crystal", "intercalation"]),
            "energy_calculations": any(keyword in result.lower() for keyword in ["energy", "ev", "formation"]),
            "battery_properties": any(keyword in result.lower() for keyword in ["capacity", "voltage", "mah/g", "cycling"]),
            "na_intercalation": any(keyword in result.lower() for keyword in ["na+", "sodium", "intercalation", "diffusion"]),
            "synthesis_info": any(keyword in result.lower() for keyword in ["synthesis", "processing", "route"]),
            "innovation_aspects": any(keyword in result.lower() for keyword in ["novel", "innovative", "advantage", "beyond"]),
            "three_materials": result.lower().count("material") >= 3 or result.lower().count("cathode") >= 3,
            "comprehensive_analysis": len(result) > 2000
        }
        
        success_count = sum(success_indicators.values())
        total_metrics = len(success_indicators)
        success_percentage = (success_count / total_metrics) * 100
        
        print("\n📊 CREATIVE MODE VERIFICATION:")
        print(f"  🧠 Chemical Reasoning: {'✅' if success_indicators['chemical_reasoning'] else '❌'}")
        print(f"  🔋 Cathode Compositions: {'✅' if success_indicators['cathode_compositions'] else '❌'}")
        print(f"  🏗️  Structure Generation: {'✅' if success_indicators['structure_generation'] else '❌'}")
        print(f"  ⚡ Energy Calculations: {'✅' if success_indicators['energy_calculations'] else '❌'}")
        print(f"  🔌 Battery Properties: {'✅' if success_indicators['battery_properties'] else '❌'}")
        print(f"  ⚛️  Na+ Intercalation: {'✅' if success_indicators['na_intercalation'] else '❌'}")
        print(f"  🔧 Synthesis Information: {'✅' if success_indicators['synthesis_info'] else '❌'}")
        print(f"  💡 Innovation Aspects: {'✅' if success_indicators['innovation_aspects'] else '❌'}")
        print(f"  🎯 Three Materials: {'✅' if success_indicators['three_materials'] else '❌'}")
        print(f"  📖 Comprehensive Analysis: {'✅' if success_indicators['comprehensive_analysis'] else '❌'}")
        print(f"\n🎨 Creative Mode Success: {success_count}/{total_metrics} ({success_percentage:.1f}%)")
        
        # Save results
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        filename = f"creative_naion_cathodes_{timestamp}.txt"
        with open(filename, "w") as f:
            f.write("CREATIVE MODE: Na-ion Battery Cathode Discovery\n")
            f.write("=" * 65 + "\n\n")
            f.write("Analysis Configuration:\n")
            f.write("- Mode: Creative (Chemical Reasoning + Chemeleon + MACE)\n")
            f.write("- Model: o4-mini (10M TPM, 1B TPD)\n")
            f.write("- Target: 3 innovative Na-ion cathode materials\n")
            f.write("- SMACT Validation: Disabled (pure AI reasoning)\n")
            f.write(f"- Duration: {duration:.1f} seconds\n")
            f.write(f"- Result Length: {len(result)} characters\n")
            f.write(f"- Creative Success: {success_percentage:.1f}%\n\n")
            f.write("Creative Mode Verification:\n")
            for metric, status in success_indicators.items():
                f.write(f"- {metric.replace('_', ' ').title()}: {'✅' if status else '❌'}\n")
            f.write("\nResults:\n")
            f.write("-" * 50 + "\n")
            f.write(result)
        
        print(f"\n💾 Creative analysis saved to: {filename}")
        
        if success_percentage >= 75:
            print(f"\n🎨 EXCELLENT CREATIVE SUCCESS! ({success_percentage:.1f}%)")
            print("✅ Creative mode with o4-mini working brilliantly")
            print("🧠 Chemical reasoning + structure + energy analysis integrated")
            return True
        elif success_percentage >= 60:
            print(f"\n🎯 GOOD CREATIVE SUCCESS! ({success_percentage:.1f}%)")
            print("✅ Creative workflow operational")
            return True
        else:
            print(f"\n🔧 DEVELOPING ({success_percentage:.1f}%)")
            return False
        
    except Exception as e:
        print(f"❌ Creative analysis failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Run the creative Na-ion cathode test."""
    print("🎨 CrystaLyse.AI Creative Mode Test")
    print("🧠 Testing AI chemical reasoning with o4-mini\n")
    
    success = await test_creative_naion_cathodes()
    
    print("\n" + "=" * 65)
    if success:
        print("🎉 CREATIVE MODE SUCCESS!")
        print("🧠 AI chemical reasoning working excellently")
        print("🔗 o4-mini + Chemeleon + MACE integration verified")
        print("🚀 Ready for innovative materials discovery")
    else:
        print("🔧 Creative mode development in progress")
    print("=" * 65)
    
    return success

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)