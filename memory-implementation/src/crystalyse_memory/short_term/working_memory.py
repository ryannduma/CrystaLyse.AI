# crystalyse_memory/short_term/working_memory.py
"""
Working Memory for CrystaLyse.AI Memory System

Provides computational caching for expensive calculations (MACE, Chemeleon)
and efficient storage/retrieval of intermediate results.
"""

from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta
import json
import hashlib
import logging
from pathlib import Path
import pickle

logger = logging.getLogger(__name__)


class WorkingMemory:
    """
    Computational working memory for CrystaLyse.AI agent.
    
    Caches expensive calculations and intermediate results to improve
    performance and avoid redundant computations.
    """
    
    def __init__(self, cache_dir: Optional[Path] = None, max_age_hours: int = 24):
        """
        Initialise working memory.
        
        Args:
            cache_dir: Directory for persistent cache storage
            max_age_hours: Maximum age for cached items in hours
        """
        self.cache_dir = cache_dir or Path("./memory/cache")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        self.max_age = timedelta(hours=max_age_hours)
        self.memory_cache: Dict[str, Dict[str, Any]] = {}
        
        logger.info(f"WorkingMemory initialised with cache_dir: {self.cache_dir}")
    
    def _generate_key(self, operation: str, **kwargs) -> str:
        """Generate unique cache key for operation and parameters."""
        # Sort kwargs for consistent hashing
        sorted_kwargs = sorted(kwargs.items())
        key_data = f"{operation}:{json.dumps(sorted_kwargs, sort_keys=True)}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def _is_expired(self, timestamp: datetime) -> bool:
        """Check if cached item has expired."""
        return datetime.now() - timestamp > self.max_age
    
    def cache_result(self, operation: str, result: Any, **kwargs) -> str:
        """
        Cache computational result.
        
        Args:
            operation: Type of operation (e.g., 'mace_energy', 'chemeleon_csp')
            result: Result to cache
            **kwargs: Operation parameters used to generate cache key
            
        Returns:
            Cache key for the stored result
        """
        cache_key = self._generate_key(operation, **kwargs)
        
        cache_entry = {
            'result': result,
            'timestamp': datetime.now(),
            'operation': operation,
            'parameters': kwargs
        }
        
        # Store in memory
        self.memory_cache[cache_key] = cache_entry
        
        # Store persistently if large/important result
        if self._should_persist(operation, result):
            cache_file = self.cache_dir / f"{cache_key}.pkl"
            try:
                with open(cache_file, 'wb') as f:
                    pickle.dump(cache_entry, f)
                logger.debug(f"Cached {operation} result to disk: {cache_key}")
            except Exception as e:
                logger.warning(f"Failed to persist cache entry {cache_key}: {e}")
        
        logger.debug(f"Cached {operation} result: {cache_key}")
        return cache_key
    
    def get_cached_result(self, operation: str, **kwargs) -> Optional[Any]:
        """
        Retrieve cached result if available and not expired.
        
        Args:
            operation: Type of operation
            **kwargs: Operation parameters
            
        Returns:
            Cached result if available, None otherwise
        """
        cache_key = self._generate_key(operation, **kwargs)
        
        # Check memory cache first
        if cache_key in self.memory_cache:
            entry = self.memory_cache[cache_key]
            if not self._is_expired(entry['timestamp']):
                logger.debug(f"Cache hit (memory): {cache_key}")
                return entry['result']
            else:
                # Remove expired entry
                del self.memory_cache[cache_key]
        
        # Check disk cache
        cache_file = self.cache_dir / f"{cache_key}.pkl"
        if cache_file.exists():
            try:
                with open(cache_file, 'rb') as f:
                    entry = pickle.load(f)
                
                if not self._is_expired(entry['timestamp']):
                    # Load back into memory
                    self.memory_cache[cache_key] = entry
                    logger.debug(f"Cache hit (disk): {cache_key}")
                    return entry['result']
                else:
                    # Remove expired file
                    cache_file.unlink()
                    logger.debug(f"Removed expired cache file: {cache_key}")
            except Exception as e:
                logger.warning(f"Failed to load cache file {cache_key}: {e}")
        
        logger.debug(f"Cache miss: {cache_key}")
        return None
    
    def _should_persist(self, operation: str, result: Any) -> bool:
        """Determine if result should be persisted to disk."""
        # Persist expensive computational results
        expensive_operations = {
            'mace_energy', 'mace_forces', 'mace_stress',
            'chemeleon_csp', 'chemeleon_structure_generation',
            'smact_feasibility_large_batch'
        }
        return operation in expensive_operations
    
    def cache_smact_result(self, formula: str, result: Dict[str, Any]) -> str:
        """Cache SMACT feasibility result."""
        return self.cache_result('smact_feasibility', result, formula=formula)
    
    def get_smact_result(self, formula: str) -> Optional[Dict[str, Any]]:
        """Get cached SMACT feasibility result."""
        return self.get_cached_result('smact_feasibility', formula=formula)
    
    def cache_chemeleon_structure(self, formula: str, structure_data: Dict[str, Any], **params) -> str:
        """Cache Chemeleon structure generation result."""
        return self.cache_result('chemeleon_csp', structure_data, formula=formula, **params)
    
    def get_chemeleon_structure(self, formula: str, **params) -> Optional[Dict[str, Any]]:
        """Get cached Chemeleon structure."""
        return self.get_cached_result('chemeleon_csp', formula=formula, **params)
    
    def cache_mace_energy(self, structure_id: str, energy_data: Dict[str, Any]) -> str:
        """Cache MACE energy calculation result."""
        return self.cache_result('mace_energy', energy_data, structure_id=structure_id)
    
    def get_mace_energy(self, structure_id: str) -> Optional[Dict[str, Any]]:
        """Get cached MACE energy result."""
        return self.get_cached_result('mace_energy', structure_id=structure_id)
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total_entries = len(self.memory_cache)
        
        # Count by operation type
        operation_counts = {}
        for entry in self.memory_cache.values():
            op = entry['operation']
            operation_counts[op] = operation_counts.get(op, 0) + 1
        
        # Count disk cache files
        disk_files = len(list(self.cache_dir.glob("*.pkl")))
        
        return {
            'memory_entries': total_entries,
            'disk_files': disk_files,
            'operations': operation_counts,
            'cache_dir': str(self.cache_dir)
        }
    
    def clear_expired(self) -> int:
        """Clear expired cache entries."""
        removed_count = 0
        
        # Clear memory cache
        expired_keys = []
        for key, entry in self.memory_cache.items():
            if self._is_expired(entry['timestamp']):
                expired_keys.append(key)
        
        for key in expired_keys:
            del self.memory_cache[key]
            removed_count += 1
        
        # Clear disk cache
        for cache_file in self.cache_dir.glob("*.pkl"):
            try:
                with open(cache_file, 'rb') as f:
                    entry = pickle.load(f)
                if self._is_expired(entry['timestamp']):
                    cache_file.unlink()
                    removed_count += 1
            except Exception as e:
                logger.warning(f"Error checking cache file {cache_file}: {e}")
        
        logger.info(f"Cleared {removed_count} expired cache entries")
        return removed_count
    
    def clear_all(self) -> None:
        """Clear all cache entries."""
        self.memory_cache.clear()
        
        # Remove all disk cache files
        for cache_file in self.cache_dir.glob("*.pkl"):
            try:
                cache_file.unlink()
            except Exception as e:
                logger.warning(f"Error removing cache file {cache_file}: {e}")
        
        logger.info("Cleared all cache entries")
    
    def get_related_results(self, operation: str, limit: int = 10) -> List[Tuple[str, Dict[str, Any]]]:
        """Get recent results for a specific operation type."""
        results = []
        
        for key, entry in self.memory_cache.items():
            if entry['operation'] == operation and not self._is_expired(entry['timestamp']):
                results.append((key, entry))
        
        # Sort by timestamp (most recent first)
        results.sort(key=lambda x: x[1]['timestamp'], reverse=True)
        
        return results[:limit]