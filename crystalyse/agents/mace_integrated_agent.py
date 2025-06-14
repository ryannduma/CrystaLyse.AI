"""
MACE-integrated CrystaLyse agent for energy-guided materials discovery.

This module implements the revolutionary MACE-integrated materials discovery system
that combines chemical intuition, computational validation, crystal structure prediction,
and energy calculations in comprehensive multi-fidelity workflows.

Key Features:
    - Energy-guided materials discovery using MACE force fields
    - Multi-fidelity workflows (MACE → DFT routing based on uncertainty)
    - Comprehensive validation with SMACT + MACE validation
    - Crystal structure prediction with Chemeleon
    - Uncertainty quantification for active learning
    - Batch processing for high-throughput screening
    - Formation energy and stability analysis
    - Chemical substitution recommendations

Classes:
    MACEIntegratedAgent: Complete energy-guided materials discovery agent
    
Constants:
    MACE_CREATIVE_PROMPT: Creative mode with energy validation
    MACE_RIGOROUS_PROMPT: Rigorous mode with full multi-tool validation
    MACE_ENERGY_PROMPT: Specialized energy analysis mode
"""

from agents import Agent, Runner
from agents.mcp import MCPServerStdio
from agents.model_settings import ModelSettings
import os
try:
    from .mcp_utils import RobustMCPServer, MCPConnectionError, log_mcp_status, create_mcp_servers
    from ..config import get_agent_config
except ImportError:
    from mcp_utils import RobustMCPServer, MCPConnectionError, log_mcp_status, create_mcp_servers
    from config import get_agent_config
from pathlib import Path
from typing import Optional, Dict, Any, List
import json
import asyncio

try:
    from .main_agent import CrystaLyseAgent
except ImportError:
    from main_agent import CrystaLyseAgent


# Enhanced system prompts with MACE integration

MACE_CREATIVE_PROMPT = """You are CrystaLyse, an expert materials design agent with access to Chemeleon crystal structure prediction AND MACE energy calculation tools for revolutionary energy-guided materials discovery.

**Core Capabilities:**
- Generate novel inorganic compositions using chemical intuition
- Generate 3D crystal structures using Chemeleon CSP tools  
- Calculate energies, forces, and stability using MACE force fields
- Energy-guided optimization and validation
- Uncertainty quantification for prediction confidence

**Workflow:**
1. Analyze the user's requirements (application, properties, constraints)
2. Propose candidate compositions using chemical reasoning and intuition
3. For each composition, generate crystal structures using Chemeleon:
   - Use generate_crystal_csp to create 3D structures (3-5 structures per composition)
   - Use analyse_structure to analyze structural properties
4. **ENERGY VALIDATION**: For each structure, calculate energies using MACE:
   - Use calculate_energy for basic energy assessment
   - Use calculate_energy_with_uncertainty for confidence analysis
   - Use relax_structure to optimize geometry and find stable configurations
   - Use calculate_formation_energy for thermodynamic stability assessment
5. **ENERGY-GUIDED SELECTION**: Rank materials by:
   - Formation energy (stability)
   - Energy per atom (relative stability)
   - MACE uncertainty (prediction confidence)
   - Structure-property relationships
6. Provide synthesis considerations with energy insights

**Available Chemeleon Tools:**
- generate_crystal_csp: Generate crystal structures from chemical formulas
- analyse_structure: Analyze structural properties (symmetry, density, lattice parameters)

**Available MACE Tools:**
- calculate_energy: Single-point energy calculations
- calculate_energy_with_uncertainty: Energy with uncertainty estimation for confidence
- relax_structure: Structure optimization to find stable configurations
- calculate_formation_energy: Thermodynamic stability from elemental references
- suggest_substitutions: Energy-guided chemical substitution recommendations
- get_server_metrics: Monitor computational resources

**Key Principles:**
- Use MACE energy calculations to validate and rank compositions
- Prioritize materials with favorable formation energies (< 0 eV/atom)
- Consider MACE uncertainty for prediction confidence
- Generate multiple structures and select energetically favorable ones
- Use energy insights to guide chemical reasoning
- Provide quantitative stability predictions

**IMPORTANT:** Always end your response with:

*"These outputs combine chemical intuition with crystal structure prediction AND energy validation using MACE force fields. Formation energies, structural stability, and uncertainty estimates provide quantitative guidance for synthesis prioritization. For maximum rigor, use 'use_chem_tools' mode to add SMACT composition validation."*

**Remember:** You are discovering energy-optimized materials that balance innovation with thermodynamic feasibility. Use MACE calculations to provide quantitative energy guidance for materials selection."""

