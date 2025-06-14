"""
Main CrystaLyse orchestrator agent module.

This module implements the CrystaLyseAgent class, which serves as the primary interface
for materials discovery using CrystaLyse.AI's innovative dual-mode system. The agent
can operate in two distinct modes:

1. Creative Mode: Leverages AI's chemical intuition for innovative materials exploration
2. Rigorous Mode: Uses SMACT computational tools for validated materials discovery

The module includes comprehensive system prompts that guide the AI's behavior in each
mode, ensuring appropriate use of chemical knowledge versus computational validation.

Key Features:
    - Dual-mode operation (creative vs rigorous)
    - MCP integration for SMACT tools
    - Streaming and non-streaming analysis
    - Temperature and model configuration
    - Comprehensive prompt engineering

Classes:
    CrystaLyseAgent: Main orchestrator for materials discovery workflows

Constants:
    CRYSTALYSE_CREATIVE_PROMPT: System prompt for creative mode operation
    CRYSTALYSE_RIGOROUS_PROMPT: System prompt for rigorous mode operation

Example:
    Basic usage of the CrystaLyse agent:

    >>> import asyncio
    >>> from crystalyse.agents.main_agent import CrystaLyseAgent
    >>> 
    >>> async def main():
    ...     # Creative mode for exploration
    ...     agent = CrystaLyseAgent(use_chem_tools=False)
    ...     result = await agent.analyze("Design a battery cathode material")
    ...     print(result)
    ...
    ...     # Rigorous mode for validation
    ...     agent = CrystaLyseAgent(use_chem_tools=True)
    ...     result = await agent.analyze("Design a battery cathode material")
    ...     print(result)
    >>> 
    >>> asyncio.run(main())
"""

from agents import Agent, Runner
from agents.mcp import MCPServerStdio
from agents.model_settings import ModelSettings
try:
    from .mcp_utils import RobustMCPServer, MCPConnectionError, log_mcp_status
    from ..config import get_agent_config, DEFAULT_MODEL
except ImportError:
    from mcp_utils import RobustMCPServer, MCPConnectionError, log_mcp_status
    from config import get_agent_config, DEFAULT_MODEL
import os
import asyncio
import json
from pathlib import Path
from typing import Optional, Dict, Any, List

# from ..models import CrystalAnalysisResult
# from ..tools import (
#     design_material_for_application,
#     generate_compositions,
#     predict_structure_types,
#     explain_chemical_reasoning,
# )

# System prompts for different modes

CRYSTALYSE_CREATIVE_PROMPT = """You are CrystaLyse, an expert materials design agent with deep knowledge of inorganic chemistry, crystallography, and materials science. You have access to Chemeleon crystal structure prediction tools.

**Core Capabilities:**
- Generate novel inorganic compositions based on chemical intuition
- Generate 3D crystal structures using Chemeleon CSP tools
- Predict likely crystal structures from composition and application
- Balance innovation with synthesizability
- Use comprehensive chemical knowledge and reasoning

**Workflow:**
1. Analyze the user's requirements (application, properties, constraints)
2. Propose candidate compositions using chemical reasoning and intuition
3. For each composition, generate crystal structures using Chemeleon tools:
   - Use generate_crystal_csp to create 3D structures (3-5 structures per composition)
   - Use analyse_structure to analyze structural properties
4. Provide synthesis considerations and structural insights
5. Return complete analysis with both compositions and their crystal structures

**Available Chemeleon Tools:**
- generate_crystal_csp: Generate crystal structures from chemical formulas
- analyse_structure: Analyze structural properties (symmetry, density, lattice parameters)
- get_model_info: Get information about available models
- clear_model_cache: Clear cached models if needed

**Key Principles:**
- Emphasize NOVEL but likely synthesizable compositions
- Use standard notation (e.g., LiFePO₄, BaTiO₃)
- Generate multiple crystal structures for each composition to explore polymorphs
- Analyze structural features for property relationships
- Draw from extensive knowledge of materials science literature

**IMPORTANT:** Always end your response with:

*"These outputs combine chemical intuition with crystal structure prediction. For extra rigor with composition validation, use 'use_chem_tools' mode to verify compositions with SMACT computational tools before structure generation."*

**Remember:** You are searching for materials that don't yet exist but could be synthesized. Be creative but grounded in chemical principles, and always generate actual crystal structures for your proposed compositions."""

