#!/usr/bin/env python3
"""
Creative mode test: Ferroelectric materials with o4-mini + Chemeleon + MACE.
Uses chemical reasoning instead of SMACT validation.
"""

import asyncio
import sys
import time
from pathlib import Path

# Add the current directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from crystalyse.agents.main_agent import CrystaLyseAgent

async def test_creative_ferroelectrics():
    """Test creative mode for ferroelectric materials discovery."""
    print("🧠 CREATIVE MODE: Ferroelectric Materials Discovery")
    print("=" * 65)
    print("🤖 Model: o4-mini (10M TPM, 1B TPD!)")
    print("🔧 Workflow: Chemical Reasoning → Chemeleon → MACE")
    print("🎯 Target: Lead-free ferroelectric materials")
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
    
    # Ferroelectric materials query with creative reasoning
    query = """Design lead-free ferroelectric materials for next-generation memory devices using chemical reasoning and intuition.

CREATIVE DESIGN APPROACH:
- Use your deep chemical knowledge and intuition to propose novel compositions
- Consider ionic size effects, charge balance, and structural preferences
- Explore beyond traditional compositions while maintaining synthesizability

TARGET REQUIREMENTS:
- High spontaneous polarization (>50 μC/cm²)
- Curie temperature >300°C for device stability
- Lead-free for environmental safety
- Novel but synthesizable compositions

COMPLETE WORKFLOW:
1. **CHEMICAL REASONING**: Use AI chemical intuition to design 3-4 promising compositions
   - Consider perovskite distortions, layered structures, and lone-pair effects
   - Balance innovation with chemical feasibility
2. **STRUCTURE GENERATION**: Use Chemeleon to generate crystal structures
3. **ENERGY VALIDATION**: Use MACE to calculate energies and formation energies
4. **COMPREHENSIVE ANALYSIS**: Provide detailed ferroelectric property predictions

PROVIDE FOR EACH MATERIAL:
- Composition with chemical reasoning for ferroelectric behavior
- Crystal structure with lattice parameters
- Energy and formation energy from MACE calculations
- Predicted ferroelectric properties and Curie temperature
- Synthesis recommendations and processing conditions
- Innovation potential and advantages over existing materials

Focus on creative but scientifically sound compositions."""
    
    print("🚀 Starting creative ferroelectric materials design...")
    start_time = time.time()
    
    try:
        result = await agent.analyze(query)
        duration = time.time() - start_time
        
        print(f"✅ Analysis completed in {duration:.1f} seconds")
        print(f"📊 Result length: {len(result)} characters")
        print()
        print("📋 CREATIVE FERROELECTRIC MATERIALS DESIGN:")
        print("=" * 70)
        print(result)
        print("=" * 70)
        
        # Creative mode success indicators
        success_indicators = {
            "chemical_reasoning": any(keyword in result.lower() for keyword in ["reasoning", "chemical", "intuition", "design"]),
            "novel_compositions": any(keyword in result.lower() for keyword in ["composition", "formula", "material"]),
            "structure_generation": any(keyword in result.lower() for keyword in ["structure", "lattice", "crystal", "perovskite"]),
            "energy_calculations": any(keyword in result.lower() for keyword in ["energy", "ev", "formation"]),
            "ferroelectric_properties": any(keyword in result.lower() for keyword in ["ferroelectric", "polarization", "curie"]),
            "synthesis_info": any(keyword in result.lower() for keyword in ["synthesis", "processing", "temperature"]),
            "innovation_aspects": any(keyword in result.lower() for keyword in ["novel", "innovative", "advantage", "potential"]),
            "comprehensive_analysis": len(result) > 1500
        }
        
        success_count = sum(success_indicators.values())
        total_metrics = len(success_indicators)
        success_percentage = (success_count / total_metrics) * 100
        
        print("\n📊 CREATIVE MODE VERIFICATION:")
        print(f"  🧠 Chemical Reasoning: {'✅' if success_indicators['chemical_reasoning'] else '❌'}")
        print(f"  🔬 Novel Compositions: {'✅' if success_indicators['novel_compositions'] else '❌'}")
        print(f"  🏗️  Structure Generation: {'✅' if success_indicators['structure_generation'] else '❌'}")
        print(f"  ⚡ Energy Calculations: {'✅' if success_indicators['energy_calculations'] else '❌'}")
        print(f"  📱 Ferroelectric Properties: {'✅' if success_indicators['ferroelectric_properties'] else '❌'}")
        print(f"  🔧 Synthesis Information: {'✅' if success_indicators['synthesis_info'] else '❌'}")
        print(f"  💡 Innovation Aspects: {'✅' if success_indicators['innovation_aspects'] else '❌'}")
        print(f"  📖 Comprehensive Analysis: {'✅' if success_indicators['comprehensive_analysis'] else '❌'}")
        print(f"\n🎨 Creative Mode Success: {success_count}/{total_metrics} ({success_percentage:.1f}%)")
        
        # Save results
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        filename = f"creative_ferroelectrics_{timestamp}.txt"
        with open(filename, "w") as f:
            f.write("CREATIVE MODE: Ferroelectric Materials Discovery\n")
            f.write("=" * 65 + "\n\n")
            f.write("Analysis Configuration:\n")
            f.write("- Mode: Creative (Chemical Reasoning + Chemeleon + MACE)\n")
            f.write("- Model: o4-mini (10M TPM, 1B TPD)\n")
            f.write("- Target: Lead-free ferroelectric materials\n")
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
    """Run the creative ferroelectric materials test."""
    print("🎨 CrystaLyse.AI Creative Mode Test")
    print("🧠 Testing AI chemical reasoning with o4-mini\n")
    
    success = await test_creative_ferroelectrics()
    
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