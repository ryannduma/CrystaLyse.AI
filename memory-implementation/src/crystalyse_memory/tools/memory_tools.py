# crystalyse_memory/tools/memory_tools.py
"""
Memory Tools for CrystaLyse.AI Memory System

Provides function tools for OpenAI Agents SDK to interact with working memory cache.
Enables efficient caching and retrieval of computational results.
"""

from typing import Any, Dict, Optional, List
import logging

logger = logging.getLogger(__name__)


def cache_computational_result(
    operation: str,
    result: Any,
    context: Optional[Dict[str, Any]] = None,
    **kwargs
) -> str:
    """
    Cache a computational result for future retrieval.
    
    Use this tool to store expensive calculation results to avoid
    redundant computations in future queries.
    
    Args:
        operation: Type of operation (e.g., 'mace_energy', 'chemeleon_csp', 'smact_feasibility')
        result: Result to cache
        **kwargs: Operation parameters used to generate cache key
        
    Returns:
        Cache key and confirmation message
    """
    try:
        if not context or "dual_working_memory" not in context:
            return "Error: No working memory available in context"
        
        dual_memory = context["dual_working_memory"]
        cache_key = dual_memory.cache_result(operation, result, **kwargs)
        
        # Create parameter summary
        params_str = ", ".join(f"{k}={v}" for k, v in list(kwargs.items())[:3])
        if len(kwargs) > 3:
            params_str += "..."
        
        return f"💾 Cached {operation} result (key: {cache_key[:8]}...) with params: {params_str}"
        
    except Exception as e:
        logger.error(f"cache_computational_result error: {e}")
        return f"Error caching result: {str(e)}"


def get_cached_result(
    operation: str,
    context: Optional[Dict[str, Any]] = None,
    **kwargs
) -> str:
    """
    Retrieve a cached computational result.
    
    Use this tool to check if a previous calculation result is available
    before running expensive computations.
    
    Args:
        operation: Type of operation to retrieve
        **kwargs: Operation parameters used to generate cache key
        
    Returns:
        Cached result if available, or message indicating cache miss
    """
    try:
        if not context or "dual_working_memory" not in context:
            return "Error: No working memory available in context"
        
        dual_memory = context["dual_working_memory"]
        result = dual_memory.get_cached_result(operation, **kwargs)
        
        if result is not None:
            # Format result for display
            if isinstance(result, dict):
                # Show key information from result
                summary_keys = ['energy_per_atom', 'feasible', 'num_structures', 'formula']
                summary = []
                for key in summary_keys:
                    if key in result:
                        summary.append(f"{key}: {result[key]}")
                
                summary_str = ", ".join(summary) if summary else "result available"
                return f"🎯 Cache hit for {operation}: {summary_str}"
            else:
                return f"🎯 Cache hit for {operation}: result available"
        else:
            params_str = ", ".join(f"{k}={v}" for k, v in list(kwargs.items())[:3])
            return f"❌ Cache miss for {operation} with params: {params_str}"
        
    except Exception as e:
        logger.error(f"get_cached_result error: {e}")
        return f"Error retrieving cached result: {str(e)}"


def cache_smact_feasibility(
    formula: str,
    feasibility_result: Dict[str, Any],
    context: Optional[Dict[str, Any]] = None
) -> str:
    """
    Cache SMACT feasibility result for a chemical formula.
    
    Args:
        formula: Chemical formula (e.g., 'NaCl', 'CaTiO3')
        feasibility_result: SMACT feasibility result dictionary
        
    Returns:
        Confirmation message
    """
    try:
        if not context or "dual_working_memory" not in context:
            return "Error: No working memory available in context"
        
        dual_memory = context["dual_working_memory"]
        cache_key = dual_memory.cache_smact_result(formula, feasibility_result)
        
        feasible = feasibility_result.get('feasible', False)
        return f"💾 Cached SMACT result for {formula}: {'feasible' if feasible else 'not feasible'}"
        
    except Exception as e:
        logger.error(f"cache_smact_feasibility error: {e}")
        return f"Error caching SMACT result: {str(e)}"


