"""Error handling framework for CrystaLyse tools."""
from typing import Optional, Any, Callable, TypeVar, List
from functools import wraps
import asyncio
import logging
from pydantic import BaseModel

logger = logging.getLogger(__name__)

T = TypeVar('T', bound=BaseModel)


class CrystaLyseToolError(Exception):
    """Base exception for tool errors."""
    def __init__(
        self,
        message: str,
        recoverable: bool = True,
        fallback: Optional[Any] = None,
        retry_after: Optional[float] = None
    ):
        super().__init__(message)
        self.recoverable = recoverable
        self.fallback = fallback
        self.retry_after = retry_after


class ValidationError(CrystaLyseToolError):
    """Validation-specific errors."""
    pass


class ComputationError(CrystaLyseToolError):
    """Computation/calculation errors."""
    pass


class ResourceUnavailableError(CrystaLyseToolError):
    """Resource (model, checkpoint) unavailable."""
    pass


def with_retry(
    max_attempts: int = 3,
    backoff_factor: float = 2.0,
    recoverable_exceptions: tuple = (ComputationError, ResourceUnavailableError),
    fallback_result: Optional[Callable[[], T]] = None
):
    """
    Decorator for automatic retry with exponential backoff.

    Args:
        max_attempts: Maximum number of retry attempts
        backoff_factor: Factor for exponential backoff
        recoverable_exceptions: Exceptions that trigger retry
        fallback_result: Function that returns a fallback result
    """
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            last_exception = None

            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)

                except recoverable_exceptions as e:
                    last_exception = e

                    if attempt < max_attempts - 1:
                        wait_time = backoff_factor ** attempt
                        logger.warning(
                            f"Attempt {attempt + 1}/{max_attempts} failed: {e}. "
                            f"Retrying in {wait_time}s..."
                        )
                        await asyncio.sleep(wait_time)
                    else:
                        logger.error(f"All {max_attempts} attempts failed: {e}")

                except Exception as e:
                    # Non-recoverable error
                    logger.error(f"Non-recoverable error in {func.__name__}: {e}")
                    raise

            # All retries exhausted
            if fallback_result:
                logger.info(f"Using fallback for {func.__name__}")
                return fallback_result()

            if last_exception and hasattr(last_exception, 'fallback'):
                return last_exception.fallback

            raise last_exception

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            # Synchronous version
            last_exception = None

            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except recoverable_exceptions as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        import time
                        wait_time = backoff_factor ** attempt
                        logger.warning(f"Retry in {wait_time}s...")
                        time.sleep(wait_time)
                except Exception as e:
                    logger.error(f"Non-recoverable: {e}")
                    raise

            if fallback_result:
                return fallback_result()
            raise last_exception

        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    return decorator


class FallbackChain:
    """Chain multiple tools with automatic fallback."""

    def __init__(self, tools: List[Callable]):
        self.tools = tools

    async def execute(self, *args, **kwargs) -> Any:
        """Execute tools in order until one succeeds."""
        errors = []

        for i, tool in enumerate(self.tools):
            try:
                logger.info(f"Trying tool {i+1}/{len(self.tools)}: {tool.__name__}")
                if asyncio.iscoroutinefunction(tool):
                    return await tool(*args, **kwargs)
                else:
                    return tool(*args, **kwargs)
            except Exception as e:
                errors.append((tool.__name__, str(e)))
                logger.warning(f"Tool {tool.__name__} failed: {e}")
                continue

        # All tools failed
        error_summary = "; ".join([f"{name}: {err}" for name, err in errors])
        raise CrystaLyseToolError(
            f"All tools in chain failed: {error_summary}",
            recoverable=False
        )
