# Changelog

All notable changes to Crystalyse will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2025-11-01

### Stable Release - First Public Release

This is the first stable public release of Crystalyse (formerly `crystalyse-ai`). This release represents a complete architectural rewrite with 32 commits of development since the last `crystalyse-ai` preview (v1.0.14).

### Added - Core Features

**Provenance System** (16 Python modules)
- Complete computational honesty with full audit trails
- Anti-hallucination render gate prevents fabricated numerical values
- Value registry tracks all computed properties with source attribution
- Artifact tracker maintains records of all generated files
- JSONL event logging for reproducibility
- Integration with OpenAI Agents SDK trace handlers

**Auto-Download System**
- Zero-configuration checkpoint management
- Automatic download of Chemeleon models (~600 MB) on first use
- Automatic download of Materials Project phase diagrams (~170 MB, 271,617 entries) on first use
- Standard cache locations (`~/.cache/crystalyse/`)
- Progress bars and error handling
- Smart caching (one-time download, cached forever)

**Enhanced PyMatGen Integration**
- Energy above hull calculations with Materials Project database
- Automatic phase diagram construction from composition
- Decomposition product analysis
- Stability classification (stable/metastable/unstable)
- Competing phases identification
- Custom data path support via `CRYSTALYSE_PPD_PATH`

**Adaptive Clarification System**
- Learns user expertise level over time
- Adapts question complexity based on user history
- Reduces unnecessary interruptions for experienced users
- Provides more detailed guidance for beginners
- Session-aware clarification strategies

**Global Mode Management**
- Mode injection into MCP servers
- Dynamic mode switching (creative/rigorous/adaptive)
- Tools adapt behavior based on current mode
- Consistent mode awareness across the system

**Modular MCP Architecture**
- Separate packages for chemistry-unified, chemistry-creative, and visualization servers
- Clean imports from `crystalyse.tools.*`
- Proper Python dependency management
- No PYTHONPATH manipulation required

### Changed - Architecture

**Package Structure**
- Renamed from `crystalyse-ai` to `crystalyse`
- Streamlined from monolithic to modular design
- Tools organized in subdirectories (`smact/`, `chemeleon/`, `mace/`, `pymatgen/`, `visualization/`)
- 90% code reduction through elimination of redundant implementations
- Cleaner separation of concerns

**CLI Interface**
- Reduced from 1385 lines to 560 lines
- Eliminated `unified_cli.py` (functionality merged into main CLI)
- More intuitive command structure
- Better error messages

**Configuration System**
- Enhanced `Config` class with mode-aware timeouts
- Auto-detection of checkpoint and data file locations
- Fallback path resolution for backward compatibility
- Environment variable support (optional, not required)

**Dependency Management**
- MCP servers bundled as core dependencies
- Chemeleon installed directly from GitHub (v0.1.2 with fixes)
- All optional dependencies properly categorized
- No manual installation steps required

### Fixed

**Upstream Chemeleon Bug**
- Created self-contained checkpoint manager to work around `chemeleon-dng` v0.1.2 bug
- Bug: `download_util.py` crashes when `default_paths=None`
- Solution: Complete replacement with robust downloader
- Provides zero-configuration setup with auto-download

**Phase Diagram Management**
- Replaced hardcoded paths with smart auto-download system
- Multiple fallback path resolution for development environments
- Better error messages when data not found
- Figshare integration for reliable downloads

**Import Structure**
- Fixed complex `crystalyse_ai` imports to clean `crystalyse` imports
- Eliminated circular import issues
- Proper module-level exports

### Breaking Changes from v1.0 (crystalyse-ai)

**Package Name**
- OLD: `pip install crystalyse-ai`
- NEW: `pip install crystalyse`

**Import Name**
- OLD: `from crystalyse_ai.agents import ...`
- NEW: `from crystalyse.agents import ...`

**MCP Servers**
- OLD: Separate installation required
- NEW: Bundled automatically with main package

**Checkpoint/Data Management**
- OLD: Manual download and environment variable setup required
- NEW: Automatic download on first use (optional custom paths)

