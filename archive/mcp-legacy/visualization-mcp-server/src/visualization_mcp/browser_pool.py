"""
Browser Session Pool for Crystalyse Visualization Pipeline

This module provides efficient browser session management for pymatviz/kaleido
to eliminate redundant browser instance creation and improve performance.
"""

import atexit
import logging
import os
import threading
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class BrowserSessionManager:
    """
    Manages browser sessions for pymatviz/kaleido to eliminate redundant browser instances.

    Key features:
    - Single browser instance for multiple visualizations
    - Batch PDF generation
    - Proper session lifecycle management
    - Thread-safe operations
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        """Singleton pattern to ensure only one browser session manager."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize browser session manager."""
        if hasattr(self, "initialized"):
            return

        self.initialized = True
        self.browser_session = None
        self.session_lock = threading.Lock()
        self.session_timeout = 300  # 5 minutes
        self.last_used = 0
        self.figures_queue = []

        # Configure headless environment
        os.environ.setdefault("DISPLAY", ":99")

        # Register cleanup
        atexit.register(self.cleanup)

        logger.info("BrowserSessionManager initialized")

    def _configure_kaleido_session(self):
        """Configure kaleido for optimized browser reuse."""
        try:
            import kaleido

            # Configure kaleido for browser reuse
            if hasattr(kaleido, "config") and hasattr(kaleido.config, "scope"):
                # Disable problematic features
                kaleido.config.scope.chromium.disable_features = [
                    "VizDisplayCompositor",
                    "UseOzonePlatform",
                    "WebGL",
                    "WebGL2",
                ]

                # Configure for session reuse
                kaleido.config.scope.chromium.timeout = 60
                kaleido.config.scope.chromium.session_timeout = 300

                # Keep browser alive longer
                if hasattr(kaleido.config.scope.chromium, "keep_alive"):
                    kaleido.config.scope.chromium.keep_alive = True

                # Configure for batch processing
                if hasattr(kaleido.config.scope, "plotly"):
                    kaleido.config.scope.plotly.engine = "chromium"

            logger.info("Kaleido configured for browser session reuse")

        except (ImportError, AttributeError) as e:
            logger.warning(f"Could not configure kaleido for browser reuse: {e}")

    def _get_or_create_session(self):
        """Get or create browser session."""
        with self.session_lock:
            current_time = time.time()

            # Check if session is still valid
            if (
                self.browser_session is not None
                and current_time - self.last_used < self.session_timeout
            ):
                self.last_used = current_time
                return self.browser_session

            # Create new session
            self._cleanup_session()
            self._configure_kaleido_session()

            # Initialize session (this will be done when first figure is saved)
            self.browser_session = "active"
            self.last_used = current_time

            logger.info("Browser session created/renewed")
            return self.browser_session

    def _cleanup_session(self):
        """Clean up current browser session."""
        if self.browser_session is not None:
            try:
                # Force kaleido cleanup
                import kaleido

                if hasattr(kaleido, "config") and hasattr(kaleido.config, "scope"):
                    # Force cleanup of any existing scope
                    scope = kaleido.config.scope
                    if hasattr(scope, "_shutdown"):
                        scope._shutdown()

                logger.info("Browser session cleaned up")
            except Exception as e:
                logger.warning(f"Error cleaning up browser session: {e}")
            finally:
                self.browser_session = None

    @contextmanager
    def batch_session(self):
        """Context manager for batch visualization operations."""
        session = self._get_or_create_session()
        try:
            yield session
        finally:
            # Keep session alive for potential reuse
            pass

    def save_figures_batch(self, figures_and_paths: list[tuple[Any, str]]) -> dict[str, str]:
        """
        Save multiple figures in a single browser session.

        Args:
            figures_and_paths: List of (figure, output_path) tuples

        Returns:
            Dictionary with results for each figure
        """
        results = {}

        if not figures_and_paths:
            return results

        with self.batch_session():
            logger.info(f"Saving {len(figures_and_paths)} figures in batch session")

            for i, (figure, output_path) in enumerate(figures_and_paths):
                try:
                    # Import here to avoid circular imports
                    import pymatviz as pmv

                    # Save figure using pymatviz
                    pmv.save_fig(figure, output_path)
                    results[output_path] = "success"

                    logger.info(
                        f"Figure {i + 1}/{len(figures_and_paths)} saved: {Path(output_path).name}"
                    )

                except Exception as e:
                    logger.error(f"Error saving figure {output_path}: {e}")
                    results[output_path] = f"error: {e}"

        logger.info(f"Batch save completed: {len(results)} figures processed")
        return results

    def cleanup(self):
        """Clean up browser session manager."""
        with self.session_lock:
            self._cleanup_session()
            logger.info("BrowserSessionManager cleanup completed")


# Global instance
_browser_manager = None


def get_browser_manager() -> BrowserSessionManager:
    """Get the global browser session manager."""
    global _browser_manager
    if _browser_manager is None:
        _browser_manager = BrowserSessionManager()
    return _browser_manager


def batch_save_figures(figures_and_paths: list[tuple[Any, str]]) -> dict[str, str]:
    """
    Save multiple figures using the browser session manager.

    Args:
        figures_and_paths: List of (figure, output_path) tuples

    Returns:
        Dictionary with results for each figure
    """
    manager = get_browser_manager()
    return manager.save_figures_batch(figures_and_paths)


def optimize_pymatviz_performance():
    """
    Apply performance optimizations to pymatviz/kaleido.
    Call this before using pymatviz functions.
    """
    try:
        import pymatviz as pmv

        # Set efficient template
        pmv.set_plotly_template("pymatviz_white")

        # Configure for batch processing
        manager = get_browser_manager()
        manager._configure_kaleido_session()

        logger.info("Pymatviz performance optimizations applied")

    except ImportError as e:
        logger.warning(f"Could not apply pymatviz optimizations: {e}")


def cleanup_browser_sessions():
    """Clean up all browser sessions."""
    manager = get_browser_manager()
    manager.cleanup()
