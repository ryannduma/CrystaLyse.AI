"""CrystaLyse tools package - V2 skills-based tools.

This package provides tools for the MaterialsAgent including:
- Core materials science tools (SMACT, Chemeleon, MACE, PyMatgen)
- Execution tools (shell, code_runner)
- Query tools (OPTIMADE, web_search)
- Artifact tools (write_artifact, read_artifact)
"""

# Import all tool modules
from . import chemeleon, errors, mace, models, pymatgen, smact, visualization

# Import V2 tools
try:
    from .artifacts import list_artifacts, read_artifact, write_artifact
except ImportError:
    pass

try:
    from .code_runner import execute_python
except ImportError:
    pass

try:
    from .optimade import query_optimade
except ImportError:
    pass

try:
    from .shell import run_shell_command
except ImportError:
    pass

try:
    from .web_search import web_search
except ImportError:
    pass
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
    # V2 Tools
    "run_shell_command",
    "execute_python",
    "query_optimade",
    "web_search",
    "write_artifact",
    "read_artifact",
    "list_artifacts",
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
