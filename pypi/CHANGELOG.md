# Changelog

All notable changes to CrystaLyse.AI will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2025-01-19

### Added
- Initial release of CrystaLyse.AI
- Complete computational materials design platform with AI agents
- Session-based architecture for persistent materials discovery
- Advanced memory systems for crystal structure and composition tracking
- Comprehensive documentation with user guides
- PyPI distribution ready with `pip install crystalyse-ai`
- Python 3.11+ requirement with automatic environment setup
- Bundled MCP servers for materials tools:
  - Creative Chemistry Server for novel crystal structure generation
  - Unified Chemistry Server for comprehensive materials analysis
  - Visualisation Server for crystal structure rendering and pymatviz analysis features like XRD
- Command-line interface with interactive mode
- Support for crystallographic file formats (CIF)
- Integration with SMACT, Chemeleon, MACE, and other materials tools
- Professional documentation structure
- Installation script with cross-platform support
- Extensive test suite and quality tools

### Core Features
- **Intelligent Materials Agents**: Purpose-built agents for crystal structure analysis and materials design
- **Session Management**: Persistent conversations and context tracking for materials projects
- **Memory Systems**: Discovery caching and cross-session learning for composition and structure exploration
- **Tool Integration**: Extensible materials science tool ecosystem (SMACT, Chemeleon, MACE)
- **Visualisation**: 3D crystal structure rendering and analysis plots
- **User Interface**: Rich command-line interface with themes
- **API Access**: Programmatic access to all functionality

### Technical Implementation
- Built on OpenAI Agents framework
- Modern Python packaging with pyproject.toml
- Type hints and comprehensive error handling
- British English throughout (analyse, visualise, etc.)
- Professional code quality with ruff, mypy, pytest
- MkDocs documentation with Material theme
- Cross-platform compatibility (Linux, macOS, Windows)

### Documentation
- Complete user guides and API reference
- Quickstart tutorial for new users
- Detailed installation instructions
- Concept explanations for agents, memory, sessions
- Materials science module documentation
- Developer guidelines and contribution guide

## [1.0.12] - 2025-07-20

### Fixed - Critical Fixes
- **Checkpoint Path Mismatch**: Fixed Chemeleon model checkpoints downloading to wrong location
  - Previous: Downloaded to `~/materialschat/ckpts/` but code expected `~/.crystalyse/checkpoints/`
  - Fixed: Robust downloader ensures checkpoints always go to `~/.crystalyse/checkpoints/`
  - Impact: Eliminates "Checkpoint not found" errors for pip users

- **Missing Visualisations**: Fixed 3Dmol.js and PyMatViz visualisations not being generated
  - Previous: Agent only connected to materials science servers, not visualisation server
  - Fixed: Added visualisation server to MCP connections for both creative and rigorous modes
  - Impact: Interactive 3D crystal structures and analysis plots now generate correctly

### Changed
- Chemeleon checkpoint downloader now uses direct HTTPS download with progress bars
- Agent MCP connections now include visualisation server by default
- Improved error handling for checkpoint download failures

## [1.0.11] - 2025-07-20

### Fixed
- Updated checkpoint paths to use portable user directories (`~/.crystalyse/checkpoints/`)
- Fixed hardcoded paths that prevented pip users from accessing downloaded checkpoints

## [1.0.10] - 2025-07-20

### Fixed
- Fixed deprecation warnings by migrating from deprecated `pkg_resources` to `importlib.metadata`
- Silenced noisy OpenAI agents SDK import warnings in production
- Fixed `get_checkpoint_path` function signature compatibility issues

## [1.0.9] - 2025-07-20

### Fixed
- Fixed incorrect package name detection in dependency checker
  - `openai_agents` → `openai-agents` (pip name vs import name)
  - `mace_torch` → `mace-torch` (pip name vs import name)
- Fixed converter import paths in MCP servers
  - Changed from `from converters import` to `from crystalyse_ai.converters import`
- Improved package import name mapping for accurate dependency detection

## [1.0.8] - 2025-07-20

### Added - Dependency Management System
- **Comprehensive Dependency Checker Tool** (`dependency_checker.py`)
  - Validates all Python packages (torch, mace-torch, smact, etc.)
  - Auto-installs Chemeleon from GitHub when needed
  - Downloads model checkpoints automatically (~500MB)
  - Tests MCP server availability
  - Rich, formatted status reports with detailed tables

