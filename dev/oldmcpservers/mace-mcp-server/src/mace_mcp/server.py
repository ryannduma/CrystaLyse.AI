"""MACE MCP Server - Production-ready energy calculations for materials discovery.

This server provides comprehensive MACE force field calculations including:
- Energy calculations with uncertainty quantification
- Structure relaxation with convergence monitoring
- Resource monitoring and adaptive batching
- Active learning target identification
- Robust descriptor extraction
"""

import logging
import sys
from pathlib import Path

# Configure logging to stderr (MCP standard)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stderr,
)

logger = logging.getLogger(__name__)

# Add the parent directory to Python path for potential local dependencies
MACE_PATH = Path(__file__).parent.parent.parent.parent.parent / "mace-main"
if MACE_PATH.exists():
    sys.path.insert(0, str(MACE_PATH))

try:
    from mcp.server.fastmcp import FastMCP
except ImportError as e:
    logger.error(f"Failed to import MCP: {e}")
    logger.error("Please install mcp: pip install mcp")
    sys.exit(1)

# Create the MCP server instance
mcp = FastMCP("MACE Materials Energy Calculator v0.1.0")

# Import tools (this registers them with the server via decorators)
try:
    from . import tools  # noqa: F401
    logger.info("MACE tools loaded successfully")
except ImportError as e:
    logger.error(f"Failed to import MACE tools: {e}")
    sys.exit(1)


def main():
    """Run the MACE MCP server."""
    try:
        logger.info("Starting MACE MCP Server v0.1.0")
        logger.info("Features: Energy calculations, uncertainty quantification, resource monitoring")
        
        # Check if MACE is available
        try:
            import torch
            logger.info(f"PyTorch version: {torch.__version__}")
            logger.info(f"CUDA available: {torch.cuda.is_available()}")
            if torch.cuda.is_available():
                logger.info(f"CUDA device count: {torch.cuda.device_count()}")
        except ImportError:
            logger.warning("PyTorch not available")
        
        # Run the server
        mcp.run(transport="stdio")
        
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Server error: {e}")
        raise


if __name__ == "__main__":
    main()