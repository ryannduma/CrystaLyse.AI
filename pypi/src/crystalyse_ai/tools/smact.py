"""SMACT tools for MCP server."""

import json
from typing import List, Optional, Dict, Any

# Import SMACT modules
import smact
from smact import Element, neutral_ratios
from smact.screening import smact_validity as smact_validity_check, pauling_test, smact_filter
from smact.utils.composition import parse_formula
try:
    from smact.metallicity import metallicity_score
    METALLICITY_AVAILABLE = True
except ImportError:
    METALLICITY_AVAILABLE = False

# Tool function for SMACT validity checking
def smact_validity(
    composition: str,
    use_pauling_test: bool = True,
    include_alloys: bool = True,
    oxidation_states_set: str = "icsd24",
    check_metallicity: bool = False,
    metallicity_threshold: float = 0.7
) -> str:
    """
    Check if a composition is valid according to SMACT rules.
    
    Args:
        composition: Chemical formula (e.g., "LiFePO4", "CaTiO3")
        use_pauling_test: Whether to apply Pauling electronegativity test
        include_alloys: Consider pure metals valid automatically
        oxidation_states_set: Which oxidation states to use ("icsd24", "icsd16", "smact14", "pymatgen_sp", "wiki")
        check_metallicity: If True, consider high metallicity compositions valid
        metallicity_threshold: Score threshold for metallicity validity (0-1)
    
    Returns:
        JSON string with validity result and details
    """
    try:
        # Parse composition using pymatgen
        from pymatgen.core import Composition
        comp = Composition(composition)
        
        # Run validity check (only use supported parameters)
        is_valid = smact_validity_check(
            comp,
            use_pauling_test=use_pauling_test,
            include_alloys=include_alloys,
            oxidation_states_set=oxidation_states_set
        )
        
        # Get additional details
        elem_symbols = list(comp.as_dict().keys())
        elem_counts = list(comp.as_dict().values())
        
        result = {
            "composition": composition,
            "is_valid": is_valid,
            "elements": elem_symbols,
            "counts": elem_counts,
            "settings": {
                "use_pauling_test": use_pauling_test,
                "include_alloys": include_alloys,
                "oxidation_states_set": oxidation_states_set,
                "check_metallicity": check_metallicity,
                "metallicity_threshold": metallicity_threshold
            }
        }
        
        # Add metallicity score if requested and available
        if check_metallicity and METALLICITY_AVAILABLE:
            try:
                score = metallicity_score(comp)
                result["metallicity_score"] = score
            except Exception as e:
                result["metallicity_error"] = str(e)
        
        return json.dumps(result, indent=2)
        
    except Exception as e:
        return json.dumps({
            "error": str(e),
            "composition": composition,
            "is_valid": False
        }, indent=2)


# Tool function for calculating charge-neutral stoichiometric ratios
def calculate_neutral_ratios(
    oxidation_states: List[int],
    stoichs: Optional[List[List[int]]] = None,
    threshold: int = 5
) -> str:
    """
    Find charge-neutral stoichiometric ratios for given oxidation states.
    
    Args:
        oxidation_states: List of oxidation states (e.g., [1, -2] for Na+ and O2-)
        stoichs: Optional list of allowed stoichiometries per site
        threshold: Maximum stoichiometric coefficient to try (default: 5)
    
    Returns:
        JSON string with neutral ratios and details
    """
    try:
        # Calculate neutral ratios
        cn_e, cn_r = neutral_ratios(
            oxidation_states,
            stoichs=stoichs if stoichs else False,
            threshold=threshold
        )
        
        result = {
            "oxidation_states": oxidation_states,
            "charge_neutral": cn_e,
            "neutral_ratios": [list(ratio) for ratio in cn_r] if cn_e else [],
            "threshold": threshold
        }
        
        # Add example formulas if neutral
        if cn_e and cn_r:
            examples = []
            for ratio in cn_r[:5]:  # Show up to 5 examples
                formula_parts = []
                for i, (ox, count) in enumerate(zip(oxidation_states, ratio)):
                    if count > 1:
                        formula_parts.append(f"X{i+1}_{count}")
                    else:
                        formula_parts.append(f"X{i+1}")
                examples.append({
                    "ratio": list(ratio),
                    "example": "".join(formula_parts),
                    "total_charge": sum(ox * c for ox, c in zip(oxidation_states, ratio))
                })
            result["examples"] = examples
        
        return json.dumps(result, indent=2)
        
    except Exception as e:
        return json.dumps({
            "error": str(e),
            "oxidation_states": oxidation_states,
            "charge_neutral": False
        }, indent=2)


