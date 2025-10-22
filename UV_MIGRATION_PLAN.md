# UV Workspace Migration Guide - Crystalyse v1.0

**Project:** Crystalyse (formerly CrystaLyse.AI)
**Target Version:** v1.0.0
**Guide Purpose:** Migrate from legacy pip/conda setup to modern UV workspace
**Audience:** Developers, contributors, and maintainers

---

## 🎯 Executive Summary

This guide documents the complete migration from the legacy Crystalyse architecture (pip/conda-based) to a modern UV workspace with src layout. The migration introduces significant performance improvements, better dependency management, and a more maintainable project structure.

### What This Migration Achieves

- **10-100x faster** dependency resolution (UV vs pip/conda)
- **Universal lockfiles** that work across Linux/macOS/Windows
- **Modern src layout** per Python Packaging Authority (PyPA) recommendations
- **Unified workspace** for core package and MCP servers
- **Standardized Python 3.11+** across all components
- **Production-ready infrastructure** for v1.0 release

### Breaking Changes Summary

| Aspect | Old (master) | New (v1.0) |
|--------|--------------|------------|
| **Package Manager** | pip/conda | UV (pure) |
| **Python Version** | 3.9+ | 3.11+ |
| **Project Layout** | Flat layout | src layout |
| **MCP Servers** | Individual `-server` dirs | Unified `servers/` directory |
| **Branding** | "CrystaLyse.AI 2.0-alpha" | "Crystalyse v1.0" |
| **CLI Usage** | Global `crystalyse` | `uv run python -m crystalyse.cli` |

---

## 📋 Prerequisites

### Before You Start

1. **Backup your environment:**
   ```bash
   git checkout -b backup-pre-uv-migration
   git push -u origin backup-pre-uv-migration
   ```

2. **Install UV:**
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

3. **Verify UV installation:**
   ```bash
   uv --version  # Should show 0.7.2 or later
   ```

4. **Clean up old environments:**
   ```bash
   # If using conda
   conda deactivate

   # Remove old virtual environments (optional)
   rm -rf .venv venv
   ```

---

## 🏗️ Target Architecture

### New Directory Structure

```
dev/
├── pyproject.toml              # Workspace root (NEW)
├── uv.lock                     # Universal lockfile (NEW)
├── .python-version             # Python 3.11 pin (NEW)
├── .venv/                      # Shared virtual environment (NEW)
├── README.md                   # User guide (NEW)
│
├── crystalyse/                 # Core package (workspace member)
│   ├── pyproject.toml          # Package config (NEW)
│   └── src/                    # src layout (NEW)
│       └── crystalyse/         # Package code moved here
│           ├── __init__.py
│           ├── cli.py
│           ├── agents/
│           ├── tools/
│           ├── ui/
│           ├── provenance/
│           └── ...
│
└── servers/                    # MCP servers (NEW structure)
    ├── chemistry-creative/
    │   ├── pyproject.toml
    │   └── src/
    │       └── chemistry_creative/
    │           ├── __init__.py
    │           └── server.py
    │
    ├── chemistry-unified/
    │   ├── pyproject.toml
    │   └── src/
    │       └── chemistry_unified/
    │           ├── __init__.py
    │           └── server.py
    │
    └── visualization/
        ├── pyproject.toml
        └── src/
            └── visualization_mcp/
                ├── __init__.py
                ├── server.py
                ├── browser_pool.py
                └── tools.py
```

### Old Structure (for reference)

```
dev/
├── crystalyse/                      # Flat layout
│   ├── __init__.py                  # Package at root (problematic)
│   ├── cli.py
│   ├── agents/
│   └── ...
│
├── chemistry-creative-server/       # Individual directories
├── chemistry-unified-server/
└── visualization-mcp-server/
```

---

## 🚀 Migration Steps

### Phase 1: Directory Reorganization

This phase restructures the project to use src layout and consolidates MCP servers.

#### Step 1.1: Create Backup Branch

```bash
cd /path/to/CrystaLyse.AI
git checkout -b uv-migration
```

#### Step 1.2: Implement src Layout for Core Package

Move all core package code into `src/crystalyse/`:

