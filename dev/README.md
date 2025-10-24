# Crystalyse v1.0 - AI-Powered Materials Design

Crystalyse enables researchers to discover and design materials using a unified agent architecture powered by OpenAI Agents SDK with true agentic behaviour.

## ✨ Key Features

- **Unified Agent Architecture** - Single intelligent agent with tool coordination
- **OpenAI Agents SDK** - True agentic behaviour with LLM-controlled workflows
- **SMACT Integration** - Chemistry validation using established libraries
- **Chemeleon CSP** - Crystal structure prediction with up to 10 polymorphs
- **MACE Integration** - Formation energy calculations for stability ranking
- **Complete Provenance** - Always-on audit trails for reproducibility
- **UV Workspace** - Fast, reproducible dependency management (10-100x faster than pip)

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) package manager

### Installation

```bash
# Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone repository
git clone https://github.com/ryannduma/crystalyse.git
cd crystalyse/dev

# Sync workspace (creates .venv with Python 3.11, installs all packages)
uv sync --all-packages

# Verify installation
uv run python -c "import crystalyse; print(f'Crystalyse v{crystalyse.__version__}')"

# Test console script
uv run crystalyse --help
```

**Important:** Always use `uv sync --all-packages` for first-time installation to ensure all workspace members (crystalyse + MCP servers) are installed.

## 📖 Usage

### From Within `/dev` Directory

When you're in the `/dev` directory, use:

```bash
cd dev

# Run discovery query (two equivalent methods)
uv run crystalyse discover "LiFePO4"
uv run python -m crystalyse.cli discover "LiFePO4"

# Start interactive chat
uv run crystalyse chat
uv run python -m crystalyse.cli chat

# Specific analysis mode
uv run crystalyse discover "novel oxide for batteries" --mode creative

# Get help
uv run crystalyse --help
```

### From Repository Root

When you're in the repository root, use the `--directory` flag:

```bash
# From /home/ryan/mycrystalyse/CrystaLyse.AI/
uv run --directory dev python -m crystalyse.cli discover "LiFePO4"
uv run --directory dev python -m crystalyse.cli --help
```

### Available Commands

```bash
# Discovery (non-interactive)
uv run python -m crystalyse.cli discover "query" [OPTIONS]

# Chat (interactive)
uv run python -m crystalyse.cli chat [OPTIONS]

# Analyze provenance
uv run python -m crystalyse.cli analyse-provenance

# User statistics
uv run python -m crystalyse.cli user-stats --user <username>
```

### Analysis Modes

- `--mode adaptive` (default) - Balanced approach, learns from user
- `--mode creative` - Fast exploration with novel suggestions
- `--mode rigorous` - Thorough validation using o3-mini model

## 🏗️ Workspace Structure

This project uses a **uv workspace** with the following structure:

```
dev/
├── pyproject.toml              # Workspace root
├── uv.lock                     # Universal lockfile (commit this!)
├── .python-version             # Python 3.11
├── .venv/                      # Shared virtual environment (DO NOT commit)
│
├── crystalyse/                 # Core package
│   ├── pyproject.toml
│   └── src/
│       └── crystalyse/         # Package source (src layout)
│           ├── __init__.py
│           ├── cli.py
│           ├── agents/
│           ├── tools/
│           ├── ui/
│           └── provenance/
│
└── servers/                    # MCP servers
    ├── chemistry-creative/
    │   ├── pyproject.toml
    │   └── src/
    ├── chemistry-unified/
    │   ├── pyproject.toml
    │   └── src/
    └── visualization/
        ├── pyproject.toml
        └── src/
```

### Why src Layout?

The `src/` layout provides:
- Clear separation between package code and project files
- Prevents accidental imports of development files
- Better compatibility with build backends (hatchling, setuptools)
- Standard practice in modern Python packaging

All workspace members share:
- Single `uv.lock` for reproducible installs
- Shared `.venv` directory (faster, disk-space efficient)
- Consistent Python version (3.11)

## 🛠️ Development

### Adding Dependencies

```bash
# Add to core package
cd dev
uv add package-name

# Add development dependency
uv add --dev pytest-plugin

# Add to specific dependency group
uv add --group test package-name
```

### Running Tests

```bash
cd dev
uv run pytest
uv run pytest --cov=crystalyse
```

### Code Quality

```bash
# Linting
uv run ruff check .
uv run ruff check . --fix

# Type checking
uv run mypy crystalyse/src/crystalyse

# Formatting
uv run black crystalyse/src/
```

### Updating Dependencies

```bash
# Update all dependencies
uv lock --upgrade

# Update specific package
uv lock --upgrade-package numpy

# Sync after update
uv sync
```

## 🔧 Workspace Commands

### Syncing

```bash
# Sync all workspace members
uv sync

# Sync specific package only
uv sync --package crystalyse

# Sync with all extras
uv sync --all-extras

# Force reinstall of specific package
uv sync --reinstall-package crystalyse
```

### Running Commands

