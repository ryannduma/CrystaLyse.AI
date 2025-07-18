"""Central configuration management for CrystaLyse.AI"""

import os
import shutil
from pathlib import Path
from typing import Dict, Any, Optional

class CrystaLyseConfig:
    """Central configuration management with environment variable support"""
    
    def __init__(self):
        self.base_dir = Path(__file__).parent.parent
        self.load_from_env()
    
    def load_from_env(self):
        """Load configuration from environment variables with sensible defaults"""
        
        # MCP Server Configurations
        self.mcp_servers = {
            "chemistry_unified": {
                "command": os.getenv("CHEMISTRY_MCP_COMMAND", "python"),
                "args": os.getenv("CHEMISTRY_MCP_ARGS", "-m chemistry_unified.server").split(),
                "cwd": os.getenv("CHEMISTRY_MCP_PATH", str(self.base_dir / "chemistry-unified-server" / "src"))
            },
            "chemistry_creative": {
                "command": os.getenv("CHEMISTRY_CREATIVE_MCP_COMMAND", "python"),
                "args": os.getenv("CHEMISTRY_CREATIVE_MCP_ARGS", "-m chemistry_creative.server").split(),
                "cwd": os.getenv("CHEMISTRY_CREATIVE_MCP_PATH", str(self.base_dir / "chemistry-creative-server" / "src"))
            },
            # Keep individual servers as fallback options
            "smact": {
                "command": os.getenv("SMACT_MCP_COMMAND", "python"),
                "args": os.getenv("SMACT_MCP_ARGS", "-m smact_mcp.server").split(),
                "cwd": os.getenv("SMACT_MCP_PATH", str(self.base_dir / "smact-mcp-server" / "src"))
            },
            "chemeleon": {
                "command": os.getenv("CHEMELEON_MCP_COMMAND", "python"),
                "args": os.getenv("CHEMELEON_MCP_ARGS", "-m chemeleon_mcp.server").split(),
                "cwd": os.getenv("CHEMELEON_MCP_PATH", str(self.base_dir / "chemeleon-mcp-server" / "src"))
            },
            "mace": {
                "command": os.getenv("MACE_MCP_COMMAND", "python"),
                "args": os.getenv("MACE_MCP_ARGS", "-m mace_mcp.server").split(),
                "cwd": os.getenv("MACE_MCP_PATH", str(self.base_dir / "mace-mcp-server" / "src"))
            },
            "visualization": {
                "command": os.getenv("VISUALIZATION_MCP_COMMAND", "python"),
                "args": os.getenv("VISUALIZATION_MCP_ARGS", "-m visualization_mcp.server").split(),
                "cwd": os.getenv("VISUALIZATION_MCP_PATH", str(self.base_dir / "visualization-mcp-server" / "src"))
            }
        }
        
        # Agent Configuration
        self.default_model = os.getenv("CRYSTALYSE_MODEL", "o4-mini")
        self.max_turns = int(os.getenv("CRYSTALYSE_MAX_TURNS", "1000"))
        
        # Performance Configuration
        self.parallel_batch_size = int(os.getenv("CRYSTALYSE_BATCH_SIZE", "10"))
        self.max_candidates = int(os.getenv("CRYSTALYSE_MAX_CANDIDATES", "100"))
        self.structure_samples = int(os.getenv("CRYSTALYSE_STRUCTURE_SAMPLES", "5"))
        
        # Development Configuration
        self.enable_metrics = os.getenv("CRYSTALYSE_METRICS", "true").lower() == "true"
        self.debug_mode = os.getenv("CRYSTALYSE_DEBUG", "false").lower() == "true"
        
    def get_server_config(self, server_name: str) -> Dict[str, Any]:
        """Get MCP server configuration with validation"""
        if server_name not in self.mcp_servers:
            raise ValueError(f"Unknown server: {server_name}. Available: {list(self.mcp_servers.keys())}")
            
        config = self.mcp_servers[server_name].copy()
        
        # Ensure the working directory exists
        cwd_path = Path(config["cwd"])
        if not cwd_path.exists():
            raise FileNotFoundError(f"MCP server directory not found: {cwd_path}")
            
        # Add environment variables
        config["env"] = os.environ.copy()
        if self.debug_mode:
            config["env"]["PYTHONPATH"] = str(self.base_dir)
            
        return config
        
    def validate_dependencies(self):
        """Perform validation of critical system dependencies."""
        if not shutil.which("python"):
            raise RuntimeError("Python interpreter not found in system PATH. CrystaLyse.AI requires Python.")
        
        try:
            import mcp
        except ImportError:
            raise RuntimeError("MCP package not found. Please install it with: pip install mcp")

    def validate_environment(self) -> Dict[str, Any]:
        """Validate that all required components are available"""
        status = {
            "servers": {},
            "dependencies": {},
            "overall": "healthy"
        }
        
        # Check for python executable
        if not shutil.which("python"):
            status["dependencies"]["python"] = False
            status["overall"] = "unhealthy"
        else:
            status["dependencies"]["python"] = True

        # Check server directories
        for server_name, server_config in self.mcp_servers.items():
            cwd_path = Path(server_config["cwd"])
            status["servers"][server_name] = {
                "directory_exists": cwd_path.exists(),
                "command": server_config["command"],
                "available": False
            }
            
            # TODO: Could add actual connectivity test here
            
        # Check Python dependencies
        try:
            import agents
            status["dependencies"]["openai_agents"] = True
        except ImportError:
            status["dependencies"]["openai_agents"] = False
            status["overall"] = "degraded"
            
        try:
            import mcp
            status["dependencies"]["mcp"] = True
        except ImportError:
            status["dependencies"]["mcp"] = False
            status["overall"] = "degraded"
            
        return status

# Global configuration instance
config = CrystaLyseConfig()
# Optional dependency validation (may fail in some environments)
try:
    config.validate_dependencies()
except RuntimeError as e:
    import warnings
    warnings.warn(f"Some dependencies not available: {e}")

# Backward compatibility functions
def get_agent_config():
    """Backward compatibility for old agent config function"""
    return {
        "model": config.default_model,
        "max_turns": config.max_turns
    }

DEFAULT_MODEL = config.default_model