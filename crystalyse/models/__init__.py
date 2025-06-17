"""Data models for CrystaLyse agent."""

from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from enum import Enum
from pydantic import BaseModel


class ValidationStatus(str, Enum):
    """Status of material validation."""
    VALID = "valid"
    OVERRIDE = "override"
    JUSTIFIED_EXCEPTION = "justified_exception"
    INVALID = "invalid"


@dataclass
class PredictedStructure:
    """Predicted crystal structure information."""
    structure_type: str
    confidence: float
    space_groups: List[str]
    reasoning: str
    properties: Dict[str, Any]


@dataclass
class MaterialCandidate:
    """Represents a candidate material composition."""
    formula: str
    validation_status: ValidationStatus
    novelty: str  # "Known" or "Novel"
    predicted_structures: List[PredictedStructure]
    chemical_justification: str
    synthesis_notes: Optional[str] = None
    smact_valid: Optional[bool] = None
    validation_details: Optional[Dict[str, Any]] = None
    metallicity_score: Optional[float] = None
    override_reasons: Optional[List[str]] = None


@dataclass
class ValidationResult:
    """Result from SMACT validation."""
    composition: str
    is_valid: bool
    elements: List[str]
    oxidation_states: Optional[List[int]] = None
    metallicity_score: Optional[float] = None
    pauling_test_passed: Optional[bool] = None
    charge_neutral: Optional[bool] = None
    error: Optional[str] = None


@dataclass
class CrystalAnalysisResult:
    """Final result from CrystaLyse analysis."""
    application: str
    requirements: Dict[str, Any]
    element_space: List[str]
    top_candidates: List[MaterialCandidate]
    generation_summary: Dict[str, int]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialisation."""
        return {
            "application": self.application,
            "requirements": self.requirements,
            "element_space": self.element_space,
            "top_candidates": [
                {
                    "formula": c.formula,
                    "validation_status": c.validation_status.value,
                    "novelty": c.novelty,
                    "predicted_structures": [
                        {
                            "structure_type": s.structure_type,
                            "confidence": s.confidence,
                            "space_groups": s.space_groups,
                            "reasoning": s.reasoning,
                            "properties": s.properties
                        }
                        for s in c.predicted_structures
                    ],
                    "chemical_justification": c.chemical_justification,
                    "synthesis_notes": c.synthesis_notes,
                    "smact_valid": c.smact_valid,
                    "metallicity_score": c.metallicity_score
                }
                for c in self.top_candidates
            ],
            "generation_summary": self.generation_summary
        }


class DesignConstraints(BaseModel):
    """Constraints for material design."""
    exclude_elements: List[str] = []
    prefer_elements: List[str] = []
    structure_type: Optional[str] = None
    band_gap_range: Optional[str] = None
    voltage_range: Optional[str] = None
    temperature_range: Optional[str] = None
    oxidation_states_set: str = "icsd24"
    
    class Config:
        extra = "allow"  # Allow additional fields


class ApplicationContext(BaseModel):
    """Context for application-specific material design."""
    application_type: Optional[str] = None
    key_properties: List[str] = []
    constraints: List[str] = []
    
    class Config:
        extra = "allow"