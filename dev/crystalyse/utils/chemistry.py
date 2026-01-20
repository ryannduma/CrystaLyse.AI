"""Chemistry utility functions for CrystaLyse."""

import re
from typing import Any


def analyse_application_requirements(application: str) -> dict[str, Any]:
    """
    Analyse application string to extract material requirements.

    Args:
        application: Description of the target application

    Returns:
        Dictionary with extracted requirements
    """
    requirements = {
        "application_type": None,
        "key_properties": [],
        "constraints": [],
        "preferred_elements": [],
        "avoid_elements": [],
    }

    app_lower = application.lower()

    # Determine application type
    if any(term in app_lower for term in ["battery", "cathode", "anode", "electrolyte"]):
        requirements["application_type"] = "energy_storage"
        requirements["key_properties"] = ["ionic_conductivity", "stability", "voltage"]
        if "cathode" in app_lower:
            requirements["preferred_elements"].extend(["Li", "Na", "K", "Co", "Ni", "Mn", "Fe"])
        if "na-ion" in app_lower:
            requirements["preferred_elements"].append("Na")
            requirements["avoid_elements"].append("Li")

    elif any(term in app_lower for term in ["solar", "photovoltaic", "semiconductor"]):
        requirements["application_type"] = "photovoltaic"
        requirements["key_properties"] = ["band_gap", "absorption", "stability"]
        if "non-toxic" in app_lower or "lead-free" in app_lower:
            requirements["avoid_elements"].extend(["Pb", "Cd", "Hg", "As"])

    elif any(term in app_lower for term in ["ferroelectric", "multiferroic", "piezoelectric"]):
        requirements["application_type"] = "functional_ceramic"
        requirements["key_properties"] = ["polarisation", "piezoelectric_coefficient"]
        if "pb-free" in app_lower or "lead-free" in app_lower:
            requirements["avoid_elements"].append("Pb")

    elif any(term in app_lower for term in ["catalyst", "catalytic"]):
        requirements["application_type"] = "catalyst"
        requirements["key_properties"] = ["surface_area", "activity", "selectivity"]

    elif any(term in app_lower for term in ["magnet", "magnetic"]):
        requirements["application_type"] = "magnetic"
        requirements["key_properties"] = ["magnetisation", "coercivity", "curie_temperature"]

    # Extract specific structure types if mentioned
    if "perovskite" in app_lower:
        requirements["constraints"].append("perovskite_structure")
    if "spinel" in app_lower:
        requirements["constraints"].append("spinel_structure")
    if "layered" in app_lower:
        requirements["constraints"].append("layered_structure")

    # Extract specific elements mentioned
    element_pattern = r"\b([A-Z][a-z]?)\b"
    mentioned_elements = re.findall(element_pattern, application)
    for elem in mentioned_elements:
        if elem not in requirements["avoid_elements"]:
            requirements["preferred_elements"].append(elem)

    return requirements


def select_element_space(
    requirements: dict[str, Any],
    exclude_elements: list[str] = None,
    prefer_elements: list[str] = None,
) -> list[str]:
    """
    Select appropriate elements based on application requirements.

    Args:
        requirements: Application requirements from analyse_application_requirements
        exclude_elements: Additional elements to exclude
        prefer_elements: Additional elements to prefer

    Returns:
        List of element symbols to consider
    """
    exclude_elements = exclude_elements or []
    prefer_elements = prefer_elements or []

    # Start with preferred elements from requirements and arguments
    element_space = list(set(requirements.get("preferred_elements", []) + prefer_elements))

    # Add application-specific elements if not enough specified
    if len(element_space) < 3:
        app_type = requirements.get("application_type")

        if app_type == "energy_storage":
            default_elements = ["Li", "Na", "K", "Co", "Ni", "Mn", "Fe", "P", "O", "S", "F"]
        elif app_type == "photovoltaic":
            default_elements = ["Si", "Ge", "Sn", "Ga", "In", "As", "Sb", "S", "Se", "Te", "I"]
        elif app_type == "functional_ceramic":
            default_elements = ["Ba", "Sr", "Ca", "Ti", "Zr", "Nb", "Ta", "Bi", "K", "Na", "O"]
        elif app_type == "catalyst":
            default_elements = ["Pt", "Pd", "Ru", "Rh", "Ni", "Co", "Fe", "Cu", "Ce", "O", "N"]
        elif app_type == "magnetic":
            default_elements = ["Fe", "Co", "Ni", "Mn", "Cr", "Gd", "Nd", "Sm", "O"]
        else:
            # General purpose elements
            default_elements = ["Li", "Na", "K", "Mg", "Ca", "Al", "Si", "Ti", "Fe", "O", "S", "N"]

        for elem in default_elements:
            if elem not in element_space and elem not in exclude_elements:
                element_space.append(elem)

    # Remove excluded elements
    all_excluded = set(requirements.get("avoid_elements", []) + exclude_elements)
    element_space = [e for e in element_space if e not in all_excluded]

    return element_space[:15]  # Limit to 15 elements for computational efficiency


