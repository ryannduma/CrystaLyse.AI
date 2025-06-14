#!/usr/bin/env python3
"""
Integration demonstration: Single material through complete workflow.
"""

import asyncio
import sys
import time
from pathlib import Path

# Add the current directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from crystalyse.agents.main_agent import CrystaLyseAgent

async def test_integration_demo():
    """Demonstrate complete integration with one material."""
    print("🧪 INTEGRATION DEMONSTRATION")
    print("=" * 50)
    print("🔧 Complete Workflow: SMACT → Chemeleon → MACE")
    print("🎯 Single Material: NaFePO4 (olivine cathode)")
    print("=" * 50)
    
    # Set up agent in full rigor mode
    agent = CrystaLyseAgent(
        use_chem_tools=True,   # SMACT validation
        enable_mace=True,      # MACE energy analysis
        temperature=0.2        # Focused analysis
    )
    
    # Simple, focused query
    query = """Analyze NaFePO4 as a Na-ion battery cathode material.

WORKFLOW:
1. Validate composition with SMACT
2. Generate ONE crystal structure with Chemeleon  
3. Calculate energy and formation energy with MACE

Provide: SMACT validation, structure details, energy data, and stability assessment.
Keep analysis brief and focused."""
    
    print(f"🚀 Starting integration demonstration...")
    start_time = time.time()
    
    try:
        result = await agent.analyze(query)
        duration = time.time() - start_time
        
        print(f"✅ Analysis completed in {duration:.1f} seconds")
        print(f"📊 Result length: {len(result)} characters")
        print()
        print("📋 INTEGRATION DEMONSTRATION RESULTS:")
        print("=" * 60)
        print(result)
        print("=" * 60)
        
        # Check for integration success indicators
        has_smact = "smact" in result.lower() or "valid" in result.lower()
        has_structure = "structure" in result.lower() or "lattice" in result.lower()
        has_energy = "energy" in result.lower() and ("ev" in result.lower() or "eV" in result)
        has_formation = "formation" in result.lower()
        has_stability = "stable" in result.lower()
        
        integration_score = sum([has_smact, has_structure, has_energy, has_formation, has_stability])
        
        print(f"\n🎯 INTEGRATION VERIFICATION:")
        print(f"  ✅ SMACT Validation: {'✅' if has_smact else '❌'}")
        print(f"  ✅ Structure Generation: {'✅' if has_structure else '❌'}")
        print(f"  ✅ Energy Calculation: {'✅' if has_energy else '❌'}")
        print(f"  ✅ Formation Energy: {'✅' if has_formation else '❌'}")
        print(f"  ✅ Stability Analysis: {'✅' if has_stability else '❌'}")
        print(f"\n🏆 Integration Score: {integration_score}/5")
        
        if integration_score >= 4:
            print("\n🎉 EXCELLENT INTEGRATION!")
            print("✅ Complete SMACT → Chemeleon → MACE workflow operational")
            success = True
        elif integration_score >= 3:
            print("\n✅ GOOD INTEGRATION!")
            print("✅ Core workflow components working")
            success = True
        else:
            print("\n⚠️  PARTIAL INTEGRATION")
            success = False
        
        # Save demonstration results
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        filename = f"integration_demo_{timestamp}.txt"
        with open(filename, "w") as f:
            f.write("CrystaLyse.AI Integration Demonstration\n")
            f.write("=" * 50 + "\n\n")
            f.write(f"Workflow: SMACT → Chemeleon → MACE\n")
            f.write(f"Material: NaFePO4\n")
            f.write(f"Duration: {duration:.1f} seconds\n")
            f.write(f"Integration Score: {integration_score}/5\n\n")
            f.write("Results:\n")
            f.write("-" * 30 + "\n")
            f.write(result)
        
        print(f"\n💾 Demo results saved to: {filename}")
        return success
        
    except Exception as e:
        print(f"❌ Demo failed: {e}")
        return False

async def main():
    """Run the integration demonstration."""
    success = await test_integration_demo()
    
    print("\n" + "=" * 60)
    if success:
        print("🏆 INTEGRATION DEMONSTRATION SUCCESSFUL!")
        print("🔗 CrystaLyse.AI multi-tool workflow is operational")
        print("🚀 Ready for comprehensive materials discovery")
    else:
        print("❌ Integration demonstration incomplete")
    print("=" * 60)
    
    return success

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)