```bash
cd dev/crystalyse

# Create src directory structure
mkdir -p src/crystalyse

# Move all Python files and directories using git mv (preserves history)
git mv __init__.py src/crystalyse/
git mv __main__.py src/crystalyse/
git mv cli.py src/crystalyse/
git mv config.py src/crystalyse/
git mv converters.py src/crystalyse/

# Move all subdirectories
git mv agents/ src/crystalyse/
git mv tools/ src/crystalyse/
git mv ui/ src/crystalyse/
git mv provenance/ src/crystalyse/
git mv infrastructure/ src/crystalyse/
git mv memory/ src/crystalyse/
git mv output/ src/crystalyse/
git mv prompts/ src/crystalyse/
git mv utils/ src/crystalyse/
git mv validation/ src/crystalyse/
git mv workspace/ src/crystalyse/
```

**Why src layout?**
- Eliminates package/project directory ambiguity
- Prevents accidental imports from project directory during development
- Ensures proper editable installs with modern build backends
- Industry standard recommended by Python Packaging Authority (PyPA)

#### Step 1.3: Consolidate MCP Servers

Reorganize MCP servers into unified `servers/` directory:

```bash
cd dev

# Create servers directory
mkdir -p servers

# Move MCP servers using git mv (preserves history)
git mv chemistry-creative-server servers/chemistry-creative
git mv chemistry-unified-server servers/chemistry-unified
git mv visualization-mcp-server servers/visualization
```

**Benefits:**
- Cleaner project structure
- Consistent naming (removed `-server` suffix)
- Easier workspace management
- Logical grouping of related components

#### Step 1.4: Create Python Version Pin

```bash
cd dev
echo "3.11" > .python-version
```

This ensures UV uses Python 3.11 consistently across all environments.

---

### Phase 2: Configuration Files

This phase creates and updates all configuration files for the UV workspace.

#### Step 2.1: Create Workspace Root Configuration

**File:** `dev/pyproject.toml`

```toml
[project]
name = "crystalyse-workspace"
version = "1.0.0"
description = "Crystalyse Development Workspace - AI-Powered Materials Design"
readme = "README.md"
requires-python = ">=3.11"
license = {text = "MIT"}
authors = [
    {name = "Your Name", email = "your.email@example.com"}
]

# Workspace has no direct dependencies (members have their own)
dependencies = []

[tool.uv.workspace]
members = [
    "crystalyse",
    "servers/*",
]

[tool.uv]
default-groups = ["dev", "test", "docs"]
required-version = ">=0.7.2"

[dependency-groups]
dev = [
    "pytest>=7.0.0",
    "pytest-asyncio>=0.21.0",
    "pytest-cov>=4.0.0",
    "ruff>=0.1.0",
    "mypy>=1.0.0",
    "black>=23.0.0",
    "pre-commit>=3.0.0",
]

test = [
    "pytest>=7.0.0",
    "pytest-asyncio>=0.21.0",
    "pytest-cov>=4.0.0",
    "pytest-mock>=3.10.0",
    "hypothesis>=6.0.0",
]

docs = [
    "mkdocs>=1.5.0",
    "mkdocs-material>=9.0.0",
    "mkdocstrings[python]>=0.24.0",
]
```

**Key features:**
- `[tool.uv.workspace]` defines workspace members
- `members = ["crystalyse", "servers/*"]` includes core + all servers
- `[dependency-groups]` separates dev/test/docs dependencies (PEP 735)
- `required-version` ensures UV 0.7.2+ is used

#### Step 2.2: Create Core Package Configuration

**File:** `dev/crystalyse/pyproject.toml`

