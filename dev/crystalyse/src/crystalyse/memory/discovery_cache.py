"""
Discovery Cache - Layer 2 of CrystaLyse Simple Memory System

Simple JSON file cache for expensive calculations.
Fast lookups, no database overhead - just like gemini-cli.
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class DiscoveryCache:
    """
    Simple JSON-based cache for material properties and calculations.
    
    Stores expensive calculation results to avoid re-running MACE, 
    Chemeleon, and SMACT calculations. Uses simple file operations
    for maximum reliability and performance.
    """
    
    def __init__(self, cache_dir: Optional[Path] = None):
        """
        Initialize discovery cache.
        
        Args:
            cache_dir: Directory for cache files (default: ~/.crystalyse)
        """
        if cache_dir is None:
            cache_dir = Path.home() / ".crystalyse"
        
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        self.cache_file = self.cache_dir / "discoveries.json"
        self.cache_data = self._load_cache()
        
        logger.info(f"DiscoveryCache initialized at {self.cache_file}")
    
    def _load_cache(self) -> Dict[str, Any]:
        """Load cache from JSON file."""
        if not self.cache_file.exists():
            return {}
        
        try:
            with open(self.cache_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            logger.warning(f"Failed to load cache file: {e}")
            return {}
    
    def _save_cache(self) -> None:
        """Save cache to JSON file."""
        try:
            with open(self.cache_file, "w", encoding="utf-8") as f:
                json.dump(self.cache_data, f, indent=2, ensure_ascii=False)
        except OSError as e:
            logger.error(f"Failed to save cache file: {e}")
    
    def get_cached_result(self, formula: str) -> Optional[Dict[str, Any]]:
        """
        Get cached result for a material formula.
        
        Args:
            formula: Chemical formula (e.g., "LiCoO2")
            
        Returns:
            Cached properties if available, None otherwise
        """
        result = self.cache_data.get(formula)
        if result:
            logger.debug(f"Cache hit for {formula}")
        else:
            logger.debug(f"Cache miss for {formula}")
        return result
    
    def save_result(self, formula: str, properties: Dict[str, Any]) -> None:
        """
        Save calculation result to cache.
        
        Args:
            formula: Chemical formula
            properties: Material properties to cache
        """
        # Add metadata
        cache_entry = {
            "formula": formula,
            "properties": properties,
            "timestamp": datetime.now().isoformat(),
            "cached_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        self.cache_data[formula] = cache_entry
        self._save_cache()
        
        logger.info(f"Cached result for {formula}")
    
    def search_similar(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Search for similar materials in cache.
        
        Args:
            query: Search query
            limit: Maximum number of results
            
        Returns:
            List of similar cached materials
        """
        query_lower = query.lower()
        matches = []
        
        for formula, data in self.cache_data.items():
            if (query_lower in formula.lower() or
                query_lower in str(data.get("properties", {})).lower()):
                matches.append(data)
        
        return matches[:limit]
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dictionary with cache statistics
        """
        return {
            "total_entries": len(self.cache_data),
            "cache_file": str(self.cache_file),
            "cache_size_mb": self.cache_file.stat().st_size / (1024 * 1024) if self.cache_file.exists() else 0
        }
    
    def clear_cache(self) -> None:
        """Clear all cached data."""
        self.cache_data.clear()
        self._save_cache()
        logger.info("Discovery cache cleared")
    
    def export_cache(self, export_path: Path) -> None:
        """
        Export cache to a different location.
        
        Args:
            export_path: Path to export cache file
        """
        try:
            with open(export_path, "w", encoding="utf-8") as f:
                json.dump(self.cache_data, f, indent=2, ensure_ascii=False)
            logger.info(f"Cache exported to {export_path}")
        except OSError as e:
            logger.error(f"Failed to export cache: {e}")
    
    def import_cache(self, import_path: Path, merge: bool = True) -> None:
        """
        Import cache from another location.
        
        Args:
            import_path: Path to import cache file from
            merge: Whether to merge with existing cache or replace
        """
        try:
            with open(import_path, "r", encoding="utf-8") as f:
                imported_data = json.load(f)
            
            if merge:
                self.cache_data.update(imported_data)
            else:
                self.cache_data = imported_data
            
            self._save_cache()
            logger.info(f"Cache imported from {import_path} (merge: {merge})")
        except (json.JSONDecodeError, OSError) as e:
            logger.error(f"Failed to import cache: {e}")
    
    def get_recent_discoveries(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get recently cached discoveries.
        
        Args:
            limit: Maximum number of discoveries to return
            
        Returns:
            List of recent discoveries sorted by timestamp
        """
        # Sort by timestamp (newest first)
        sorted_discoveries = sorted(
            self.cache_data.values(),
            key=lambda x: x.get("timestamp", ""),
            reverse=True
        )
        
        return sorted_discoveries[:limit] 