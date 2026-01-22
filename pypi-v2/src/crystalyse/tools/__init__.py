"""CrystaLyse tools package - modular MCP tool implementations."""

# Import all tool modules
from . import chemeleon, errors, mace, models, pymatgen, smact, visualization
from .chemeleon import ChemeleonPredictor, CrystalStructure, PredictionResult
from .errors import (
    ComputationError,
    CrystaLyseToolError,
    FallbackChain,
    ResourceUnavailableError,
    ValidationError,
    with_retry,
)
from .mace import (
    EnergyResult,
    EOSResult,
    FoundationModelInfo,
    FoundationModelListResult,
    MACECalculator,
    MACEFoundationModels,
    MACEStressCalculator,
    RelaxationResult,
    StressResult,
)
from .models import MaterialProperty, ToolResult
from .pymatgen import (
    CoordinationResult,
    EnergyAboveHullResult,
    OxidationStateResult,
    PhaseDiagramAnalyzer,
    PyMatgenAnalyzer,
    SpaceGroupResult,
)

# Export key classes and functions
from .smact import (
    BandGapResult,
    CompositionFilterResult,
    CompositionValidityResult,
    DopantPredictionResult,
    DopantSuggestion,
    ElementInfo,
    MLRepresentationResult,
    SMACTCalculator,
    SMACTDopantPredictor,
    SMACTScreener,
    SMACTValidator,
    StabilityResult,
    ValidationResult,
)
from .visualization import CrystaLyseVisualizer, VisualizationResult

__all__ = [
    # Modules
    "smact",
    "chemeleon",
    "mace",
    "pymatgen",
    "visualization",
    "errors",
    "models",
    # SMACT
    "SMACTValidator",
    "SMACTCalculator",
    "SMACTDopantPredictor",
    "SMACTScreener",
    "ValidationResult",
    "StabilityResult",
    "BandGapResult",
    "ElementInfo",
    "DopantPredictionResult",
    "DopantSuggestion",
    "CompositionValidityResult",
    "MLRepresentationResult",
    "CompositionFilterResult",
    # Chemeleon
    "ChemeleonPredictor",
    "PredictionResult",
    "CrystalStructure",
    # MACE
    "MACECalculator",
    "MACEStressCalculator",
    "MACEFoundationModels",
    "EnergyResult",
    "RelaxationResult",
    "StressResult",
    "EOSResult",
    "FoundationModelInfo",
    "FoundationModelListResult",
    # PyMatgen
    "PyMatgenAnalyzer",
    "PhaseDiagramAnalyzer",
    "SpaceGroupResult",
    "CoordinationResult",
    "OxidationStateResult",
    "EnergyAboveHullResult",
    # Visualization
    "CrystaLyseVisualizer",
    "VisualizationResult",
    # Error handling
    "CrystaLyseToolError",
    "ValidationError",
    "ComputationError",
    "ResourceUnavailableError",
    "with_retry",
    "FallbackChain",
    # Base models
    "ToolResult",
    "MaterialProperty",
]
