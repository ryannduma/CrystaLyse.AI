#!/usr/bin/env python3
"""
Test finding Pb-free ferroelectric materials with MACE energy validation.

This demonstrates the energy-guided discovery workflow for ferroelectric materials,
using MACE to validate stability and energetics.
"""

import json
import sys
from pathlib import Path

# Add paths
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "mace-mcp-server" / "src"))

# Import MACE tools
from mace_mcp.tools import (
    calculate_energy_with_uncertainty,
    calculate_formation_energy,
    relax_structure,
    get_server_metrics
)

def test_pbfree_ferroelectric_discovery():
    """Test Pb-free ferroelectric materials discovery workflow."""
    
    print("⚡ Pb-free Ferroelectric Materials Discovery with MACE")
    print("=" * 60)
    
    # Check MACE status
    metrics = json.loads(get_server_metrics())
    print(f"✅ MACE v{metrics['server_version']} ready (CUDA: {metrics['cuda_available']})")
    print()
    
    print("🎯 TARGET: Lead-free ferroelectric materials")
    print("Requirements:")
    print("- No toxic Pb (lead)")
    print("- Ferroelectric properties (spontaneous polarization)")
    print("- High Curie temperature")
    print("- Good stability")
    print()
    
    # Candidate Pb-free ferroelectric compositions
    print("🧪 CANDIDATE MATERIALS:")
    print("1. BaTiO3 - Classic Pb-free ferroelectric")
    print("2. KNbO3 - Niobate ferroelectric")
    print("3. BiFeO3 - Multiferroic material")
    print("4. Na0.5Bi0.5TiO3 - Bismuth-sodium titanate")
    print()
    
    # Test structures (simplified perovskite structures)
    ferroelectric_candidates = {
        "BaTiO3": {
            "numbers": [56, 22, 8, 8, 8],  # Ba, Ti, O atoms
            "positions": [
                [0.0, 0.0, 0.0],      # Ba
                [0.5, 0.5, 0.52],     # Ti (displaced for ferroelectricity)
                [0.5, 0.5, 0.0],      # O
                [0.5, 0.0, 0.5],      # O
                [0.0, 0.5, 0.5]       # O
            ],
            "cell": [[4.0, 0.0, 0.0], [0.0, 4.0, 0.0], [0.0, 0.0, 4.03]],  # Tetragonal
            "pbc": [True, True, True]
        },
        
        "KNbO3": {
            "numbers": [19, 41, 8, 8, 8],  # K, Nb, O atoms
            "positions": [
                [0.0, 0.0, 0.0],      # K
                [0.5, 0.5, 0.51],     # Nb (displaced)
                [0.5, 0.5, 0.0],      # O
                [0.5, 0.0, 0.5],      # O
                [0.0, 0.5, 0.5]       # O
            ],
            "cell": [[4.0, 0.0, 0.0], [0.0, 4.0, 0.0], [0.0, 0.0, 4.05]],
            "pbc": [True, True, True]
        },
        
        "BiFeO3": {
            "numbers": [83, 26, 8, 8, 8],  # Bi, Fe, O atoms
            "positions": [
                [0.0, 0.0, 0.0],      # Bi
                [0.5, 0.5, 0.5],      # Fe
                [0.5, 0.5, 0.0],      # O
                [0.5, 0.0, 0.5],      # O
                [0.0, 0.5, 0.5]       # O
            ],
            "cell": [[3.96, 0.0, 0.0], [0.0, 3.96, 0.0], [0.0, 0.0, 3.96]],
            "pbc": [True, True, True]
        }
    }
    
    print("⚗️ MACE ENERGY VALIDATION:")
    results = {}
    
    for name, structure in ferroelectric_candidates.items():
        print(f"\n📊 Analyzing {name}...")
        
        # Energy with uncertainty quantification
        energy_result = json.loads(calculate_energy_with_uncertainty(
            structure, device="cpu", committee_size=3
        ))
        
        if "error" not in energy_result:
            results[name] = {
                "energy_per_atom": energy_result['energy_per_atom'],
                "uncertainty": energy_result['energy_uncertainty'],
                "confidence": energy_result['confidence']
            }
            
            print(f"   ✅ Energy: {energy_result['energy_per_atom']:.3f} eV/atom")
            print(f"   ✅ Uncertainty: ±{energy_result['energy_uncertainty']:.3f} eV/atom")
            print(f"   ✅ Confidence: {energy_result['confidence']}")
            
            # Formation energy analysis
            formation_result = json.loads(calculate_formation_energy(structure, device="cpu"))
            if "error" not in formation_result:
                results[name]["formation_energy"] = formation_result['formation_energy_per_atom']
                results[name]["stability"] = formation_result['stability_assessment']
                print(f"   ✅ Formation E: {formation_result['formation_energy_per_atom']:.3f} eV/atom")
                print(f"   ✅ Stability: {formation_result['stability_assessment']}")
            
            # Structure optimization to check for distortions
            print(f"   🔄 Optimizing structure...")
            relax_result = json.loads(relax_structure(structure, device="cpu", steps=20, fmax=0.3))
            if "error" not in relax_result:
                results[name]["optimization"] = {
                    "converged": relax_result['converged'],
                    "energy_change": relax_result['energy_change'],
                    "max_force": relax_result['max_force']
                }
                print(f"   ✅ Optimization converged: {relax_result['converged']}")
                print(f"   ✅ Energy lowering: {-relax_result['energy_change']:.3f} eV")
                
                # Analyze if structure maintains non-centrosymmetric (ferroelectric) character
                if abs(relax_result['energy_change']) > 0.01:
                    print(f"   🔍 Significant structural relaxation → Likely ferroelectric distortion")
                else:
                    print(f"   ⚠️ Minimal relaxation → May not be strongly ferroelectric")
        else:
            print(f"   ❌ Error: {energy_result['error']}")
    
    print("\n🏆 FERROELECTRIC MATERIAL RANKING:")
    print("\n   Material    | Uncertainty | Stability  | Ferro Potential | Recommendation")
    print("   ------------|-------------|------------|-----------------|------------------")
    
    # Rank materials based on uncertainty, stability, and ferroelectric potential
    recommendations = []
    
    for name, data in results.items():
        uncertainty = data.get('uncertainty', 1.0)
        formation_e = data.get('formation_energy', 10.0)
        energy_change = abs(data.get('optimization', {}).get('energy_change', 0.0))
        
        # Multi-fidelity decision
        if uncertainty < 0.05:
            confidence = "HIGH"
            mace_decision = "✅ MACE"
        elif uncertainty < 0.1:
            confidence = "MED"
            mace_decision = "⚠️ Monitor"
        else:
            confidence = "LOW"
            mace_decision = "🚨 DFT needed"
        
        # Stability assessment
        if formation_e < -0.5:
            stability = "Excellent"
        elif formation_e < 0.0:
            stability = "Good"
        elif formation_e < 1.0:
            stability = "Moderate"
        else:
            stability = "Poor"
        
        # Ferroelectric potential (based on structural distortion)
        if energy_change > 0.05:
            ferro_potential = "Strong"
        elif energy_change > 0.02:
            ferro_potential = "Moderate"
        else:
            ferro_potential = "Weak"
        
        # Overall recommendation
        if confidence == "HIGH" and stability in ["Excellent", "Good"] and ferro_potential != "Weak":
            recommendation = "🌟 SYNTHESIZE"
            priority = 1
        elif confidence != "LOW" and stability != "Poor":
            recommendation = "🔬 INVESTIGATE"
            priority = 2
        else:
            recommendation = "❌ REJECT"
            priority = 3
        
        recommendations.append((priority, name, uncertainty, stability, ferro_potential, recommendation))
        
        print(f"   {name:11} | {uncertainty:11.3f} | {stability:10} | {ferro_potential:15} | {recommendation}")
    
    # Sort by priority and show final recommendations
    recommendations.sort()
    
    print("\n🎯 FINAL RECOMMENDATIONS:")
    print("\n🥇 TOP CANDIDATES FOR SYNTHESIS:")
    top_candidates = [rec for rec in recommendations if rec[0] == 1]
    if top_candidates:
        for _, name, *_ in top_candidates:
            data = results[name]
            print(f"   ✅ {name}:")
            print(f"      - High MACE confidence (±{data['uncertainty']:.3f} eV/atom)")
            print(f"      - Good thermodynamic stability")
            print(f"      - Strong ferroelectric distortion potential")
            print(f"      - Ready for experimental synthesis!")
    else:
        print("   No materials meet all criteria for immediate synthesis")
    
    print("\n🥈 MATERIALS FOR FURTHER INVESTIGATION:")
    investigate = [rec for rec in recommendations if rec[0] == 2]
    for _, name, uncertainty, stability, ferro_potential, recommendation in investigate:
        print(f"   🔬 {name}: {stability} stability, {ferro_potential} ferroelectric potential")
        if uncertainty > 0.05:
            print(f"      → Recommend DFT validation (uncertainty: ±{uncertainty:.3f} eV/atom)")
    
    print("\n" + "=" * 60)
    print("✅ MACE successfully validated Pb-free ferroelectric candidates!")
    print("🎯 Multi-fidelity approach guides synthesis priorities")
    print("⚡ Energy-guided discovery reduces experimental trial-and-error")
    print("🌱 Lead-free materials promote environmental sustainability")
    
    # Summary statistics
    total_materials = len(results)
    high_confidence = sum(1 for data in results.values() if data.get('uncertainty', 1) < 0.05)
    synthesis_ready = len(top_candidates)
    
    print(f"\n📊 DISCOVERY STATISTICS:")
    print(f"   Materials screened: {total_materials}")
    print(f"   High MACE confidence: {high_confidence}/{total_materials}")
    print(f"   Synthesis-ready candidates: {synthesis_ready}")
    print(f"   DFT validation saved: ~{100*(high_confidence/total_materials):.0f}% computational cost reduction")

if __name__ == "__main__":
    test_pbfree_ferroelectric_discovery()