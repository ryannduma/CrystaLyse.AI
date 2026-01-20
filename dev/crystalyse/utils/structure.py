"""Structure analysis utility functions for CrystaLyse."""

from typing import Any


def matches_perovskite_pattern(comp_data: dict[str, Any], elements_info: dict[str, Any]) -> bool:
    """
    Check if composition matches ABX3 perovskite stoichiometry.

    Args:
        comp_data: Parsed composition data with element counts
        elements_info: Element property information

    Returns:
        True if matches perovskite pattern
    """
    counts = comp_data.get("element_counts", {})

    # Check for ABX3 stoichiometry
    count_values = sorted(counts.values())

    # Classic ABX3
    if count_values == [1, 1, 3]:
        return True

    # Double perovskite A2BB'X6
    if count_values == [1, 1, 2, 6]:
        return True

    # Check normalized ratios
    if len(counts) == 3:
        min_count = min(count_values)
        normalized = [c / min_count for c in count_values]
        if sorted(normalized) == [1.0, 1.0, 3.0]:
            return True

    return False


def matches_spinel_pattern(comp_data: dict[str, Any], elements_info: dict[str, Any]) -> bool:
    """
    Check if composition matches AB2X4 spinel stoichiometry.

    Args:
        comp_data: Parsed composition data
        elements_info: Element property information

    Returns:
        True if matches spinel pattern
    """
    counts = comp_data.get("element_counts", {})
    count_values = sorted(counts.values())

    # Check for AB2X4 stoichiometry
    if count_values == [1, 2, 4]:
        return True

    # Check normalized ratios
    if len(counts) == 3:
        min_count = min(count_values)
        normalized = sorted([c / min_count for c in count_values])
        if normalized == [1.0, 2.0, 4.0]:
            return True

    return False


def suitable_for_layered(comp_data: dict[str, Any], elements_info: dict[str, Any]) -> bool:
    """
    Check if composition is suitable for layered structures.

    Args:
        comp_data: Parsed composition data
        elements_info: Element property information

    Returns:
        True if suitable for layered structure
    """
    elements = list(comp_data.get("element_counts", {}).keys())

    # Check for mobile cations
    mobile_cations = {"Li", "Na", "K", "Rb", "Cs", "Ag"}
    has_mobile = any(elem in mobile_cations for elem in elements)

    # Check for transition metals
    transition_metals = {"Ti", "V", "Cr", "Mn", "Fe", "Co", "Ni", "Cu", "Nb", "Mo"}
    has_tm = any(elem in transition_metals for elem in elements)

    # Check for appropriate anions
    layered_anions = {"O", "S", "Se"}
    has_anion = any(elem in layered_anions for elem in elements)

    return has_mobile and has_tm and has_anion


def predict_dimensionality(comp_data: dict[str, Any], elements_info: dict[str, Any]) -> str:
    """
    Predict structural dimensionality based on composition.

    Args:
        comp_data: Parsed composition data
        elements_info: Element property information

    Returns:
        Predicted dimensionality: "0D", "1D", "2D", or "3D"
    """
    elements = list(comp_data.get("element_counts", {}).keys())

    # Large cations often template lower dimensional structures
    large_cations = {"Cs", "Rb", "K", "Ba", "Sr", "Pb"}
    has_large_cation = any(elem in large_cations for elem in elements)

    # Chalcogenides often form layered/chain structures
    chalcogens = {"S", "Se", "Te"}
    has_chalcogen = any(elem in chalcogens for elem in elements)

    # Halides can form various dimensionalities
    halides = {"F", "Cl", "Br", "I"}
    has_halide = any(elem in halides for elem in elements)

    if has_large_cation and has_halide:
        return "0D"  # Often molecular/cluster
    elif has_chalcogen and "O" not in elements:
        return "2D"  # Often layered
    elif suitable_for_layered(comp_data, elements_info):
        return "2D"
    else:
        return "3D"  # Default framework structure


def analyse_bonding(elements_info: dict[str, Any]) -> str:
    """
    Analyse bonding character based on element electronegativities.

    Args:
        elements_info: Element property information with electronegativities

    Returns:
        Bonding character: "ionic", "covalent", "metallic", or "mixed"
    """
    electronegativities = []

    for elem_data in elements_info.values():
        if isinstance(elem_data, dict) and "electronegativity" in elem_data:
            eneg = elem_data["electronegativity"]
            if isinstance(eneg, dict) and "pauling" in eneg:
                electronegativities.append(eneg["pauling"])
            elif isinstance(eneg, int | float):
                electronegativities.append(eneg)

    if not electronegativities or len(electronegativities) < 2:
        return "unknown"

    # Calculate electronegativity difference
    max_diff = max(electronegativities) - min(electronegativities)

    # Classify bonding
    if max_diff > 1.7:
        return "ionic"
    elif max_diff < 0.5:
        return "metallic"
    elif max_diff < 1.0:
        return "covalent"
    else:
        return "mixed ionic-covalent"