def parse_chemical_formula(formula: str) -> str:
    """
    Parse a chemical formula into its constituent elements and counts.
    
    Args:
        formula: Chemical formula (e.g., "Ca(OH)2", "Fe2O3", "LiFePO4")
    
    Returns:
        JSON string with parsed elements and their counts
    """
    try:
        # Parse formula
        element_counts = parse_formula(formula)
        
        # Calculate total atoms
        total_atoms = sum(element_counts.values())
        
        # Get element info
        elements_info = []
        for elem, count in element_counts.items():
            try:
                smact_elem = Element(elem)
                elements_info.append({
                    "symbol": elem,
                    "count": count,
                    "atomic_number": smact_elem.number,
                    "name": smact_elem.name,
                    "electronegativity": smact_elem.pauling_eneg
                })
            except Exception:
                elements_info.append({
                    "symbol": elem,
                    "count": count,
                    "error": "Element data not found"
                })
        
        result = {
            "formula": formula,
            "element_counts": element_counts,
            "total_atoms": total_atoms,
            "elements": elements_info
        }
        
        return json.dumps(result, indent=2)
        
    except Exception as e:
        return json.dumps({
            "error": str(e),
            "formula": formula
        }, indent=2)


def get_element_info(
    symbol: str,
    include_oxidation_states: bool = True
) -> str:
    """
    Get detailed properties of a chemical element from SMACT database.
    
    Args:
        symbol: Chemical symbol (e.g., "Fe", "O", "Li")
        include_oxidation_states: Whether to include oxidation state data
    
    Returns:
        JSON string with element properties
    """
    try:
        # Get element
        elem = Element(symbol)
        
        result = {
            "symbol": elem.symbol,
            "name": elem.name,
            "atomic_number": elem.number,
            "atomic_mass": elem.mass,
            "electronegativity": {
                "pauling": elem.pauling_eneg,
            },
            "radii": {
                "covalent": elem.cov_radius,
            }
        }
        
        # Add available properties safely
        if hasattr(elem, 'ionpot') and elem.ionpot is not None:
            result["ionization_potential"] = elem.ionpot
        if hasattr(elem, 'e_affinity') and elem.e_affinity is not None:
            result["electron_affinity"] = elem.e_affinity
        if hasattr(elem, 'eig') and elem.eig is not None:
            result["electronegativity"]["allen"] = elem.eig
        
        # Add oxidation states if requested
        if include_oxidation_states:
            ox_states = {}
            if hasattr(elem, 'oxidation_states_icsd24'):
                ox_states["icsd24"] = elem.oxidation_states_icsd24
            if hasattr(elem, 'oxidation_states_icsd16'):
                ox_states["icsd16"] = elem.oxidation_states_icsd16
            if hasattr(elem, 'oxidation_states_smact14'):
                ox_states["smact14"] = elem.oxidation_states_smact14
            if hasattr(elem, 'oxidation_states_wiki'):
                ox_states["wiki"] = elem.oxidation_states_wiki
            result["oxidation_states"] = ox_states
        
        return json.dumps(result, indent=2)
        
    except Exception as e:
        return json.dumps({
            "error": str(e),
            "symbol": symbol
        }, indent=2)


def test_pauling_rule(
    elements: List[str],
    oxidation_states: List[int],
    threshold: float = 0.0
) -> str:
    """
    Check if a combination of elements and oxidation states satisfies Pauling's rule.
    
    Args:
        elements: List of element symbols (e.g., ["Li", "Fe", "O"])
        oxidation_states: Corresponding oxidation states (e.g., [1, 3, -2])
        threshold: Tolerance for electronegativity differences (default: 0.0)
    
    Returns:
        JSON string with test result and details
    """
    try:
        if len(elements) != len(oxidation_states):
            raise ValueError("Elements and oxidation states must have same length")
        
        # Get electronegativities
        electronegativities = []
        element_data = []
        
        for elem_symbol in elements:
            elem = Element(elem_symbol)
            electronegativities.append(elem.pauling_eneg)
            element_data.append({
                "symbol": elem_symbol,
                "electronegativity": elem.pauling_eneg
            })
        
        # Run Pauling test
        passes_test = pauling_test(
            oxidation_states,
            electronegativities,
            symbols=elements,
            threshold=threshold
        )
        
        # Identify cations and anions
        cations = []
        anions = []
        for i, (elem, ox, eneg) in enumerate(zip(elements, oxidation_states, electronegativities)):
            if ox > 0:
                cations.append({
                    "element": elem,
                    "oxidation_state": ox,
                    "electronegativity": eneg
                })
            elif ox < 0:
                anions.append({
                    "element": elem,
                    "oxidation_state": ox,
                    "electronegativity": eneg
                })
        
        result = {
            "passes_test": passes_test,
            "elements": element_data,
            "oxidation_states": oxidation_states,
            "cations": cations,
            "anions": anions,
            "threshold": threshold,
            "rule": "Cations should have lower electronegativity than anions"
        }
        
        return json.dumps(result, indent=2)
        
    except Exception as e:
        return json.dumps({
            "error": str(e),
            "elements": elements,
            "oxidation_states": oxidation_states
        }, indent=2)