MACE_RIGOROUS_PROMPT = """You are CrystaLyse, an expert materials design agent with access to SMACT computational validation, Chemeleon crystal structure prediction, AND MACE energy calculation tools for the most comprehensive and rigorous materials discovery workflow available.

**Core Capabilities:**
- Generate novel inorganic compositions using chemical reasoning
- Validate ALL compositions using SMACT computational tools
- Generate 3D crystal structures using Chemeleon CSP tools
- Calculate energies, forces, and stability using MACE force fields
- Multi-fidelity uncertainty-guided workflows
- Comprehensive stability and property analysis

**Multi-Fidelity Workflow:**
1. Analyze the user's requirements (application, properties, constraints)
2. Propose candidate compositions using chemical reasoning
3. **COMPOSITION VALIDATION**: MANDATORY validation using SMACT tools:
   - check_smact_validity for composition validation
   - parse_chemical_formula for elemental analysis
   - get_element_info for elemental properties
   - calculate_neutral_ratios for charge balance verification
4. **STRUCTURE GENERATION**: For SMACT-validated compositions:
   - Use generate_crystal_csp to create 3D structures (3-5 structures per composition)
   - Use analyse_structure to analyze structural properties
5. **ENERGY ASSESSMENT**: For each generated structure:
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
   - Use calculate_phonons_supercell for dynamical stability (if needed)
   - Use identify_active_learning_targets for prioritization
8. Only recommend materials that pass ALL validation steps

**Available SMACT Tools:**
- check_smact_validity: Validate composition using SMACT rules
- parse_chemical_formula: Parse formula into elemental breakdown
- get_element_info: Get detailed element properties and oxidation states
- calculate_neutral_ratios: Find charge-neutral stoichiometric ratios

**Available Chemeleon Tools:**
- generate_crystal_csp: Generate crystal structures from chemical formulas
- analyse_structure: Analyze structural properties (symmetry, density, lattice parameters)

**Available MACE Tools:**
- calculate_energy: Single-point energy calculations
- calculate_energy_with_uncertainty: Energy with uncertainty for confidence assessment
- relax_structure: Structure optimization for stable configurations
- relax_structure_monitored: Detailed optimization with convergence tracking
- calculate_formation_energy: Thermodynamic stability analysis
- suggest_substitutions: Energy-guided chemical substitution recommendations
- calculate_phonons_supercell: Dynamical stability assessment
- extract_descriptors_robust: Comprehensive structural descriptors
- identify_active_learning_targets: Uncertainty-based prioritization
- batch_energy_calculation: High-throughput energy screening
- get_server_metrics: Monitor computational performance

**Key Principles:**
- ALL compositions MUST pass SMACT validation first
- ALL structures MUST have crystal structure generation
- ALL structures MUST have MACE energy assessment
- Show actual tool outputs as validation evidence
- Use uncertainty to guide confidence levels and DFT routing
- Prioritize materials with: favorable formation energy + high MACE confidence
- Provide quantitative stability metrics and confidence levels
- Use multi-fidelity routing: MACE (fast) → DFT (accurate) based on uncertainty

**Confidence-Based Recommendations:**
- **High Confidence**: Formation energy < 0 eV/atom, MACE uncertainty < 0.05 eV/atom
- **Medium Confidence**: Formation energy < 0.1 eV/atom, MACE uncertainty < 0.1 eV/atom  
- **Low Confidence**: Recommend DFT validation for final assessment

**Remember:** This represents the state-of-the-art in computational materials discovery, combining the rigor of SMACT validation, the innovation of Chemeleon structure prediction, and the quantitative energy insights of MACE force fields for maximum scientific confidence."""

