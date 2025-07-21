"""
Utility functions for robust MCP server connections with retry logic and error handling.
"""

import asyncio
import logging
import subprocess
import sys
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta

from agents.mcp import MCPServerStdio

logger = logging.getLogger(__name__)


class MCPConnectionError(Exception):
    """Raised when MCP server connection fails after all retries."""
    pass


class RobustMCPServer:
    """
    A wrapper around MCPServerStdio that provides:
    - Automatic retry logic with exponential backoff
    - Server health checking before connection
    - Better error messages and logging
    - Connection validation
    """
    
    def __init__(
        self,
        name: str,
        command: str,
        args: List[str],
        cwd: str,
        timeout_seconds: int = 30,
        max_retries: int = 3,
        initial_retry_delay: float = 1.0,
        health_check_timeout: float = 5.0
    ):
        self.name = name
        self.command = command
        self.args = args
        self.cwd = Path(cwd)
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self.initial_retry_delay = initial_retry_delay
        self.health_check_timeout = health_check_timeout
        self.server = None
        
    async def __aenter__(self):
        """Async context manager entry with robust connection handling."""
        for attempt in range(self.max_retries):
            try:
                logger.info(f"Attempting to connect to {self.name} (attempt {attempt + 1}/{self.max_retries})")
                
                # First verify the server directory exists
                if not self.cwd.exists():
                    raise MCPConnectionError(f"MCP server directory not found: {self.cwd}")
                
                # Check if the module can be imported
                if not await self._check_server_health():
                    raise MCPConnectionError(f"MCP server health check failed for {self.name}")
                
                # Create the MCP server
                self.server = MCPServerStdio(
                    name=self.name,
                    params={
                        "command": self.command,
                        "args": self.args,
                        "cwd": str(self.cwd)
                    },
                    cache_tools_list=False,
                    client_session_timeout_seconds=self.timeout_seconds
                )
                
                # Try to start the server
                await self.server.__aenter__()
                
                # Validate the connection
                if await self._validate_connection():
                    logger.info(f"Successfully connected to {self.name}")
                    return self.server
                else:
                    raise MCPConnectionError(f"Connection validation failed for {self.name}")
                    
            except Exception as e:
                logger.warning(f"Failed to connect to {self.name}: {str(e)}")
                
                # Clean up if server was partially initialized
                if self.server:
                    try:
                        await self.server.__aexit__(None, None, None)
                    except:
                        pass
                    self.server = None
                
                # If this was our last attempt, raise the error
                if attempt == self.max_retries - 1:
                    raise MCPConnectionError(
                        f"Failed to connect to {self.name} after {self.max_retries} attempts. "
                        f"Last error: {str(e)}"
                    )
                
                # Wait before retrying with exponential backoff
                retry_delay = self.initial_retry_delay * (2 ** attempt)
                logger.info(f"Retrying in {retry_delay} seconds...")
                await asyncio.sleep(retry_delay)
        
        raise MCPConnectionError(f"Unexpected error: exhausted retries for {self.name}")
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.server:
            return await self.server.__aexit__(exc_type, exc_val, exc_tb)
    
    async def _check_server_health(self) -> bool:
        """
        Check if the MCP server can be started by verifying the module exists.
        """
        try:
            # Try to run a quick health check command
            module_name = self.args[1] if self.args[0] == "-m" else None
            if not module_name:
                return True  # Can't verify, assume it's okay
            
            # Run a quick import check
            proc = await asyncio.create_subprocess_exec(
                self.command,
                "-c",
                f"import {module_name}",
                cwd=str(self.cwd),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            try:
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(),
                    timeout=self.health_check_timeout
                )
                
                if proc.returncode == 0:
                    logger.debug(f"Health check passed for {self.name}")
                    return True
                else:
                    logger.error(f"Health check failed for {self.name}: {stderr.decode()}")
                    return False
                    
            except asyncio.TimeoutError:
                logger.error(f"Health check timed out for {self.name}")
                if proc.returncode is None:
                    proc.kill()
                    await proc.wait()
                return False
                
        except Exception as e:
            logger.error(f"Health check error for {self.name}: {str(e)}")
            return False
    
    async def _validate_connection(self) -> bool:
        """
        Validate that the MCP server connection is working.
        """
        try:
            # The server should be connected at this point
            # We can check if it has tools available
            if hasattr(self.server, 'mcp') and self.server.mcp:
                return True
            else:
                logger.warning(f"MCP server {self.name} appears to be connected but has no mcp attribute")
                return True  # Still consider it valid if the server started
                
        except Exception as e:
            logger.error(f"Connection validation error for {self.name}: {str(e)}")
            return False


async def create_mcp_servers(
    servers_config: Dict[str, Dict[str, Any]],
    max_parallel_connections: int = 3
) -> List[RobustMCPServer]:
    """
    Create multiple MCP servers with controlled parallelism.
    
    Args:
        servers_config: Dictionary mapping server names to their configurations
        max_parallel_connections: Maximum number of servers to connect simultaneously
        
    Returns:
        List of connected MCP servers
        
    Example:
        servers_config = {
            "SMACT": {
                "command": "python",
                "args": ["-m", "smact_mcp"],
                "cwd": "/path/to/smact-mcp-server",
                "timeout_seconds": 10
            },
            "MACE": {
                "command": "python", 
                "args": ["-m", "mace_mcp"],
                "cwd": "/path/to/mace-mcp-server",
                "timeout_seconds": 60
            }
        }
        servers = await create_mcp_servers(servers_config)
    """
    connected_servers = []
    
    # Create server instances
    servers = []
    for name, config in servers_config.items():
        server = RobustMCPServer(
            name=name,
            command=config.get("command", "python"),
            args=config.get("args", []),
            cwd=config["cwd"],
            timeout_seconds=config.get("timeout_seconds", 30),
            max_retries=config.get("max_retries", 3),
            initial_retry_delay=config.get("initial_retry_delay", 1.0),
            health_check_timeout=config.get("health_check_timeout", 5.0)
        )
        servers.append(server)
    
    # Connect with controlled parallelism
    for i in range(0, len(servers), max_parallel_connections):
        batch = servers[i:i + max_parallel_connections]
        
        # Try to connect servers in this batch
        tasks = [server.__aenter__() for server in batch]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Check results and add successful connections
        for server, result in zip(batch, results):
            if isinstance(result, Exception):
                logger.error(f"Failed to connect to {server.name}: {result}")
                # Don't add to connected_servers
            else:
                connected_servers.append(server)
    
    if not connected_servers:
        raise MCPConnectionError("Failed to connect to any MCP servers")
    
    logger.info(f"Successfully connected to {len(connected_servers)} out of {len(servers)} MCP servers")
    return connected_servers


def log_mcp_status(servers: List[RobustMCPServer]):
    """Log the status of all MCP servers."""
    logger.info("=== MCP Server Status ===")
    for server in servers:
        status = "Connected" if server.server else "Disconnected"
        logger.info(f"  {server.name}: {status}")
    logger.info("========================")