# CLI Reference

Complete command-line interface reference for CrystaLyse.AI.

## Overview

CrystaLyse.AI provides a unified command-line interface with multiple commands for different workflows:

- **Analysis Commands**: Direct materials analysis and evaluation
- **Session Commands**: Interactive conversation management
- **Configuration Commands**: System setup and customisation
- **Utility Commands**: Demonstrations and system information

## Command Structure

```bash
crystalyse [GLOBAL_OPTIONS] COMMAND [COMMAND_OPTIONS] [ARGUMENTS]
```

### Global Options

Available for all commands:

| Option | Description |
|--------|-------------|
| `-h, --help` | Show help message and exit |
| `--version` | Display version information |
| `--verbose, -v` | Enable verbose logging |
| `--config PATH` | Use custom configuration file |

## Commands Overview

### Analysis Commands

#### [`crystalyse analyse`](analyse.md)
Run one-shot materials analysis with immediate results.

```bash
crystalyse analyse QUERY [OPTIONS]
```

**Key Options**:
- `--mode {creative,rigorous}` - Analysis mode selection
- `--user-id USER` - User identification for caching
- `--verbose, -v` - Detailed output

**Examples**:
```bash
crystalyse analyse "Find battery cathode materials" --mode creative
crystalyse analyse "Analyse LiCoO2 stability" --mode rigorous
```

### Session Commands

#### [`crystalyse chat`](chat.md)
Start interactive session-based conversation.

```bash
crystalyse chat [OPTIONS]
```

**Key Options**:
- `--user-id, -u USER` - User identifier
- `--session-id, -s ID` - Session identifier
- `--mode, -m {creative,rigorous}` - Analysis mode

**Examples**:
```bash
crystalyse chat -u researcher -s battery_project -m rigorous
crystalyse chat -u student -m creative
```

#### [`crystalyse resume`](resume.md)
Resume a previous session with full context.

```bash
crystalyse resume SESSION_ID [OPTIONS]
```

**Key Options**:
- `--user-id, -u USER` - User identifier
- `--mode, -m {creative,rigorous}` - Override mode

**Examples**:
```bash
crystalyse resume battery_project -u researcher
crystalyse resume solar_study -u scientist -m rigorous
```

#### [`crystalyse sessions`](sessions.md)
List and manage user sessions.

```bash
crystalyse sessions [OPTIONS]
```

**Key Options**:
- `--user-id, -u USER` - Filter by user

**Examples**:
```bash
crystalyse sessions -u researcher
crystalyse sessions  # Default user
```

### Interactive Interface

#### [`crystalyse`](unified.md) (Unified Interface)
Launch unified interface with real-time mode switching.

```bash
crystalyse
```

**In-Session Commands**:
- `/mode creative` - Switch to creative mode
- `/mode rigorous` - Switch to rigorous mode
- `/agent chat` - Switch to chat agent
- `/agent analyse` - Switch to analysis agent
- `/help` - Show available commands
- `/clear` - Clear screen
- `/exit` - Exit interface

### Configuration Commands

#### [`crystalyse config`](config.md)
View and manage system configuration.

```bash
crystalyse config SUBCOMMAND [OPTIONS]
```

**Subcommands**:
- `show` - Display current configuration
- `path` - Show configuration file location

**Examples**:
```bash
crystalyse config show
crystalyse config path
```

### Utility Commands

#### [`crystalyse demo`](demo.md)
Run demonstration workflow.

```bash
crystalyse demo [OPTIONS]
```

**Key Options**:
- `--user-id, -u USER` - User for demo session

**Examples**:
```bash
crystalyse demo
crystalyse demo -u demo_user
```

#### [`crystalyse examples`](examples.md)
Show example queries and workflows.

```bash
crystalyse examples
```

#### [`crystalyse dashboard`](dashboard.md)
Display live system status.

```bash
crystalyse dashboard
```

## Command Categories

### By Workflow Type

**Quick Analysis**:
```bash
crystalyse analyse "query" --mode creative    # Fast results
```

**Research Sessions**:
```bash
crystalyse chat -u researcher -s project      # Interactive research
crystalyse resume project -u researcher       # Continue research
```

**System Management**:
```bash
crystalyse config show                        # Check configuration
crystalyse sessions -u researcher             # Manage sessions
```

### By Analysis Mode

**Creative Mode** (Fast exploration):
```bash
crystalyse analyse "query" --mode creative
crystalyse chat -m creative
```

**Rigorous Mode** (Complete validation):
```bash
crystalyse analyse "query" --mode rigorous
crystalyse chat -m rigorous
```

