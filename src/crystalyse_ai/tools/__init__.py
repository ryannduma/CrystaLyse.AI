"""
CrystaLyse.AI Chemistry Tools

This module contains the chemistry computation tools used by the MCP servers:
- Chemeleon: Crystal structure prediction and generation
- MACE: Materials energetics and property calculation  
- SMACT: Compositional screening and feasibility analysis
- Visualization: 3D structure visualization and analysis plots
"""

# Make tools available for import
try:
    from . import chemeleon
    CHEMELEON_AVAILABLE = True
except ImportError:
    CHEMELEON_AVAILABLE = False

try:
    from . import mace
    MACE_AVAILABLE = True
except ImportError:
    MACE_AVAILABLE = False

try:
    from . import smact
    SMACT_AVAILABLE = True
except ImportError:
    SMACT_AVAILABLE = False

try:
    from . import visualization
    VISUALIZATION_AVAILABLE = True
except ImportError:
    VISUALIZATION_AVAILABLE = False

__all__ = ["chemeleon", "mace", "smact", "visualization"]