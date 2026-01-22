"""
Shared test fixtures for CrystaLyse test suite.

This module provides common fixtures used across unit, integration, and MCP server tests.
Combines patterns from SMACT, Chemeleon2, OpenAI-Agents-Python, Codex, and MCP Python SDK.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

# =============================================================================
# Async Backend Configuration (from MCP SDK pattern)
# =============================================================================


@pytest.fixture
def anyio_backend() -> str:
    """Specify asyncio backend for anyio tests."""
    return "asyncio"


# =============================================================================
# Device Detection (from Chemeleon2 pattern)
# =============================================================================


@pytest.fixture(scope="session")
def device() -> str:
    """Detect available compute device (GPU/CPU).

    Returns:
        "cuda" if GPU available, else "cpu"
    """
    try:
        import torch

        return "cuda" if torch.cuda.is_available() else "cpu"
    except ImportError:
        return "cpu"


@pytest.fixture(scope="session")
def has_gpu() -> bool:
    """Check if GPU is available."""
    try:
        import torch

        return torch.cuda.is_available()
    except ImportError:
        return False


# =============================================================================
# Skip Markers (combine patterns from all repos)
# =============================================================================


def pytest_configure(config: pytest.Config) -> None:
    """Register custom markers."""
    config.addinivalue_line("markers", "slow: marks tests as slow")
    config.addinivalue_line("markers", "requires_gpu: marks tests that require GPU")
    config.addinivalue_line("markers", "requires_api: marks tests that require real API keys")
    config.addinivalue_line("markers", "integration: marks integration tests")


@pytest.fixture(scope="session")
def skip_if_no_gpu(has_gpu: bool) -> None:
    """Skip test if GPU is not available."""
    if not has_gpu:
        pytest.skip("GPU not available")


@pytest.fixture(scope="session")
def skip_if_no_api_key() -> None:
    """Skip test if real API key is not available."""
    api_key = os.getenv("OPENAI_MDG_API_KEY", "")
    if not api_key or api_key == "fake-for-tests":
        pytest.skip("Real API key not available")


# =============================================================================
# Crystal Structure Fixtures
# =============================================================================


@pytest.fixture
def sample_perovskite_structure() -> dict[str, Any]:
    """CaTiO3 perovskite structure for testing.

    Returns:
        Dictionary with atomic numbers, positions, cell, and metadata
    """
    return {
        "numbers": [20, 22, 8, 8, 8],  # Ca, Ti, O, O, O
        "positions": [
            [0.0, 0.0, 0.0],  # Ca
            [1.95, 1.95, 1.95],  # Ti
            [1.95, 0.0, 1.95],  # O
            [0.0, 1.95, 1.95],  # O
            [1.95, 1.95, 0.0],  # O
        ],
        "cell": [
            [3.9, 0.0, 0.0],
            [0.0, 3.9, 0.0],
            [0.0, 0.0, 3.9],
        ],
        "pbc": [True, True, True],
        "formula": "CaTiO3",
        "symbols": ["Ca", "Ti", "O", "O", "O"],
    }


@pytest.fixture
def sample_spinel_structure() -> dict[str, Any]:
    """LiCoO2 layered oxide structure for testing.

    Returns:
        Dictionary with atomic numbers, positions, cell, and metadata
    """
    return {
        "numbers": [3, 27, 8, 8],  # Li, Co, O, O
        "positions": [
            [0.0, 0.0, 0.0],  # Li
            [0.0, 0.0, 2.81],  # Co
            [0.0, 0.0, 1.05],  # O
            [0.0, 0.0, 4.57],  # O
        ],
        "cell": [
            [2.82, 0.0, 0.0],
            [-1.41, 2.44, 0.0],
            [0.0, 0.0, 14.05],
        ],
        "pbc": [True, True, True],
        "formula": "LiCoO2",
        "symbols": ["Li", "Co", "O", "O"],
    }


@pytest.fixture
def invalid_structure() -> dict[str, Any]:
    """Invalid structure for testing error handling.

    Returns:
        Dictionary with invalid/missing data
    """
    return {
        "numbers": [],
        "positions": [],
        "cell": [[1, 0, 0], [0, 1, 0], [0, 0, 1]],
        "formula": "Invalid",
    }


# =============================================================================
# Mock Calculator Fixtures
# =============================================================================


@pytest.fixture
def mock_mace_calculator() -> MagicMock:
    """Mock MACE calculator to avoid GPU/model requirements.

    Returns:
        MagicMock configured to return typical MACE outputs
    """
    mock = MagicMock()
    mock.get_potential_energy.return_value = -25.5  # eV
    mock.get_forces.return_value = [[0.0, 0.0, 0.0]] * 5  # Zero forces (relaxed)
    mock.get_stress.return_value = [0.0] * 6  # Voigt notation
    return mock


@pytest.fixture
def mock_chemeleon_predictor() -> MagicMock:
    """Mock Chemeleon predictor to avoid model loading.

    Returns:
        MagicMock configured to return typical Chemeleon outputs
    """
    mock = MagicMock()
    mock.predict.return_value = {
        "numbers": [20, 22, 8, 8, 8],
        "positions": [
            [0.0, 0.0, 0.0],
            [1.95, 1.95, 1.95],
            [1.95, 0.0, 1.95],
            [0.0, 1.95, 1.95],
            [1.95, 1.95, 0.0],
        ],
        "cell": [[3.9, 0.0, 0.0], [0.0, 3.9, 0.0], [0.0, 0.0, 3.9]],
        "formula": "CaTiO3",
        "confidence": 0.85,
    }
    return mock


# =============================================================================
# Temporary Directory Fixtures
# =============================================================================


@pytest.fixture
def temp_dir() -> Path:
    """Create a temporary directory for test files.

    Yields:
        Path to temporary directory (cleaned up after test)
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def temp_memory_dir(temp_dir: Path) -> Path:
    """Create a temporary directory mimicking ~/.crystalyse structure.

    Args:
        temp_dir: Parent temporary directory

    Returns:
        Path to memory directory
    """
    memory_dir = temp_dir / ".crystalyse"
    memory_dir.mkdir(parents=True, exist_ok=True)
    return memory_dir