## Exit Codes

CrystaLyse.AI uses standard exit codes:

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | General error |
| 2 | Invalid command or arguments |
| 3 | Configuration error |
| 4 | API connection error |
| 5 | MCP server error |
| 6 | Analysis timeout |

## Environment Variables

### Required
```bash
export OPENAI_API_KEY="sk-your-key-here"
```

### Optional
```bash
export CRYSTALYSE_MODEL="o4-mini"              # Default model
export CRYSTALYSE_MAX_TURNS="1000"             # Conversation limit
export CRYSTALYSE_DEBUG="true"                 # Debug mode
export CRYSTALYSE_STRUCTURE_SAMPLES="5"        # Structure samples
export CRYSTALYSE_MAX_CANDIDATES="100"         # Max candidates
```

## Common Usage Patterns

### Research Workflow
```bash
# 1. Start with creative exploration
crystalyse analyse "battery materials" --mode creative

# 2. Interactive refinement
crystalyse chat -u researcher -s battery_study -m creative

# 3. Detailed validation
crystalyse chat -u researcher -s battery_study -m rigorous

# 4. Review session history
crystalyse sessions -u researcher
```

### Batch Analysis
```bash
# Multiple one-shot analyses
crystalyse analyse "LiCoO2 cathode" --mode rigorous --user-id batch1
crystalyse analyse "LiFePO4 cathode" --mode rigorous --user-id batch1
crystalyse analyse "LiMn2O4 cathode" --mode rigorous --user-id batch1

# Review batch results
crystalyse sessions -u batch1
```

### Mode Switching
```bash
# Unified interface with mode switching
crystalyse
> /mode creative
> Find perovskite materials
> /mode rigorous
> Analyse the most stable candidate
> /exit
```

## Output Formats

### Analysis Results

**Creative Mode**:
- Structured terminal output with formation energies
- 3D visualisation files (`{formula}_3dmol.html`)
- Performance metrics

**Rigorous Mode**:
- Complete analysis pipeline output
- Professional PDF analysis plots
- CIF structure files
- 3D visualisation files

### Session Output

**Interactive Sessions**:
- Real-time conversation display
- Progress indicators
- Error messages with context
- Session management feedback

### Configuration Output

**Configuration Display**:
- Structured table format
- MCP server status
- Current settings overview

## Error Handling

### Common Error Scenarios

**API Key Missing**:
```bash
$ crystalyse analyse "test"
Error: OpenAI API key not found. Set OPENAI_API_KEY environment variable.
```

**Invalid Mode**:
```bash
$ crystalyse analyse "test" --mode invalid
Error: Invalid mode 'invalid'. Choose 'creative' or 'rigorous'.
```

**Session Not Found**:
```bash
$ crystalyse resume nonexistent -u user
Error: Session 'nonexistent' not found for user 'user'.
```

### Error Recovery

Most errors provide suggestions for resolution:
```bash
Error: MCP server connection failed
Suggestion: Check server status with 'crystalyse config show'
```

## Performance Tuning

### Environment Variables for Performance
```bash
export CRYSTALYSE_STRUCTURE_SAMPLES="3"        # Faster generation
export CRYSTALYSE_MAX_CANDIDATES="50"          # Reduced candidates
export CRYSTALYSE_BATCH_SIZE="5"               # Smaller batches
```

### GPU Acceleration
```bash
# MACE automatically uses GPU if available
nvidia-smi  # Check GPU status
```

## Debugging

### Verbose Output
```bash
crystalyse --verbose analyse "query"
crystalyse -v chat -u user
```

### Debug Environment
```bash
export CRYSTALYSE_DEBUG="true"
crystalyse analyse "query"
```

## Integration Examples

### Shell Scripting
```bash
#!/bin/bash
export OPENAI_API_KEY="sk-..."

materials=("LiCoO2" "LiFePO4" "LiMn2O4")
for material in "${materials[@]}"; do
    crystalyse analyse "Analyse $material cathode" --mode rigorous
done
```

### Python Integration
```python
import subprocess

def analyse_material(formula, mode="creative"):
    cmd = ["crystalyse", "analyse", f"Analyse {formula}", "--mode", mode]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.stdout
```

## See Also

- [Installation Guide](../../guides/installation.md) - Setup and configuration
- [CLI Usage Guide](../../guides/cli_usage.md) - Comprehensive examples
- [Configuration Reference](../config/index.md) - Configuration options
- [Error Reference](../errors/index.md) - Error codes and troubleshooting