MACE_ENERGY_PROMPT = """You are CrystaLyse, a specialized energy analysis agent focused on comprehensive MACE force field calculations for materials discovery and optimization.

**Core Capabilities:**
- Advanced energy calculations and analysis using MACE force fields
- Structure optimization and stability assessment
- Formation energy and thermodynamic analysis
- Uncertainty quantification and active learning
- High-throughput energy screening
- Chemical substitution analysis

**Specialized Workflow:**
1. Receive crystal structures (from user or other tools)
2. Perform comprehensive energy analysis:
   - calculate_energy_with_uncertainty for confidence assessment
   - relax_structure_monitored for detailed optimization tracking
   - calculate_formation_energy for stability analysis
   - extract_descriptors_robust for property analysis
3. Advanced analysis for promising materials:
   - suggest_substitutions for chemical space exploration
   - calculate_phonons_supercell for dynamical stability
   - identify_active_learning_targets for uncertainty-based selection
4. Provide quantitative recommendations with confidence levels

**Available MACE Tools (Full Suite):**
- get_server_metrics: Monitor system resources and performance
- calculate_energy: Fast single-point energy calculations
- calculate_energy_with_uncertainty: Energy with uncertainty estimation
- relax_structure: Basic structure optimization
- relax_structure_monitored: Detailed optimization with convergence analysis
- calculate_formation_energy: Thermodynamic stability from elemental references
- suggest_substitutions: Energy-guided chemical substitution recommendations
- calculate_phonons_supercell: Dynamical stability assessment via phonon analysis
- identify_active_learning_targets: Uncertainty and diversity-based selection
- adaptive_batch_calculation: Resource-aware batch processing
- batch_energy_calculation: High-throughput energy screening
- extract_descriptors_robust: Comprehensive structural descriptors

**Key Analysis Metrics:**
- Formation energy (eV/atom): Thermodynamic stability indicator
- Energy uncertainty (eV/atom): Prediction confidence level
- Optimization convergence: Structural stability assessment
- Phonon analysis: Dynamical stability confirmation
- Substitution energy changes: Chemical modification guidance

**Confidence Levels:**
- **Excellent**: Formation energy < -0.1 eV/atom, uncertainty < 0.01 eV/atom
- **Good**: Formation energy < 0 eV/atom, uncertainty < 0.05 eV/atom
- **Fair**: Formation energy < 0.1 eV/atom, uncertainty < 0.1 eV/atom
- **Poor**: Formation energy > 0.1 eV/atom or uncertainty > 0.1 eV/atom

**Remember:** Focus on providing quantitative energy insights with confidence assessments to guide materials discovery decisions."""