```toml
[project]
name = "crystalyse"
version = "1.0.0"
description = "Crystalyse - AI-Powered Materials Design"
readme = "README.md"
requires-python = ">=3.11"
license = {text = "MIT"}
authors = [
    {name = "Your Name", email = "your.email@example.com"}
]

dependencies = [
    # Core AI/Agent dependencies
    "openai>=1.0.0",
    "openai-agents>=0.0.16",

    # Materials science
    "pymatgen>=2024.1.0",
    "ase>=3.22.0",
    "smact>=3.2.0",

    # Data handling
    "numpy>=1.24.0,<2.0.0",
    "pandas>=2.0.0",
    "pydantic>=2.0.0",

    # CLI & UI
    "rich>=13.0.0",
    "click>=8.1.0",
    "prompt-toolkit>=3.0.0",
    "typer>=0.12.0",

    # Utilities
    "typing-extensions>=4.5.0",
    "python-dotenv>=1.0.0",
    "httpx>=0.27.0",
]

[project.optional-dependencies]
visualization = [
    "plotly>=5.18.0",
    "py3Dmol>=2.0.4",
    "kaleido>=0.2.1",
    "pymatviz>=0.8.5",
]

ml = [
    "torch>=2.0.0",
    "mace-torch>=0.3.0",
]

all = [
    "crystalyse[visualization,ml]",
]

[project.scripts]
crystalyse = "crystalyse.cli:main"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/crystalyse"]  # CRITICAL: Points to src layout

[tool.ruff]
line-length = 100
target-version = "py311"

[tool.mypy]
python_version = "3.11"
strict = true
warn_return_any = true
warn_unused_configs = true
```

**Critical points:**
- `packages = ["src/crystalyse"]` - Tells hatchling where package code is
- `[project.scripts]` - Defines CLI entry point
- Dependencies match your actual requirements (adjust as needed)

#### Step 2.3: Update MCP Server Configurations

Update all three MCP server `pyproject.toml` files with workspace awareness.

**File:** `dev/servers/chemistry-creative/pyproject.toml`

```toml
[project]
name = "chemistry-creative-server"
version = "1.0.0"
description = "Creative Chemistry MCP Server for Crystalyse"
requires-python = ">=3.11"

dependencies = [
    "crystalyse",  # Workspace dependency
    "mcp>=1.0.0",
    "fastmcp>=0.5.0",
    "ase>=3.22.0",
    "pymatgen>=2024.1.0",
]

[tool.uv.sources]
crystalyse = { workspace = true }  # Critical: Enables workspace resolution

[project.scripts]
chemistry-creative-server = "chemistry_creative.server:main"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/chemistry_creative"]  # CRITICAL: Specific package path
```

**File:** `dev/servers/chemistry-unified/pyproject.toml`

```toml
[project]
name = "chemistry-unified-server"
version = "1.0.0"
description = "Unified Chemistry MCP Server for Crystalyse"
requires-python = ">=3.11"

dependencies = [
    "crystalyse",
    "mcp>=1.0.0",
    "fastmcp>=0.5.0",
    "ase>=3.22.0",
    "pymatgen>=2024.1.0",
    "smact>=3.2.0",
    "mace-torch>=0.3.0",
]

[tool.uv.sources]
crystalyse = { workspace = true }

[project.scripts]
chemistry-unified-server = "chemistry_unified.server:main"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/chemistry_unified"]  # CRITICAL: Specific package path
```

**File:** `dev/servers/visualization/pyproject.toml`

```toml
[project]
name = "visualization-mcp-server"
version = "1.0.0"
description = "Visualization MCP Server for Crystalyse"
requires-python = ">=3.11"

dependencies = [
    "crystalyse",
    "mcp>=1.0.0",
    "fastmcp>=0.5.0",
    "plotly>=5.18.0",
    "py3Dmol>=2.0.4",
    "kaleido>=0.2.1",
    "playwright>=1.40.0",
]

[tool.uv.sources]
crystalyse = { workspace = true }

[project.scripts]
visualization-server = "visualization_mcp.server:main"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/visualization_mcp"]  # CRITICAL: Specific package path
```

**Critical changes:**
1. `packages = ["src/{package_name}"]` - Must specify exact package path, not just `["src"]`
2. `[tool.uv.sources]` - Enables workspace dependency resolution
3. Updated dependencies to include workspace-aware `crystalyse`

---

### Phase 3: Code Updates

This phase updates code files to work with the new structure.

#### Step 3.1: Update Version and Branding

Update `dev/crystalyse/src/crystalyse/__init__.py`:

```python
"""
Crystalyse - AI-Powered Materials Design

Crystalyse enables researchers to discover and design materials using a unified
agent architecture powered by OpenAI Agents SDK with true agentic behaviour.

Key Features:
    - Unified Agent Architecture: Single agent with intelligent tool coordination
    - OpenAI Agents SDK: True agentic behaviour with LLM-controlled workflows
    - SMACT Integration: Chemistry validation using established libraries
    - Chemeleon CSP: Crystal structure prediction with up to 10 polymorphs
    - MACE Integration: Formation energy calculations for stability ranking
    - Complete Provenance: Always-on audit trails for reproducibility
    - UV Workspace: Fast, reproducible dependency management
"""

__version__ = "1.0.0"  # Changed from "2.0.0-alpha"

# Rest of your __init__.py code...
```

#### Step 3.2: Update CLI Branding

Update `dev/crystalyse/src/crystalyse/cli.py`:

```python
"""
Crystalyse v1.0 - AI-Powered Materials Design
"""

import typer
from rich.console import Console

console = Console()

app = typer.Typer(
    name="crystalyse",
    help="Crystalyse v1.0 - AI-Powered Materials Design",  # Updated
    # ... rest of configuration
)

# Update version callback
def version_callback(value: bool):
    if value:
        console.print("Crystalyse v1.0.0")  # Updated
        raise typer.Exit()

# ... rest of your CLI code
```

#### Step 3.3: Fix Import Paths in __main__.py

Update `dev/crystalyse/src/crystalyse/__main__.py`:

```python
"""
Crystalyse command-line interface entry point.

Allows running the CLI as: python -m crystalyse.cli
"""

import sys
from pathlib import Path

# Add parent directory to path for direct execution
if __name__ == "__main__":
    parent_dir = Path(__file__).resolve().parent.parent
    if str(parent_dir) not in sys.path:
        sys.path.insert(0, str(parent_dir))

    from crystalyse.cli import main
    main()
else:
    from .cli import main
```

This ensures the module can be run both as `python -m crystalyse.cli` and via the console script.

#### Step 3.4: Update MCP Server Paths

**CRITICAL:** Update `dev/crystalyse/src/crystalyse/config.py` to account for new directory structure:

```python
def load_from_env(self):
    """Load configuration from environment variables with sensible defaults"""

    # Important: base_dir is now crystalyse/src/crystalyse due to src layout
    # Navigate up three levels: src/crystalyse -> src -> crystalyse -> dev
    dev_dir = self.base_dir.parent.parent.parent

    # MCP Server Configurations
    self.mcp_servers = {
        "chemistry_unified": {
            "command": os.getenv("CRYSTALYSE_PYTHON_PATH", sys.executable),
            "args": ["-m", "chemistry_unified.server"],
            "cwd": str(dev_dir / "servers" / "chemistry-unified" / "src")
            # OLD: self.base_dir / "chemistry-unified-server" / "src"
        },
        "chemistry_creative": {
            "command": sys.executable,
            "args": ["-m", "chemistry_creative.server"],
            "cwd": str(dev_dir / "servers" / "chemistry-creative" / "src")
            # OLD: self.base_dir / "chemistry-creative-server" / "src"
        },
        "visualization": {
            "command": sys.executable,
            "args": ["-m", "visualization_mcp.server"],
            "cwd": str(dev_dir / "servers" / "visualization" / "src")
            # OLD: self.base_dir / "visualization-mcp-server" / "src"
        }
    }

    # ... rest of config
```

**Two critical fixes:**
1. `dev_dir = self.base_dir.parent.parent.parent` - Navigate from `crystalyse/src/crystalyse` to `dev/`
2. Updated paths: `servers/chemistry-unified` instead of `chemistry-unified-server`

#### Step 3.5: Update .gitignore

Update `.gitignore` to exclude UV artifacts but keep lockfile:

```gitignore
# UV
.venv/          # Exclude virtual environment
*/.venv/
# uv.lock kept in version control for reproducibility
# .python-version kept in version control for consistency

# External repositories (if cloned for reference)
/uv/
/SMACT/
/mace/
/modelcontextprotocol/
/python-sdk/

# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# IDEs
.vscode/
.idea/
*.swp
*.swo
*~

# Testing
.pytest_cache/
.coverage
htmlcov/
.tox/

# Environment
.env
.env.local
```