def get_smact_feasibility(
    formula: str,
    context: Optional[Dict[str, Any]] = None
) -> str:
    """
    Retrieve cached SMACT feasibility result.
    
    Args:
        formula: Chemical formula to check
        
    Returns:
        Cached feasibility result or cache miss message
    """
    try:
        if not context or "dual_working_memory" not in context:
            return "Error: No working memory available in context"
        
        dual_memory = context["dual_working_memory"]
        result = dual_memory.get_smact_result(formula)
        
        if result:
            feasible = result.get('feasible', False)
            confidence = result.get('confidence', 'unknown')
            return f"🎯 Cached SMACT for {formula}: {'feasible' if feasible else 'not feasible'} (confidence: {confidence})"
        else:
            return f"❌ No cached SMACT result for {formula}"
        
    except Exception as e:
        logger.error(f"get_smact_feasibility error: {e}")
        return f"Error retrieving SMACT result: {str(e)}"


def cache_chemeleon_structure(
    formula: str,
    structure_data: Dict[str, Any],
    context: Optional[Dict[str, Any]] = None,
    **generation_params
) -> str:
    """
    Cache Chemeleon structure generation result.
    
    Args:
        formula: Chemical formula
        structure_data: Generated structure data
        **generation_params: Parameters used for generation
        
    Returns:
        Confirmation message
    """
    try:
        if not context or "dual_working_memory" not in context:
            return "Error: No working memory available in context"
        
        dual_memory = context["dual_working_memory"]
        cache_key = dual_memory.cache_chemeleon_structure(formula, structure_data, **generation_params)
        
        num_structures = len(structure_data.get('structures', []))
        return f"💾 Cached {num_structures} Chemeleon structure(s) for {formula}"
        
    except Exception as e:
        logger.error(f"cache_chemeleon_structure error: {e}")
        return f"Error caching Chemeleon result: {str(e)}"


def get_chemeleon_structure(
    formula: str,
    context: Optional[Dict[str, Any]] = None,
    **generation_params
) -> str:
    """
    Retrieve cached Chemeleon structure.
    
    Args:
        formula: Chemical formula
        **generation_params: Parameters used for generation
        
    Returns:
        Cached structure result or cache miss message
    """
    try:
        if not context or "dual_working_memory" not in context:
            return "Error: No working memory available in context"
        
        dual_memory = context["dual_working_memory"]
        result = dual_memory.get_chemeleon_structure(formula, **generation_params)
        
        if result:
            num_structures = len(result.get('structures', []))
            return f"🎯 Found {num_structures} cached Chemeleon structure(s) for {formula}"
        else:
            return f"❌ No cached Chemeleon structures for {formula}"
        
    except Exception as e:
        logger.error(f"get_chemeleon_structure error: {e}")
        return f"Error retrieving Chemeleon result: {str(e)}"


def cache_mace_energy(
    structure_id: str,
    energy_data: Dict[str, Any],
    context: Optional[Dict[str, Any]] = None
) -> str:
    """
    Cache MACE energy calculation result.
    
    Args:
        structure_id: Unique identifier for the structure
        energy_data: MACE energy calculation result
        
    Returns:
        Confirmation message
    """
    try:
        if not context or "dual_working_memory" not in context:
            return "Error: No working memory available in context"
        
        dual_memory = context["dual_working_memory"]
        cache_key = dual_memory.cache_mace_energy(structure_id, energy_data)
        
        energy = energy_data.get('energy_per_atom', 'unknown')
        return f"💾 Cached MACE energy for {structure_id}: {energy} eV/atom"
        
    except Exception as e:
        logger.error(f"cache_mace_energy error: {e}")
        return f"Error caching MACE result: {str(e)}"


def get_mace_energy(
    structure_id: str,
    context: Optional[Dict[str, Any]] = None
) -> str:
    """
    Retrieve cached MACE energy result.
    
    Args:
        structure_id: Structure identifier
        
    Returns:
        Cached energy result or cache miss message
    """
    try:
        if not context or "dual_working_memory" not in context:
            return "Error: No working memory available in context"
        
        dual_memory = context["dual_working_memory"]
        result = dual_memory.get_mace_energy(structure_id)
        
        if result:
            energy = result.get('energy_per_atom', 'unknown')
            forces_available = 'forces' in result
            return f"🎯 Cached MACE for {structure_id}: {energy} eV/atom (forces: {'yes' if forces_available else 'no'})"
        else:
            return f"❌ No cached MACE energy for {structure_id}"
        
    except Exception as e:
        logger.error(f"get_mace_energy error: {e}")
        return f"Error retrieving MACE result: {str(e)}"


