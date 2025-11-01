"""
Provenance Bridge for CrystaLyse.AI

Integrates the standalone provenance_system module with CrystaLyse's core architecture.
This bridge extends ProvenanceTraceHandler with CrystaLyse-specific functionality whilst
maintaining compatibility with the existing trace handler interface.

Design:
- Provenance capture is always enabled (core feature)
- Users can customise display and storage location
- Graceful degradation if provenance writes fail
- Compatible with existing ToolTraceHandler interface
"""

import logging
from pathlib import Path
from typing import Optional
from datetime import datetime

from rich.console import Console

# Import from internal provenance system
try:
    from ..provenance.handlers import ProvenanceTraceHandler
    PROVENANCE_AVAILABLE = True
except ImportError as e:
    PROVENANCE_AVAILABLE = False
    logging.warning(f"Provenance system handlers not available: {e}")
    # Fallback to base trace handler if provenance unavailable
    from .trace_handler import ToolTraceHandler
    ProvenanceTraceHandler = ToolTraceHandler

logger = logging.getLogger(__name__)


class CrystaLyseProvenanceHandler(ProvenanceTraceHandler):
    """
    CrystaLyse-specific provenance handler.

    Extends ProvenanceTraceHandler with CrystaLyse configuration integration
    and provides convenient access methods for provenance data.

    Key Features:
    - Automatic session ID generation with mode prefix
    - Configuration-driven behaviour
    - Graceful error handling
    - Easy access to provenance files

    Usage:
        handler = CrystaLyseProvenanceHandler(
            config=config,
            mode="creative",
            console=console
        )

        result = await agent.discover(query, trace_handler=handler)
        summary = handler.finalize()
    """

    def __init__(
        self,
        console: Optional[Console] = None,
        config: Optional['CrystaLyseConfig'] = None,
        mode: str = "adaptive",
        session_id: Optional[str] = None,
        **kwargs
    ):
        """
        Initialise provenance handler with CrystaLyse configuration.

        Args:
            console: Rich console for visual output
            config: CrystaLyse configuration object (auto-loaded if None)
            mode: Discovery mode (creative/adaptive/rigorous)
            session_id: Override automatic session ID generation
            **kwargs: Additional arguments passed to ProvenanceTraceHandler
        """
        # Load configuration if not provided
        if config is None:
            from ..config import Config
            config = Config.load()

        self.config = config
        self.mode = mode

        # Generate session ID with mode prefix if not provided
        if session_id is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            session_id = f"{config.provenance['session_prefix']}_{mode}_{timestamp}"

        self.session_id = session_id

        # Initialise parent with configuration settings
        # Provenance is ALWAYS enabled - this is a core feature
        try:
            super().__init__(
                console=console or Console(),
                output_dir=config.provenance['output_dir'],
                session_id=session_id,
                enable_provenance=True,  # Always enabled
                enable_visual=config.provenance['visual_trace'],
                capture_mcp_logs=config.provenance['capture_mcp_logs'],
                save_raw_outputs=config.provenance['capture_raw'],
                **kwargs
            )
            logger.info(f"Provenance handler initialised: {session_id}")
        except Exception as e:
            logger.error(f"Failed to initialise provenance handler: {e}")
            # If provenance fails to initialise, still allow discovery to proceed
            # Re-raise only if it's a critical error
            if not PROVENANCE_AVAILABLE:
                logger.warning("Provenance system unavailable - discovery will proceed without provenance")
            else:
                raise

    def get_summary_path(self) -> Path:
        """
        Get path to the summary JSON file.

        Returns:
            Path to summary.json
        """
        if hasattr(self, 'output_dir') and self.output_dir:
            return self.output_dir / "summary.json"
        return None

    def get_materials_catalogue_path(self) -> Path:
        """
        Get path to the materials catalogue JSON file.

        Returns:
            Path to materials_catalog.json
        """
        if hasattr(self, 'output_dir') and self.output_dir:
            return self.output_dir / "materials_catalog.json"
        return None

    def get_events_path(self) -> Path:
        """
        Get path to the events JSONL file.

        Returns:
            Path to events.jsonl
        """
        if hasattr(self, 'output_dir') and self.output_dir:
            return self.output_dir / "events.jsonl"
        return None

    def get_session_info(self) -> dict:
        """
        Get session information.

        Returns:
            Dictionary with session metadata
        """
        return {
            "session_id": self.session_id,
            "mode": self.mode,
            "output_dir": str(self.output_dir) if hasattr(self, 'output_dir') else None,
            "summary_file": str(self.get_summary_path()) if self.get_summary_path() else None,
            "materials_file": str(self.get_materials_catalogue_path()) if self.get_materials_catalogue_path() else None,
            "events_file": str(self.get_events_path()) if self.get_events_path() else None
        }

    def finalize(self) -> dict:
        """
        Finalise provenance capture and return summary.

        Overrides parent method to add graceful error handling.

        Returns:
            Summary dictionary with provenance statistics
        """
        try:
            summary = super().finalize()

            # Add CrystaLyse-specific metadata
            if summary:
                summary['mode'] = self.mode
                summary['session_info'] = self.get_session_info()
                # Add output_dir at top level for easier access
                if hasattr(self, 'output_dir') and self.output_dir:
                    summary['output_dir'] = str(self.output_dir)

            logger.info(f"Provenance finalised: {self.session_id}")
            return summary
        except Exception as e:
            logger.error(f"Error finalising provenance: {e}")
            # Return minimal summary on error
            return {
                "session_id": self.session_id,
                "mode": self.mode,
                "error": str(e)
            }


def create_provenance_handler(
    mode: str = "adaptive",
    config: Optional['CrystaLyseConfig'] = None,
    console: Optional[Console] = None,
    session_id: Optional[str] = None
) -> CrystaLyseProvenanceHandler:
    """
    Factory function to create a provenance handler with sensible defaults.

    Args:
        mode: Discovery mode
        config: CrystaLyse configuration (auto-loaded if None)
        console: Rich console (created if None)
        session_id: Override automatic session ID

    Returns:
        Configured CrystaLyseProvenanceHandler instance
    """
    if config is None:
        from ..config import Config
        config = Config.load()

    if console is None:
        console = Console()

    return CrystaLyseProvenanceHandler(
        console=console,
        config=config,
        mode=mode,
        session_id=session_id
    )


# Export main class and factory
__all__ = [
    'CrystaLyseProvenanceHandler',
    'create_provenance_handler',
    'PROVENANCE_AVAILABLE'
]
