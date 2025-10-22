"""
CrystaLyse Provenance System

Complete provenance capture for materials discovery with CrystaLyse.AI
"""

from .core import JSONLLogger, Event, MaterialsTracker, Material, MCPDetector
from .handlers import ProvenanceTraceHandler, EnhancedToolCall

# Note: CrystaLyseWithProvenance not imported at module level to avoid circular imports
# Import explicitly if needed: from provenance_system.integration import CrystaLyseWithProvenance

__version__ = "1.0.0"

__all__ = [
    # Core components
    'JSONLLogger',
    'Event',
    'MaterialsTracker',
    'Material',
    'MCPDetector',

    # Handlers
    'ProvenanceTraceHandler',
    'EnhancedToolCall',
]