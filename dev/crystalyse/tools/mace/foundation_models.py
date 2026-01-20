"""
MACE Foundation Model Support

Provides easy access to pre-trained MACE foundation models with automatic
checkpoint download and caching.
"""

import logging
from typing import Any

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class FoundationModelInfo(BaseModel):
    """Information about available foundation models."""

    success: bool = True
    model_name: str = Field(description="Model identifier")
    model_type: str = Field(description="Model family (mace_mp, mace_omat, mace_matpes)")
    size: str = Field(description="Model size (small, medium, large)")
    description: str = Field(description="Model description")
    training_data: str = Field(description="Training dataset description")
    functional: str | None = Field(None, description="DFT functional if applicable")
    license: str = Field(description="License type (MIT or ASL)")
    url: str = Field(description="Download URL")
    error_message: str | None = None


class FoundationModelListResult(BaseModel):
    """List of available foundation models."""

    success: bool = True
    models: list[FoundationModelInfo] = Field(default_factory=list)
    error_message: str | None = None


try:
    from mace.calculators import MACECalculator as MACECalc
    from mace.calculators import mace_mp, mace_off
    from mace.calculators.foundations_models import download_mace_mp_checkpoint, mace_mp_urls

    MACE_AVAILABLE = True
except ImportError:
    MACE_AVAILABLE = False
    mace_mp = None
    mace_off = None
    MACECalc = None
    download_mace_mp_checkpoint = None
    mace_mp_urls = {}


