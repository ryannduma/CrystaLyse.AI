"""
MCP Connection Pool for CrystaLyse.AI
Maintains persistent connections to MCP servers to prevent connection failures.
"""
import asyncio
import logging
import time
from typing import Dict, Optional, Any
from contextlib import AsyncExitStack
# Fix circular import by using absolute import
try:
    import sys
    import os
    
    # Temporarily remove the local crystalyse directory from sys.path
    current_dir = os.path.dirname(os.path.abspath(__file__))
    crystalyse_parent = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(current_dir))))
    
    # Store original sys.path and remove conflicting paths
    original_paths = sys.path[:]
    paths_to_remove = [p for p in sys.path if 'crystalyse' in p.lower()]
    for path in paths_to_remove:
        if path in sys.path:
            sys.path.remove(path)
    
    # Add the OpenAI agents SDK path explicitly
    openai_agents_path = os.path.join(crystalyse_parent, 'openai-agents-python', 'src')
    if os.path.exists(openai_agents_path) and openai_agents_path not in sys.path:
        sys.path.insert(0, openai_agents_path)
    
    from agents.mcp.server import MCPServerStdio
    
    # Restore original sys.path
    sys.path = original_paths
    
except ImportError as e:
    # Provide placeholder implementation
    print(f"⚠️  Warning: MCPServerStdio not available: {e}")
    
    class MCPServerStdio:
        def __init__(self, *args, **kwargs):
            pass
        
        async def connect(self):
            pass
        
        async def cleanup(self):
            pass

logger = logging.getLogger(__name__)

class MCPConnectionPool:
    """Manage persistent connections to MCP servers with health checking and auto-reconnection."""
    
    def __init__(self, health_check_interval: int = 30, max_reconnect_attempts: int = 3):
        self.connections: Dict[str, MCPServerStdio] = {}
        self.connection_configs: Dict[str, Dict[str, Any]] = {}
        self.last_health_check: Dict[str, float] = {}
        self.health_check_interval = health_check_interval
        self.max_reconnect_attempts = max_reconnect_attempts
        self.exit_stack = AsyncExitStack()
        self._lock = asyncio.Lock()
        
    async def register_server(self, name: str, config: Dict[str, Any]) -> None:
        """Register a server configuration for connection management."""
        self.connection_configs[name] = config
        logger.info(f"Registered MCP server configuration: {name}")
        
    async def get_connection(self, server_name: str) -> Optional[MCPServerStdio]:
        """Get a healthy connection to the specified server, creating if necessary."""
        async with self._lock:
            # Check if we have a healthy connection
            if await self._is_connection_healthy(server_name):
                return self.connections[server_name]
            
            # Need to establish or re-establish connection
            return await self._establish_connection(server_name)
    
    async def _is_connection_healthy(self, server_name: str) -> bool:
        """Check if the connection is healthy and recently verified."""
        if server_name not in self.connections:
            return False
            
        # Check if we've verified health recently
        last_check = self.last_health_check.get(server_name, 0)
        if time.time() - last_check < self.health_check_interval:
            return True
            
        # Perform health check
        try:
            connection = self.connections[server_name]
            # Try to list tools as a health check
            await asyncio.wait_for(connection.list_tools(), timeout=10)
            self.last_health_check[server_name] = time.time()
            logger.debug(f"Health check passed for {server_name}")
            return True
        except Exception as e:
            logger.warning(f"Health check failed for {server_name}: {e}")
            return False
    
    async def _establish_connection(self, server_name: str) -> Optional[MCPServerStdio]:
        """Establish a new connection with retry logic."""
        if server_name not in self.connection_configs:
            logger.error(f"No configuration found for server: {server_name}")
            return None
            
        config = self.connection_configs[server_name]
        
        for attempt in range(self.max_reconnect_attempts):
            try:
                logger.info(f"Establishing connection to {server_name} (attempt {attempt + 1})")
                
                # Create new connection with 5-minute timeout
                connection = await self.exit_stack.enter_async_context(
                    MCPServerStdio(
                        name=server_name,
                        params={
                            "command": config["command"],
                            "args": config["args"],
                            "cwd": config["cwd"],
                            "env": config.get("env", {})
                        },
                        client_session_timeout_seconds=300  # 5 minutes for complex operations
                    )
                )
                
                # Test the connection
                await asyncio.wait_for(connection.list_tools(), timeout=30)
                
                # Store successful connection
                self.connections[server_name] = connection
                self.last_health_check[server_name] = time.time()
                
                logger.info(f"✅ Successfully connected to {server_name}")
                return connection
                
            except Exception as e:
                logger.warning(f"Connection attempt {attempt + 1} failed for {server_name}: {e}")
                
                if attempt < self.max_reconnect_attempts - 1:
                    # Exponential backoff with jitter
                    wait_time = (2 ** attempt) + (asyncio.get_event_loop().time() % 1)
                    logger.info(f"Retrying connection to {server_name} in {wait_time:.1f}s...")
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"❌ Failed to establish connection to {server_name} after {self.max_reconnect_attempts} attempts")
        
        return None
    
    async def close_connection(self, server_name: str) -> None:
        """Close a specific connection."""
        if server_name in self.connections:
            try:
                # The exit_stack will handle cleanup
                del self.connections[server_name]
                if server_name in self.last_health_check:
                    del self.last_health_check[server_name]
                logger.info(f"Closed connection to {server_name}")
            except Exception as e:
                logger.error(f"Error closing connection to {server_name}: {e}")
    
    async def close_all_connections(self) -> None:
        """Close all connections and cleanup resources."""
        logger.info("Closing all MCP connections...")
        try:
            await self.exit_stack.aclose()
            self.connections.clear()
            self.last_health_check.clear()
            logger.info("✅ All MCP connections closed")
        except Exception as e:
            logger.error(f"Error closing MCP connections: {e}")
    
    def get_connection_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all registered connections."""
        status = {}
        for server_name in self.connection_configs:
            last_check = self.last_health_check.get(server_name, 0)
            status[server_name] = {
                "connected": server_name in self.connections,
                "last_health_check": last_check,
                "health_check_age": time.time() - last_check if last_check > 0 else float('inf'),
                "needs_health_check": (time.time() - last_check) > self.health_check_interval
            }
        return status

# Global connection pool instance
_connection_pool: Optional[MCPConnectionPool] = None

def get_connection_pool() -> MCPConnectionPool:
    """Get the global connection pool instance."""
    global _connection_pool
    if _connection_pool is None:
        _connection_pool = MCPConnectionPool()
    return _connection_pool

async def cleanup_connection_pool() -> None:
    """Cleanup the global connection pool."""
    global _connection_pool
    if _connection_pool is not None:
        await _connection_pool.close_all_connections()
        _connection_pool = None