def classify_composition(composition: str) -> str:
    """
    Classify a composition into chemical families.

    Args:
        composition: Chemical formula

    Returns:
        Chemical family classification
    """
    composition.lower()

    # Check for specific anions
    if "O" in composition and not any(
        x in composition for x in ["S", "Se", "Te", "F", "Cl", "Br", "I"]
    ):
        return "oxide"
    elif "S" in composition and "O" not in composition:
        return "sulfide"
    elif "Se" in composition:
        return "selenide"
    elif "Te" in composition:
        return "telluride"
    elif "N" in composition and "O" not in composition:
        return "nitride"
    elif "P" in composition and "O" not in composition:
        return "phosphide"
    elif "F" in composition:
        return "fluoride"
    elif "Cl" in composition:
        return "chloride"
    elif "Br" in composition:
        return "bromide"
    elif "I" in composition:
        return "iodide"
    elif "O" in composition and any(x in composition for x in ["S", "F"]):
        return "oxyanion"
    else:
        # Check if all elements are metals
        metals = {
            "Li",
            "Na",
            "K",
            "Rb",
            "Cs",
            "Be",
            "Mg",
            "Ca",
            "Sr",
            "Ba",
            "Al",
            "Ga",
            "In",
            "Sn",
            "Pb",
            "Bi",
            "Sc",
            "Ti",
            "V",
            "Cr",
            "Mn",
            "Fe",
            "Co",
            "Ni",
            "Cu",
            "Zn",
            "Y",
            "Zr",
            "Nb",
            "Mo",
            "Tc",
            "Ru",
            "Rh",
            "Pd",
            "Ag",
            "Cd",
            "Hf",
            "Ta",
            "W",
            "Re",
            "Os",
            "Ir",
            "Pt",
            "Au",
            "Hg",
        }

        elements = re.findall(r"[A-Z][a-z]?", composition)
        if all(elem in metals for elem in elements):
            return "intermetallic"

    return "mixed_anion"


def calculate_goldschmidt_tolerance(
    composition_data: dict[str, Any], elements_info: dict[str, Any]
) -> float:
    """
    Calculate Goldschmidt tolerance factor for perovskite ABX3.

    Args:
        composition_data: Parsed composition data
        elements_info: Element property information

    Returns:
        Tolerance factor (0.8-1.0 typically stable for perovskites)
    """
    # This is a simplified implementation
    # In practice, would need ionic radii and proper A/B site identification

    # For now, return a placeholder that indicates likely stability
    return 0.92  # Typical value for stable perovskites


def suggest_synthesis_route(candidate: dict[str, Any], requirements: dict[str, Any]) -> str:
    """
    Suggest synthesis route based on composition and application.

    Args:
        candidate: Material candidate information
        requirements: Application requirements

    Returns:
        Suggested synthesis method
    """
    formula = candidate.get("formula", "")
    app_type = requirements.get("application_type", "")

    # Determine synthesis method based on composition and application
    if "oxide" in classify_composition(formula):
        if app_type == "functional_ceramic":
            return "Solid-state reaction at 1200-1400°C, followed by sintering"
        elif app_type == "energy_storage":
            return "Sol-gel method followed by calcination at 800-900°C"
        else:
            return "Ceramic method: mix, grind, calcine at 1000°C"

    elif "sulfide" in classify_composition(formula):
        return "Sealed tube synthesis at 600-800°C with elemental precursors"

    elif "fluoride" in classify_composition(formula) or "chloride" in classify_composition(formula):
        return "Hydrothermal synthesis at 150-200°C or flux growth"

    elif classify_composition(formula) == "intermetallic":
        return "Arc melting under inert atmosphere, followed by annealing"

    else:
        return "Method depends on specific composition - consider solid-state, sol-gel, or hydrothermal routes"
