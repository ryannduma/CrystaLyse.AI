"""
Unified Chemistry MCP Server
Integrates SMACT, Chemeleon, and MACE for a comprehensive materials discovery workflow.
"""

import asyncio
import logging
import json
from typing import List, Dict, Any, Optional
from pathlib import Path
import sys

# Add parent directories to path for importing existing tools
current_dir = Path(__file__).parent
project_root = current_dir.parent.parent.parent
# Add paths for all the old servers
sys.path.insert(0, str(project_root / "oldmcpservers" / "smact-mcp-server" / "src"))
sys.path.insert(0, str(project_root / "oldmcpservers" / "chemeleon-mcp-server" / "src"))
sys.path.insert(0, str(project_root / "oldmcpservers" / "mace-mcp-server" / "src"))
# Add path for the new converter
sys.path.insert(0, str(project_root / "crystalyse"))


from mcp.server.fastmcp import FastMCP

# Configure logging
logging.basicConfig(level=logging.INFO, stream=sys.stderr)
logger = logging.getLogger(__name__)

# Initialise unified server
mcp = FastMCP("chemistry-unified")

# --- Tool Imports ---

# Import SMACT tools
try:
    from smact_mcp.tools import smact_validity
    SMACT_AVAILABLE = True
    logger.info("SMACT tools loaded successfully")
except ImportError as e:
    logger.warning(f"SMACT tools not available: {e}")
    SMACT_AVAILABLE = False

# Import Chemeleon tools
try:
    from chemeleon_mcp.tools import generate_crystal_csp, analyse_structure
    CHEMELEON_AVAILABLE = True
    logger.info("Chemeleon tools loaded successfully")
except ImportError as e:
    logger.warning(f"Chemeleon tools not available: {e}")
    CHEMELEON_AVAILABLE = False

# Import MACE tools
try:
    from mace_mcp.tools import (
        calculate_formation_energy,
        calculate_energy,
        relax_structure,
        suggest_substitutions,
        extract_descriptors_robust,
        adaptive_batch_calculation
    )
    MACE_AVAILABLE = True
    logger.info("MACE tools loaded successfully")
except ImportError as e:
    logger.warning(f"MACE tools not available: {e}")
    MACE_AVAILABLE = False

# Import the new converter tool
try:
    from converters import convert_cif_to_mace_input
    CONVERTER_AVAILABLE = True
    logger.info("CIF to MACE converter loaded successfully")
except ImportError as e:
    logger.warning(f"CIF to MACE converter not available: {e}")
    CONVERTER_AVAILABLE = False


# --- Direct Tool Access ---

# Expose SMACT tools
if SMACT_AVAILABLE:
    @mcp.tool()
    def validate_composition_smact(composition: str) -> str:
        """Validate a chemical composition using SMACT."""
        return smact_validity(composition)

# Expose Chemeleon tools
if CHEMELEON_AVAILABLE:
    @mcp.tool()
    def generate_structures(composition: str, num_samples: int = 3) -> str:
        """Generate crystal structures for a composition using Chemeleon."""
        return generate_crystal_csp(composition, num_samples=num_samples, output_format="both")

# Expose MACE tools
if MACE_AVAILABLE:
    @mcp.tool()
    def calculate_energy_mace(structure: Dict[str, Any]) -> str:
        """Calculate formation energy using MACE."""        
        return calculate_formation_energy(structure)

# Expose the new converter tool
if CONVERTER_AVAILABLE:
    @mcp.tool()
    def convert_cif_to_mace(cif_string: str) -> Dict[str, Any]:
        """Converts a CIF string into a MACE-compatible dictionary."""
        return convert_cif_to_mace_input(cif_string)

# Import the new supercell converter tool
try:
    from converters import create_supercell_cif
    SUPERCELL_CONVERTER_AVAILABLE = True
    logger.info("Supercell converter loaded successfully")
except ImportError as e:
    logger.warning(f"Supercell converter not available: {e}")
    SUPERCELL_CONVERTER_AVAILABLE = False

# Expose the new supercell converter tool
if SUPERCELL_CONVERTER_AVAILABLE:
    @mcp.tool()
    def create_supercell(cif_string: str, supercell_matrix: List[List[int]]) -> Dict[str, Any]:
        """Creates a supercell from a CIF string and returns the supercell as a CIF string."""
        return create_supercell_cif(cif_string, supercell_matrix)


# --- Health Check ---
@mcp.tool()
async def health_check() -> Dict[str, Any]:
    """Check health of all integrated chemistry tools"""
    health = {
        "server": "chemistry-unified",
        "status": "healthy",
        "tools": {
            "smact": "available" if SMACT_AVAILABLE else "unavailable",
            "chemeleon": "available" if CHEMELEON_AVAILABLE else "unavailable",
            "mace": "available" if MACE_AVAILABLE else "unavailable",
            "converter": "available" if CONVERTER_AVAILABLE else "unavailable",
        },
    }
    if not all(health["tools"].values()):
        health["status"] = "degraded"
    return health

# --- Server Startup ---
if __name__ == "__main__":
    logger.info("Starting Chemistry Unified MCP Server")
    logger.info(f"Available tools: SMACT={SMACT_AVAILABLE}, Chemeleon={CHEMELEON_AVAILABLE}, MACE={MACE_AVAILABLE}, Converter={CONVERTER_AVAILABLE}")
    mcp.run()