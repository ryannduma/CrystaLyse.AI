"""
Resilient Tool Caller for CrystaLyse.AI
Provides retry logic and error handling for MCP tool calls.
"""
import asyncio
import logging
import random
import time
from typing import Any, Callable, Dict, Optional, Union
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)

class ResilientToolCaller:
    """
    Wraps tool calls with retry logic, timeout handling, and error recovery.
    
    Designed specifically for CrystaLyse's computational tools (SMACT, Chemeleon, MACE).
    """
    
    def __init__(self):
        self.call_statistics = {}
        self.timeout_config = ToolTimeoutConfig()
        
    async def call_with_retry(
        self,
        tool_func: Callable,
        *args,
        tool_name: str = "unknown",
        operation_type: str = "default",
        max_retries: int = 3,
        timeout_override: Optional[int] = None,
        **kwargs
    ) -> Any:
        """
        Call a tool function with retry logic and appropriate timeouts.
        
        Args:
            tool_func: The tool function to call
            *args: Arguments to pass to the tool function
            tool_name: Name of the tool (smact, chemeleon, mace)
            operation_type: Type of operation (validation, structure, energy, etc.)
            max_retries: Maximum number of retry attempts
            timeout_override: Override the default timeout
            **kwargs: Keyword arguments to pass to the tool function
            
        Returns:
            Result from the tool function
            
        Raises:
            Exception: If all retry attempts fail
        """
        # Determine appropriate timeout
        timeout = timeout_override or self.timeout_config.get_timeout(tool_name, operation_type)
        
        # Track call statistics
        call_key = f"{tool_name}_{operation_type}"
        if call_key not in self.call_statistics:
            self.call_statistics[call_key] = {
                'total_calls': 0,
                'successful_calls': 0,
                'failed_calls': 0,
                'avg_duration': 0.0,
                'timeout_failures': 0,
                'connection_failures': 0
            }
        
        stats = self.call_statistics[call_key]
        stats['total_calls'] += 1
        
        last_error = None
        start_time = time.time()
        
        for attempt in range(max_retries):
            try:
                logger.info(f"🔧 Calling {tool_name} ({operation_type}) - attempt {attempt + 1}/{max_retries}")
                
                # Add jitter to prevent thundering herd for retries
                if attempt > 0:
                    jitter = random.uniform(0, 1.0)
                    wait_time = (2 ** attempt) + jitter
                    logger.info(f"⏳ Waiting {wait_time:.1f}s before retry...")
                    await asyncio.sleep(wait_time)
                
                # Execute the tool call with timeout
                result = await asyncio.wait_for(
                    tool_func(*args, **kwargs),
                    timeout=timeout
                )
                
                # Success!
                duration = time.time() - start_time
                stats['successful_calls'] += 1
                stats['avg_duration'] = (
                    (stats['avg_duration'] * (stats['successful_calls'] - 1) + duration) 
                    / stats['successful_calls']
                )
                
                logger.info(f"✅ {tool_name} call succeeded in {duration:.1f}s (attempt {attempt + 1})")
                return result
                
            except asyncio.TimeoutError as e:
                duration = time.time() - start_time
                stats['timeout_failures'] += 1
                last_error = e
                
                logger.warning(f"⏰ {tool_name} timed out after {timeout}s (attempt {attempt + 1})")
                
                # For timeouts, don't retry unless it's a very short timeout
                if timeout >= 60:  # Don't retry long operations
                    logger.error(f"❌ {tool_name} operation too complex, not retrying timeout")
                    break
                    
            except ConnectionError as e:
                stats['connection_failures'] += 1
                last_error = e
                
                logger.warning(f"🔌 {tool_name} connection failed: {e} (attempt {attempt + 1})")
                
                # Connection errors are worth retrying
                continue
                
            except Exception as e:
                last_error = e
                logger.warning(f"⚠️ {tool_name} call failed: {e} (attempt {attempt + 1})")
                
                # For other errors, only retry if it might be transient
                if "server" in str(e).lower() or "connection" in str(e).lower():
                    continue
                else:
                    # Non-transient error, don't retry
                    break
        
        # All attempts failed
        total_duration = time.time() - start_time
        stats['failed_calls'] += 1
        
        logger.error(f"❌ {tool_name} failed after {max_retries} attempts in {total_duration:.1f}s")
        
        # Provide detailed error information
        error_msg = f"Tool call failed: {tool_name} ({operation_type})\n"
        error_msg += f"Attempts: {max_retries}, Duration: {total_duration:.1f}s\n"
        error_msg += f"Last error: {last_error}"
        
        raise Exception(error_msg) from last_error
    
    async def call_with_fallback(
        self,
        primary_func: Callable,
        fallback_func: Optional[Callable] = None,
        *args,
        tool_name: str = "unknown",
        **kwargs
    ) -> Any:
        """
        Call a tool with a fallback option if the primary fails.
        
        Useful for creative mode where we can fall back to cached results or simpler operations.
        """
        try:
            return await self.call_with_retry(primary_func, *args, tool_name=tool_name, **kwargs)
        except Exception as e:
            if fallback_func is not None:
                logger.warning(f"🔄 {tool_name} primary call failed, trying fallback: {e}")
                try:
                    return await fallback_func(*args, **kwargs)
                except Exception as fallback_error:
                    logger.error(f"❌ {tool_name} fallback also failed: {fallback_error}")
                    raise e  # Raise original error
            else:
                raise e
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get call statistics for monitoring and debugging."""
        return {
            'call_stats': self.call_statistics.copy(),
            'overall_stats': self._calculate_overall_stats()
        }
    
    def _calculate_overall_stats(self) -> Dict[str, Any]:
        """Calculate overall statistics across all tools."""
        total_calls = sum(stats['total_calls'] for stats in self.call_statistics.values())
        successful_calls = sum(stats['successful_calls'] for stats in self.call_statistics.values())
        failed_calls = sum(stats['failed_calls'] for stats in self.call_statistics.values())
        
        if total_calls == 0:
            return {'success_rate': 0.0, 'total_calls': 0}
            
        return {
            'total_calls': total_calls,
            'successful_calls': successful_calls,
            'failed_calls': failed_calls,
            'success_rate': (successful_calls / total_calls) * 100,
            'failure_rate': (failed_calls / total_calls) * 100
        }

class ToolTimeoutConfig:
    """Configuration for tool timeouts based on operation complexity."""
    
    def __init__(self):
        # 5-minute default as requested
        self.default_timeout = 300
        
        # Specific timeouts for different operations
        self.timeouts = {
            # SMACT operations (usually quick)
            'smact_validation': 60,
            'smact_element_filter': 30,
            'smact_composition_generation': 120,
            
            # Chemeleon operations (structure generation can be slow)
            'chemeleon_structure_single': 180,
            'chemeleon_structure_batch': 300,
            'chemeleon_novel_discovery': 300,
            
            # MACE operations (energy calculations)
            'mace_single_energy': 120,
            'mace_batch_energy': 300,
            'mace_optimization': 300,
            
            # Combined operations
            'discovery_workflow': 300,
            'validation_workflow': 180,
        }
    
    def get_timeout(self, tool_name: str, operation_type: str) -> int:
        """Get appropriate timeout for a tool operation."""
        # Try specific key first
        key = f"{tool_name}_{operation_type}"
        if key in self.timeouts:
            return self.timeouts[key]
        
        # Try tool-based defaults
        tool_defaults = {
            'smact': 60,
            'chemeleon': 300,  # 5 minutes for structure generation
            'mace': 180,
            'chemistry_unified': 300
        }
        
        return tool_defaults.get(tool_name, self.default_timeout)
    
    def update_timeout(self, tool_name: str, operation_type: str, timeout: int) -> None:
        """Update timeout configuration."""
        key = f"{tool_name}_{operation_type}"
        self.timeouts[key] = timeout
        logger.info(f"Updated timeout for {key}: {timeout}s")

# Global resilient caller instance
_resilient_caller: Optional[ResilientToolCaller] = None

def get_resilient_caller() -> ResilientToolCaller:
    """Get the global resilient caller instance."""
    global _resilient_caller
    if _resilient_caller is None:
        _resilient_caller = ResilientToolCaller()
    return _resilient_caller