---

### Phase 4: Initialize Workspace

#### Step 4.1: Install Python 3.11 via UV

```bash
cd dev
uv python install 3.11
```

This ensures UV uses Python 3.11 for the workspace.

#### Step 4.2: Sync Workspace

```bash
cd dev
uv sync
```

This command:
1. Reads workspace configuration from `pyproject.toml`
2. Resolves dependencies for all workspace members
3. Creates universal lockfile (`uv.lock`)
4. Creates shared virtual environment (`.venv/`)
5. Installs all packages in editable mode

**Expected output:**
```
Using Python 3.11.x
Creating virtual environment at: .venv
Resolved 87 packages in 1.2s
Downloaded 87 packages in 3.4s
Installed 87 packages in 1.1s
+ crystalyse==1.0.0 (from file:///path/to/dev/crystalyse)
+ chemistry-creative-server==1.0.0 (from file:///path/to/dev/servers/chemistry-creative)
+ chemistry-unified-server==1.0.0 (from file:///path/to/dev/servers/chemistry-unified)
+ visualization-mcp-server==1.0.0 (from file:///path/to/dev/servers/visualization)
+ ... (other dependencies)
```

#### Step 4.3: Verify Installation

```bash
# Check Python version
uv run python --version
# Output: Python 3.11.x

# Check package import
uv run python -c "import crystalyse; print(crystalyse.__version__)"
# Output: 1.0.0

# Check CLI
uv run python -m crystalyse.cli --version
# Output: Crystalyse v1.0.0

# Check CLI help
uv run python -m crystalyse.cli --help
# Should show full CLI help

# Check console script (from .venv)
.venv/bin/crystalyse --version
# Output: Crystalyse v1.0.0
```

---

### Phase 5: Testing & Verification

#### Step 5.1: Run Test Suite

```bash
cd dev
uv run pytest
```

If you have tests, they should all pass. Address any failures before proceeding.

#### Step 5.2: Test Core Functionality

Test a basic discovery query:

```bash
uv run python -m crystalyse.cli discover "LiFePO4" --mode adaptive
```

**Expected behavior:**
- MCP servers should auto-start
- Agent should use tools (validate_composition, analyze_stability, etc.)
- Provenance tracking should show all operations
- Results should be comprehensive

#### Step 5.3: Test MCP Integration

Run a complex query that requires MCP tools:

```bash
uv run python -m crystalyse.cli discover "Design a novel self healing concrete additive"
```

**Verify:**
- MCP servers start successfully
- Tools are called: `validate_composition`, `analyze_stability`, `predict_band_gap`, etc.
- Provenance shows MCP tool calls (e.g., "4 MCP tool calls, 7 total operations")
- Comprehensive materials design is generated

#### Step 5.4: Test Interactive Mode

```bash
uv run python -m crystalyse.cli chat -u test_user
```

**Verify:**
- Interactive session starts
- Commands work (discovery queries, user stats, etc.)
- Session memory persists
- Can exit cleanly

---

### Phase 6: Documentation

#### Step 6.1: Create User README

**File:** `dev/README.md`

```markdown
# Crystalyse v1.0

**AI-Powered Materials Design**

Crystalyse enables researchers to discover and design materials using advanced AI agents with complete provenance tracking.

## Quick Start

### Installation

**Using UV (Recommended):**
```bash
# Install UV
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone repository
git clone https://github.com/yourusername/crystalyse.git
cd crystalyse/dev

# Install dependencies
uv sync

# Verify installation
uv run python -m crystalyse.cli --version
```

**Using pip:**
```bash
pip install crystalyse
```

### Usage

**From /dev directory:**
```bash
# Basic discovery
uv run python -m crystalyse.cli discover "Find novel battery materials"

# Interactive chat
uv run python -m crystalyse.cli chat -u username

