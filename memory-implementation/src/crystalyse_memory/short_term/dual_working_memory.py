# crystalyse_memory/short_term/dual_working_memory.py
"""
Dual Working Memory for CrystaLyse.AI Memory System

Combines computational working memory (caching) with agent reasoning scratchpad
to provide both performance benefits and transparent reasoning capabilities.
"""

from typing import Dict, Any, Optional, List, Tuple
from pathlib import Path
import logging

from .working_memory import WorkingMemory
from .agent_scratchpad import AgentScratchpad

logger = logging.getLogger(__name__)


class DualWorkingMemory:
    """
    Dual working memory system combining computational cache and reasoning scratchpad.
    
    This class provides both:
    1. Computational Working Memory: Caches expensive calculations (MACE, Chemeleon)
    2. Agent Reasoning Scratchpad: Erasable planning and reasoning workspace
    
    Designed to work with OpenAI Agents SDK for transparent AI reasoning.
    """
    
    def __init__(
        self, 
        session_id: str, 
        user_id: str,
        cache_dir: Optional[Path] = None,
        scratchpad_dir: Optional[Path] = None,
        max_cache_age_hours: int = 24
    ):
        """
        Initialise dual working memory system.
        
        Args:
            session_id: Unique session identifier
            user_id: User identifier
            cache_dir: Directory for computational cache storage
            scratchpad_dir: Directory for scratchpad files
            max_cache_age_hours: Maximum age for cached items in hours
        """
        self.session_id = session_id
        self.user_id = user_id
        
        # Initialise computational working memory
        self.working_memory = WorkingMemory(
            cache_dir=cache_dir,
            max_age_hours=max_cache_age_hours
        )
        
        # Initialise agent scratchpad
        self.scratchpad = AgentScratchpad(
            session_id=session_id,
            user_id=user_id,
            base_dir=scratchpad_dir
        )
        
        logger.info(f"DualWorkingMemory initialised for user {user_id}, session {session_id}")
    
    # ========== Computational Cache Interface ==========
    
    def cache_result(self, operation: str, result: Any, **kwargs) -> str:
        """Cache computational result and log to scratchpad."""
        cache_key = self.working_memory.cache_result(operation, result, **kwargs)
        
        # Log caching operation to scratchpad
        cache_message = f"Cached {operation} result (key: {cache_key[:8]}...)"
        if kwargs:
            params_str = ", ".join(f"{k}={v}" for k, v in list(kwargs.items())[:3])
            cache_message += f" with parameters: {params_str}"
        
        self.scratchpad.write_to_scratchpad(cache_message, "tools_used")
        
        return cache_key
    
    def get_cached_result(self, operation: str, **kwargs) -> Optional[Any]:
        """Retrieve cached result and log to scratchpad."""
        result = self.working_memory.get_cached_result(operation, **kwargs)
        
        if result is not None:
            cache_message = f"Retrieved cached {operation} result (cache hit)"
            self.scratchpad.write_to_scratchpad(cache_message, "tools_used")
        else:
            cache_message = f"No cached result for {operation} (cache miss)"
            self.scratchpad.write_to_scratchpad(cache_message, "observation")
        
        return result
    
    # Specific computational caching methods
    
    def cache_smact_result(self, formula: str, result: Dict[str, Any]) -> str:
        """Cache SMACT result with scratchpad logging."""
        cache_key = self.working_memory.cache_smact_result(formula, result)
        
        feasible = result.get('feasible', False)
        message = f"SMACT validation for {formula}: {'feasible' if feasible else 'not feasible'}"
        self.scratchpad.write_to_scratchpad(message, "analysis")
        
        return cache_key
    
    def get_smact_result(self, formula: str) -> Optional[Dict[str, Any]]:
        """Get cached SMACT result with scratchpad logging."""
        result = self.working_memory.get_smact_result(formula)
        
        if result:
            feasible = result.get('feasible', False)
            message = f"Found cached SMACT result for {formula}: {'feasible' if feasible else 'not feasible'}"
            self.scratchpad.write_to_scratchpad(message, "observation")
        
        return result
    
    def cache_chemeleon_structure(self, formula: str, structure_data: Dict[str, Any], **params) -> str:
        """Cache Chemeleon structure with scratchpad logging."""
        cache_key = self.working_memory.cache_chemeleon_structure(formula, structure_data, **params)
        
        num_structures = len(structure_data.get('structures', []))
        message = f"Generated {num_structures} structure(s) for {formula} using Chemeleon"
        self.scratchpad.write_to_scratchpad(message, "progress")
        
        return cache_key
    
    def get_chemeleon_structure(self, formula: str, **params) -> Optional[Dict[str, Any]]:
        """Get cached Chemeleon structure with scratchpad logging."""
        result = self.working_memory.get_chemeleon_structure(formula, **params)
        
        if result:
            num_structures = len(result.get('structures', []))
            message = f"Retrieved {num_structures} cached structure(s) for {formula}"
            self.scratchpad.write_to_scratchpad(message, "observation")
        
        return result
    
    def cache_mace_energy(self, structure_id: str, energy_data: Dict[str, Any]) -> str:
        """Cache MACE energy with scratchpad logging."""
        cache_key = self.working_memory.cache_mace_energy(structure_id, energy_data)
        
        energy = energy_data.get('energy_per_atom')
        message = f"MACE energy for {structure_id}: {energy:.3f} eV/atom" if energy else f"MACE calculation completed for {structure_id}"
        self.scratchpad.write_to_scratchpad(message, "analysis")
        
        return cache_key
    
    def get_mace_energy(self, structure_id: str) -> Optional[Dict[str, Any]]:
        """Get cached MACE energy with scratchpad logging."""
        result = self.working_memory.get_mace_energy(structure_id)
        
        if result:
            energy = result.get('energy_per_atom')
            message = f"Retrieved cached MACE energy for {structure_id}: {energy:.3f} eV/atom" if energy else f"Found cached MACE result for {structure_id}"
            self.scratchpad.write_to_scratchpad(message, "observation")
        
        return result
    
    # ========== Scratchpad Interface ==========
    
    def write_to_scratchpad(self, content: str, section: str = "reasoning") -> None:
        """Write to agent scratchpad."""
        self.scratchpad.write_to_scratchpad(content, section)
    
    def read_scratchpad(self) -> str:
        """Read current scratchpad contents."""
        return self.scratchpad.read_scratchpad()
    
    def update_plan(self, new_plan: str) -> None:
        """Update current plan in scratchpad."""
        self.scratchpad.update_plan(new_plan)
    
    def get_current_plan(self) -> Optional[str]:
        """Get current plan from scratchpad."""
        return self.scratchpad.get_current_plan()
    
    def erase_scratchpad_section(self, section: str) -> None:
        """Erase specific section from scratchpad."""
        self.scratchpad.erase_section(section)
    
    def clear_scratchpad(self) -> None:
        """Clear all scratchpad content."""
        self.scratchpad.clear_scratchpad()
    
    def get_scratchpad_file_path(self) -> str:
        """Get path to scratchpad file."""
        return self.scratchpad.get_file_path()
    
    # ========== Integrated Workflows ==========
    
    def start_complex_query(self, query: str, initial_plan: str) -> None:
        """
        Start a complex multi-step query with planning.
        
        Args:
            query: The user's query
            initial_plan: Initial approach plan
        """
        self.scratchpad.write_to_scratchpad(f"Starting complex query: {query}", "thought")
        self.scratchpad.write_to_scratchpad(initial_plan, "plan")
        
        # Clear old cache if needed
        cache_stats = self.working_memory.get_cache_stats()
        if cache_stats['memory_entries'] > 100:
            cleared = self.working_memory.clear_expired()
            if cleared > 0:
                self.scratchpad.write_to_scratchpad(f"Cleared {cleared} expired cache entries", "tools_used")
    
    def log_tool_usage(self, tool_name: str, parameters: Dict[str, Any], result_summary: str) -> None:
        """
        Log tool usage with parameters and results.
        
        Args:
            tool_name: Name of the tool used
            parameters: Parameters passed to the tool
            result_summary: Brief summary of the result
        """
        params_str = ", ".join(f"{k}={v}" for k, v in list(parameters.items())[:3])
        tool_message = f"Used {tool_name} with {params_str} → {result_summary}"
        self.scratchpad.write_to_scratchpad(tool_message, "tools_used")
    
    def log_reasoning_step(self, reasoning: str) -> None:
        """Log a reasoning step."""
        self.scratchpad.write_to_scratchpad(reasoning, "reasoning")
    
    def log_observation(self, observation: str) -> None:
        """Log an observation from tool results."""
        self.scratchpad.write_to_scratchpad(observation, "observation")
    
    def log_progress(self, progress: str) -> None:
        """Log progress update."""
        self.scratchpad.write_to_scratchpad(progress, "progress")
    
    def conclude_query(self, conclusion: str) -> None:
        """Log final conclusion."""
        self.scratchpad.write_to_scratchpad(conclusion, "conclusion")
    
    # ========== Statistics and Management ==========
    
    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive statistics for both memory systems."""
        cache_stats = self.working_memory.get_cache_stats()
        scratchpad_stats = self.scratchpad.get_stats()
        
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "computational_cache": cache_stats,
            "reasoning_scratchpad": scratchpad_stats
        }
    
    def export_session_summary(self) -> Dict[str, Any]:
        """Export a comprehensive session summary."""
        cache_stats = self.working_memory.get_cache_stats()
        scratchpad_summary = self.scratchpad.export_summary()
        
        return {
            "session_summary": {
                "session_id": self.session_id,
                "user_id": self.user_id,
                "computational_performance": {
                    "cache_hits": cache_stats,
                    "operations_cached": cache_stats.get('operations', {})
                },
                "reasoning_process": scratchpad_summary
            }
        }
    
    def cleanup(self) -> None:
        """Clean up both memory systems."""
        # Archive scratchpad
        self.scratchpad.cleanup()
        
        # Optionally clear working memory cache
        # (Usually kept for future sessions)
        logger.info(f"DualWorkingMemory cleanup completed for session {self.session_id}")
    
    # ========== Context for OpenAI Agents SDK ==========
    
    def get_agent_context(self) -> Dict[str, Any]:
        """
        Get context data for OpenAI Agents SDK agent.
        
        Returns:
            Context dictionary with both memory systems
        """
        return {
            "dual_working_memory": self,
            "computational_cache": self.working_memory,
            "reasoning_scratchpad": self.scratchpad,
            "session_id": self.session_id,
            "user_id": self.user_id
        }