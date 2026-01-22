"""
SMACT Dopant Prediction Module

Predicts n-type and p-type dopants for materials using chemical and electronic filters.
Based on SMACT's dopant_prediction.doper module.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

try:
    from smact import data_directory
    from smact.dopant_prediction.doper import Doper

    SMACT_AVAILABLE = True
except ImportError:
    SMACT_AVAILABLE = False
    Doper = None
    data_directory = None


class DopantSuggestion(BaseModel):
    """Single dopant suggestion with scoring."""

    dopant_species: str = Field(description="Dopant species (e.g., 'Fe3+')")
    host_species: str = Field(description="Host species being replaced")
    substitution_probability: float = Field(description="Probability of substitution")
    chemical_similarity: float = Field(description="Chemical similarity (lambda value)")
    selectivity: float = Field(description="Selectivity score (0-1)")
    combined_score: float = Field(description="Combined probability-selectivity score")


class DopantPredictionResult(BaseModel):
    """Result from dopant prediction."""

    success: bool = True
    composition: str = Field(description="Original composition formula")
    embedding: str = Field(description="Embedding used for prediction")

    # Dopant suggestions
    n_type_cation: list[DopantSuggestion] = Field(
        default_factory=list, description="N-type cation dopants"
    )
    p_type_cation: list[DopantSuggestion] = Field(
        default_factory=list, description="P-type cation dopants"
    )
    n_type_anion: list[DopantSuggestion] = Field(
        default_factory=list, description="N-type anion dopants"
    )
    p_type_anion: list[DopantSuggestion] = Field(
        default_factory=list, description="P-type anion dopants"
    )

    # Metadata
    num_suggestions: int = Field(description="Number of suggestions per category")
    error_message: str | None = None


class SMACTDopantPredictor:
    """
    Wrapper for SMACT's dopant prediction capabilities.

    Predicts n-type and p-type dopants based on:
    - Electronic filters (oxidation states)
    - Chemical filters (ionic radius, electronegativity)
    - Machine learning embeddings (SkipSpecies, M3GNet)
    """

    AVAILABLE_EMBEDDINGS = [
        "skipspecies",
        "M3GNet-MP-2023.11.1-oxi-Eform",
        "M3GNet-MP-2023.11.1-oxi-band_gap",
    ]

    @staticmethod
    def predict_dopants(
        species: list[str],
        composition: str,
        num_dopants: int = 5,
        embedding: str = "skipspecies",
        get_selectivity: bool = True,
        group_by_charge: bool = True,
    ) -> DopantPredictionResult:
        """
        Predict dopants for a given composition.

        Args:
            species: List of species with oxidation states (e.g., ["Li+", "Fe3+", "P5-", "O2-"])
            composition: Chemical formula for reference
            num_dopants: Number of dopant suggestions per category
            embedding: Embedding method to use
            get_selectivity: Calculate selectivity scores
            group_by_charge: Group suggestions by charge state

        Returns:
            Structured dopant prediction result
        """
        if not SMACT_AVAILABLE:
            return DopantPredictionResult(
                success=False,
                composition=composition,
                embedding=embedding,
                num_suggestions=num_dopants,
                error_message="SMACT not available - install with: pip install SMACT",
            )

        try:
            # Validate embedding
            if embedding not in SMACTDopantPredictor.AVAILABLE_EMBEDDINGS:
                return DopantPredictionResult(
                    success=False,
                    composition=composition,
                    embedding=embedding,
                    num_suggestions=num_dopants,
                    error_message=f"Invalid embedding. Choose from: {SMACTDopantPredictor.AVAILABLE_EMBEDDINGS}",
                )

            # Initialize Doper
            doper = Doper(
                original_species=tuple(species), embedding=embedding, use_probability=True
            )

            # Get dopant suggestions
            results = doper.get_dopants(
                num_dopants=num_dopants,
                get_selectivity=get_selectivity,
                group_by_charge=group_by_charge,
            )

            # Parse results into structured format
            def parse_dopant_list(dopant_data: list) -> list[DopantSuggestion]:
                suggestions = []
                for entry in dopant_data:
                    if len(entry) >= 6:  # Full data with selectivity
                        suggestions.append(
                            DopantSuggestion(
                                dopant_species=entry[0],
                                host_species=entry[1],
                                substitution_probability=float(entry[2]),
                                chemical_similarity=float(entry[3]),
                                selectivity=float(entry[4]),
                                combined_score=float(entry[5]),
                            )
                        )
                return suggestions

            # Extract sorted results
            n_type_cat = parse_dopant_list(
                results.get("n-type cation substitutions", {}).get("sorted", [])
            )
            p_type_cat = parse_dopant_list(
                results.get("p-type cation substitutions", {}).get("sorted", [])
            )
            n_type_an = parse_dopant_list(
                results.get("n-type anion substitutions", {}).get("sorted", [])
            )
            p_type_an = parse_dopant_list(
                results.get("p-type anion substitutions", {}).get("sorted", [])
            )

            return DopantPredictionResult(
                success=True,
                composition=composition,
                embedding=embedding,
                n_type_cation=n_type_cat,
                p_type_cation=p_type_cat,
                n_type_anion=n_type_an,
                p_type_anion=p_type_an,
                num_suggestions=num_dopants,
            )

        except Exception as e:
            return DopantPredictionResult(
                success=False,
                composition=composition,
                embedding=embedding,
                num_suggestions=num_dopants,
                error_message=f"Dopant prediction failed: {str(e)}",
            )