# Specific analysis mode
uv run python -m crystalyse.cli discover "perovskite solar cells" --mode creative
```

**From repository root:**
```bash
uv run --directory dev python -m crystalyse.cli discover "..."
```

## Development

### Workspace Structure

This project uses a UV workspace with the following members:

- **crystalyse/** - Core package
- **servers/chemistry-creative/** - Creative chemistry MCP server
- **servers/chemistry-unified/** - Unified chemistry MCP server
- **servers/visualization/** - Visualization MCP server

All packages share a single lockfile (`uv.lock`) for reproducible installations.

### Common Commands

```bash
# Sync all dependencies
uv sync

# Run tests
uv run pytest

# Lint code
uv run ruff check .

# Type check
uv run mypy crystalyse

# Add dependency
uv add package-name

# Add dev dependency
uv add --dev tool-name
```

### Adding Dependencies

**Core package:**
```bash
cd dev
uv add requests
```

**Development tools:**
```bash
uv add --dev pytest-mock
```

**Optional dependencies:**
```bash
# Edit dev/crystalyse/pyproject.toml:
[project.optional-dependencies]
visualization = ["plotly>=5.18.0", ...]
```

## Features

- **Unified Agent Architecture** - Single agent with intelligent tool coordination
- **OpenAI Agents SDK** - True agentic behavior with LLM-controlled workflows
- **Materials Science Tools** - SMACT, Pymatgen, ASE, Chemeleon, MACE
- **Complete Provenance** - Always-on audit trails for reproducibility
- **Multiple Analysis Modes** - Adaptive, creative, rigorous
- **Interactive Chat** - Session-based conversations with memory
- **MCP Integration** - Model Context Protocol servers for tool access

## Documentation

- User Guide: [docs/user-guide.md](docs/user-guide.md)
- API Reference: [docs/api-reference.md](docs/api-reference.md)
- Contributing: [CONTRIBUTING.md](CONTRIBUTING.md)

## License

MIT License - see [LICENSE](LICENSE) for details.
```

#### Step 6.2: Update CLAUDE.md

Update your AI assistant context file to reflect the new architecture:

```markdown
# Crystalyse v1.0 Development Notes

## Environment Setup
**Active Development Environment**: Pure UV (no conda)
```bash
cd dev
uv sync              # Install dependencies
uv run python -m crystalyse.cli --help  # Test CLI
```

## Architecture v1.0

### Package Manager
- **UV workspace** with 4 members (crystalyse + 3 MCP servers)
- **Python 3.11+** standardized across all components
- **src layout** for core package (PyPA recommended)
- **Unified MCP servers** in `servers/` directory

### Important Paths
- Core package: `dev/crystalyse/src/crystalyse/`
- MCP servers: `dev/servers/{chemistry-creative,chemistry-unified,visualization}/`
- Workspace root: `dev/pyproject.toml`
- Lockfile: `dev/uv.lock` (universal, all platforms)

## Key Commands

```bash
# Development
uv sync                      # Sync all dependencies
uv run python -m crystalyse.cli discover "..."  # Run discovery
uv run pytest                # Run tests

# Adding dependencies
uv add package-name          # Add to core
uv add --dev tool-name       # Add dev tool

# Workspace operations
uv sync --all-packages       # Sync all members
uv run --package chemistry-unified-server chemistry-unified-server
```

## Troubleshooting

### Console script not found
- Run from /dev: `uv run python -m crystalyse.cli`
- Or use .venv script: `.venv/bin/crystalyse`

### MCP servers not working
- Check paths in config.py (should use `dev_dir = self.base_dir.parent.parent.parent`)
- Verify packages in server pyproject.toml: `["src/{package_name}"]`

### Import errors
- Ensure you're in /dev directory
- Run `uv sync` to update environment
- Check src layout: code should be in `src/crystalyse/`

## Quick Reference
```bash
# Test basic functionality
uv run python -m crystalyse.cli --version  # Should show v1.0.0
uv run python -m crystalyse.cli discover "LiFePO4" --mode creative
uv run python -m crystalyse.cli chat -u test_user
```
```

#### Step 6.3: Create Migration Guide

Create a comprehensive guide for contributors in `dev/docs/UV_MIGRATION_GUIDE.md` (see Phase 3 from original plan for full content).

