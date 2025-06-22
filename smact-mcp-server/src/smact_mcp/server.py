"""Main SMACT MCP Server implementation."""

import sys
import os
import asyncio
import logging
from pathlib import Path

# SMACT should be properly installed in the environment
# If running in development, ensure SMACT is in PYTHONPATH or installed via pip

from mcp.server.fastmcp import FastMCP

# Configure logging
logging.basicConfig(level=logging.INFO, stream=sys.stderr)
logger = logging.getLogger(__name__)

# Initialize FastMCP server
mcp = FastMCP("SMACT Materials Discovery Tools")

# Server metadata
SERVER_NAME = "smact-materials"
SERVER_VERSION = "0.1.0"

# Import tools (this registers them with the mcp server)
from . import tools

# Log that tools module was imported
logger.info(f"Tools module imported successfully")

def main():
    """Run the server."""
    try:
        logger.info(f"Starting {SERVER_NAME} v{SERVER_VERSION}")
        mcp.run(transport='stdio')
    except KeyboardInterrupt:
        logger.info("Server interrupted by user")
    except Exception as e:
        logger.error(f"Server error: {e}")
        raise

if __name__ == "__main__":
    main()