"""Central configuration management for Crystalyse V2.

This is a simplified configuration module for the skills-based architecture.
MCP server configuration has been removed in favor of direct tool imports.
"""

import os
from pathlib import Path
from typing import Any

# Model configuration - two modes only
CREATIVE_MODEL = "o4-mini"
RIGOROUS_MODEL = "o3"


class CrystaLyseConfig:
    """Central configuration management with environment variable support."""

    def __init__(self):
        self.base_dir = Path(__file__).parent
        self.load_from_env()

    @classmethod
    def load(cls):
        """Load configuration - class method for consistent interface."""
        return cls()

    def load_from_env(self):
        """Load configuration from environment variables with sensible defaults."""

        # API Configuration
        self.openai_api_key = os.getenv("OPENAI_MDG_API_KEY") or os.getenv("OPENAI_API_KEY")

        # Performance Configuration
        self.parallel_batch_size = int(os.getenv("CRYSTALYSE_BATCH_SIZE", "10"))
        self.max_candidates = int(os.getenv("CRYSTALYSE_MAX_CANDIDATES", "100"))
        self.structure_samples = int(os.getenv("CRYSTALYSE_STRUCTURE_SAMPLES", "5"))

        # Development Configuration
        self.enable_metrics = os.getenv("CRYSTALYSE_METRICS", "true").lower() == "true"
        self.debug_mode = os.getenv("CRYSTALYSE_DEBUG", "false").lower() == "true"

        # Visualisation preferences - Default to CIF-only for simplicity
        self.visualization = {
            "enable_html": os.getenv("CRYSTALYSE_ENABLE_HTML_VIZ", "false").lower() == "true",
            "cif_only": os.getenv("CRYSTALYSE_CIF_ONLY", "true").lower() == "true",
            "default_color_scheme": os.getenv("CRYSTALYSE_COLOR_SCHEME", "vesta"),
        }

        # Provenance Configuration (ALWAYS ENABLED)
        # Provenance is a core feature of CrystaLyse - always captures complete audit trails
        self.provenance = {
            "output_dir": Path(os.getenv("CRYSTALYSE_PROVENANCE_DIR", "./provenance_output")),
            "capture_raw": os.getenv("CRYSTALYSE_CAPTURE_RAW", "true").lower() == "true",
            "session_prefix": os.getenv("CRYSTALYSE_SESSION_PREFIX", "crystalyse"),
            "show_summary": os.getenv("CRYSTALYSE_SHOW_PROVENANCE_SUMMARY", "true").lower()
            == "true",
        }

        # Render Gate Configuration (Intelligent hallucination prevention)
        self.render_gate = {
            "enabled": os.getenv("CRYSTALYSE_RENDER_GATE", "true").lower() == "true",
            "strictness": os.getenv(
                "CRYSTALYSE_RENDER_GATE_STRICTNESS", "intelligent"
            ),  # strict/intelligent/permissive
            "log_violations": os.getenv("CRYSTALYSE_RENDER_GATE_LOG", "true").lower() == "true",
            "block_unprovenanced": os.getenv("CRYSTALYSE_BLOCK_UNPROVENANCED", "true").lower()
            == "true",
        }

        # Skills Configuration
        self.skills = {
            "script_timeout": int(os.getenv("CRYSTALYSE_SKILL_TIMEOUT", "300")),
            "enable_sandboxing": os.getenv("CRYSTALYSE_SKILL_SANDBOX", "true").lower() == "true",
        }

    def get_model(self, rigorous: bool = False) -> str:
        """Get the appropriate model based on mode.

        Args:
            rigorous: If True, return the rigorous model. Otherwise creative.

        Returns:
            Model name string.
        """
        return RIGOROUS_MODEL if rigorous else CREATIVE_MODEL

    def validate_environment(self) -> dict[str, Any]:
        """Validate that all required components are available."""
        status = {"dependencies": {}, "skills": {}, "overall": "healthy"}

        # Check Python dependencies
        import importlib.util

        if importlib.util.find_spec("agents") is not None:
            status["dependencies"]["openai_agents"] = True
        else:
            status["dependencies"]["openai_agents"] = False
            status["overall"] = "degraded"

        # Check for skills directory
        skills_dir = self.base_dir.parent / "skills"
        if skills_dir.exists():
            skill_count = len(list(skills_dir.glob("*/SKILL.md")))
            status["skills"]["directory"] = str(skills_dir)
            status["skills"]["count"] = skill_count
        else:
            status["skills"]["directory"] = None
            status["skills"]["count"] = 0

        # Check API key
        if self.openai_api_key:
            status["dependencies"]["api_key"] = True
        else:
            status["dependencies"]["api_key"] = False
            status["overall"] = "degraded"

        return status


# Global configuration instance
config = CrystaLyseConfig()

# Alias for clean import
Config = CrystaLyseConfig

# Optional dependency validation (may fail in some environments)
try:
    import importlib.util

    if importlib.util.find_spec("agents") is None:
        import warnings

        warnings.warn(
            "OpenAI Agents SDK not available. Install with: pip install openai-agents",
            stacklevel=2,
        )
except Exception:
    pass


# Backward compatibility functions
def get_agent_config():
    """Backward compatibility for old agent config function."""
    return {
        "creative_model": CREATIVE_MODEL,
        "rigorous_model": RIGOROUS_MODEL,
    }


DEFAULT_MODEL = CREATIVE_MODEL