---

## 🐛 Common Issues & Solutions

### Issue 1: Console Script Not Found

**Problem:**
```bash
$ uv run crystalyse
ModuleNotFoundError: No module named 'crystalyse'
```

**Root Cause:** Package not properly installed with src layout.

**Solution:**
1. Verify `packages = ["src/crystalyse"]` in `dev/crystalyse/pyproject.toml`
2. Run `uv sync` to reinstall
3. Use `uv run python -m crystalyse.cli` instead

### Issue 2: MCP Servers Not Found

**Problem:** Agent says "cannot compute precise values... without a dedicated DFT-based materials-analysis tool"

**Root Causes:**
1. **Incorrect package path in MCP server pyproject.toml:**
   ```toml
   # WRONG:
   packages = ["src"]

   # CORRECT:
   packages = ["src/chemistry_unified"]
   ```

2. **Incorrect paths in config.py:**
   ```python
   # WRONG:
   "cwd": str(self.base_dir / "chemistry-unified-server" / "src")

   # CORRECT:
   dev_dir = self.base_dir.parent.parent.parent
   "cwd": str(dev_dir / "servers" / "chemistry-unified" / "src")
   ```

**Solution:**
1. Fix all three MCP server pyproject.toml files
2. Update config.py paths
3. Run `uv sync --all-packages`
4. Test with: `uv run python -m crystalyse.cli discover "test query"`

### Issue 3: Import Errors After Migration

**Problem:**
```python
ImportError: No module named 'crystalyse'
```

**Root Cause:** Code still using old import paths or not in editable mode.

**Solution:**
1. Verify you're in `/dev` directory
2. Run `uv sync` to ensure editable install
3. Check imports are `from crystalyse import ...` (not `from src.crystalyse import ...`)

### Issue 4: UV Lock Resolution Conflicts

**Problem:** UV can't resolve dependencies, conflicts reported.

**Solution:**
```bash
# Clear cache and retry
uv cache clean
uv sync

# If still issues, use --resolution flag
uv sync --resolution=highest  # Try highest compatible versions
uv sync --resolution=lowest   # Try lowest compatible versions
```

### Issue 5: Python Version Mismatch

**Problem:** UV using wrong Python version.

**Solution:**
```bash
# Check current Python
uv python list

# Install Python 3.11
uv python install 3.11

# Verify .python-version exists
cat dev/.python-version  # Should show "3.11"

# Re-sync
uv sync
```

---

## ✅ Verification Checklist

Use this checklist to ensure migration is complete:

### Phase 1: Directory Structure
- [ ] `dev/servers/` directory created
- [ ] MCP servers moved to `servers/{chemistry-creative,chemistry-unified,visualization}`
- [ ] Core package restructured to src layout: `dev/crystalyse/src/crystalyse/`
- [ ] All files moved with `git mv` (preserves history)
- [ ] `.python-version` created with "3.11"

### Phase 2: Configuration Files
- [ ] `dev/pyproject.toml` created (workspace root)
- [ ] `dev/crystalyse/pyproject.toml` created with `packages = ["src/crystalyse"]`
- [ ] All three MCP server pyproject.toml files updated with `packages = ["src/{package_name}"]`
- [ ] All MCP servers have `[tool.uv.sources]` with `crystalyse = { workspace = true }`
- [ ] `.gitignore` updated (excludes `.venv/`, keeps `uv.lock`)

### Phase 3: Code Updates
- [ ] `__init__.py` version updated to "1.0.0"
- [ ] `cli.py` branding updated to "Crystalyse v1.0"
- [ ] `__main__.py` import logic fixed for src layout
- [ ] `config.py` MCP paths updated for new structure
- [ ] All references to "CrystaLyse.AI" changed to "Crystalyse"

### Phase 4: Workspace Initialization
- [ ] Python 3.11 installed via UV
- [ ] `uv sync` completes successfully
- [ ] `uv.lock` file generated (631KB typical)
- [ ] `.venv/` directory created
- [ ] All 4 packages installed in editable mode