def get_cache_statistics(context: Optional[Dict[str, Any]] = None) -> str:
    """
    Get working memory cache statistics.
    
    Use this tool to understand cache performance and utilisation.
    
    Returns:
        Cache statistics summary
    """
    try:
        if not context or "dual_working_memory" not in context:
            return "Error: No working memory available in context"
        
        dual_memory = context["dual_working_memory"]
        stats = dual_memory.get_stats()
        
        cache_stats = stats.get("computational_cache", {})
        
        memory_entries = cache_stats.get("memory_entries", 0)
        disk_files = cache_stats.get("disk_files", 0)
        operations = cache_stats.get("operations", {})
        
        stats_text = f"📊 Cache Statistics:\n"
        stats_text += f"Memory entries: {memory_entries}\n"
        stats_text += f"Disk files: {disk_files}\n"
        
        if operations:
            stats_text += "Operations cached:\n"
            for op, count in operations.items():
                stats_text += f"  - {op}: {count}\n"
        
        return stats_text
        
    except Exception as e:
        logger.error(f"get_cache_statistics error: {e}")
        return f"Error getting cache statistics: {str(e)}"


def clear_expired_cache(context: Optional[Dict[str, Any]] = None) -> str:
    """
    Clear expired cache entries to free up space.
    
    Returns:
        Number of entries cleared
    """
    try:
        if not context or "dual_working_memory" not in context:
            return "Error: No working memory available in context"
        
        dual_memory = context["dual_working_memory"]
        working_memory = dual_memory.working_memory
        
        cleared_count = working_memory.clear_expired()
        
        return f"🧹 Cleared {cleared_count} expired cache entries"
        
    except Exception as e:
        logger.error(f"clear_expired_cache error: {e}")
        return f"Error clearing cache: {str(e)}"


def get_related_cached_results(
    operation: str,
    limit: int = 5,
    context: Optional[Dict[str, Any]] = None
) -> str:
    """
    Get recent cached results for a specific operation type.
    
    Args:
        operation: Operation type to search for
        limit: Maximum number of results to return
        
    Returns:
        List of related cached results
    """
    try:
        if not context or "dual_working_memory" not in context:
            return "Error: No working memory available in context"
        
        dual_memory = context["dual_working_memory"]
        working_memory = dual_memory.working_memory
        
        related_results = working_memory.get_related_results(operation, limit)
        
        if not related_results:
            return f"No cached results found for operation: {operation}"
        
        results_text = f"🔍 Recent {operation} results ({len(related_results)}):\n"
        
        for i, (cache_key, entry) in enumerate(related_results, 1):
            timestamp = entry['timestamp'].strftime("%H:%M:%S")
            params = entry.get('parameters', {})
            
            # Extract key parameter for display
            key_param = ""
            if 'formula' in params:
                key_param = params['formula']
            elif 'structure_id' in params:
                key_param = params['structure_id']
            
            results_text += f"  {i}. {timestamp} - {key_param} (key: {cache_key[:8]}...)\n"
        
        return results_text
        
    except Exception as e:
        logger.error(f"get_related_cached_results error: {e}")
        return f"Error getting related results: {str(e)}"


# Tool registry for easy access
MEMORY_TOOLS = {
    "cache_computational_result": cache_computational_result,
    "get_cached_result": get_cached_result,
    "cache_smact_feasibility": cache_smact_feasibility,
    "get_smact_feasibility": get_smact_feasibility,
    "cache_chemeleon_structure": cache_chemeleon_structure,
    "get_chemeleon_structure": get_chemeleon_structure,
    "cache_mace_energy": cache_mace_energy,
    "get_mace_energy": get_mace_energy,
    "get_cache_statistics": get_cache_statistics,
    "clear_expired_cache": clear_expired_cache,
    "get_related_cached_results": get_related_cached_results
}