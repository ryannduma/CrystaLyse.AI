"""Advanced example showing constraint-based materials discovery with the unified agent."""

import asyncio
import os
from crystalyse import CrystaLyseUnifiedAgent, AgentConfig


async def main():
    """Demonstrate advanced materials discovery with specific constraints."""
    
    # Check for OpenAI API key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("Error: OPENAI_API_KEY environment variable not set!")
        return
        
    print("CrystaLyse.AI - Advanced Constraint-Based Discovery")
    print("=" * 60)
    
    # Configure agent for rigorous constraint handling
    config = AgentConfig(
        model="o4-mini",
        mode="rigorous",
        temperature=0.2,  # Low temperature for precise constraint following
        enable_smact=False,  # Enable if MCP servers available
        enable_chemeleon=False,
        enable_mace=False,
        max_turns=25  # More turns for complex constraints
    )
    
    agent = CrystaLyseUnifiedAgent(config)
    
    # Example 1: Multi-constraint materials design
    print("\n1. Multi-Constraint Thermoelectric Materials")
    
    constraints_query = """
    Design a thermoelectric material with these specific constraints:
    
    REQUIRED CONSTRAINTS:
    - Must be lead-free and non-toxic
    - Band gap between 0.1-0.3 eV (narrow gap semiconductor)
    - Contains earth-abundant elements only (no rare earth metals)
    - Stable at temperatures up to 600°C
    - Low thermal conductivity (<2 W/m·K)
    
    PREFERRED FEATURES:
    - High electrical conductivity (>1000 S/cm when doped)
    - Figure of merit ZT > 1.5 at 500°C
    - Suitable for n-type doping
    - Compatible with oxide-based interfaces
    
    Provide 3 specific compositions with detailed reasoning.
    """
    
    print("Query:", constraints_query[:100] + "...")
    result1 = await agent.discover_materials(constraints_query)
    
    if result1.get('status') == 'completed':
        print("Multi-constraint analysis completed!")
        discovery = result1['discovery_result']
        print(f"Analysis length: {len(discovery)} characters")
        
        # Extract key findings
        lines = discovery.split('\n')
        compositions = [line for line in lines if any(element in line for element in ['Sb', 'Bi', 'Te', 'Se', 'Ge', 'Sn'])]
        print(f"Found {len(compositions)} material candidates")
        
    else:
        print(f"Error: {result1.get('error', 'Unknown error')}")
    
    # Example 2: Application-specific optimization
    print("\n\n2. Application-Specific Optimisation - Solid Electrolytes")
    
    optimisation_query = """
    Optimise a solid electrolyte for next-generation batteries with these specifications:
    
    TARGET APPLICATION: All-solid-state lithium metal batteries
    
    CRITICAL REQUIREMENTS:
    - Ionic conductivity >1 mS/cm at room temperature
    - Electronic conductivity <10^-8 S/cm (insulating)
    - Electrochemical stability window >4.5V vs Li/Li+
    - Chemical stability with lithium metal anode
    - Mechanical properties: Young's modulus >20 GPa
    
    PROCESSING CONSTRAINTS:
    - Sinterable at <800°C (compatible with electrode processing)
    - Air-stable during handling
    - No fluorine or toxic elements
    
    Suggest 2 optimised compositions and explain the design rationale.
    """
    
    print("Query:", optimisation_query[:100] + "...")
    result2 = await agent.discover_materials(optimisation_query)
    
    if result2.get('status') == 'completed':
        print("Application optimisation completed!")
        
        # Show performance metrics
        metrics = result2.get('metrics', {})
        print(f"Analysis time: {metrics.get('elapsed_time', 0):.1f}s")
        print(f"Model: {metrics.get('model', 'unknown')} in {metrics.get('mode', 'unknown')} mode")
        
    else:
        print(f"Error: {result2.get('error', 'Unknown error')}")
    
    # Example 3: Comparative analysis
    print("\n\n3. Comparative Analysis - Alternative Materials")
    
    comparison_query = """
    Compare and rank these three material classes for photovoltaic applications:
    
    1. Halide perovskites (lead-free variants)
    2. Copper zinc tin sulfide (CZTS) quaternary compounds  
    3. Antimony chalcogenide binaries
    
    EVALUATION CRITERIA:
    - Band gap suitability (1.1-1.6 eV optimal)
    - Absorption coefficient (>10^4 cm-1 preferred)
    - Defect tolerance and carrier lifetime
    - Synthesis complexity and scalability
    - Material stability under operation
    
    Provide detailed comparison and recommend the best option.
    """
    
    print("Query:", comparison_query[:100] + "...")
    result3 = await agent.discover_materials(comparison_query)
    
    if result3.get('status') == 'completed':
        print("Comparative analysis completed!")
        print("Advanced constraint-based discovery demonstration finished!")
    else:
        print(f"Error: {result3.get('error', 'Unknown error')}")
    
    print("\n" + "=" * 60)
    print("Key Benefits of Unified Agent:")
    print("• Handles complex multi-constraint problems")
    print("• Maintains context across constraint categories") 
    print("• Provides detailed scientific reasoning")
    print("• Adapts analysis depth based on temperature setting")
    print("• Can integrate computational validation when MCP tools enabled")


if __name__ == "__main__":
    asyncio.run(main())