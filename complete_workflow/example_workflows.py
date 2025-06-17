#!/usr/bin/env python3
"""
Example workflows demonstrating MACE-integrated CrystaLyse.AI capabilities.

This module showcases comprehensive energy-guided materials discovery workflows
that combine SMACT validation, Chemeleon structure prediction, and MACE energy
calculations for various applications.
"""

import asyncio
import json
import sys
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional

# Configure OpenAI API key for high rate limits
import openai
if os.getenv("OPENAI_MDG_API_KEY"):
    openai.api_key = os.getenv("OPENAI_MDG_API_KEY")

# Add CrystaLyse to path
crystalyse_path = Path(__file__).parent.parent
sys.path.insert(0, str(crystalyse_path))

from crystalyse.agents.mace_integrated_agent import MACEIntegratedAgent


class WorkflowExamples:
    """Collection of example workflows for MACE-integrated materials discovery."""
    
    def __init__(self, save_results: bool = True):
        """Initialise workflow examples with optional result saving."""
        self.save_results = save_results
        self.results_dir = Path(__file__).parent / "workflow_results"
        if save_results:
            self.results_dir.mkdir(exist_ok=True)
    
    def _save_result(self, workflow_name: str, result: Any):
        """Save workflow result to file."""
        if not self.save_results:
            return None
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{workflow_name}_{timestamp}.json"
        filepath = self.results_dir / filename
        
        with open(filepath, 'w') as f:
            json.dump({
                'workflow': workflow_name,
                'timestamp': timestamp,
                'result': result
            }, f, indent=2)
        
        return filepath
    
    async def battery_cathode_discovery(self) -> Dict[str, Any]:
        """
        Workflow 1: Battery Cathode Material Discovery
        
        Demonstrates energy-guided discovery of novel cathode materials
        for next-generation battery applications.
        """
        print("🔋 Workflow 1: Battery Cathode Material Discovery")
        print("=" * 50)
        
        # Create agent for comprehensive analysis
        agent = MACEIntegratedAgent(
            use_chem_tools=True,   # Full SMACT validation
            enable_mace=True,      # Energy calculations
            temperature=0.5,       # Balanced creativity/precision
            uncertainty_threshold=0.08
        )
        
        query = """Design novel cathode materials for high-performance lithium-ion batteries.

Requirements:
- High energy density (>160 mAh/g theoretical capacity)
- Operating voltage 3.5-4.2V vs Li/Li+
- Use earth-abundant elements (minimise Co, minimise cost)
- Good structural stability during cycling
- Consider layered, spinel, and olivine structures

Workflow:
1. Propose 3-4 candidate compositions using chemical intuition
2. Validate all compositions with SMACT tools
3. Generate crystal structures with Chemeleon (3 structures per composition)
4. Calculate formation energies and stability with MACE
5. Assess uncertainty and confidence levels
6. Rank materials by energy density potential and stability
7. Suggest chemical modifications for improvement

Target applications: Electric vehicles, grid storage"""
        
        print("Running comprehensive battery cathode analysis...")
        result = await agent.analyse(query)
        
        workflow_result = {
            'workflow_type': 'battery_cathode_discovery',
            'agent_config': agent.get_mace_configuration(),
            'query': query,
            'result': result,
            'timestamp': datetime.now().isoformat()
        }
        
        saved_path = self._save_result('battery_cathode_discovery', workflow_result)
        print(f"✅ Battery cathode discovery completed")
        if saved_path:
            print(f"📁 Results saved to: {saved_path}")
        
        return workflow_result
    
    async def solar_cell_materials_screening(self) -> Dict[str, Any]:
        """
        Workflow 2: High-Throughput Solar Cell Materials Screening
        
        Demonstrates batch screening for photovoltaic materials with
        specific band gap and stability requirements.
        """
        print("\n☀️ Workflow 2: Solar Cell Materials Screening")
        print("=" * 50)
        
        agent = MACEIntegratedAgent(
            use_chem_tools=True,
            enable_mace=True,
            temperature=0.3,  # Lower for systematic screening
            batch_size=6
        )
        
        # Define candidate compositions for screening
        candidate_compositions = [
            "CsPbI3", "MAPbI3", "FAPbI3",      # Perovskites
            "CuInSe2", "CuInGaSe2", "CuZnSnS4", # Chalcopyrites/Kesterites
            "Sb2S3", "Sb2Se3", "BiI3",         # Alternative absorbers
            "SnS", "SnSe", "GeS"               # Tin/Germanium compounds
        ]
        
        print(f"Screening {len(candidate_compositions)} candidate compositions...")
        result = await agent.batch_screening(
            compositions=candidate_compositions,
            num_structures_per_comp=2
        )
        
        workflow_result = {
            'workflow_type': 'solar_cell_screening',
            'agent_config': agent.get_mace_configuration(),
            'candidate_compositions': candidate_compositions,
            'result': result,
            'timestamp': datetime.now().isoformat()
        }
        
        saved_path = self._save_result('solar_cell_screening', workflow_result)
        print(f"✅ Solar cell screening completed")
        if saved_path:
            print(f"📁 Results saved to: {saved_path}")
        
        return workflow_result
    
    async def thermoelectric_optimisation(self) -> Dict[str, Any]:
        """
        Workflow 3: Thermoelectric Material Optimisation
        
        Demonstrates energy-guided optimisation and chemical substitution
        for thermoelectric applications.
        """
        print("\n🌡️ Workflow 3: Thermoelectric Material Optimisation")
        print("=" * 50)
        
        agent = MACEIntegratedAgent(
            use_chem_tools=True,
            enable_mace=True,
            temperature=0.4
        )
        
        query = """Optimise thermoelectric materials for high-temperature waste heat recovery.

Base systems to explore:
- Bi2Te3 and related compounds (established TE materials)
- Half-Heusler compounds (TiNiSn, ZrNiSn family)
- Skutterudites (CoSb3-based)
- Oxide thermoelectrics (SrTiO3, CaMnO3 family)

Optimisation strategy:
1. Start with known TE materials as base compositions
2. Use SMACT to validate chemically reasonable substitutions
3. Generate crystal structures for promising compositions
4. Calculate formation energies and structural stability with MACE
5. Use suggest_substitutions tool for energy-guided modifications
6. Focus on elements: Ti, Zr, Hf, Co, Ni, Fe, Mn (avoid rare/toxic elements)
7. Assess uncertainty and recommend DFT validation for top candidates

Target: Figure of merit ZT > 1.5 at 800K, good stability"""
        
        print("Running thermoelectric optimisation analysis...")
        result = await agent.analyse(query)
        
        workflow_result = {
            'workflow_type': 'thermoelectric_optimisation',
            'agent_config': agent.get_mace_configuration(),
            'query': query,
            'result': result,
            'timestamp': datetime.now().isoformat()
        }
        
        saved_path = self._save_result('thermoelectric_optimisation', workflow_result)
        print(f"✅ Thermoelectric optimisation completed")
        if saved_path:
            print(f"📁 Results saved to: {saved_path}")
        
        return workflow_result
    
    async def multiferroic_discovery(self) -> Dict[str, Any]:
        """
        Workflow 4: Multiferroic Material Discovery
        
        Demonstrates creative exploration for materials with coupled
        magnetic and ferroelectric properties.
        """
        print("\n🧲 Workflow 4: Multiferroic Material Discovery")
        print("=" * 50)
        
        agent = MACEIntegratedAgent(
            use_chem_tools=False,  # Creative mode for novel exploration
            enable_mace=True,      # But with energy validation
            temperature=0.6        # Higher temperature for creativity
        )
        
        query = """Discover novel multiferroic materials with coupled magnetic and ferroelectric properties.

Design requirements:
- Room temperature ferroelectricity AND magnetism
- Avoid lead-based compounds (environmental concerns)
- Consider perovskite, hexagonal, and layered structures
- Target applications: memory devices, sensors, actuators

Chemical design principles:
- Ferroelectricity: Need off-centre cations (Ti4+, Nb5+, W6+) or lone pair elements (Bi3+, Pb2+)
- Magnetism: Include transition metals (Fe, Mn, Cr, Co, Ni) with unpaired electrons
- Structural coupling: Crystal structures that allow both distortions

Exploration approach:
1. Propose innovative multiferroic compositions
2. Generate crystal structures with focus on structural distortions
3. Calculate formation energies to assess synthesis feasibility
4. Use uncertainty quantification to guide experimental priorities
5. Consider both single-phase and composite approaches
6. Analyze structure-property relationships

Be creative but grounded in solid-state chemistry principles."""
        
        print("Running creative multiferroic discovery...")
        result = await agent.analyse(query)
        
        workflow_result = {
            'workflow_type': 'multiferroic_discovery',
            'agent_config': agent.get_mace_configuration(),
            'query': query,
            'result': result,
            'timestamp': datetime.now().isoformat()
        }
        
        saved_path = self._save_result('multiferroic_discovery', workflow_result)
        print(f"✅ Multiferroic discovery completed")
        if saved_path:
            print(f"📁 Results saved to: {saved_path}")
        
        return workflow_result
    
    async def energy_storage_electrolytes(self) -> Dict[str, Any]:
        """
        Workflow 5: Solid-State Electrolyte Discovery
        
        Demonstrates specialized energy analysis for ionic conductivity
        and electrochemical stability.
        """
        print("\n⚡ Workflow 5: Solid-State Electrolyte Discovery")
        print("=" * 50)
        
        agent = MACEIntegratedAgent(
            use_chem_tools=True,
            enable_mace=True,
            energy_focus=True,  # Specialized energy analysis
            temperature=0.3
        )
        
        query = """Design solid-state electrolytes for all-solid-state batteries with high ionic conductivity.

Target specifications:
- Li+ ionic conductivity > 1 mS/cm at room temperature
- Wide electrochemical stability window (0-5V vs Li/Li+)
- Chemical compatibility with electrodes
- Mechanical stability and processability

Material families to explore:
- Garnet-type: Li7La3Zr2O12 (LLZO) derivatives
- NASICON-type: Li1+xAlxTi2-x(PO4)3 (LATP) family
- Sulfide glasses: Li2S-P2S5 system
- Argyrodites: Li6PS5X (X = Cl, Br, I)

Analysis workflow:
1. Propose compositions with good Li+ mobility potential
2. Validate compositions and check for phase stability
3. Generate crystal structures with emphasis on Li+ pathways
4. Calculate formation energies and assess thermodynamic stability
5. Analyze structural descriptors for conductivity predictions
6. Use relaxation studies to understand Li+ migration barriers
7. Provide uncertainty assessment for experimental prioritisation

Focus on identifying the most promising candidates for synthesis."""
        
        print("Running solid-state electrolyte analysis...")
        result = await agent.analyse(query)
        
        workflow_result = {
            'workflow_type': 'energy_storage_electrolytes',
            'agent_config': agent.get_mace_configuration(),
            'query': query,
            'result': result,
            'timestamp': datetime.now().isoformat()
        }
        
        saved_path = self._save_result('energy_storage_electrolytes', workflow_result)
        print(f"✅ Electrolyte discovery completed")
        if saved_path:
            print(f"📁 Results saved to: {saved_path}")
        
        return workflow_result
    
    async def multifidelity_catalyst_screening(self) -> Dict[str, Any]:
        """
        Workflow 6: Multi-Fidelity Catalyst Screening
        
        Demonstrates intelligent MACE → DFT routing for catalyst discovery
        with uncertainty-guided computational resource allocation.
        """
        print("\n⚗️ Workflow 6: Multi-Fidelity Catalyst Screening")
        print("=" * 50)
        
        agent = MACEIntegratedAgent(
            use_chem_tools=True,
            enable_mace=True,
            uncertainty_threshold=0.05,  # Conservative threshold
            temperature=0.3
        )
        
        query = """Design heterogeneous catalysts for CO2 reduction to useful chemicals using multi-fidelity screening.

Target reaction: CO2 + H2 → CO + H2O (reverse water gas shift)
Operating conditions: 400-600°C, 1-10 bar

Catalyst requirements:
- High activity and selectivity for CO production
- Thermal stability at operating temperature
- Resistance to coking and sintering
- Use earth-abundant elements (avoid Pt group metals)

Multi-fidelity screening strategy:
1. Generate catalyst compositions (supported and bulk catalysts)
2. Use SMACT validation for chemical feasibility
3. Create surface and bulk crystal structures
4. Apply MACE energy calculations with uncertainty quantification
5. Implement intelligent routing logic:
   - High confidence (uncertainty < 0.05 eV/atom): Accept MACE results
   - Medium confidence (0.05-0.1 eV/atom): Flag for verification
   - Low confidence (> 0.1 eV/atom): Recommend DFT validation
6. Focus on transition metal carbides, nitrides, and oxides
7. Consider support effects (Al2O3, SiO2, TiO2)

Provide quantitative confidence assessment and DFT routing recommendations."""
        
        print("Running multi-fidelity catalyst screening...")
        result = await agent.analyse(query)
        
        workflow_result = {
            'workflow_type': 'multifidelity_catalyst_screening',
            'agent_config': agent.get_mace_configuration(),
            'query': query,
            'result': result,
            'uncertainty_threshold': agent.uncertainty_threshold,
            'timestamp': datetime.now().isoformat()
        }
        
        saved_path = self._save_result('multifidelity_catalyst_screening', workflow_result)
        print(f"✅ Catalyst screening completed")
        if saved_path:
            print(f"📁 Results saved to: {saved_path}")
        
        return workflow_result


