"""Tools for querying the discovery cache.

Provides agent tools to check for cached computation results and search
previous discoveries. Helps avoid re-running expensive MACE/Chemeleon/SMACT
calculations.
"""

import json
import logging

try:
    from agents import function_tool

    AGENTS_AVAILABLE = True
except ImportError:
    AGENTS_AVAILABLE = False

    def function_tool(func):
        return func


from ..memory.discovery_cache import DiscoveryCache

logger = logging.getLogger(__name__)

# Module-level cache instance (lazy initialization)
_cache: DiscoveryCache | None = None


def get_cache() -> DiscoveryCache:
    """Get or create the discovery cache singleton."""
    global _cache
    if _cache is None:
        _cache = DiscoveryCache()
    return _cache


@function_tool
def get_cached_computation(
    formula: str,
    computation_type: str,
    parameters_json: str = "{}",
) -> str:
    """Check if a computation result is already cached.

    Use this tool BEFORE running expensive calculations (MACE energy,
    Chemeleon structure prediction, SMACT validation) to avoid redundant work.

    Args:
        formula: Chemical formula (e.g., "LiFePO4", "BaTiO3")
        computation_type: Type of computation. Common types:
            - "mace_energy": MACE formation energy calculation
            - "mace_relax": MACE structure relaxation
            - "chemeleon_structure": Chemeleon crystal structure prediction
            - "chemeleon_dng": Chemeleon de novo generation
            - "smact_validity": SMACT composition validation
        parameters_json: JSON string of computation parameters that affect
            the result (e.g., '{"model": "medium"}' for MACE model selection)

    Returns:
        Cached result as JSON string if found, or "NOT_FOUND" if not cached.

    Example:
        # Check for cached MACE energy before calculating
        cached = get_cached_computation("LiFePO4", "mace_energy", '{"model": "medium"}')
        if cached != "NOT_FOUND":
            result = json.loads(cached)
            # Use cached result
    """
    try:
        params = json.loads(parameters_json)
    except json.JSONDecodeError:
        params = {}

    result = get_cache().get(formula, computation_type, params)
    if result:
        logger.debug(f"Cache hit: {formula} / {computation_type}")
        return json.dumps(result)
    logger.debug(f"Cache miss: {formula} / {computation_type}")
    return "NOT_FOUND"


@function_tool
def search_previous_discoveries(query: str, limit: int = 10) -> str:
    """Search previously computed materials by formula pattern.

    Use this to find materials you've analyzed before. Helps identify
    related work and avoid duplicate analysis.

    Args:
        query: Search pattern matching formula (e.g., "Li" finds all lithium
            compounds, "Perovskite" won't match - use element symbols)
        limit: Maximum number of results to return (default: 10)

    Returns:
        JSON list of matching discoveries with formula, computation type,
        and timestamp. Returns "[]" if no matches found.

    Example:
        # Find all previous lithium compound calculations
        results = search_previous_discoveries("Li", limit=5)
        discoveries = json.loads(results)
        for d in discoveries:
            print(f"{d['formula']}: {d['type']} at {d['created']}")
    """
    discoveries = get_cache().search(query, limit=limit)
    return json.dumps(
        [
            {
                "formula": d.formula,
                "type": d.computation_type,
                "params_hash": d.parameters_hash,
                "created": d.created_at,
            }
            for d in discoveries
        ]
    )


@function_tool
def get_all_computations_for_formula(formula: str) -> str:
    """Get all cached computations for a specific formula.

    Use this to see the complete computation history for a material,
    including all computation types and parameter variants.

    Args:
        formula: Exact chemical formula (e.g., "LiFePO4")

    Returns:
        JSON list of all cached results for this formula, including
        full result data.

    Example:
        # Get everything we know about LiFePO4
        results = get_all_computations_for_formula("LiFePO4")
        computations = json.loads(results)
        for c in computations:
            print(f"{c['type']}: {c['result']}")
    """
    discoveries = get_cache().get_all_for_formula(formula)
    return json.dumps(
        [
            {
                "type": d.computation_type,
                "params_hash": d.parameters_hash,
                "result": d.result,
                "created": d.created_at,
            }
            for d in discoveries
        ]
    )


def cache_computation(
    formula: str,
    computation_type: str,
    result: dict,
    params: dict | None = None,
) -> None:
    """Cache a computation result (for use by tool implementations).

    This is NOT a function_tool - it's a helper for other tools to cache
    their results.

    Args:
        formula: Chemical formula
        computation_type: Type of computation
        result: Result dictionary to cache
        params: Computation parameters
    """
    get_cache().put(formula, computation_type, result, params)
    logger.debug(f"Cached: {formula} / {computation_type}")
