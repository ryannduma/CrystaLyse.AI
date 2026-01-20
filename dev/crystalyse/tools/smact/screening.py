"""
SMACT Advanced Screening Functions

Fast screening tools for materials discovery including:
- smact_validity() with metallicity and alloy support
- ML representation generation
- Pauling electronegativity tests
- Multiple oxidation state dataset support
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

try:
    from smact import Element
    from smact.screening import ml_rep_generator, smact_filter, smact_validity

    SMACT_AVAILABLE = True
except ImportError:
    SMACT_AVAILABLE = False
    smact_validity = None
    ml_rep_generator = None
    smact_filter = None
    Element = None


class CompositionValidityResult(BaseModel):
    """Result from SMACT validity check."""

    success: bool = True
    composition: str = Field(description="Chemical formula tested")
    is_valid: bool = Field(description="Whether composition passes SMACT tests")

    # Test parameters
    use_pauling_test: bool = Field(description="Whether Pauling EN test was used")
    include_alloys: bool = Field(description="Whether alloys are considered valid")
    check_metallicity: bool = Field(description="Whether metallicity was checked")
    oxidation_states_set: str | None = Field(description="Oxidation state dataset used")

    # Optional metadata
    metallicity_threshold: float | None = None
    error_message: str | None = None


class MLRepresentationResult(BaseModel):
    """Result from ML representation generation."""

    success: bool = True
    composition: str = Field(description="Chemical formula")
    ml_vector: list[float] = Field(description="103-element ML representation vector (normalized)")
    vector_length: int = Field(default=103, description="Length of ML vector")
    error_message: str | None = None


class CompositionFilterResult(BaseModel):
    """Result from SMACT composition filtering."""

    success: bool = True
    elements: list[str] = Field(description="Element symbols tested")
    num_valid_compositions: int = Field(description="Number of valid compositions found")
    valid_compositions: list[dict[str, Any]] = Field(
        default_factory=list,
        description="List of valid compositions with oxidation states and stoichiometry",
    )
    threshold: int = Field(description="Stoichiometry threshold used")
    oxidation_states_set: str = Field(description="Oxidation state dataset used")
    error_message: str | None = None


class SMACTScreener:
    """
    Advanced screening functions for high-throughput materials discovery.

    Provides fast composition validation, ML representation generation,
    and systematic composition enumeration with SMACT rules.
    """

    AVAILABLE_OXIDATION_SETS = [
        "icsd24",  # Default: 2024 ICSD (most up-to-date)
        "smact14",  # Original SMACT 2014 oxidation states
        "icsd16",  # 2016 ICSD
        "pymatgen_sp",  # PyMatgen structure predictor
        "wiki",  # Wikipedia (use with caution)
    ]

    @staticmethod
    def validate_composition(
        composition: str,
        use_pauling_test: bool = True,
        include_alloys: bool = True,
        check_metallicity: bool = False,
        metallicity_threshold: float = 0.7,
        oxidation_states_set: str | None = "icsd24",
        include_zero: bool = False,
        consensus: int = 3,
        commonality: str = "medium",
    ) -> CompositionValidityResult:
        """
        Fast SMACT validity check for a composition.

        Args:
            composition: Chemical formula (e.g., "LiFePO4")
            use_pauling_test: Apply Pauling electronegativity test
            include_alloys: Consider pure metals valid automatically
            check_metallicity: Consider high metallicity compositions valid
            metallicity_threshold: Threshold for metallicity validity (0-1)
            oxidation_states_set: Which oxidation state dataset to use
            include_zero: Include zero oxidation states
            consensus: Minimum literature occurrences for valid ion
            commonality: Filter by commonality ("low", "medium", "high", "main")

        Returns:
            Structured validity result
        """
        if not SMACT_AVAILABLE:
            return CompositionValidityResult(
                success=False,
                composition=composition,
                is_valid=False,
                use_pauling_test=use_pauling_test,
                include_alloys=include_alloys,
                check_metallicity=check_metallicity,
                oxidation_states_set=oxidation_states_set,
                error_message="SMACT not available - install with: pip install SMACT",
            )

        try:
            # Validate oxidation states set
            if (
                oxidation_states_set
                and oxidation_states_set not in SMACTScreener.AVAILABLE_OXIDATION_SETS
            ):
                return CompositionValidityResult(
                    success=False,
                    composition=composition,
                    is_valid=False,
                    use_pauling_test=use_pauling_test,
                    include_alloys=include_alloys,
                    check_metallicity=check_metallicity,
                    oxidation_states_set=oxidation_states_set,
                    error_message=f"Invalid oxidation set. Choose from: {SMACTScreener.AVAILABLE_OXIDATION_SETS}",
                )

            # Run SMACT validity check
            is_valid = smact_validity(
                composition=composition,
                use_pauling_test=use_pauling_test,
                include_alloys=include_alloys,
                check_metallicity=check_metallicity,
                metallicity_threshold=metallicity_threshold,
                oxidation_states_set=oxidation_states_set,
                include_zero=include_zero,
                consensus=consensus,
                commonality=commonality,
            )

            return CompositionValidityResult(
                success=True,
                composition=composition,
                is_valid=is_valid,
                use_pauling_test=use_pauling_test,
                include_alloys=include_alloys,
                check_metallicity=check_metallicity,
                oxidation_states_set=oxidation_states_set,
                metallicity_threshold=metallicity_threshold if check_metallicity else None,
            )

        except Exception as e:
            return CompositionValidityResult(
                success=False,
                composition=composition,
                is_valid=False,
                use_pauling_test=use_pauling_test,
                include_alloys=include_alloys,
                check_metallicity=check_metallicity,
                oxidation_states_set=oxidation_states_set,
                error_message=f"Validation failed: {str(e)}",
            )

    @staticmethod
    def generate_ml_representation(
        composition: str | list[str], stoichs: list[int] | None = None
    ) -> MLRepresentationResult:
        """
        Generate 103-element ML-compatible vector for a composition.

        The vector represents elemental composition normalized to sum to 1.
        Useful for machine learning models.

        Example: Li2O -> [0, 0, 2/3, 0, 0, 0, 0, 1/3, 0, ...]

        Args:
            composition: List of element symbols OR chemical formula string
            stoichs: Stoichiometry list (if composition is list of symbols)

        Returns:
            Structured ML representation result with 103-element vector
        """
        if not SMACT_AVAILABLE:
            return MLRepresentationResult(
                success=False,
                composition=str(composition),
                ml_vector=[],
                error_message="SMACT not available - install with: pip install SMACT",
            )

        try:
            # Handle string composition by parsing it
            if isinstance(composition, str):
                from pymatgen.core import Composition

                comp = Composition(composition)
                elements = [Element(sym) for sym in comp.as_dict().keys()]
                stoichs = list(comp.as_dict().values())
                composition_str = composition
            else:
                # List of element symbols
                elements = [Element(sym) if isinstance(sym, str) else sym for sym in composition]
                composition_str = "".join(
                    [f"{el.symbol}{s}" for el, s in zip(elements, stoichs or [], strict=False)]
                )

            # Generate ML representation
            ml_vector = ml_rep_generator(elements, stoichs=stoichs)

            return MLRepresentationResult(
                success=True,
                composition=composition_str,
                ml_vector=ml_vector,
                vector_length=len(ml_vector),
            )

        except Exception as e:
            return MLRepresentationResult(
                success=False,
                composition=str(composition),
                ml_vector=[],
                error_message=f"ML representation generation failed: {str(e)}",
            )

    @staticmethod
    def filter_compositions(
        elements: list[str],
        threshold: int = 8,
        stoichs: list[list[int]] | None = None,
        species_unique: bool = True,
        oxidation_states_set: str = "icsd24",
    ) -> CompositionFilterResult:
        """
        Generate all valid compositions for a given set of elements.

        Applies charge neutrality and electronegativity tests to enumerate
        valid compositions up to a stoichiometry threshold.

        Args:
            elements: List of element symbols (e.g., ["Li", "Fe", "P", "O"])
            threshold: Maximum stoichiometry coefficient
            stoichs: Optional fixed stoichiometry ratios per site
            species_unique: Consider different oxidation states as unique
            oxidation_states_set: Which oxidation state dataset to use

        Returns:
            Structured result with all valid compositions
        """
        if not SMACT_AVAILABLE:
            return CompositionFilterResult(
                success=False,
                elements=elements,
                num_valid_compositions=0,
                threshold=threshold,
                oxidation_states_set=oxidation_states_set,
                error_message="SMACT not available - install with: pip install SMACT",
            )

        try:
            # Create Element objects
            smact_elements = tuple(Element(sym) for sym in elements)

            # Run SMACT filter
            valid_comps = smact_filter(
                els=smact_elements,
                threshold=threshold,
                stoichs=stoichs,
                species_unique=species_unique,
                oxidation_states_set=oxidation_states_set,
            )

            # Format results
            formatted_comps = []
            for comp in valid_comps[:100]:  # Limit to 100 for response size
                if species_unique and len(comp) == 3:
                    formatted_comps.append(
                        {
                            "elements": list(comp[0]),
                            "oxidation_states": list(comp[1]),
                            "stoichiometry": list(comp[2]),
                        }
                    )
                elif not species_unique and len(comp) == 2:
                    formatted_comps.append(
                        {"elements": list(comp[0]), "stoichiometry": list(comp[1])}
                    )

            return CompositionFilterResult(
                success=True,
                elements=elements,
                num_valid_compositions=len(valid_comps),
                valid_compositions=formatted_comps,
                threshold=threshold,
                oxidation_states_set=oxidation_states_set,
            )

        except Exception as e:
            return CompositionFilterResult(
                success=False,
                elements=elements,
                num_valid_compositions=0,
                threshold=threshold,
                oxidation_states_set=oxidation_states_set,
                error_message=f"Composition filtering failed: {str(e)}",
            )
