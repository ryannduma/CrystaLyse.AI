"""Shared Pydantic models for all tools."""
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime

# Base models
class ToolResult(BaseModel):
    """Base class for all tool results."""
    success: bool = True
    timestamp: datetime = Field(default_factory=datetime.now)
    computation_time: Optional[float] = None
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)


class MaterialProperty(BaseModel):
    """Generic material property."""
    name: str
    value: float
    unit: str
    confidence: float = Field(ge=0.0, le=1.0, default=1.0)


# Import specific models from each module
from .smact.validators import ValidationResult, StabilityResult
from .smact.calculators import BandGapResult, ElementInfo
from .smact.dopant_predictor import DopantPredictionResult, DopantSuggestion
from .smact.screening import CompositionValidityResult, MLRepresentationResult, CompositionFilterResult
from .chemeleon.predictor import PredictionResult, CrystalStructure
from .mace.energy import EnergyResult, RelaxationResult
from .mace.stress import StressResult, EOSResult
from .mace.foundation_models import FoundationModelInfo, FoundationModelListResult
from .pymatgen.analyzer import SpaceGroupResult, CoordinationResult, OxidationStateResult
from .pymatgen.phase_diagram import EnergyAboveHullResult
from .visualization.visualizer import VisualizationResult

__all__ = [
    'ToolResult',
    'MaterialProperty',
    'ValidationResult',
    'StabilityResult',
    'BandGapResult',
    'ElementInfo',
    'DopantPredictionResult',
    'DopantSuggestion',
    'CompositionValidityResult',
    'MLRepresentationResult',
    'CompositionFilterResult',
    'PredictionResult',
    'CrystalStructure',
    'EnergyResult',
    'RelaxationResult',
    'StressResult',
    'EOSResult',
    'FoundationModelInfo',
    'FoundationModelListResult',
    'SpaceGroupResult',
    'CoordinationResult',
    'OxidationStateResult',
    'EnergyAboveHullResult',
    'VisualizationResult'
]