```bash
# Run in workspace context (auto-syncs)
uv run python script.py

# Run without syncing (faster, uses locked versions)
uv run --frozen python script.py

# Run for specific package
uv run --package chemistry-unified-server chemistry-unified-server --help
```

### Building

```bash
# Build wheel
uv build

# Build for specific package
cd crystalyse
uv build
```

## 🌍 Environment Variables

```bash
# Optional: Override checkpoint directory
export CHEMELEON_CHECKPOINT_DIR=/path/to/checkpoints

# Optional: Set OpenAI API key
export OPENAI_API_KEY=your-key-here

# Optional: Configure provenance output
export PROVENANCE_OUTPUT_DIR=./my_provenance
```

## 📊 Provenance System

Provenance tracking is **always-on by default** - every discovery query automatically generates complete audit trails.

### Accessing Provenance Data

```bash
# Provenance is captured automatically
uv run python -m crystalyse.cli discover "LiFePO4"

# Check output directory
ls provenance_output/runs/

# Each session creates:
# - events.jsonl              # Real-time event stream
# - materials.jsonl           # Discovered materials
# - materials_catalog.json    # Full catalog with metadata
# - summary.json              # Session summary
# - assistant_full.md         # Complete conversation
```

### Analyzing Provenance

```bash
uv run python -m crystalyse.cli analyse-provenance
```

## 🐛 Troubleshooting

### "Command not found: uv"
```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Reload shell
source ~/.bashrc  # or ~/.zshrc
```

### "No module named 'crystalyse'"
```bash
# Make sure you're in the dev/ directory or use --directory
cd dev
uv sync --all-packages
uv run python -c "import crystalyse; print('OK')"
```

### "Failed to spawn: crystalyse" or "No such file or directory"

This error occurs when the console script isn't installed or when using the wrong Python version.

**Solution 1: Wrong Python Version**
```bash
# Check current Python version
uv run python --version

# If showing Python 3.9 instead of 3.11:
cd dev
rm -rf .venv
uv sync --all-packages

# Verify
uv run python --version  # Should show 3.11.x
uv run crystalyse --help
```

**Solution 2: Package Not Installed**
```bash
# Re-sync with all packages
cd dev
uv sync --all-packages

# Verify
uv run crystalyse --help
```

**Why this happens:**
- UV may use system Python (3.9) instead of the required Python 3.11
- The `.venv` must be created with Python 3.11 for the package to install
- `uv sync` alone doesn't always install workspace members; use `--all-packages`

### "Package not found"
```bash
# Re-sync workspace with all packages
cd dev
uv sync --all-packages
```

### Stale Virtual Environment
```bash
# Clean reinstall
cd dev
rm -rf .venv
uv sync --all-packages
```

### Import Errors After Moving Files
```bash
# Reinstall with --reinstall flag
uv sync --reinstall-package crystalyse
```

### Wrong Python Version in Virtual Environment
```bash
# Check .python-version file
cat dev/.python-version  # Should show: 3.11

# List available Python versions
uv python list

# If Python 3.11 not installed:
uv python install 3.11

# Recreate venv with correct version
cd dev
rm -rf .venv
uv sync --all-packages
```

## 📚 Documentation

- **Migration Guide**: See `UV_MIGRATION_PLAN.md` for UV migration details
- **Provenance System**: See `crystalyse/src/crystalyse/provenance/README.md`
- **Render Gate**: See `docs/concepts/render_gate_system.md`
- **CLI Architecture**: See `docs/concepts/cli_architecture.md`

## 🤝 Contributing

### Development Workflow

1. **Fork and clone**
   ```bash
   git clone your-fork-url
   cd crystalyse/dev
   ```

2. **Create feature branch**
   ```bash
   git checkout -b feature/my-feature
   ```

3. **Install dependencies**
   ```bash
   uv sync
   ```

4. **Make changes**
   - Edit code in `crystalyse/src/crystalyse/`
   - Add tests in `crystalyse/tests/`
   - Update documentation

5. **Test changes**
   ```bash
   uv run pytest
   uv run ruff check .
   uv run mypy crystalyse/src/crystalyse
   ```

6. **Commit and push**
   ```bash
   git add .
   git commit -m "feat: Add feature description"
   git push origin feature/my-feature
   ```

7. **Create pull request**

### Coding Standards

- **Python 3.11+** features encouraged
- **Type hints** required for public APIs
- **Docstrings** required (Google style)
- **Tests** required for new features
- **Ruff** for linting and formatting
- **Mypy** for type checking

## 📄 License

MIT License - See LICENSE file for details

## 🙏 Acknowledgments

- **OpenAI Agents SDK** - Agent framework
- **SMACT** - Chemistry validation
- **Chemeleon** - Crystal structure prediction
- **MACE** - Formation energy calculations
- **PyMatGen** - Materials analysis
- **UV** - Fast package management

## 📞 Support

- **Issues**: https://github.com/ryannduma/crystalyse/issues
- **Discussions**: https://github.com/ryannduma/crystalyse/discussions
- **Email**: ryannduma@gmail.com

---

**Crystalyse v1.0** - Built with ❤️ for the materials science community
