"""
CrystaLyse Provenance System

Complete provenance capture for materials discovery with Crystalyse
"""

from .core import Event, JSONLLogger, Material, MaterialsTracker, MCPDetector
from .handlers import EnhancedToolCall, ProvenanceTraceHandler

# Note: CrystaLyseWithProvenance not imported at module level to avoid circular imports
# Import explicitly if needed: from provenance_system.integration import CrystaLyseWithProvenance

__version__ = "1.0.0"

__all__ = [
    # Core components
    "JSONLLogger",
    "Event",
    "MaterialsTracker",
    "Material",
    "MCPDetector",
    # Handlers
    "ProvenanceTraceHandler",
    "EnhancedToolCall",
]
