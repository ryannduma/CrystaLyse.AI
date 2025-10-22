"""CrystaLyse tools package - modular MCP tool implementations."""

# Import all tool modules
from . import smact
from . import chemeleon
from . import mace
from . import pymatgen
from . import visualization
from . import errors
from . import models

# Export key classes and functions
from .smact import (
    SMACTValidator,
    SMACTCalculator,
    SMACTDopantPredictor,
    SMACTScreener,
    ValidationResult,
    StabilityResult,
    BandGapResult,
    ElementInfo,
    DopantPredictionResult,
    DopantSuggestion,
    CompositionValidityResult,
    MLRepresentationResult,
    CompositionFilterResult
)

from .chemeleon import (
    ChemeleonPredictor,
    PredictionResult,
    CrystalStructure
)

from .mace import (
    MACECalculator,
    MACEStressCalculator,
    MACEFoundationModels,
    EnergyResult,
    RelaxationResult,
    StressResult,
    EOSResult,
    FoundationModelInfo,
    FoundationModelListResult
)

from .pymatgen import (
    PyMatgenAnalyzer,
    PhaseDiagramAnalyzer,
    SpaceGroupResult,
    CoordinationResult,
    OxidationStateResult,
    EnergyAboveHullResult
)

from .visualization import (
    CrystaLyseVisualizer,
    VisualizationResult
)

from .errors import (
    CrystaLyseToolError,
    ValidationError,
    ComputationError,
    ResourceUnavailableError,
    with_retry,
    FallbackChain
)

from .models import (
    ToolResult,
    MaterialProperty
)

__all__ = [
    # Modules
    'smact',
    'chemeleon',
    'mace',
    'pymatgen',
    'visualization',
    'errors',
    'models',
    # SMACT
    'SMACTValidator',
    'SMACTCalculator',
    'SMACTDopantPredictor',
    'SMACTScreener',
    'ValidationResult',
    'StabilityResult',
    'BandGapResult',
    'ElementInfo',
    'DopantPredictionResult',
    'DopantSuggestion',
    'CompositionValidityResult',
    'MLRepresentationResult',
    'CompositionFilterResult',
    # Chemeleon
    'ChemeleonPredictor',
    'PredictionResult',
    'CrystalStructure',
    # MACE
    'MACECalculator',
    'MACEStressCalculator',
    'MACEFoundationModels',
    'EnergyResult',
    'RelaxationResult',
    'StressResult',
    'EOSResult',
    'FoundationModelInfo',
    'FoundationModelListResult',
    # PyMatgen
    'PyMatgenAnalyzer',
    'PhaseDiagramAnalyzer',
    'SpaceGroupResult',
    'CoordinationResult',
    'OxidationStateResult',
    'EnergyAboveHullResult',
    # Visualization
    'CrystaLyseVisualizer',
    'VisualizationResult',
    # Error handling
    'CrystaLyseToolError',
    'ValidationError',
    'ComputationError',
    'ResourceUnavailableError',
    'with_retry',
    'FallbackChain',
    # Base models
    'ToolResult',
    'MaterialProperty'
]