async def run_example_workflow(workflow_name: str, examples: WorkflowExamples) -> Dict[str, Any]:
    """Run a specific example workflow."""
    workflows = {
        'battery': examples.battery_cathode_discovery,
        'solar': examples.solar_cell_materials_screening,
        'thermoelectric': examples.thermoelectric_optimisation,
        'multiferroic': examples.multiferroic_discovery,
        'electrolyte': examples.energy_storage_electrolytes,
        'catalyst': examples.multifidelity_catalyst_screening
    }
    
    if workflow_name not in workflows:
        raise ValueError(f"Unknown workflow: {workflow_name}. Available: {list(workflows.keys())}")
    
    return await workflows[workflow_name]()


async def run_all_workflows():
    """Run all example workflows to demonstrate complete capabilities."""
    print("🚀 CrystaLyse.AI MACE-Integrated Workflow Examples")
    print("=" * 60)
    print("Demonstrating energy-guided materials discovery across multiple applications")
    print()
    
    examples = WorkflowExamples(save_results=True)
    
    workflows = [
        ("Battery Cathode Discovery", examples.battery_cathode_discovery),
        ("Solar Cell Materials Screening", examples.solar_cell_materials_screening),
        ("Thermoelectric Optimisation", examples.thermoelectric_optimisation),
        ("Multiferroic Discovery", examples.multiferroic_discovery),
        ("Energy Storage Electrolytes", examples.energy_storage_electrolytes),
        ("Multi-Fidelity Catalyst Screening", examples.multifidelity_catalyst_screening)
    ]
    
    results = {}
    successful = 0
    
    for workflow_name, workflow_func in workflows:
        try:
            print(f"\n{'='*60}")
            result = await workflow_func()
            results[workflow_name] = result
            successful += 1
            print(f"✅ {workflow_name}: SUCCESS")
        except Exception as e:
            print(f"❌ {workflow_name}: FAILED - {str(e)}")
            results[workflow_name] = {'error': str(e)}
    
    # Save summary
    summary = {
        'total_workflows': len(workflows),
        'successful': successful,
        'failed': len(workflows) - successful,
        'timestamp': datetime.now().isoformat(),
        'results': results
    }
    
    summary_file = examples.results_dir / f"workflow_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(summary_file, 'w') as f:
        json.dump(summary, f, indent=2)
    
    print(f"\n{'='*60}")
    print(f"🎯 Workflow Summary: {successful}/{len(workflows)} completed successfully")
    print(f"📊 Results saved to: {summary_file}")
    
    if successful == len(workflows):
        print("🎉 All workflows completed successfully!")
        print("✅ CrystaLyse.AI MACE integration is fully functional across all applications")
    
    return summary


async def main():
    """Main function to run workflow examples."""
    import argparse
    
    parser = argparse.ArgumentParser(description="CrystaLyse.AI MACE-Integrated Workflow Examples")
    parser.add_argument('--workflow', '-w', type=str, 
                       choices=['battery', 'solar', 'thermoelectric', 'multiferroic', 'electrolyte', 'catalyst', 'all'],
                       default='all', help='Which workflow to run')
    parser.add_argument('--save', '-s', action='store_true', default=True,
                       help='Save results to files')
    
    args = parser.parse_args()
    
    examples = WorkflowExamples(save_results=args.save)
    
    try:
        if args.workflow == 'all':
            await run_all_workflows()
        else:
            await run_example_workflow(args.workflow, examples)
        
        return 0
    except KeyboardInterrupt:
        print("\n⏹️ Workflow interrupted by user")
        return 1
    except Exception as e:
        print(f"\n💥 Workflow failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))