**Environment Variables**
- OLD: `OPENAI_API_KEY` (required)
- NEW: `OPENAI_MDG_API_KEY` (required, custom name)
- NEW: `CHEMELEON_CHECKPOINT_DIR` (optional)
- NEW: `CRYSTALYSE_PPD_PATH` (optional)

### Migration Guide

For users migrating from `crystalyse-ai` (v1.0.x):

1. **Uninstall old version**:
   ```bash
   pip uninstall crystalyse-ai
   ```

2. **Install new version**:
   ```bash
   pip install crystalyse
   ```

3. **Update imports in your code**:
   ```python
   # OLD
   from crystalyse_ai.agents import EnhancedCrystaLyseAgent
   from crystalyse_ai.config import Config

   # NEW
   from crystalyse.agents import EnhancedCrystaLyseAgent
   from crystalyse.config import CrystaLyseConfig
   ```

4. **Update environment variables**:
   ```bash
   # OLD
   export OPENAI_API_KEY="sk-..."

   # NEW
   export OPENAI_MDG_API_KEY="sk-..."
   ```

5. **Remove manual checkpoint/data management**:
   - Delete manual checkpoint downloads
   - Remove checkpoint environment variable setup
   - Everything auto-downloads now

### Technical Details

**Version**: 1.0.0 (Stable Release)
**Python**: 3.11+ required
**Git Commits**: 32 commits since last PyPI release (67ee9f0)
**Lines Changed**: ~15,000+ lines added/modified/removed
**New Files**: 20+ new Python modules
**Architecture**: Complete rewrite

### Performance Characteristics

| Operation | Creative Mode | Rigorous Mode |
|-----------|---------------|---------------|
| Simple query | ~50 seconds | 2-3 minutes |
| Complex analysis | 1-2 minutes | 3-5 minutes |
| Batch processing | 5-10 minutes | 15-30 minutes |

### Known Limitations

- First-run downloads require internet connection (~770 MB total)
- GPU recommended for large-scale MACE calculations
- PyMatGen phase diagrams limited to Materials Project entries
- OpenAI API rate limits apply

### Deprecation Notice

The old `crystalyse-ai` package (v1.0.x) is deprecated in favor of this new `crystalyse` package. While `crystalyse-ai` will remain available on PyPI, no further updates are planned. All development continues in `crystalyse`.

---

## Previous Versions (crystalyse-ai)

For changelog of the old `crystalyse-ai` package (v1.0.0 - v1.0.14), see:
https://github.com/ryannduma/CrystaLyse.AI/blob/master/pypi/CHANGELOG.md

### Key Differences vs crystalyse-ai v1.0.14

| Feature | crystalyse-ai v1.0.14 | crystalyse v1.0.0 |
|---------|----------------------|-------------------|
| Provenance system | ❌ Not present | ✅ Complete (16 modules) |
| Checkpoint management | ❌ Manual setup | ✅ Auto-download |
| Phase diagrams | ❌ Manual download | ✅ Auto-download |
| MCP servers | Bundled in package | Separate packages |
| Package size | 174 KB | ~2 MB (with MCP servers) |
| Tools organization | Flat files | Subdirectories |
| Import name | `crystalyse_ai` | `crystalyse` |
| CLI lines | 1385 | 560 |
| Code reduction | Baseline | 90% reduction |
| Adaptive clarification | ❌ Basic | ✅ Learning system |
| Mode injection | ❌ Not present | ✅ Global manager |

---

## Links

- [GitHub Repository](https://github.com/ryannduma/CrystaLyse.AI)
- [Issues](https://github.com/ryannduma/CrystaLyse.AI/issues)
- [Discussions](https://github.com/ryannduma/CrystaLyse.AI/discussions)
- [Documentation](https://github.com/ryannduma/CrystaLyse.AI/tree/master/docs)

---

**For support and bug reports, please visit our [GitHub Issues](https://github.com/ryannduma/CrystaLyse.AI/issues).**