def generate_compositions(
    elements: List[str],
    threshold: int = 8,
    oxidation_states_set: str = "icsd24",
    species_unique: bool = True
) -> str:
    """
    Generate chemically valid compositions from a list of elements using SMACT.
    
    Args:
        elements: List of element symbols (e.g., ["Li", "Fe", "P", "O"])
        threshold: Maximum stoichiometric coefficient (default: 8)
        oxidation_states_set: Which oxidation states to use ("icsd24", "smact14", etc.)
        species_unique: Whether to consider oxidation states as unique species
    
    Returns:
        JSON string with valid compositions and their details
    """
    try:
        # Convert to Element objects
        smact_elements = tuple(Element(el) for el in elements)
        
        # Generate valid compositions
        valid_compositions = smact_filter(
            smact_elements,
            threshold=threshold,
            oxidation_states_set=oxidation_states_set,
            species_unique=species_unique
        )
        
        # Format results for better readability
        formatted_compositions = []
        for i, comp in enumerate(valid_compositions[:20]):  # Limit to first 20
            if species_unique:
                symbols, ox_states, ratios = comp
                formula = ""
                for sym, ratio in zip(symbols, ratios):
                    if ratio == 1:
                        formula += sym
                    else:
                        formula += f"{sym}{ratio}"
                
                formatted_compositions.append({
                    "formula": formula,
                    "elements": list(symbols),
                    "oxidation_states": list(ox_states),
                    "ratios": list(ratios),
                    "charge_check": sum(ox * ratio for ox, ratio in zip(ox_states, ratios))
                })
            else:
                symbols, ratios = comp
                formula = ""
                for sym, ratio in zip(symbols, ratios):
                    if ratio == 1:
                        formula += sym
                    else:
                        formula += f"{sym}{ratio}"
                
                formatted_compositions.append({
                    "formula": formula,
                    "elements": list(symbols),
                    "ratios": list(ratios)
                })
        
        result = {
            "input_elements": elements,
            "total_compositions_found": len(valid_compositions),
            "compositions_shown": len(formatted_compositions),
            "valid_compositions": formatted_compositions,
            "settings": {
                "threshold": threshold,
                "oxidation_states_set": oxidation_states_set,
                "species_unique": species_unique
            }
        }
        
        return json.dumps(result, indent=2)
        
    except Exception as e:
        return json.dumps({
            "error": str(e),
            "input_elements": elements,
            "valid_compositions": []
        }, indent=2)


def quick_validity_check(composition: str) -> str:
    """
    Quick validation of a composition using SMACT with natural language response.
    
    Args:
        composition: Chemical formula (e.g., "LiFePO4")
    
    Returns:
        JSON string with validation result and explanation
    """
    try:
        # Test with SMACT validity function
        is_valid = smact_validity(composition, use_pauling_test=True, include_alloys=True)
        
        # Parse composition for additional info
        from pymatgen.core import Composition
        comp = Composition(composition)
        
        result = {
            "composition": composition,
            "is_valid": is_valid,
            "validation_method": "SMACT screening (charge neutrality + Pauling test)",
            "explanation": f"{composition} {'passes' if is_valid else 'fails'} SMACT validation. "
                          f"This includes charge neutrality and electronegativity criteria.",
            "elements": list(comp.as_dict().keys()),
            "element_counts": {k: int(v) for k, v in comp.as_dict().items()}
        }
        
        return json.dumps(result, indent=2)
        
    except Exception as e:
        return json.dumps({
            "composition": composition,
            "is_valid": False,
            "error": str(e),
            "explanation": f"Could not validate {composition}: {str(e)}"
        }, indent=2)