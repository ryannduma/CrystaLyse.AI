"""Central configuration management for CrystaLyse.AI"""

import os
import shutil
import sys
from pathlib import Path
from typing import Dict, Any

class CrystaLyseConfig:
    """Central configuration management with environment variable support"""
    
    def __init__(self):
        self.base_dir = Path(__file__).parent.parent
        self.load_from_env()
    
    @classmethod
    def load(cls):
        """Load configuration - class method for consistent interface"""
        return cls()
    
    def load_from_env(self):
        """Load configuration from environment variables with sensible defaults"""
        
        # MCP Server Configurations
        self.mcp_servers = {
            "chemistry_unified": {
                "command": os.getenv("CRYSTALYSE_PYTHON_PATH", sys.executable),
                "args": ["-m", "chemistry_unified.server"],
                "cwd": str(self.base_dir / "chemistry-unified-server" / "src")
            },
            "chemistry_creative": {
                "command": sys.executable,
                "args": ["-m", "chemistry_creative.server"],
                "cwd": str(self.base_dir / "chemistry-creative-server" / "src")
            },
            "visualization": {
                "command": sys.executable,
                "args": ["-m", "visualization_mcp.server"],
                "cwd": str(self.base_dir / "visualization-mcp-server" / "src")
            }
        }
        
        # Agent Configuration
        self.default_model = os.getenv("CRYSTALYSE_MODEL", "o4-mini")
        self.max_turns = int(os.getenv("CRYSTALYSE_MAX_TURNS", "1000"))
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        
        # Mode-specific timeouts
        self.mode_timeouts = {
            "creative": 120,    # 2 minutes for fast exploration
            "adaptive": 180,    # 3 minutes for balanced approach  
            "rigorous": 300     # 5 minutes for comprehensive validation
        }
        
        # Performance Configuration
        self.parallel_batch_size = int(os.getenv("CRYSTALYSE_BATCH_SIZE", "10"))
        self.max_candidates = int(os.getenv("CRYSTALYSE_MAX_CANDIDATES", "100"))
        self.structure_samples = int(os.getenv("CRYSTALYSE_STRUCTURE_SAMPLES", "5"))
        
        # Development Configuration
        self.enable_metrics = os.getenv("CRYSTALYSE_METRICS", "true").lower() == "true"
        self.debug_mode = os.getenv("CRYSTALYSE_DEBUG", "false").lower() == "true"
        
        # Visualization preferences - Default to CIF-only for simplicity
        self.visualization = {
            "enable_html": os.getenv("CRYSTALYSE_ENABLE_HTML_VIZ", "false").lower() == "true",
            "cif_only": os.getenv("CRYSTALYSE_CIF_ONLY", "true").lower() == "true",
            "default_color_scheme": os.getenv("CRYSTALYSE_COLOR_SCHEME", "vesta")
        }
        
    def get_server_config(self, server_name: str) -> Dict[str, Any]:
        """Get MCP server configuration with validation"""
        if server_name not in self.mcp_servers:
            raise ValueError(f"Unknown server: {server_name}. Available: {list(self.mcp_servers.keys())}")
            
        config = self.mcp_servers[server_name].copy()
        
        # Ensure the working directory exists
        cwd_path = Path(config["cwd"])
        if not cwd_path.exists():
            raise FileNotFoundError(f"MCP server directory not found: {cwd_path}")
            
        # Validate Python executable exists
        python_cmd = config["command"]
        if not shutil.which(python_cmd):
            raise FileNotFoundError(f"Python executable not found: {python_cmd}. Set CRYSTALYSE_PYTHON_PATH environment variable if using a specific conda environment.")
            
        # Add environment variables
        config["env"] = os.environ.copy()
        
        # Construct the PYTHONPATH
        python_path = [str(self.base_dir)]
        chemeleon_dng_path = "/home/ryan/mycrystalyse/CrystaLyse.AI/chemeleon-dng"
        if chemeleon_dng_path not in python_path:
            python_path.append(chemeleon_dng_path)
        
        existing_python_path = config["env"].get("PYTHONPATH")
        if existing_python_path:
            python_path.append(existing_python_path)
            
        config["env"]["PYTHONPATH"] = os.pathsep.join(python_path)

        if self.debug_mode:
            config["env"]["CRYSTALYSE_DEBUG"] = "true"
            
        return config
        
    def validate_dependencies(self):
        """Perform validation of critical system dependencies."""
        if not shutil.which("python"):
            raise RuntimeError("Python interpreter not found in system PATH. CrystaLyse.AI requires Python.")
        
        import importlib.util
        if importlib.util.find_spec("agents") is None:
            raise RuntimeError("OpenAI Agents package not found. Please install it with: pip install openai-agents")

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
            
            # Validate Python executable exists
            python_cmd = server_config["command"]
            if not shutil.which(python_cmd):
                status["servers"][server_name]["available"] = False
                if status["overall"] == "healthy":
                    status["overall"] = "degraded"
            else:
                status["servers"][server_name]["available"] = True
            
        # Check Python dependencies
        import importlib.util
        if importlib.util.find_spec("agents") is not None:
            status["dependencies"]["openai_agents"] = True
        else:
            status["dependencies"]["openai_agents"] = False
            status["overall"] = "degraded"
            
        if importlib.util.find_spec("mcp") is not None:
            status["dependencies"]["mcp"] = True
        else:
            status["dependencies"]["mcp"] = False
            status["overall"] = "degraded"
            
        return status

# Global configuration instance
config = CrystaLyseConfig()

# Alias for clean import
Config = CrystaLyseConfig

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