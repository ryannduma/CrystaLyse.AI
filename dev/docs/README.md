# CrystaLyse.AI Documentation

Welcome to the comprehensive documentation for CrystaLyse.AI v1.0.0.

## Documentation Structure

### Architecture
- **[System Overview](architecture/overview.md)** - Complete system architecture and design

### Core Concepts
- **[CLI Architecture](concepts/cli_architecture.md)** - Command-line interface design and entry points
- **[Analysis Modes](concepts/analysis_modes.md)** - Adaptive, creative, and rigorous analysis modes
- **[Autonomous Mode Switching](concepts/autonomous_mode_switching.md)** - Dynamic mode adaptation system
- **[Clarification System](concepts/clarification_system.md)** - Expertise-aware adaptive questioning
- **[Agents](concepts/agents.md)** - Enhanced agent system and coordination
- **[Memory](concepts/memory.md)** - Memory architecture and persistence
- **[Sessions](concepts/sessions.md)** - Session-based research workflows
- **[Tools](concepts/tools.md)** - Computational chemistry tool integration
- **[UI](concepts/ui.md)** - User interface components and experience

### Features
- **[Session Management](features/session-management.md)** - Persistent research workflows
- **[Memory System](features/memory-system.md)** - 4-layer caching and learning architecture

### Guides
- **[Installation](guides/installation.md)** - Complete installation instructions
- **[Quick Start](guides/quick-start.md)** - Get up and running quickly
- **[CLI Usage](guides/cli_usage.md)** - Comprehensive command-line usage guide
- **[Session-Based Usage](guides/session_based_usage.md)** - Multi-day research workflows

### Tools Documentation
- **[SMACT](tools/smact.md)** - Composition validation and screening
- **[Chemeleon](tools/chemeleon.md)** - AI-powered crystal structure prediction
- **[MACE](tools/mace.md)** - Machine learning force fields for energy calculations
- **[Visualisation](tools/visualisation.md)** - 3D structures and analysis plots

### API Reference
- **[CLI Reference](api/cli-reference.md)** - Complete command documentation
- **[CLI Commands](reference/cli/index.md)** - Detailed command reference
- **[Configuration](reference/config/index.md)** - Configuration options and settings
- **[Error Handling](reference/errors/index.md)** - Error codes and troubleshooting

### Quick References
- **[Index](index.md)** - Complete documentation index
- **[Quickstart](quickstart.md)** - Rapid getting started guide

## Getting Started

For new users, we recommend starting with the [Quick Start Guide](guides/quick-start.md) which covers:
- Installation and setup
- Basic usage patterns
- Example workflows
- Troubleshooting tips

## Key Concepts

### Enhanced Agent Architecture
CrystaLyse.AI features a single `EnhancedCrystaLyseAgent` that provides intelligent tool coordination, dynamic mode switching, and adaptive clarification through the OpenAI Agents SDK.

### Three-Mode Analysis System
- **Adaptive Mode** (Default) - Enhanced clarification with context-aware tool selection
- **Creative Mode** - Fast exploration (~50 seconds) with transparent operations
- **Rigorous Mode** - Complete validation (2-5 minutes) with comprehensive analysis

### Autonomous Mode Switching
The system switches between analysis modes based on user feedback, performance monitoring, and query context analysis, creating a responsive research experience.

### Adaptive Clarification System
Expertise-aware questioning that detects user knowledge level and adapts clarification strategies, learning from interaction patterns.

### Memory & Session Management
The 4-layer memory architecture with persistent SQLite-based sessions provides:
1. **Session Memory** - Current conversation context
2. **Discovery Cache** - Computational result caching
3. **User Memory** - Personal preferences and notes
4. **Cross-Session Context** - Research insights and patterns

## Scientific Integrity

Crystalyse maintains complete computational honesty through:
- **Tool Validation** - All results trace to actual computations
- **Anti-Hallucination System** - Prevents fabricated numerical claims
- **Uncertainty Quantification** - MACE committee model confidence
- **Error Transparency** - Clear reporting of computational failures

## Contributing to Documentation

Documentation improvements are welcome. Please:
1. Follow the existing structure and style
2. Use British English spelling consistently
3. Include practical examples where appropriate
4. Maintain focus on production usage patterns

## Support

For questions or issues:
- Check the [Quick Start Guide](guides/quick-start.md) for common solutions
- Review the [CLI Reference](api/cli-reference.md) for command details
- Consult the [Architecture Overview](architecture/overview.md) for system understanding
- Open an issue for bugs or feature requests

---

**Version**: 1.0.0-dev
**PyPI Stable**: 1.0.1