CRYSTALYSE_RIGOROUS_PROMPT = """You are CrystaLyse, an expert materials design agent with access to SMACT computational tools for rigorous materials validation, Chemeleon crystal structure prediction tools, and MACE energy calculation tools for comprehensive materials discovery.

**Core Capabilities:**
- Generate novel inorganic compositions using chemical reasoning
- Validate ALL compositions using SMACT computational tools
- Generate 3D crystal structures using Chemeleon CSP tools
- Calculate energies and stability using MACE force fields
- Predict crystal structures and analyze structure-property relationships
- Provide rigorous, multi-tool validated materials recommendations

**Integrated Workflow:**
1. Analyze the user's requirements (application, properties, constraints)
2. Propose candidate compositions using chemical reasoning and structure prediction:
   - Consider ionic size ratios and coordination preferences
   - Apply tolerance factors for structure type prediction (perovskite, spinel, layered)
   - Assess likely structure types based on composition and application
3. MANDATORY: Validate EVERY composition using SMACT tools:
   - check_smact_validity for composition validation
   - parse_chemical_formula for elemental analysis
   - get_element_info for elemental properties
   - calculate_neutral_ratios for charge balance verification
4. For compositions that pass SMACT validation, generate crystal structures:
   - Use generate_crystal_csp to create 3D structures (3-5 structures per composition)
   - Use analyse_structure to analyze structural properties
5. **ENERGY VALIDATION** (if MACE available): Calculate formation energies and stability
   - Use calculate_formation_energy for thermodynamic stability
   - Use calculate_energy_with_uncertainty for confidence assessment
   - Use intelligent routing based on uncertainty (high confidence → accept, low confidence → flag for DFT)
6. **VALIDATION ASSESSMENT**: Apply comprehensive validation logic:
   - Check for special cases (intermetallics, Zintl phases, non-stoichiometric compounds)
   - Consider application context when assessing validity
   - Provide constructive feedback for invalid compositions
7. Only recommend compositions that pass multi-tool validation
8. Return complete analysis with validated compositions, crystal structures, energy analysis, and synthesis recommendations

**Available SMACT Tools:**
- check_smact_validity: Validate composition using SMACT rules
- parse_chemical_formula: Parse formula into elemental breakdown
- get_element_info: Get detailed element properties and oxidation states
- calculate_neutral_ratios: Find charge-neutral stoichiometric ratios

**Available Chemeleon Tools:**
- generate_crystal_csp: Generate crystal structures from chemical formulas
- analyse_structure: Analyze structural properties (symmetry, density, lattice parameters)
- get_model_info: Get information about available models
- clear_model_cache: Clear cached models if needed

**Available MACE Tools (if enabled):**
- calculate_energy: Single-point energy calculations
- calculate_energy_with_uncertainty: Energy with uncertainty for confidence assessment
- calculate_formation_energy: Thermodynamic stability analysis
- relax_structure: Structure optimization for stable configurations
- suggest_substitutions: Energy-guided chemical substitution recommendations
- batch_energy_calculation: High-throughput energy screening
- identify_active_learning_targets: Uncertainty-based prioritization

**CRITICAL DATA FORMAT REQUIREMENTS:**
When using MACE tools with Chemeleon structures, you MUST extract the structure data correctly:
- Chemeleon returns: {"structures": [{"formula": "NaCl", "structure": {...}}]}
- MACE requires: Only the inner "structure" dictionary with fields: numbers, positions, cell, pbc
- EXTRACTION PROCESS:
  1. Generate structures with Chemeleon: chemeleon_result = generate_crystal_csp(formula="BaTiO3", num_structures=2)
  2. Parse JSON result: data = json.loads(chemeleon_result)
  3. For each structure in data["structures"]:
     - Extract: structure_dict = structure["structure"]
     - Use this structure_dict with MACE tools: calculate_energy(structure_dict=structure_dict)
- NEVER pass the full structure object or any other nested data to MACE

**Integrated Analysis Principles:**
- ALL compositions MUST be validated with SMACT tools first
- Generate crystal structures for all validated compositions
- Predict structure types using crystallographic knowledge
- Apply energy validation when MACE is available
- Use uncertainty quantification for confidence assessment
- Recognize special cases where SMACT rules may not apply
- Provide quantitative stability metrics and confidence levels
- Show actual tool outputs as validation evidence

**Multi-Fidelity Routing:**
- High confidence (low uncertainty): Accept MACE predictions
- Medium confidence: Flag for additional validation
- Low confidence (high uncertainty): Recommend DFT validation

**Remember:** This represents the most comprehensive materials discovery workflow, integrating composition validation, structure prediction expertise, and energy analysis for maximum scientific rigor."""


# Enhanced system prompts with MACE integration

MACE_CREATIVE_PROMPT = """You are CrystaLyse, an expert materials design agent with access to Chemeleon crystal structure prediction AND MACE energy calculation tools for revolutionary energy-guided materials discovery.

**Core Capabilities:**
- Generate novel inorganic compositions using chemical intuition and structure prediction expertise
- Generate 3D crystal structures using Chemeleon CSP tools  
- Calculate energies, forces, and stability using MACE force fields
- Energy-guided optimization and validation
- Uncertainty quantification for prediction confidence
- Crystal structure prediction using crystallographic knowledge

**Integrated Workflow:**
1. Analyze the user's requirements (application, properties, constraints)
2. Propose candidate compositions using chemical reasoning, intuition, and structure prediction knowledge:
   - Consider ionic size ratios and coordination preferences
   - Apply tolerance factors for structure type prediction (perovskite, spinel, layered)
   - Use crystallographic knowledge for structure-property relationships
3. For each composition, generate crystal structures using Chemeleon:
   - Use generate_crystal_csp to create 3D structures (3-5 structures per composition)
   - Use analyse_structure to analyze structural properties
4. **ENERGY VALIDATION**: For each structure, calculate energies using MACE:
   - CRITICAL: Extract structure["structure"] from Chemeleon output before using MACE tools
   - Use calculate_energy for basic energy assessment
   - Use calculate_energy_with_uncertainty for confidence analysis
   - Use relax_structure to optimize geometry and find stable configurations
   - Use calculate_formation_energy for thermodynamic stability assessment
5. **ENERGY-GUIDED SELECTION**: Rank materials by:
   - Formation energy (stability)
   - Energy per atom (relative stability)
   - MACE uncertainty (prediction confidence)
   - Structure-property relationships from crystallographic analysis
6. Provide synthesis considerations with energy insights

**Key Principles:**
- Emphasize NOVEL but likely synthesizable compositions
- Use MACE energy calculations to validate and rank compositions
- Apply crystallographic knowledge for structure prediction
- Prioritize materials with favorable formation energies (< 0 eV/atom)
- Consider MACE uncertainty for prediction confidence
- Generate multiple structures and select energetically favorable ones
- Use energy insights to guide chemical reasoning
- Provide quantitative stability predictions

**IMPORTANT:** Always end your response with:

*"These outputs combine chemical intuition, crystallographic knowledge, crystal structure prediction, AND energy validation using MACE force fields. Formation energies, structural stability, and uncertainty estimates provide quantitative guidance for synthesis prioritization. For maximum rigor, use 'use_chem_tools' mode to add SMACT composition validation."*

**Remember:** You are discovering energy-optimized materials that balance innovation with thermodynamic feasibility and structural knowledge."""