- **CLI Integration for Dependency Checking**
  - Added `crystalyse check` command with options:
    - `--install`: Automatically install missing components
    - `--verbose`: Show detailed output
    - `--details`: Display comprehensive dependency information
  - Added `/check` command to unified CLI interface

- **Auto-Installation Features**
  - Chemeleon: Automatic GitHub clone and installation on first use
  - Checkpoints: Downloads 500MB+ model files when needed (without bloating package)
  - Smart detection and installation workflow

### Fixed
- Resolved logger definition order issue in `chemeleon.py` that was breaking MCP servers
- Fixed module import errors preventing proper materials science tool access

## [1.0.7] - 2025-07-19

### Fixed
- Fixed MCP server import issues by adding proper `main()` entry points
- Resolved `ImportError: cannot import name 'main'` for all MCP servers
- Added proper logging and tool availability reporting in server startup

## [1.0.6] - 2025-07-19

### Added - Major Materials Tools Integration
- **Complete Materials Science Toolchain Integration**
  - Copied all materials tools directly into package (`src/crystalyse_ai/tools/`)
    - `smact.py` - Composition validation and screening for inorganic materials
    - `chemeleon.py` - Crystal structure prediction and generation
    - `mace.py` - Formation energy calculations and materials property prediction
    - `visualization.py` - 3D crystal structure visualisation
    - `chemeleon_installer.py` - Auto-installer for non-PyPI dependencies
  - Removed dependency on external MCP servers
  - Real materials calculations instead of text-only responses

### Changed
- **MCP Server Architecture Overhaul**
  - Updated imports from external servers to local tools
  - Removed MCP decorators from tool functions
  - Made all materials science functions standard Python callables
  - Improved error handling and defensive imports

- **Dependency Management**
  - Added materials science dependencies to `pyproject.toml`:
    - `smact>=2.7.0`, `torch>=2.0.0`, `mace-torch>=0.3.4`
    - `fastmcp>=0.5.0`, `gitpython>=3.1.0`
  - Auto-installer for Chemeleon (crystal structure predictor not available on PyPI)
  - Solved package size issue (reduced from 548MB to 174KB)

### Fixed
- **Package Size Compliance**: Removed large checkpoint files, added auto-downloader
- **Import Safety**: Added defensive imports to prevent crashes when dependencies missing
- **PyPI Distribution**: Package now includes actual materials science tools for real computations

## [1.0.5] - 2025-07-19

### Fixed
- Added missing `main()` entry points to all MCP servers
- Fixed `ImportError: cannot import name 'main'` for materials science servers
- Improved server startup logging with tool availability reporting

## [1.0.4] - 2025-07-19

### Changed
- Updated CLI prompt text to be more encouraging and user-friendly
- Changed prompt from basic to "Ready when you are, design something great. Or use commands:"

## [1.0.3] - 2025-07-19

### Changed
- Restored "Research Preview" version display in CLI interface
- Updated ASCII art subtitle to show version information clearly

## [1.0.2] - 2025-07-19

### Fixed
- **MCP Server Configuration**: Updated config to use built-in server commands
  - Changed from external directory paths to packaged server commands
  - Fixed "MCP server directory not found" errors
  - Improved server discovery and initialization

## [1.0.1] - 2025-07-19

### Fixed
- **Import Error Resolution**: Added defensive imports in `__init__.py`
  - Fixed `ModuleNotFoundError: No module named 'pydantic'`
  - Added graceful degradation when optional dependencies missing
  - Improved package initialization robustness

## [Unreleased]

### Planned Features (Immediate)
- Enhanced crystal structure visualisation with improved reliability
- VESTA color scheme integration for consistent materials visualisation
- Extended materials tooling availability
- CLI enhancements for read/write ability
- Advanced quantum chemistry calculations for materials
- Machine learning model integration for materials discovery
- Cloud deployment templates
- Web interface for remote access
- Plugin system for custom materials tools
- Integration with additional crystallographic databases
- Batch processing improvements for high-throughput materials screening
- Real-time collaboration features for research teams

### Known Issues
- Visualisation suite needs dependency fixes
- Need for more transparent error handling
- Multi-candidate exploration and analysis needs timeout enhancements and reliability fixes
- API rate limits may affect bulk materials screening operations and model access.

---

For support and bug reports, please visit our [GitHub Issues](https://github.com/ryannduma/CrystaLyse.AI/issues).