# =============================================================================
# Environment Variable Fixtures
# =============================================================================


@pytest.fixture
def mock_env_vars() -> dict[str, str]:
    """Provide mock environment variables for testing.

    Returns:
        Dictionary of environment variables
    """
    return {
        "OPENAI_MDG_API_KEY": "fake-test-key",
        "CRYSTALYSE_MODEL": "o4-mini",
        "CRYSTALYSE_DEBUG": "false",
        "CRYSTALYSE_ENABLE_HTML_VIZ": "false",
    }


@pytest.fixture
def patched_env(mock_env_vars: dict[str, str]):
    """Patch environment variables for a test.

    Args:
        mock_env_vars: Dictionary of environment variables to set

    Yields:
        None (env vars are patched during test)
    """
    with patch.dict(os.environ, mock_env_vars, clear=False):
        yield


# =============================================================================
# Sample Data Fixtures
# =============================================================================


@pytest.fixture
def sample_formulas() -> list[str]:
    """List of valid chemical formulas for testing.

    Returns:
        List of formula strings
    """
    return [
        "CaTiO3",  # Perovskite
        "LiCoO2",  # Layered oxide
        "BaTiO3",  # Ferroelectric perovskite
        "SrTiO3",  # Cubic perovskite
        "MgO",  # Simple oxide
        "NaCl",  # Salt
        "Fe2O3",  # Hematite
        "ZnO",  # Wurtzite
    ]


@pytest.fixture
def invalid_formulas() -> list[str]:
    """List of invalid chemical formulas for testing.

    Returns:
        List of invalid formula strings
    """
    return [
        "",  # Empty
        "XxYy",  # Invalid elements
        "123",  # Numbers only
        "Ca Ti O3",  # Spaces
        "Ca-Ti-O3",  # Dashes
    ]


# =============================================================================
# Provenance Fixtures
# =============================================================================


@pytest.fixture
def sample_tool_output() -> dict[str, Any]:
    """Sample tool output for provenance tracking.

    Uses field names recognized by the artifact tracker:
    - formation_energy, energy_per_atom, total_energy
    - band_gap, energy_above_hull, bulk_modulus
    - lattice_params, space_group_number

    Returns:
        Dictionary representing typical MCP tool output
    """
    return {
        "success": True,
        "formula": "CaTiO3",
        "total_energy": -25.5,
        "energy_per_atom": -5.1,
        "formation_energy": -1.2,
        "energy_above_hull": 0.015,
        "band_gap": 3.2,
        "forces": [[0.0, 0.0, 0.0]] * 5,
    }


@pytest.fixture
def sample_artifact_data() -> dict[str, Any]:
    """Sample artifact data for testing.

    Returns:
        Dictionary with artifact metadata
    """
    return {
        "tool_name": "mace_calculate_energy",
        "tool_call_id": "call_abc123",
        "timestamp": "2025-01-20T12:00:00Z",
        "input_data": {"formula": "CaTiO3"},
        "output_data": {"energy": -25.5, "energy_per_atom": -5.1},
    }


# =============================================================================
# Memory System Fixtures
# =============================================================================


@pytest.fixture
def sample_discovery() -> dict[str, Any]:
    """Sample discovery result for caching.

    Returns:
        Dictionary with discovery data
    """
    return {
        "formula": "CaTiO3",
        "smact_valid": True,
        "structure": {
            "numbers": [20, 22, 8, 8, 8],
            "positions": [
                [0.0, 0.0, 0.0],
                [1.95, 1.95, 1.95],
                [1.95, 0.0, 1.95],
                [0.0, 1.95, 1.95],
                [1.95, 1.95, 0.0],
            ],
            "cell": [[3.9, 0.0, 0.0], [0.0, 3.9, 0.0], [0.0, 0.0, 3.9]],
        },
        "energy": -25.5,
        "formation_energy": -1.2,
        "stable": True,
        "cached_at": "2025-01-20T12:00:00Z",
    }


# =============================================================================
# Utility Functions
# =============================================================================


def assert_valid_structure(structure: dict[str, Any]) -> None:
    """Assert that a structure dictionary has required fields.

    Args:
        structure: Structure dictionary to validate

    Raises:
        AssertionError: If structure is invalid
    """
    assert "numbers" in structure, "Structure missing 'numbers'"
    assert "positions" in structure, "Structure missing 'positions'"
    assert "cell" in structure, "Structure missing 'cell'"
    assert len(structure["numbers"]) == len(
        structure["positions"]
    ), "Mismatch between numbers and positions"
    assert len(structure["cell"]) == 3, "Cell must have 3 lattice vectors"


def assert_valid_energy_result(result: dict[str, Any]) -> None:
    """Assert that an energy calculation result is valid.

    Args:
        result: Energy result dictionary to validate

    Raises:
        AssertionError: If result is invalid
    """
    assert "success" in result, "Result missing 'success' field"
    if result["success"]:
        assert "energy" in result or "energy_per_atom" in result, "Successful result missing energy"
