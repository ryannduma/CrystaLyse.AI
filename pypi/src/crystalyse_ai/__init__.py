"""
CrystaLyse.AI - Advanced AI-powered chemistry analysis platform.

CrystaLyse.AI combines large language models with specialised chemistry tools to provide
intelligent molecular analysis, synthesis planning, and visualisation capabilities.
"""

__version__ = "1.0.5"
__author__ = "CrystaLyse.AI Development Team"
__email__ = "contact@crystalyse.ai"
__license__ = "MIT"

# Defensive imports - handle missing dependencies gracefully
try:
    from .agents import CrystaLyse, CrystaLyseSession, CrystaLyseSessionManager
    _AGENTS_AVAILABLE = True
except ImportError as e:
    CrystaLyse = None
    CrystaLyseSession = None
    CrystaLyseSessionManager = None
    _AGENTS_AVAILABLE = False

try:
    from .infrastructure import PersistentSessionManager, MCPConnectionPool
    _INFRASTRUCTURE_AVAILABLE = True
except ImportError as e:
    PersistentSessionManager = None
    MCPConnectionPool = None
    _INFRASTRUCTURE_AVAILABLE = False

try:
    from .memory import CrystaLyseMemory, DiscoveryCache
    _MEMORY_AVAILABLE = True
except ImportError as e:
    CrystaLyseMemory = None
    DiscoveryCache = None
    _MEMORY_AVAILABLE = False

try:
    from .cli import main as cli_main
    _CLI_AVAILABLE = True
except ImportError as e:
    cli_main = None
    _CLI_AVAILABLE = False

# Build __all__ dynamically based on what's available
__all__ = ["__version__", "__author__", "__email__", "__license__"]

if _AGENTS_AVAILABLE:
    __all__.extend(["CrystaLyse", "CrystaLyseSession", "CrystaLyseSessionManager"])

if _INFRASTRUCTURE_AVAILABLE:
    __all__.extend(["PersistentSessionManager", "MCPConnectionPool"])

if _MEMORY_AVAILABLE:
    __all__.extend(["CrystaLyseMemory", "DiscoveryCache"])

if _CLI_AVAILABLE:
    __all__.append("cli_main")