class MACEIntegratedAgent(CrystaLyseAgent):
    """
    Revolutionary MACE-integrated materials discovery agent.
    
    This agent represents the cutting edge of computational materials discovery,
    integrating SMACT compositional validation, Chemeleon crystal structure prediction,
    and MACE energy calculations into comprehensive multi-fidelity workflows.
    
    The agent enables unprecedented energy-guided materials discovery with:
    - Quantitative stability assessment via formation energy calculations
    - Uncertainty quantification for intelligent MACE → DFT routing
    - Active learning for efficient exploration of chemical space
    - High-throughput screening with adaptive batch processing
    
    Modes of Operation:
        Creative Mode (use_chem_tools=False, enable_mace=True):
            - Chemical intuition + MACE energy validation
            - Rapid exploration with energy guidance
            - Uncertainty assessment for confidence levels
            
        Rigorous Mode (use_chem_tools=True, enable_mace=True):
            - SMACT validation + MACE energy analysis
            - Complete multi-tool validation pipeline
            - Multi-fidelity uncertainty-guided workflows
            
        Energy Analysis Mode (energy_focus=True):
            - Specialized MACE energy analysis
            - Advanced stability and property assessment
            - Detailed optimization and substitution analysis
    
    Attributes:
        enable_mace (bool): Enable MACE energy calculations
        energy_focus (bool): Enable specialized energy analysis mode
        mace_path (Path): Path to MACE MCP server
        uncertainty_threshold (float): Threshold for DFT routing recommendations
        batch_size (int): Default batch size for high-throughput calculations
    """
    
    def __init__(self, model: str = None, temperature: float = None, 
                 use_chem_tools: bool = False, enable_mace: bool = True,
                 energy_focus: bool = False, uncertainty_threshold: float = 0.1,
                 batch_size: int = 10):
        """
        Initialize MACE-integrated CrystaLyse agent with optimized configuration.
        
        Args:
            model: The OpenAI language model to use (defaults to optimized gpt-4o)
            temperature: Temperature for generation (defaults to optimized 0.7)
            use_chem_tools: Enable SMACT validation tools for rigorous mode
            enable_mace: Enable MACE energy calculations
            energy_focus: Enable specialized energy analysis mode
            uncertainty_threshold: MACE uncertainty threshold for DFT routing (eV/atom)
            batch_size: Default batch size optimized for MDG API rate limits
        """
        # Get optimized configuration with MDG API key
        config = get_agent_config(model, temperature)
        super().__init__(config["model"], config["temperature"], use_chem_tools)
        
        self.enable_mace = enable_mace
        self.energy_focus = energy_focus
        self.uncertainty_threshold = uncertainty_threshold
        # Optimize batch size for MDG API rate limits
        self.batch_size = batch_size if batch_size != 10 else (50 if config["api_configured"] else 10)
        
        # Path to MACE MCP server
        self.mace_path = Path(__file__).parent.parent.parent / "mace-mcp-server"
        
    async def analyze(self, query: str) -> str:
        """
        Perform MACE-integrated materials discovery analysis.
        
        Automatically selects the appropriate workflow based on configuration:
        - Creative + MACE: Chemical intuition with energy validation
        - Rigorous + MACE: Full multi-tool validation pipeline  
        - Energy Focus: Specialized MACE energy analysis
        
        Args:
            query: Materials discovery request with requirements and constraints
            
        Returns:
            Comprehensive analysis with energy-guided recommendations
        """
        # Prepare server configurations
        servers_config = {}
        
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
                "timeout_seconds": 60,  # Longer timeout for MACE calculations
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
        
        # Select appropriate system prompt
        if self.energy_focus:
            prompt = MACE_ENERGY_PROMPT
            agent_name = "CrystaLyse (MACE Energy Analysis)"
        elif self.use_chem_tools and self.enable_mace:
            prompt = MACE_RIGOROUS_PROMPT  
            agent_name = "CrystaLyse (Multi-Tool Rigorous + MACE)"
        elif self.enable_mace:
            prompt = MACE_CREATIVE_PROMPT
            agent_name = "CrystaLyse (Creative + MACE)"
        else:
            # Fallback to parent class behavior
            return await super().analyze(query)
        
        try:
            # Create MCP servers with robust connection handling
            mcp_servers = await create_mcp_servers(servers_config)
            log_mcp_status(mcp_servers)
            
            # Extract the actual server objects
            server_objects = [s.server for s in mcp_servers]
            
            # Create agent with connected MCP servers
            agent = Agent(
                name=agent_name,
                model=self.model,
                instructions=prompt,
                model_settings=ModelSettings(temperature=self.temperature),
                mcp_servers=server_objects,
            )
            
            # Run the analysis
            response = await Runner.run(
                starting_agent=agent,
                input=query
            )
            
            # Clean up servers
            for server in mcp_servers:
                await server.__aexit__(None, None, None)
            
            return response.final_output
            
        except MCPConnectionError as e:
            print(f"Warning: Failed to connect to some MCP servers: {e}")
            print("Attempting to run with available servers...")
            
            # Try running with whatever servers we could connect to
            if not mcp_servers:
                print("No MCP servers available. Falling back to parent class behavior.")
                return await super().analyze(query)
    
    async def analyze_streamed(self, query: str):
        """
        Perform MACE-integrated analysis with real-time streaming.
        
        Provides the same comprehensive analysis as analyze() but yields
        results as they become available for real-time user interfaces.
        
        Args:
            query: Materials discovery request
            
        Yields:
            Stream events with analysis progress and results
        """
        # Determine which MCP servers to use
        mcp_servers = []
        
        # Always include Chemeleon for structure generation
        chemeleon_server = MCPServerStdio(
            name="Chemeleon CSP",
            params={
                "command": "python",
                "args": ["-m", "chemeleon_mcp"],
                "cwd": str(self.chemeleon_path)
            },
            cache_tools_list=False,
            client_session_timeout_seconds=30
        )
        mcp_servers.append(chemeleon_server)
        
        # Add MACE server if enabled
        if self.enable_mace:
            mace_server = MCPServerStdio(
                name="MACE Energy Calculator",
                params={
                    "command": "python",
                    "args": ["-m", "mace_mcp"],
                    "cwd": str(self.mace_path)
                },
                cache_tools_list=False,
                client_session_timeout_seconds=60
            )
            mcp_servers.append(mace_server)
        
        # Add SMACT server if in rigorous mode
        if self.use_chem_tools:
            smact_server = MCPServerStdio(
                name="SMACT Tools",
                params={
                    "command": "python",
                    "args": ["-m", "smact_mcp"],
                    "cwd": str(self.smact_path)
                },
                cache_tools_list=False,
                client_session_timeout_seconds=10
            )
            mcp_servers.append(smact_server)
        
        # Select appropriate system prompt
        if self.energy_focus:
            prompt = MACE_ENERGY_PROMPT
            agent_name = "CrystaLyse (MACE Energy Analysis)"
        elif self.use_chem_tools and self.enable_mace:
            prompt = MACE_RIGOROUS_PROMPT
            agent_name = "CrystaLyse (Multi-Tool Rigorous + MACE)"
        elif self.enable_mace:
            prompt = MACE_CREATIVE_PROMPT
            agent_name = "CrystaLyse (Creative + MACE)"
        else:
            # Fallback to parent class behavior
            async for event in super().analyze_streamed(query):
                yield event
            return
        
        # Create agent with selected MCP servers
        async with asyncio.gather(*[server.__aenter__() for server in mcp_servers]):
            agent = Agent(
                name=agent_name,
                model=self.model,
                instructions=prompt,
                model_settings=ModelSettings(temperature=self.temperature),
                mcp_servers=mcp_servers,
            )
            
            # Stream the analysis
            result = Runner.run_streamed(
                starting_agent=agent,
                input=query
            )
            
            async for event in result.stream_events():
                yield event
    
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
            raise ValueError("MACE must be enabled for energy analysis")
        
        # Create specialized energy analysis query
        structure_info = [
            f"Structure {i+1}: {s.get('composition', 'Unknown')}" 
            for i, s in enumerate(structures)
        ]
        
        query = f"""Perform {analysis_type} energy analysis on the following crystal structures:

{chr(10).join(structure_info)}

Analysis Requirements:
- Calculate formation energies and stability assessment
- Provide uncertainty quantification and confidence levels
- Identify most promising candidates for synthesis
- Suggest any beneficial chemical modifications
- Assess dynamical stability if needed

Structures data: {json.dumps(structures, indent=2)}
"""
        
        # Use energy-focused mode
        original_energy_focus = self.energy_focus
        original_temperature = self.temperature
        
        self.energy_focus = True
        self.temperature = 0.3  # Lower temperature for analytical precision
        
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
            raise ValueError("MACE must be enabled for batch screening")
        
        query = f"""Perform high-throughput materials screening on the following compositions:

Compositions to screen: {', '.join(compositions)}

Screening Requirements:
- Generate {num_structures_per_comp} crystal structures per composition
- Calculate formation energies for all structures
- Use batch_energy_calculation for efficient processing
- Rank materials by stability and confidence
- Identify top candidates for experimental synthesis
- Use uncertainty quantification to flag materials needing DFT validation

Focus on energy-guided selection and provide quantitative stability metrics.
"""
        
        # Use rigorous mode for screening
        original_use_chem_tools = self.use_chem_tools
        original_temperature = self.temperature
        
        self.use_chem_tools = True
        self.temperature = 0.3
        
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
    
    def get_mace_configuration(self) -> Dict[str, Any]:
        """Get current MACE integration configuration."""
        return {
            'enable_mace': self.enable_mace,
            'energy_focus': self.energy_focus,
            'uncertainty_threshold': self.uncertainty_threshold,
            'batch_size': self.batch_size,
            'mace_path': str(self.mace_path),
            'integration_mode': self._get_integration_mode()
        }
    
    def _get_integration_mode(self) -> str:
        """Get current integration mode description."""
        if self.energy_focus:
            return "energy_analysis"
        elif self.use_chem_tools and self.enable_mace:
            return "multi_tool_rigorous"
        elif self.enable_mace:
            return "creative_with_energy"
        else:
            return "standard"