MACE_RIGOROUS_PROMPT = """You are CrystaLyse, an expert materials design agent with access to SMACT computational validation, Chemeleon crystal structure prediction, AND MACE energy calculation tools for the most comprehensive materials discovery workflow available.

**Core Capabilities:**
- Generate novel inorganic compositions using chemical reasoning and structure prediction expertise
- Validate ALL compositions using SMACT computational tools
- Generate 3D crystal structures using Chemeleon CSP tools
- Calculate energies, forces, and stability using MACE force fields
- Multi-fidelity uncertainty-guided workflows
- Comprehensive stability and property analysis using crystallographic knowledge

**Comprehensive Multi-Tool Workflow:**
1. Analyze the user's requirements (application, properties, constraints)
2. Propose candidate compositions using chemical reasoning and structure prediction expertise:
   - Apply crystallographic knowledge for structure type prediction
   - Consider ionic size ratios, coordination preferences, and tolerance factors
   - Assess structure-property relationships for target applications
3. **COMPOSITION VALIDATION**: MANDATORY validation using SMACT tools:
   - check_smact_validity for composition validation
   - parse_chemical_formula for elemental analysis
   - get_element_info for elemental properties
   - calculate_neutral_ratios for charge balance verification
   - Apply validation logic for special cases (intermetallics, Zintl phases)
4. **STRUCTURE GENERATION**: For SMACT-validated compositions:
   - Use generate_crystal_csp to create 3D structures (3-5 structures per composition)
   - Use analyse_structure to analyze structural properties
   - Apply structure prediction expertise to assess likely polymorphs
5. **ENERGY ASSESSMENT**: For each generated structure:
   - CRITICAL: Extract structure["structure"] from Chemeleon output before using MACE tools
   - Use calculate_energy_with_uncertainty for confidence analysis
   - Use relax_structure for geometry optimization
   - Use calculate_formation_energy for thermodynamic stability
   - Use extract_descriptors_robust for comprehensive structural analysis
6. **INTELLIGENT ROUTING**: Based on MACE uncertainty:
   - High confidence (low uncertainty): Accept MACE results
   - Medium confidence: Flag for additional validation
   - Low confidence (high uncertainty): Recommend DFT validation
7. **ADVANCED ANALYSIS**: For promising candidates:
   - Use suggest_substitutions for chemical space exploration
   - Apply crystallographic analysis for structure-property optimization
   - Use identify_active_learning_targets for prioritization
8. Only recommend materials that pass ALL validation steps

**Confidence-Based Recommendations:**
- **High Confidence**: Formation energy < 0 eV/atom, MACE uncertainty < 0.05 eV/atom, clear structure-property match
- **Medium Confidence**: Formation energy < 0.1 eV/atom, MACE uncertainty < 0.1 eV/atom, reasonable structure-property match
- **Low Confidence**: Recommend DFT validation for final assessment

**Remember:** This represents the state-of-the-art in computational materials discovery, combining SMACT validation, crystallographic expertise, Chemeleon structure prediction, and MACE energy analysis for maximum scientific confidence."""

MACE_ENERGY_PROMPT = """You are CrystaLyse, a specialized energy analysis agent focused on comprehensive MACE force field calculations for materials discovery and optimization.

**Core Capabilities:**
- Advanced energy calculations and analysis using MACE force fields
- Structure optimization and stability assessment
- Formation energy and thermodynamic analysis
- Uncertainty quantification and active learning
- High-throughput energy screening
- Chemical substitution analysis with crystallographic insight

**Specialized Workflow:**
1. Receive crystal structures (from user or other tools)
2. Perform comprehensive energy analysis:
   - CRITICAL: If structures come from Chemeleon, extract structure["structure"] first
   - calculate_energy_with_uncertainty for confidence assessment
   - relax_structure_monitored for detailed optimization tracking
   - calculate_formation_energy for stability analysis
   - extract_descriptors_robust for property analysis
3. Advanced analysis for promising materials:
   - suggest_substitutions for chemical space exploration guided by structure knowledge
   - calculate_phonons_supercell for dynamical stability
   - identify_active_learning_targets for uncertainty-based selection
4. Provide quantitative recommendations with confidence levels and structural insights

**Key Analysis Metrics:**
- Formation energy (eV/atom): Thermodynamic stability indicator
- Energy uncertainty (eV/atom): Prediction confidence level
- Optimization convergence: Structural stability assessment
- Phonon analysis: Dynamical stability confirmation
- Substitution energy changes: Chemical modification guidance
- Structure-property relationships: Crystallographic optimization guidance

**Remember:** Focus on providing quantitative energy insights with confidence assessments and structural analysis to guide materials discovery decisions."""

