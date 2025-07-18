# CrystaLyse.AI Development Guide

## Language Preferences
- **Always use British English** in all code, comments, documentation, and communication
- Common conversions:
  - -ize → -ise (analyse, optimise, synthesise, visualise, etc.)
  - -or → -our (colour, behaviour, favour, etc.)
  - -er → -re (centre, metre, fibre, etc.)
  - -og → -ogue (dialogue, catalogue, etc.)
  - license → licence (as a noun)
  - gray → grey
  - defense → defence

## Code Style
- **No emojis** in any code, comments, or documentation
- Keep code professional and clean
- Use clear, descriptive variable and function names in British English

## Project-Specific Commands

### Testing
When completing tasks, run these commands to ensure code quality:
```bash
# Python linting
ruff check .

# Python type checking  
mypy .

# Run tests
python -m pytest
python test_session_system.py  # Session-based functionality tests
```

### Development Setup
```bash
# Activate conda environment
conda activate crystalyse

# Install in development mode
pip install -e .

# Install MCP servers
pip install -e ./chemistry-unified-server
pip install -e ./chemistry-creative-server
pip install -e ./visualization-mcp-server

# Old individual servers (deprecated, moved to oldmcpservers/)
# pip install -e ./oldmcpservers/smact-mcp-server
# pip install -e ./oldmcpservers/chemeleon-mcp-server
# pip install -e ./oldmcpservers/mace-mcp-server
```

## Project Structure

### Core Components
- `crystalyse/` - Main package with agents, infrastructure, prompts
- `crystalyse/agents/` - Agent implementations (crystalyse_agent.py, session_based_agent.py)
- `crystalyse/memory/` - New simplified memory system
- `crystalyse/infrastructure/` - Connection pooling, session management
- `crystalyse/output/` - Dual formatter, universal CIF visualiser
- `crystalyse/converters.py` - CIF to MACE conversion utilities

### MCP Servers (Active)
- `chemistry-unified-server/` - Unified server for rigorous mode (SMACT + Chemeleon + MACE)
- `chemistry-creative-server/` - Fast exploration without SMACT validation
- `visualization-mcp-server/` - Advanced 3D visualisations and analysis

### Important Files
- `crystalyse/agents/session_based_agent.py` - Session-based agent with conversation persistence
- `crystalyse/cli.py` - Enhanced CLI with session management commands
- `crystalyse/memory/memory_tools.py` - 8 memory tools for OpenAI Agents SDK
- `crystalyse/config.py` - Configuration management
- `crystalyse/validation/response_validator.py` - Anti-hallucination system

## Current Project Status (July 2025)

### What Works ✅
- **Session-based chat agent** with SQLite conversation persistence
- **Complete discovery pipeline**: SMACT → Chemeleon → MACE
- **Memory system**: Simple file-based approach (JSON/Markdown)
- **Visualisation server**: 3D molecular views and analysis plots
- **CLI commands**: `analyse`, `chat`, `resume`, `sessions`, `demo`
- **Dual output**: JSON + Markdown with visualisations
- **Anti-hallucination**: 100% computational honesty maintained

### Recent Fixes ✅
- **MACE Interface Fix**: Properly extract mace_input from converter output
- **Import Path Fix**: Correct visualisation server imports
- **Coordinate Array Fix**: Prevent flattening of 3D coordinate arrays in JSON
- **Session Management**: Added missing `_run_chat_session_sync` function

### Development Priorities
1. Expand test coverage for session-based workflows
2. Optimise memory system performance for large discovery sets
3. Add batch processing capabilities
4. Enhance visualisation features with VESTA integration
5. Implement cross-session learning and pattern recognition

## Project Standards

### Scientific Integrity (Non-Negotiable)
- Every numerical result must trace back to actual tool calls
- No fabricated energies, structures, or properties
- Clear distinction between AI reasoning and computational validation
- Transparent tool failure reporting

### Code Quality
- Follow the vision and standards outlined in `VISION.md`
- Maintain computational honesty at all times
- Use proper error handling and graceful degradation
- Write clear, maintainable code with British English

### Documentation
- Be honest about current capabilities and limitations
- Document what actually works, not aspirational features
- Keep README.md and STATUS.md up to date with reality
- Remove any misleading or inflated claims

## Working with CrystaLyse.AI

### Memory System Architecture
The new memory system follows a simple file-based approach:
1. **Session Memory**: In-memory conversation context
2. **Discovery Cache**: JSON files for computational results
3. **User Memory**: Markdown files for preferences/notes
4. **Cross-Session Context**: Auto-generated weekly summaries

### Session Management
- Sessions are stored in SQLite database (`crystalyse_sessions.db`)
- Each session maintains conversation history and context
- Use `crystalyse chat -u <user> -s <session>` to start/resume
- Sessions can be listed with `crystalyse sessions -u <user>`

### CLI Usage Examples
```bash
# One-time analysis
crystalyse analyse "Find a lead-free perovskite" --model o3

# Start a new chat session
crystalyse chat -u researcher1 -s project_solar -m rigorous

# Resume existing session
crystalyse resume project_solar -u researcher1

# Demo session
crystalyse demo
```

### Testing Strategy
- Run `python test_session_system.py` for session tests
- Test individual MCP servers with simple queries first
- Verify complete workflows: composition → structure → energy
- Check memory persistence across sessions

## Important Reminders

1. **Session-based development** - Use sessions for multi-turn research
2. **Memory integration** - Leverage the memory tools for context
3. **Test with sessions** - Verify persistence and context retention
4. **Use British English** - Consistent language throughout
5. **Maintain scientific integrity** - Never fabricate computational results
6. **Follow the vision** - Refer to `VISION.md` for guidance

The project has evolved from proof-of-concept to a functional research platform with session management and persistent memory.