### Phase 5: Verification
- [ ] `uv run python -m crystalyse.cli --version` shows "Crystalyse v1.0.0"
- [ ] `uv run python -c "import crystalyse; print(crystalyse.__version__)"` shows "1.0.0"
- [ ] Console script works: `.venv/bin/crystalyse --help`
- [ ] Basic discovery test passes
- [ ] MCP integration test passes (tools called, provenance tracked)
- [ ] All tests pass: `uv run pytest`

### Phase 6: Documentation
- [ ] `dev/README.md` created with UV instructions
- [ ] `CLAUDE.md` updated with new architecture
- [ ] Migration guide created (optional but recommended)
- [ ] All documentation references updated

---

## 📊 Expected Results

### Performance Metrics

| Metric | Old (pip/conda) | New (UV) | Improvement |
|--------|----------------|----------|-------------|
| **Dependency Resolution** | ~30s | <2s | **15x faster** |
| **Fresh Install** | ~2min | ~10s | **12x faster** |
| **Environment Sync** | ~1min | ~3s | **20x faster** |
| **Lockfile Generation** | Per-platform | Universal | **Cross-platform** |

### File Changes Summary

**Typical migration:**
- **Files renamed:** ~97 (src layout + server moves)
- **Files modified:** ~9 (configs + version updates)
- **Files created:** ~5 (workspace config + docs)
- **Lockfile size:** ~631KB (universal for all platforms)

---

## 🔄 Rollback Plan

If you encounter critical issues and need to rollback:

### Option 1: Git Reset (Safest)

```bash
# Return to backup branch
git checkout backup-pre-uv-migration

# Or reset migration branch
git checkout uv-migration
git reset --hard origin/master
```

### Option 2: Manual Restoration

1. **Remove UV files:**
   ```bash
   rm -rf dev/.venv dev/uv.lock dev/.python-version
   ```

2. **Restore old structure:**
   ```bash
   # Move MCP servers back
   git mv dev/servers/chemistry-creative dev/chemistry-creative-server
   git mv dev/servers/chemistry-unified dev/chemistry-unified-server
   git mv dev/servers/visualization dev/visualization-mcp-server

   # Restore flat layout
   git mv dev/crystalyse/src/crystalyse/* dev/crystalyse/
   ```

3. **Restore old environment:**
   ```bash
   conda activate rust  # Or your old environment
   pip install -e dev/crystalyse
   ```

---

## 🎉 Post-Migration Steps

### Immediate Actions

1. **Commit changes:**
   ```bash
   git add -A
   git commit -m "feat: Migrate to UV workspace with src layout - Crystalyse v1.0"
   ```

2. **Push to remote:**
   ```bash
   git push -u origin uv-migration
   ```

3. **Create pull request:**
   - Use detailed PR description from earlier in this guide
   - Link to this migration plan
   - Request review from team members

4. **Test in CI/CD:**
   - Ensure GitHub Actions workflows updated for UV
   - Verify tests pass in clean environment

### Long-term Enhancements

- [ ] Add pre-commit hooks with UV
- [ ] Set up automated dependency updates (Dependabot/Renovate)
- [ ] Create Docker image with UV
- [ ] Add UV scripts for common tasks
- [ ] Set up UV-based documentation builds
- [ ] Monitor performance metrics

---

## 📚 References

- **UV Documentation:** https://docs.astral.sh/uv/
- **UV Workspaces Guide:** https://docs.astral.sh/uv/concepts/workspaces/
- **PEP 735 - Dependency Groups:** https://peps.python.org/pep-0735/
- **Python Packaging Guide:** https://packaging.python.org/
- **src Layout Benefits:** https://packaging.python.org/en/latest/discussions/src-layout-vs-flat-layout/

---

## 🤝 Support

If you encounter issues during migration:

1. **Check this guide's troubleshooting section**
2. **Review UV documentation:** https://docs.astral.sh/uv/
3. **Search GitHub issues:** Look for similar problems
4. **Ask for help:** Create an issue with detailed error messages

---

**Guide Version:** 1.0
**Last Updated:** 2025-10-22
**Maintainer:** Ryan Nduma
**Status:** Production-ready