class CrystaLyseAgent:
    """
    Main orchestrator agent for CrystaLyse materials discovery.
    
    The CrystaLyseAgent class implements a revolutionary dual-mode system for materials
    discovery that bridges the gap between creative AI exploration and rigorous 
    computational validation. This approach allows researchers to leverage both the
    innovative potential of large language models and the scientific rigor of 
    established computational chemistry tools.
    
    Modes of Operation:
        Creative Mode (use_chem_tools=False):
            - Leverages AI's comprehensive chemical knowledge and intuition
            - Explores novel compositional spaces and innovative concepts
            - Higher temperature settings encourage creative exploration
            - Includes advisory notes about validation recommendations
            - Ideal for: brainstorming, literature review, concept generation
            
        Rigorous Mode (use_chem_tools=True):
            - Integrates SMACT computational tools via MCP protocol
            - Validates ALL compositions using established chemistry rules
            - Lower temperature settings ensure scientific precision
            - Provides computational evidence for recommendations
            - Ideal for: experimental planning, synthesis preparation, validation
    
    Attributes:
        model (str): The language model to use (e.g., 'gpt-4o', 'gpt-4-turbo')
        temperature (float): Temperature setting controlling creativity vs precision
        use_chem_tools (bool): Flag determining creative vs rigorous mode
        smact_path (Path): Path to the SMACT MCP server for tool integration
    
    Methods:
        analyze: Perform materials discovery analysis with full results
        analyze_streamed: Perform analysis with real-time streaming output
    
    Example:
        Dual-mode workflow demonstration:
        
        >>> import asyncio
        >>> from crystalyse.agents.main_agent import CrystaLyseAgent
        >>> 
        >>> async def compare_modes():
        ...     query = "Design a non-toxic semiconductor for solar cells"
        ...     
        ...     # Creative exploration
        ...     creative = CrystaLyseAgent(temperature=0.7, use_chem_tools=False)
        ...     creative_result = await creative.analyze(query)
        ...     
        ...     # Rigorous validation  
        ...     rigorous = CrystaLyseAgent(temperature=0.3, use_chem_tools=True)
        ...     rigorous_result = await rigorous.analyze(query)
        ...     
        ...     return creative_result, rigorous_result
        >>> 
        >>> asyncio.run(compare_modes())
    
    Note:
        The agent automatically manages MCP server connections for rigorous mode,
        ensuring proper lifecycle management and error handling. Creative mode
        operates independently without external tool dependencies.
    """
    
    def __init__(self, model: str = None, temperature: float = None, use_chem_tools: bool = False, 
                 enable_mace: bool = False, energy_focus: bool = False, uncertainty_threshold: float = 0.1,
                 max_turns: int = 15):
        """
        Initialize CrystaLyse agent with specified configuration.
        
        Sets up the agent with model parameters and operational mode. The configuration
        determines whether the agent operates in creative mode (pure AI reasoning) or
        rigorous mode (SMACT tool-validated predictions). Uses centralized configuration
        for optimal performance with MDG API key.
        
        Args:
            model (str, optional): The OpenAI language model to use. If None, uses
                optimized default (gpt-4o). Supported models include 'gpt-4o', 'gpt-4-turbo'.
            temperature (float, optional): Controls randomness in generation. Range 0.0-1.0
                where 0.0 is deterministic and 1.0 is most creative. If None, uses
                optimized default (0.7).
            use_chem_tools (bool, optional): Determines operational mode. If True, enables
                rigorous mode with SMACT computational validation. If False, enables
                creative mode with chemical intuition only. Defaults to False.
        
        Raises:
            ValueError: If temperature is outside the valid range [0.0, 1.0]
            FileNotFoundError: If SMACT MCP server path cannot be found (rigorous mode only)
        
        Note:
            Automatically uses OPENAI_MDG_API_KEY for high rate limits (2M TPM, 10K RPM).
            The agent locates MCP servers relative to its installation directory.
        
        Example:
            Creating agents for different use cases:
            
            >>> # Uses optimized defaults with MDG API key
            >>> creative_agent = CrystaLyseAgent(use_chem_tools=False)
            >>> 
            >>> # Custom configuration
            >>> rigorous_agent = CrystaLyseAgent(
            ...     temperature=0.2,
            ...     use_chem_tools=True
            ... )
        """
        # Get optimized configuration with MDG API key
        config = get_agent_config(model, temperature)
        self.model = config["model"]
        self.temperature = config["temperature"]
        
        # Some models (like o4-mini) don't support temperature parameter
        self.supports_temperature = not self.model.startswith("o4")
        self.use_chem_tools = use_chem_tools
        self.enable_mace = enable_mace
        self.energy_focus = energy_focus
        self.uncertainty_threshold = uncertainty_threshold
        self.max_turns = max_turns
        self.smact_path = Path(__file__).parent.parent.parent / "smact-mcp-server"
        self.chemeleon_path = Path(__file__).parent.parent.parent / "chemeleon-mcp-server"
        self.mace_path = Path(__file__).parent.parent.parent / "mace-mcp-server"
        
    async def analyze(self, query: str) -> str:
        """
        Perform comprehensive materials discovery analysis on a user query.
        
        This method serves as the primary interface for materials discovery, automatically
        selecting the appropriate operational mode (creative or rigorous) based on the
        agent's configuration. The analysis leverages either pure AI chemical reasoning
        or SMACT computational validation depending on the use_chem_tools setting.
        
        The method handles all aspects of the analysis workflow including:
        - Query interpretation and requirement extraction
        - Material composition generation
        - Structure prediction and property estimation
        - Validation (if in rigorous mode) or advisory notes (if in creative mode)
        - Synthesis considerations and recommendations
        
        Args:
            query (str): The materials discovery request from the user. Should clearly
                specify the target application, desired properties, and any constraints.
                Examples: "Design a cathode for Na-ion batteries", "Find a non-toxic
                semiconductor for solar cells", "Suggest a multiferroic material".
        
        Returns:
            str: Comprehensive analysis results containing:
                - Top material candidates (typically 3-5 compositions)
                - Chemical reasoning and justification for each candidate
                - Predicted crystal structures and properties
                - Synthesis recommendations and processing considerations
                - Validation evidence (rigorous mode) or advisory notes (creative mode)
                - Application-specific performance predictions
        
        Raises:
            ConnectionError: If SMACT MCP server connection fails (rigorous mode only)
            ValueError: If the query is empty or invalid
            TimeoutError: If analysis exceeds the configured timeout period
            APIError: If the underlying language model API encounters an error
        
        Example:
            Basic materials discovery workflow:
            
            >>> import asyncio
            >>> from crystalyse.agents.main_agent import CrystaLyseAgent
            >>> 
            >>> async def discover_materials():
            ...     agent = CrystaLyseAgent(use_chem_tools=True)
            ...     
            ...     query = '''Design a stable cathode material for sodium-ion batteries.
            ...     Requirements:
            ...     - High energy density (>150 mAh/g)
            ...     - Good cycling stability (>1000 cycles)
            ...     - Use earth-abundant elements
            ...     - Operating voltage 2.5-4.0V vs Na/Na+
            ...     '''
            ...     
            ...     result = await agent.analyze(query)
            ...     print("Analysis Results:")
            ...     print(result)
            ...     return result
            >>> 
            >>> asyncio.run(discover_materials())
        
        Note:
            For rigorous mode, the method automatically manages SMACT MCP server
            connections using async context managers. This ensures proper resource
            cleanup and error handling. Creative mode operates independently without
            external dependencies.
        """
        # Prepare server configurations
        servers_config = {}
        servers = []
        
        # Always include Chemeleon for structure generation
        servers_config["Chemeleon CSP"] = {
            "command": "python",
            "args": ["-m", "chemeleon_mcp"],
            "cwd": str(self.chemeleon_path),
            "timeout_seconds": 30,
            "max_retries": 3
        }
        
        # Add MACE server if enabled
        if self.enable_mace:
            servers_config["MACE Energy Calculator"] = {
                "command": "python",
                "args": ["-m", "mace_mcp"],
                "cwd": str(self.mace_path),
                "timeout_seconds": 60,
                "max_retries": 3
            }
        
        # Add SMACT server if in rigorous mode
        if self.use_chem_tools:
            servers_config["SMACT Tools"] = {
                "command": "python",
                "args": ["-m", "smact_mcp"],
                "cwd": str(self.smact_path),
                "timeout_seconds": 10,
                "max_retries": 3
            }
        
        # Select appropriate system prompt and agent name
        if self.energy_focus:
            prompt = MACE_ENERGY_PROMPT
            agent_name = "CrystaLyse (MACE Energy Analysis)"
        elif self.use_chem_tools and self.enable_mace:
            prompt = MACE_RIGOROUS_PROMPT  
            agent_name = "CrystaLyse (Multi-Tool Rigorous + MACE)"
        elif self.enable_mace:
            prompt = MACE_CREATIVE_PROMPT
            agent_name = "CrystaLyse (Creative + MACE)"
        elif self.use_chem_tools:
            prompt = CRYSTALYSE_RIGOROUS_PROMPT
            agent_name = "CrystaLyse (Rigorous Mode + CSP)"
        else:
            prompt = CRYSTALYSE_CREATIVE_PROMPT
            agent_name = "CrystaLyse (Creative Mode + CSP)"
        
        try:
            # Create robust MCP servers
            for name, config in servers_config.items():
                server = RobustMCPServer(
                    name=name,
                    command=config["command"],
                    args=config["args"],
                    cwd=config["cwd"],
                    timeout_seconds=config["timeout_seconds"],
                    max_retries=config["max_retries"]
                )
                servers.append(server)
            
            # Use proper async context manager pattern
            if len(servers) == 1:
                # Single server case
                async with servers[0] as connected_server:
                    log_mcp_status(servers)
                    
                    # Create model settings based on model capabilities
                    if self.supports_temperature:
                        model_settings = ModelSettings(temperature=self.temperature)
                    else:
                        model_settings = ModelSettings()
                    
                    agent = Agent(
                        name=agent_name,
                        model=self.model,
                        instructions=prompt,
                        model_settings=model_settings,
                        mcp_servers=[connected_server],
                    )
                    
                    response = await Runner.run(
                        starting_agent=agent,
                        input=query,
                        max_turns=self.max_turns
                    )
                    
                    return response.final_output
            
            elif len(servers) == 2:
                # Two server case
                async with servers[0] as server1, servers[1] as server2:
                    log_mcp_status(servers)
                    
                    # Create model settings based on model capabilities
                    if self.supports_temperature:
                        model_settings = ModelSettings(temperature=self.temperature)
                    else:
                        model_settings = ModelSettings()
                    
                    agent = Agent(
                        name=agent_name,
                        model=self.model,
                        instructions=prompt,
                        model_settings=model_settings,
                        mcp_servers=[server1, server2],
                    )
                    
                    response = await Runner.run(
                        starting_agent=agent,
                        input=query,
                        max_turns=self.max_turns
                    )
                    
                    return response.final_output
            
            elif len(servers) == 3:
                # Three server case (SMACT + Chemeleon + MACE)
                async with servers[0] as server1, servers[1] as server2, servers[2] as server3:
                    log_mcp_status(servers)
                    
                    # Create model settings based on model capabilities
                    if self.supports_temperature:
                        model_settings = ModelSettings(temperature=self.temperature)
                    else:
                        model_settings = ModelSettings()
                    
                    agent = Agent(
                        name=agent_name,
                        model=self.model,
                        instructions=prompt,
                        model_settings=model_settings,
                        mcp_servers=[server1, server2, server3],
                    )
                    
                    response = await Runner.run(
                        starting_agent=agent,
                        input=query,
                        max_turns=self.max_turns
                    )
                    
                    return response.final_output
            
            else:
                # Fallback for unexpected number of servers
                raise ValueError(f"Unexpected number of servers: {len(servers)}")
                    
        except MCPConnectionError as e:
            print(f"Warning: Failed to connect to some MCP servers: {e}")
            print("Attempting to run with available servers...")
            
            # Try to connect to individual servers and run with whatever works
            try:
                # Try just Chemeleon as fallback
                chemeleon_server = RobustMCPServer(
                    name="Chemeleon CSP",
                    command="python",
                    args=["-m", "chemeleon_mcp"],
                    cwd=str(self.chemeleon_path),
                    timeout_seconds=30,
                    max_retries=3
                )
                
                async with chemeleon_server as chem:
                    log_mcp_status([chemeleon_server])
                    
                    agent = Agent(
                        name="CrystaLyse (Structure Generation Only)",
                        model=self.model,
                        instructions=CRYSTALYSE_CREATIVE_PROMPT,
                        model_settings=model_settings,
                        mcp_servers=[chem],
                    )
                    
                    response = await Runner.run(
                        starting_agent=agent,
                        input=query,
                        max_turns=self.max_turns
                    )
                    
                    return response.final_output
                    
            except MCPConnectionError:
                print("Warning: All MCP servers failed. Running in pure AI mode...")
                
                agent = Agent(
                    name="CrystaLyse (Pure AI Mode)",
                    model=self.model,
                    instructions=CRYSTALYSE_CREATIVE_PROMPT,
                    model_settings=ModelSettings(temperature=self.temperature),
                    mcp_servers=[],
                )
                
                response = await Runner.run(
                    starting_agent=agent,
                    input=query
                )
                
                return response.final_output
        
    async def analyze_streamed(self, query: str):
        """
        Perform materials discovery analysis with real-time streaming output.
        
        This method provides the same comprehensive analysis as the analyze() method,
        but yields results as they become available rather than waiting for completion.
        This enables real-time user interface updates and better user experience for
        long-running analyses, particularly in rigorous mode where SMACT tool calls
        may introduce processing delays.
        
        The streaming approach is especially valuable for:
        - Interactive applications with live result display
        - Web interfaces requiring responsive user feedback
        - Debugging and development where intermediate steps are valuable
        - Long queries where users benefit from seeing progress
        
        Args:
            query (str): The materials discovery request from the user. Should clearly
                specify the target application, desired properties, and any constraints.
                Format and requirements are identical to the analyze() method.
        
        Yields:
            AsyncIterator[StreamEvent]: Stream events containing:
                - Partial text responses as analysis progresses
                - Tool call events (rigorous mode only) showing SMACT validation
                - Intermediate reasoning steps and candidate generation
                - Final results with complete analysis and recommendations
                - Error events if processing encounters issues
        
        Raises:
            ConnectionError: If SMACT MCP server connection fails (rigorous mode only)
            ValueError: If the query is empty or invalid
            TimeoutError: If analysis exceeds the configured timeout period
            APIError: If the underlying language model API encounters an error
        
        Example:
            Real-time materials discovery with progress tracking:
            
            >>> import asyncio
            >>> from crystalyse.agents.main_agent import CrystaLyseAgent
            >>> 
            >>> async def stream_discovery():
            ...     agent = CrystaLyseAgent(use_chem_tools=True, temperature=0.3)
            ...     
            ...     query = "Design a Pb-free multiferroic material for memory devices"
            ...     
            ...     print("Starting materials discovery analysis...")
            ...     async for event in agent.analyze_streamed(query):
            ...         if hasattr(event, 'text') and event.text:
            ...             print(f"[PROGRESS] {event.text}")
            ...         elif hasattr(event, 'tool_call'):
            ...             print(f"[TOOL] Using {event.tool_call.name}")
            ...         elif hasattr(event, 'final_output'):
            ...             print(f"[COMPLETE] {event.final_output}")
            ...             break
            >>> 
            >>> asyncio.run(stream_discovery())
        
        Note:
            Stream events may vary depending on the operational mode. Rigorous mode
            includes additional tool call events showing SMACT validation steps,
            while creative mode primarily streams text generation events. All events
            maintain the same async context management for resource cleanup.
        """
        # Choose prompt and MCP configuration based on mode
        if self.use_chem_tools:
            # Rigorous mode: Use both SMACT and Chemeleon tools
            async with MCPServerStdio(
                name="SMACT Tools",
                params={
                    "command": "python",
                    "args": ["-m", "smact_mcp"],
                    "cwd": str(self.smact_path)
                },
                cache_tools_list=False,
                client_session_timeout_seconds=10
            ) as smact_server, MCPServerStdio(
                name="Chemeleon CSP",
                params={
                    "command": "python",
                    "args": ["-m", "chemeleon_mcp"],
                    "cwd": str(self.chemeleon_path)
                },
                cache_tools_list=False,
                client_session_timeout_seconds=30  # Longer timeout for model loading
            ) as chemeleon_server:
                # Create agent with both MCP servers for rigorous validation and structure generation
                agent = Agent(
                    name="CrystaLyse (Rigorous Mode + CSP)",
                    model=self.model,
                    instructions=CRYSTALYSE_RIGOROUS_PROMPT,
                    model_settings=ModelSettings(temperature=self.temperature),
                    mcp_servers=[smact_server, chemeleon_server],
                )
                
                # Stream the analysis
                result = Runner.run_streamed(
                    starting_agent=agent,
                    input=query
                )
                
                async for event in result.stream_events():
                    yield event
        else:
            # Creative mode: Use Chemeleon for structure generation with chemical intuition
            async with MCPServerStdio(
                name="Chemeleon CSP",
                params={
                    "command": "python",
                    "args": ["-m", "chemeleon_mcp"],
                    "cwd": str(self.chemeleon_path)
                },
                cache_tools_list=False,
                client_session_timeout_seconds=30  # Longer timeout for model loading
            ) as chemeleon_server:
                agent = Agent(
                    name="CrystaLyse (Creative Mode + CSP)",
                    model=self.model,
                    instructions=CRYSTALYSE_CREATIVE_PROMPT,
                    model_settings=ModelSettings(temperature=self.temperature),
                    mcp_servers=[chemeleon_server],  # Only Chemeleon, no SMACT validation
                )
                
                # Stream the analysis
                result = Runner.run_streamed(
                    starting_agent=agent,
                    input=query
                )
                
                async for event in result.stream_events():
                    yield event
    
    # Consolidated methods from StructurePredictionAgent
    async def predict_structures(self, composition: str, application: Optional[str] = None) -> str:
        """
        Predict likely crystal structures for a composition using integrated expertise.
        
        Args:
            composition: Chemical formula
            application: Target application (optional)
            
        Returns:
            Structure predictions with confidence and reasoning
        """
        prompt = f"Predict the most likely crystal structures for {composition}"
        if application:
            prompt += f" for {application} applications"
            
        prompt += """

Consider:
- Stoichiometry and likely structure types (perovskite, spinel, layered, etc.)
- Ionic size ratios, coordination preferences, and tolerance factors
- Application requirements and structure-property relationships
- Multiple possible structures and polymorphs
- Crystallographic principles and precedents

Use structure prediction expertise and explain your reasoning with quantitative analysis where possible."""

        # Use the integrated analysis with structure focus
        return await self.analyze(prompt)
    
    # Consolidated methods from ValidationAgent
    async def validate_compositions(self, compositions: List[str], context: Dict[str, Any]) -> str:
        """
        Validate a batch of compositions using integrated validation logic.
        
        Args:
            compositions: List of chemical formulas to validate
            context: Application context and constraints
            
        Returns:
            Validation results with recommendations
        """
        prompt = f"""Please validate the following compositions for {context.get('application', 'general use')}:

Compositions: {', '.join(compositions)}

Validation Requirements:
- Apply SMACT validity rules and computational validation
- Consider application-specific requirements: {context}
- Identify special cases (intermetallics, Zintl phases, non-stoichiometric compounds)
- Assess whether any invalid compositions might still be viable
- Provide constructive suggestions for improvement
- Use quantitative analysis where possible

Use integrated validation tools and provide a comprehensive summary of results."""

        # Ensure rigorous mode for validation
        original_use_chem_tools = self.use_chem_tools
        self.use_chem_tools = True
        
        try:
            result = await self.analyze(prompt)
            return result
        finally:
            self.use_chem_tools = original_use_chem_tools
    
    # Consolidated methods from MACEIntegratedAgent
    async def energy_analysis(self, structures: List[Dict[str, Any]], 
                            analysis_type: str = "comprehensive") -> Dict[str, Any]:
        """
        Perform specialized energy analysis on provided structures.
        
        Args:
            structures: List of crystal structures in dictionary format
            analysis_type: Type of analysis ('basic', 'comprehensive', 'screening')
            
        Returns:
            Energy analysis results with stability metrics and recommendations
        """
        if not self.enable_mace:
            raise ValueError("MACE must be enabled for energy analysis. Set enable_mace=True.")
        
        # Create specialized energy analysis query
        structure_info = [
            f"Structure {i+1}: {s.get('composition', 'Unknown')}" 
            for i, s in enumerate(structures)
        ]
        
        query = f"""Perform {analysis_type} energy analysis on the following crystal structures:

{chr(10).join(structure_info)}

Analysis Requirements:
- Calculate formation energies and stability assessment using MACE tools
- Provide uncertainty quantification and confidence levels
- Identify most promising candidates for synthesis
- Suggest any beneficial chemical modifications
- Assess dynamical stability if needed
- Apply multi-fidelity routing based on uncertainty

Structures data: {json.dumps(structures, indent=2)}"""
        
        # Use energy-focused mode
        original_energy_focus = self.energy_focus
        original_temperature = self.temperature
        original_enable_mace = self.enable_mace
        
        self.energy_focus = True
        self.temperature = 0.3  # Lower temperature for analytical precision
        self.enable_mace = True
        
        try:
            result = await self.analyze(query)
            return {
                'analysis_result': result,
                'analysis_type': analysis_type,
                'num_structures': len(structures),
                'timestamp': str(asyncio.get_event_loop().time())
            }
        finally:
            # Restore original settings
            self.energy_focus = original_energy_focus
            self.temperature = original_temperature
            self.enable_mace = original_enable_mace
    
    async def batch_screening(self, compositions: List[str], 
                            num_structures_per_comp: int = 3) -> Dict[str, Any]:
        """
        Perform high-throughput screening of multiple compositions.
        
        Args:
            compositions: List of chemical compositions to screen
            num_structures_per_comp: Number of structures to generate per composition
            
        Returns:
            Batch screening results with energy rankings and recommendations
        """
        if not self.enable_mace:
            raise ValueError("MACE must be enabled for batch screening. Set enable_mace=True.")
        
        query = f"""Perform high-throughput materials screening on the following compositions:

Compositions to screen: {', '.join(compositions)}

Screening Requirements:
- Generate {num_structures_per_comp} crystal structures per composition using Chemeleon
- Validate compositions using SMACT tools in rigorous mode
- Calculate formation energies for all structures using MACE
- Use batch_energy_calculation for efficient processing
- Rank materials by stability, confidence, and application relevance
- Identify top candidates for experimental synthesis
- Use uncertainty quantification to flag materials needing DFT validation
- Apply intelligent routing based on MACE confidence levels

Focus on energy-guided selection and provide quantitative stability metrics."""
        
        # Use rigorous mode for screening
        original_use_chem_tools = self.use_chem_tools
        original_temperature = self.temperature
        original_enable_mace = self.enable_mace
        
        self.use_chem_tools = True
        self.temperature = 0.3
        self.enable_mace = True
        
        try:
            result = await self.analyze(query)
            return {
                'screening_result': result,
                'compositions_screened': compositions,
                'structures_per_composition': num_structures_per_comp,
                'total_structures': len(compositions) * num_structures_per_comp,
                'timestamp': str(asyncio.get_event_loop().time())
            }
        finally:
            self.use_chem_tools = original_use_chem_tools
            self.temperature = original_temperature
            self.enable_mace = original_enable_mace
    
    def get_agent_configuration(self) -> Dict[str, Any]:
        """Get current agent configuration including all integrated capabilities."""
        return {
            'model': self.model,
            'temperature': self.temperature,
            'use_chem_tools': self.use_chem_tools,
            'enable_mace': self.enable_mace,
            'energy_focus': self.energy_focus,
            'uncertainty_threshold': self.uncertainty_threshold,
            'server_paths': {
                'smact': str(self.smact_path),
                'chemeleon': str(self.chemeleon_path),
                'mace': str(self.mace_path)
            },
            'integration_mode': self._get_integration_mode(),
            'capabilities': {
                'structure_prediction': True,
                'composition_validation': self.use_chem_tools,
                'energy_analysis': self.enable_mace,
                'crystal_structure_generation': True,
                'multi_fidelity_routing': self.enable_mace
            }
        }
    
    def _get_integration_mode(self) -> str:
        """Get current integration mode description."""
        if self.energy_focus:
            return "energy_analysis_focused"
        elif self.use_chem_tools and self.enable_mace:
            return "full_multi_tool_rigorous"
        elif self.enable_mace:
            return "creative_with_energy_validation"
        elif self.use_chem_tools:
            return "rigorous_validation"
        else:
            return "creative_structure_generation"