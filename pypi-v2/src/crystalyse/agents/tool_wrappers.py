"""OpenAI SDK tool wrappers with error handling."""
from agents import function_tool
from agents.tool_context import ToolContext
from typing import Any
import logging

from crystalyse.tools.errors import (
    CrystaLyseToolError,
    ValidationError,
    ComputationError
)
from crystalyse.tools.models import (
    ValidationResult,
    PredictionResult,
    EnergyResult
)

logger = logging.getLogger(__name__)


def crystalyse_error_handler(context: ToolContext, error: Exception) -> str:
    """
    Custom error handler for OpenAI SDK integration.

    Returns user-friendly error messages for the LLM.
    """
    logger.error(f"Tool error in {context.tool.name}: {error}", exc_info=True)

    if isinstance(error, ValidationError):
        return (
            "Validation service temporarily unavailable. "
            "Consider using alternative validation methods or "
            "proceeding with caution."
        )
    elif isinstance(error, ComputationError):
        return (
            "Computation failed - this might be due to complex structure. "
            "Try simplifying the input or using cached results."
        )
    elif "timeout" in str(error).lower():
        return "Operation timed out. Try with a simpler structure."
    else:
        return f"Tool encountered an error: {str(error)[:200]}"


# Wrapped tools for OpenAI SDK
@function_tool(
    failure_error_function=crystalyse_error_handler,
    name="validate_material"
)
async def validate_material_wrapped(formula: str) -> ValidationResult:
    """
    Validate material composition with comprehensive error handling.

    Args:
        formula: Chemical formula to validate

    Returns:
        Structured validation result
    """
    from crystalyse.tools.smact import SMACTValidator
    validator = SMACTValidator()
    return await validator.validate_composition_async(formula)


@function_tool(
    failure_error_function=crystalyse_error_handler,
    name="predict_structure"
)
async def predict_structure_wrapped(formula: str, num_samples: int = 1) -> PredictionResult:
    """
    Predict crystal structure with error handling.

    Args:
        formula: Chemical formula
        num_samples: Number of structures to generate

    Returns:
        Structure prediction result
    """
    from crystalyse.tools.chemeleon import ChemeleonPredictor
    predictor = ChemeleonPredictor()
    return await predictor.predict_structure(formula, num_samples=num_samples)


@function_tool(
    failure_error_function=crystalyse_error_handler,
    name="calculate_formation_energy"
)
async def calculate_formation_energy_wrapped(structure: dict) -> EnergyResult:
    """
    Calculate formation energy with error handling.

    Args:
        structure: Structure dictionary with numbers, positions, cell

    Returns:
        Energy calculation result
    """
    from crystalyse.tools.mace import MACECalculator
    calculator = MACECalculator()
    return await calculator.calculate_formation_energy(structure)
