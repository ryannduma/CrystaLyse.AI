# Feature Classification Matrix

This document classifies CrystaLyse features into stable (PyPI v1.0.1) versus development-only (v1.0.0-dev) categories.

**Key Finding**: Nearly all features are included in the stable PyPI release. The development version represents ongoing refinements rather than a separate feature set.

## Feature Comparison

| Feature | PyPI v1.0.1 | Dev v1.0.0 | Description |
|---------|-------------|------------|-------------|
| **Core Agent System** | ✓ | ✓ | OpenAI Agents SDK integration with `EnhancedCrystaLyseAgent` |
| **SMACT Integration** | ✓ | ✓ | Composition validation, dopant prediction, screening, validators |
| **Chemeleon Integration** | ✓ | ✓ | Structure prediction with checkpoint manager, auto-download |
| **MACE Integration** | ✓ | ✓ | Formation energy, stress calculations, structure relaxation |
| **PyMatGen Integration** | ✓ | ✓ | Phase diagram analysis, stability calculations, 271,617 MP entries |
| **Provenance System** | ✓ | ✓ | Full computational audit trail, artifact tracking, render gate, value registry |
| **Analysis Modes** | ✓ | ✓ | Creative, Rigorous, Adaptive modes with mode injection |
| **Auto-Download** | ✓ | ✓ | Chemeleon checkpoints (~600 MB) and Materials Project data (~170 MB) |
| **Configuration System** | ✓ | ✓ | Environment-based config with `Config.load()` |
| **MCP Server Architecture** | ✓ | ✓ | Chemistry Creative, Chemistry Unified, Visualisation servers |
| **CLI Commands** | ✓ | ✓ | `discover`, `chat`, `analyse-provenance`, `user-stats` |
| **4-Layer Memory System** | ✓ | ✓ | Session, Discovery Cache, User Memory, Cross-Session Context |
| **Adaptive Clarification** | ✓ | ✓ | Learns user expertise, adjusts question complexity |
| **Session Management** | ✓ | ✓ | Persistent sessions with MCP connection pooling |
| **Enhanced UI Components** | ✓ | ✓ | Rich console, chat interface, trace handlers, progress tracking |
| **Visualisation Tools** | ✓ (optional) | ✓ | 3D structures (3Dmol.js), plots (pymatviz), CIF generation |
| **Resilient Tool Calling** | ✓ | ✓ | Fault-tolerant tool invocation with retries |
| **User Preference Memory** | ✓ | ✓ | Learning system that adapts to user expertise |
| **Workspace Tools** | ✓ | ✓ | File operations, approval callbacks, clarification system |
| **Phase Diagram Downloader** | ✓ | ✗ | Auto-download Materials Project data (PyPI-specific feature) |

## CLI Command Status

All CLI commands are **stable** and included in PyPI v1.0.1:

| Command | Status | Description |
|---------|--------|-------------|
| `crystalyse analyse` | Stable | Non-interactive single-shot materials discovery |
| `crystalyse chat` | Stable | Interactive chat session with memory and learning |
| `crystalyse analyse-provenance` | Stable | Analyse provenance data from previous sessions |
| `crystalyse user-stats` | Stable | Display user learning statistics and preferences |
| `crystalyse resume` | Stable | Resume previous session |
| `--mode creative/rigorous/adaptive` | Stable | Global mode flag |
| `--project` | Stable | Project name for workspace |
| `--model` | Stable | Override default language model |
| `--version` | Stable | Show version information |

## Package Structure Comparison

### PyPI v1.0.1 (Stable)
- **Files**: 86 Python files
- **Package Name**: `crystalyse` on PyPI
- **Version Display**: "CrystaLyse.AI 2.0" (note: still shows old version string in CLI)
- **Status**: Production/Stable in PyPI classifiers
- **Unique Feature**: `phase_diagram_downloader.py` for automatic Materials Project data download

### Development v1.0.0-dev
- **Files**: 85 Python files (missing phase diagram downloader)
- **Package Name**: Not published (development only)
- **Version Display**: "CrystaLyse.AI v1.0.0-dev"
- **Status**: Development branch
- **Differences**: Slightly older, missing auto-downloader feature

## Architecture Components

All architectural components are present in both versions:

**Agent Layer**
- `openai_agents_bridge.py` - Main agent implementation
- `mode_injector.py` - Global mode management
- `tool_wrappers.py` - OpenAI SDK to MCP bridges

**Memory Layer**
- `crystalyse_memory.py` - Unified memory interface
- Session, discovery, user, and cross-session storage
- SQLite and JSON file-based persistence

**Infrastructure Layer**
- `session_manager.py` - Long-lived session management
- `mcp_connection_pool.py` - Connection pooling
- `resilient_tool_caller.py` - Fault-tolerant tool invocation

**UI Layer**
- `chat_ui.py` - Rich-based interactive chat
- `enhanced_clarification.py` - Adaptive questioning
- `trace_handler.py` - Real-time progress tracking
- `provenance_bridge.py` - Computational honesty UI integration

**Provenance Layer** (Always enabled)
- `artifact_tracker.py` - File/structure tracking
- `render_gate.py` - Anti-hallucination gate
- `value_registry.py` - Registry of computed values

**Tool Implementations**
- `tools/chemeleon/` - Structure prediction with checkpoint manager
- `tools/mace/` - Energy calculations
- `tools/smact/` - Composition validation
- `tools/pymatgen/` - Materials analysis
- `tools/visualization/` - 3D rendering and plotting

## MCP Servers

All three MCP servers are included in both versions:

1. **Chemistry Creative Server**
   - Version: 0.1.0
   - Tools: Chemeleon + MACE + basic visualisation
   - Mode: Fast exploration (~50s)

2. **Chemistry Unified Server**
   - Version: 0.1.0
   - Tools: SMACT + Chemeleon + MACE + PyMatgen + advanced analysis
   - Mode: Complete validation (2-5min)
   - Endpoints: 20 MCP tools

3. **Visualisation Server**
   - Version: 0.1.0
   - Tools: 3D visualisation (3Dmol.js), plots (pymatviz), CIF generation

## Conclusion

**The distinction between stable and experimental is minimal.** The PyPI v1.0.1 release is feature-complete with all advanced capabilities documented in the paper and CLAUDE.md.

Key observations:
- All analysis modes are production-ready
- Complete provenance system is stable
- Advanced memory and adaptive clarification are included
- Session management and UI enhancements are stable
- MCP connection pooling is production-ready

The development branch (v1.0.0-dev) should be marketed as:
- Ongoing refinements and bug fixes
- Preparation for future v1.1+ features
- Testing ground for enhancements before PyPI release

Not as a separate feature-rich experimental version, since nearly everything is already in stable.

---

**Last Updated**: 2025-12-01
**PyPI Version**: 1.0.1
**Development Version**: 1.0.0-dev