class MACEFoundationModels:
    """
    Access to MACE foundation models with automatic download and caching.

    Available model families:
    - MACE-MP: Materials Project trained models (general inorganic materials)
    - MACE-MPA: Materials Project with improved accuracy
    - MACE-OMAT: Optimized for oxide materials
    - MACE-MatPES: Trained on MatPES dataset with PBE/r2SCAN functionals
    """

    AVAILABLE_MODELS = {
        # MACE-MP (original Materials Project models)
        "small": {
            "type": "mace_mp",
            "size": "small",
            "description": "MACE-MP small model (128 channels, L=0)",
            "training_data": "Materials Project DFT calculations",
            "functional": "PBE",
            "license": "MIT",
            "url": "https://github.com/ACEsuit/mace-mp/releases/download/mace_mp_0/2023-12-10-mace-128-L0_energy_epoch-249.model",
        },
        "medium": {
            "type": "mace_mp",
            "size": "medium",
            "description": "MACE-MP medium model (128 channels, L=1)",
            "training_data": "Materials Project DFT calculations",
            "functional": "PBE",
            "license": "MIT",
            "url": "https://github.com/ACEsuit/mace-mp/releases/download/mace_mp_0/2023-12-03-mace-128-L1_epoch-199.model",
        },
        "large": {
            "type": "mace_mp",
            "size": "large",
            "description": "MACE-MP large model (MPtrj 2022.9)",
            "training_data": "Materials Project with trajectory data",
            "functional": "PBE",
            "license": "MIT",
            "url": "https://github.com/ACEsuit/mace-mp/releases/download/mace_mp_0/MACE_MPtrj_2022.9.model",
        },
        # MACE-MPA (improved accuracy)
        "medium-mpa-0": {
            "type": "mace_mp",
            "size": "medium-mpa-0",
            "description": "MACE-MPA-0 medium (default, improved accuracy)",
            "training_data": "Materials Project with enhanced training",
            "functional": "PBE",
            "license": "MIT",
            "url": "https://github.com/ACEsuit/mace-mp/releases/download/mace_mpa_0/mace-mpa-0-medium.model",
        },
        # MACE-OMAT (oxide materials specialized)
        "small-omat-0": {
            "type": "mace_mp",
            "size": "small-omat-0",
            "description": "MACE-OMAT-0 small (oxide materials)",
            "training_data": "OMAT24 oxide materials dataset",
            "functional": "PBE",
            "license": "ASL",
            "url": "https://github.com/ACEsuit/mace-mp/releases/download/mace_omat_0/mace-omat-0-small.model",
        },
        "medium-omat-0": {
            "type": "mace_mp",
            "size": "medium-omat-0",
            "description": "MACE-OMAT-0 medium (oxide materials)",
            "training_data": "OMAT24 oxide materials dataset",
            "functional": "PBE",
            "license": "ASL",
            "url": "https://github.com/ACEsuit/mace-mp/releases/download/mace_omat_0/mace-omat-0-medium.model",
        },
        # MACE-MatPES (MatPES dataset)
        "mace-matpes-pbe-0": {
            "type": "mace_mp",
            "size": "mace-matpes-pbe-0",
            "description": "MACE-MatPES with PBE functional",
            "training_data": "MatPES dataset",
            "functional": "PBE",
            "license": "ASL",
            "url": "https://github.com/ACEsuit/mace-foundations/releases/download/mace_matpes_0/MACE-matpes-pbe-omat-ft.model",
        },
        "mace-matpes-r2scan-0": {
            "type": "mace_mp",
            "size": "mace-matpes-r2scan-0",
            "description": "MACE-MatPES with r2SCAN functional",
            "training_data": "MatPES dataset",
            "functional": "r2SCAN",
            "license": "ASL",
            "url": "https://github.com/ACEsuit/mace-foundations/releases/download/mace_matpes_0/MACE-matpes-r2scan-omat-ft.model",
        },
    }

    @staticmethod
    def list_models() -> FoundationModelListResult:
        """
        List all available foundation models.

        Returns:
            Structured list of available models with metadata
        """
        if not MACE_AVAILABLE:
            return FoundationModelListResult(
                success=False,
                error_message="MACE not available - install with: pip install mace-torch",
            )

        try:
            models = []
            for name, info in MACEFoundationModels.AVAILABLE_MODELS.items():
                models.append(
                    FoundationModelInfo(
                        model_name=name,
                        model_type=info["type"],
                        size=info["size"],
                        description=info["description"],
                        training_data=info["training_data"],
                        functional=info.get("functional"),
                        license=info["license"],
                        url=info["url"],
                    )
                )

            return FoundationModelListResult(success=True, models=models)

        except Exception as e:
            return FoundationModelListResult(
                success=False, error_message=f"Failed to list models: {str(e)}"
            )

    @staticmethod
    def get_model_calculator(
        model_name: str = "medium-mpa-0",
        device: str = "auto",
        dispersion: bool = False,
        dispersion_xc: str = "pbe",
        default_dtype: str = "float32",
    ) -> Any:
        """
        Get a MACE calculator for a foundation model.

        Models are automatically downloaded and cached on first use.

        Args:
            model_name: Model identifier (see list_models() for options)
            device: Compute device ('auto', 'cpu', 'cuda')
            dispersion: Enable D3/D4 dispersion correction
            dispersion_xc: Exchange-correlation functional for dispersion
            default_dtype: Model precision ('float32' or 'float64')

        Returns:
            MACE calculator instance
        """
        if not MACE_AVAILABLE:
            raise ImportError("MACE not available - install with: pip install mace-torch")

        # Validate model name
        if model_name not in MACEFoundationModels.AVAILABLE_MODELS:
            available = ", ".join(MACEFoundationModels.AVAILABLE_MODELS.keys())
            raise ValueError(f"Invalid model_name '{model_name}'. Choose from: {available}")

        try:
            # Download checkpoint if needed (cached automatically)
            checkpoint_path = download_mace_mp_checkpoint(model_name)
            logger.info(f"Using MACE foundation model: {model_name} from {checkpoint_path}")

            # Create calculator
            if device == "auto":
                import torch

                device = "cuda" if torch.cuda.is_available() else "cpu"

            calc = mace_mp(
                model=model_name,
                device=device,
                dispersion=dispersion,
                dispersion_xc=dispersion_xc,
                default_dtype=default_dtype,
            )

            logger.info(f"MACE calculator created successfully on {device}")
            return calc

        except Exception as e:
            logger.error(f"Failed to load foundation model: {e}")
            raise

    @staticmethod
    def get_model_info(model_name: str) -> FoundationModelInfo | None:
        """
        Get detailed information about a specific model.

        Args:
            model_name: Model identifier

        Returns:
            Model information or None if not found
        """
        if model_name not in MACEFoundationModels.AVAILABLE_MODELS:
            return None

        info = MACEFoundationModels.AVAILABLE_MODELS[model_name]
        return FoundationModelInfo(
            model_name=model_name,
            model_type=info["type"],
            size=info["size"],
            description=info["description"],
            training_data=info["training_data"],
            functional=info.get("functional"),
            license=info["license"],
            url=info["url"],
        )
