# CLI Usage Guide

Complete guide to using CrystaLyse.AI from the command line. This covers all available commands, options, and advanced usage patterns.

## Overview

CrystaLyse.AI provides three ways to interact with the system:

1. **Unified Interface**: `crystalyse` - Interactive mode with in-session switching
2. **Direct Commands**: `crystalyse analyse`, `crystalyse chat` - Specific operations
3. **Session Management**: `crystalyse resume`, `crystalyse sessions` - Persistent workflows

## Command Structure

```bash
crystalyse [GLOBAL_OPTIONS] COMMAND [COMMAND_OPTIONS] [ARGUMENTS]
```

### Global Options

```bash
-h, --help     Show help message
--version      Show version information
--verbose, -v  Enable verbose logging
--config PATH  Use custom configuration file
```

## Core Commands

### `crystalyse` (Unified Interface)

Launch the interactive unified interface with mode and agent switching capabilities.

```bash
crystalyse
```

**Features:**
- Real-time mode switching (`/mode creative`, `/mode rigorous`)
- Agent switching (`/agent chat`, `/agent analyse`)
- Session persistence
- Clean, modern interface

**Available Commands in Session:**
```bash
/mode creative     # Switch to creative mode (fast)
/mode rigorous     # Switch to rigorous mode (complete)
/agent chat        # Switch to conversation mode
/agent analyse     # Switch to one-shot analysis mode
/help              # Show help
/clear             # Clear screen
/exit              # Exit interface
```

**Example Session:**
```bash
$ crystalyse
╭──────────────────────────────────────────────────────────────────────────────╮
│                 CrystaLyse.AI - Materials Discovery Platform                 │
│                 Research Preview v1.0.0 - AI-Powered Materials Design        │
╰──────────────────────────────────────────────────────────────────────────────╯

╭─────────────────────────────────────────────────────────────────────────╮
│ Mode: Creative | Agent: Chat | User: default                           │
╰─────────────────────────────────────────────────────────────────────────╯

➤ Find perovskites for solar cells
[Analysis results...]

➤ /mode rigorous
✅ Mode switched to Rigorous

➤ Analyse the most stable candidate in detail
[Detailed analysis results...]
```

### `crystalyse analyse`

Run one-shot materials analysis with immediate results.

```bash
crystalyse analyse QUERY [OPTIONS]
```

**Options:**
```bash
--mode MODE           Analysis mode: creative, rigorous (default: creative)
--user-id USER        User ID for memory and caching (default: cli_user)
--verbose, -v         Enable verbose output and logging
```

**Examples:**

```bash
# Basic analysis
crystalyse analyse "Find battery cathode materials"

# Rigorous analysis
crystalyse analyse "Analyse LiCoO2 stability" --mode rigorous

# With specific user
crystalyse analyse "Design superconductors" --user-id researcher1

# Verbose output
crystalyse analyse "Screen perovskites" --verbose
```

**Expected Output:**
```bash
$ crystalyse analyse "Find perovskite solar cell materials" --mode creative

╭──────────────────────────────────────────────────────────────────────────────╮
│                 CrystaLyse.AI - Materials Discovery Platform                 │
│                 Research Preview v1.0.0 - AI-Powered Materials Design        │
╰──────────────────────────────────────────────────────────────────────────────╯

╭───────────────────────────────╮
│ ✅ Analysis Complete          │
│ Completed in 50.3s            │
╰───────────────────────────────╯

╭───────────────────────────── Discovery Results ──────────────────────────────╮
│ Generated 5 perovskite candidates with formation energies:                   │
│                                                                              │
│ 1. CsGeI₃ - Formation energy: -2.558 eV/atom (most stable)                  │
│ 2. CsPbI₃ - Formation energy: -2.542 eV/atom                                │
│ 3. CsSnI₃ - Formation energy: -2.529 eV/atom                                │
│ 4. RbPbI₃ - Formation energy: -2.503 eV/atom                                │
│ 5. RbSnI₃ - Formation energy: -2.488 eV/atom                                │
│                                                                              │
│ 3D visualisations created: CsGeI3_3dmol.html, CsPbI3_3dmol.html             │
╰──────────────────────────────────────────────────────────────────────────────╯

╭──────────────────────────── Performance Metrics ─────────────────────────────╮
│   Time               50.2s                                                   │
│   Tool Calls         1                                                       │
│   Model              o4-mini                                                 │
│   Mode               creative                                                │
╰──────────────────────────────────────────────────────────────────────────────╯
```

### `crystalyse chat`

Start interactive session-based chat with persistent memory.

```bash
crystalyse chat [OPTIONS]
```

**Options:**
```bash
--user-id, -u USER       User ID for memory system (default: default)
--session-id, -s ID      Session ID (auto-generated if not provided)
--mode, -m MODE          Analysis mode: creative, rigorous (default: creative)
--verbose, -v            Enable verbose logging
```

**Examples:**

```bash
# Start new chat session
crystalyse chat -u researcher1 -s battery_study -m creative

# Auto-generated session ID
crystalyse chat -u materials_scientist -m rigorous

# Simple chat
crystalyse chat
```

**In-Session Commands:**
```bash
/history              # Show conversation history
/clear                # Clear conversation history
/undo                 # Remove last interaction
/sessions             # List all sessions for user
/resume <session_id>  # Instructions to resume another session
/help                 # Show session help
/exit                 # Exit chat
```

**Example Session:**
```bash
$ crystalyse chat -u researcher -s solar_study -m creative

╭──────────────────────────────────────────────────────────────────────────────╮
│                🔬 CrystaLyse.AI - Session-Based Chat                         │
│                                                                              │
│ User: researcher                                                             │
│ Session: solar_study                                                         │
│ Mode: Creative                                                               │
│                                                                              │
│ Key Features:                                                                │
│ ✅ Automatic conversation history                                            │
│ ✅ Persistent memory across sessions                                         │
│ ✅ Multi-turn context understanding                                          │
│ ✅ Computational validation with live tools                                  │
╰──────────────────────────────────────────────────────────────────────────────╯

🔬 You: Analyse perovskite stability for photovoltaics

[Agent processes with Chemeleon + MACE...]

╭─────────────────────── 🔬 CrystaLyse Response ────────────────────────╮
│ I've analysed several perovskite compositions for photovoltaic        │
│ applications. Here are the key findings:                              │
│                                                                        │
│ Most Stable Candidates:                                                │
│ 1. CsGeI₃: -2.558 eV/atom (excellent stability)                       │
│ 2. CsPbI₃: -2.542 eV/atom (good alternative)                          │
│                                                                        │
│ 3D visualisations saved for detailed inspection.                      │
╰────────────────────────────────────────────────────────────────────────╯

🔬 You: What about band gaps for these materials?

╭─────────────────────── 🔬 CrystaLyse Response ────────────────────────╮
│ Based on the structures I generated for CsGeI₃ and CsPbI₃:            │
│                                                                        │
│ Band Gap Estimates (from structural analysis):                        │
│ - CsGeI₃: ~1.6 eV (excellent for single-junction solar cells)         │
│ - CsPbI₃: ~1.5 eV (good for photovoltaics)                           │
│                                                                        │
│ These are preliminary estimates. For precise values, consider          │
│ DFT calculations with hybrid functionals.                             │
╰────────────────────────────────────────────────────────────────────────╯

🔬 You: /exit
✅ Session ended successfully
```

### `crystalyse resume`

Resume a previous session with full context restoration.

```bash
crystalyse resume SESSION_ID [OPTIONS]
```

**Options:**
```bash
--user-id, -u USER    User ID (default: default)  
--mode, -m MODE       Analysis mode (default: creative)
```

**Examples:**

```bash
# Resume specific session
crystalyse resume battery_study -u researcher1

# Resume with mode override
crystalyse resume solar_project -u scientist -m rigorous
```

### `crystalyse sessions`

List and manage user sessions.

```bash
crystalyse sessions [OPTIONS]
```

**Options:**
```bash
--user-id, -u USER    User ID to list sessions for (default: default)
```

**Example:**
```bash
$ crystalyse sessions -u researcher1

┏━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Session ID              ┃ Messages ┃ Last Activity              ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ battery_study           │ 15       │ 2025-01-15 14:30:25       │
│ solar_project           │ 8        │ 2025-01-15 09:15:43       │
│ superconductor_research │ 22       │ 2025-01-14 16:45:12       │
└─────────────────────────┴──────────┴─────────────────────────────┘
```

## Utility Commands

### `crystalyse demo`

Run a demonstration showing session-based capabilities.

```bash
crystalyse demo [OPTIONS]
```

**Options:**
```bash
--user-id, -u USER    User ID for demo (default: demo_user)
```

### `crystalyse examples`

Show example queries and workflow patterns.

```bash
crystalyse examples
```

### `crystalyse config`

View and manage configuration.

```bash
crystalyse config SUBCOMMAND
```

**Subcommands:**
```bash
show    # Display current configuration
path    # Show configuration file location
```

**Example:**
```bash
$ crystalyse config show

   CrystaLyse.AI Runtime   
       Configuration       
┏━━━━━━━━━━━━━━━┳━━━━━━━━━┓
┃ Setting       ┃ Value   ┃
┡━━━━━━━━━━━━━━━╇━━━━━━━━━┩
│ Default Model │ o4-mini │
│ Max Turns     │ 1000    │
└───────────────┴─────────┘

╭───────────────────────── MCP Server Configurations ──────────────────────────╮
│ {                                                                            │
│   "chemistry_unified": {                                                     │
│     "command": "python",                                                     │
│     "args": ["-m", "chemistry_unified.server"],                             │
│     "cwd": "/path/to/chemistry-unified-server/src"                          │
│   },                                                                         │
│   "chemistry_creative": {                                                    │
│     "command": "python",                                                     │
│     "args": ["-m", "chemistry_creative.server"],                            │
│     "cwd": "/path/to/chemistry-creative-server/src"                         │
│   }                                                                          │
│ }                                                                            │
╰──────────────────────────────────────────────────────────────────────────────╯
```

### `crystalyse dashboard`

Display live system status dashboard.

```bash
crystalyse dashboard
```

## Advanced Usage

### Environment Variables

Control CrystaLyse.AI behaviour with environment variables:

```bash
# API Configuration
export OPENAI_API_KEY="sk-..."
export CRYSTALYSE_MODEL="o4-mini"          # Default model
export CRYSTALYSE_MAX_TURNS="1000"         # Conversation limit

# MCP Server Configuration  
export CHEMISTRY_MCP_PATH="/custom/path"   # Custom server paths
export CRYSTALYSE_DEBUG="true"             # Debug mode

# Performance Tuning
export CRYSTALYSE_BATCH_SIZE="10"          # Batch processing size
export CRYSTALYSE_MAX_CANDIDATES="100"     # Structure candidates
export CRYSTALYSE_STRUCTURE_SAMPLES="5"    # Samples per composition
```

### Configuration File

Create `~/.crystalyse/config.yaml` for persistent settings:

```yaml
# Model configuration
default_model: "o4-mini"
max_turns: 1000

# Performance settings
parallel_batch_size: 10
max_candidates: 100
structure_samples: 5

# MCP server overrides
mcp_servers:
  chemistry_unified:
    command: "python"
    args: ["-m", "chemistry_unified.server"]
    cwd: "/custom/path/chemistry-unified-server/src"

# Logging
debug_mode: false
enable_metrics: true
```

### Batch Processing

Process multiple queries efficiently:

```bash
# Create query file
echo "Find battery cathode materials" > queries.txt
echo "Design superconductor materials" >> queries.txt
echo "Analyse perovskite stability" >> queries.txt

# Process in batch (planned feature)
crystalyse batch analyse queries.txt --mode creative
```

### Integration with Workflows

#### Shell Scripting

```bash
#!/bin/bash
# Automated materials screening

# Set environment
export OPENAI_API_KEY="sk-..."

# Screen multiple compositions
for material in "LiCoO2" "LiFePO4" "LiMn2O4"; do
    echo "Analysing $material..."
    crystalyse analyse "Analyse $material cathode properties" \
        --mode rigorous \
        --user-id battery_screening
done

# Summarise results
crystalyse sessions -u battery_screening
```

#### Python Integration

```python
import subprocess
import json

def analyse_material(formula, mode="creative"):
    """Analyse material using CrystaLyse.AI CLI."""
    cmd = [
        "crystalyse", "analyse", 
        f"Analyse {formula} properties",
        "--mode", mode
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.stdout

# Use in research pipeline
materials = ["CsSnI3", "CsPbI3", "CsGeI3"]
for material in materials:
    analysis = analyse_material(material, mode="rigorous")
    print(f"Analysis of {material}:")
    print(analysis)
```

## Troubleshooting

### Common Issues

#### 1. Command Not Found
```bash
$ crystalyse: command not found

# Solution: Check installation
pip install -e .
# or
pip install crystalyse-ai
```

#### 2. API Key Errors
```bash
$ Error: OpenAI API key not found

# Solution: Set environment variable
export OPENAI_API_KEY="sk-your-key-here"

# Or check current setting
echo $OPENAI_API_KEY
```

#### 3. MCP Server Connection Errors
```bash
$ Error: Chemistry server connection failed

# Solution: Check server status
crystalyse config show

# Look for server availability status
# Restart if needed (servers auto-restart)
```

#### 4. Session Database Issues
```bash
$ Error: Cannot access session database

# Solution: Check permissions
ls -la ~/.crystalyse/conversations.db

# Reset if corrupted
rm ~/.crystalyse/conversations.db
crystalyse chat  # Creates new database
```

#### 5. Memory/Performance Issues
```bash
# Reduce resource usage
export CRYSTALYSE_STRUCTURE_SAMPLES="3"  # Fewer samples
export CRYSTALYSE_MAX_CANDIDATES="50"    # Fewer candidates

# Use creative mode for faster processing
crystalyse analyse "query" --mode creative
```

### Debug Mode

Enable detailed logging for troubleshooting:

```bash
# Verbose output
crystalyse --verbose analyse "your query"

# Debug environment variable
export CRYSTALYSE_DEBUG="true"
crystalyse analyse "your query"

# Check logs
tail -f ~/.crystalyse/debug.log
```

### Performance Optimisation

#### GPU Acceleration
```bash
# Check GPU availability
nvidia-smi

# MACE will automatically use GPU if available
# Monitor GPU usage during analysis
watch -n 1 nvidia-smi
```

#### Memory Management
```bash
# Monitor memory usage
htop

# Reduce batch sizes if memory limited
export CRYSTALYSE_BATCH_SIZE="5"
```

#### Disk Space
```bash
# Check disk usage
df -h

# Clean old visualisation files
find . -name "*_3dmol.html" -mtime +7 -delete
find . -name "*_analysis" -type d -mtime +7 -exec rm -rf {} +
```

## Best Practices

### Workflow Recommendations

1. **Start Simple**: Use creative mode for initial exploration
2. **Iterate**: Refine queries based on initial results
3. **Validate**: Use rigorous mode for final validation
4. **Document**: Use sessions to maintain research context
5. **Organise**: Use meaningful session and user IDs

### Query Optimisation

```bash
# Good: Specific, actionable queries
crystalyse analyse "Find stable perovskites with band gaps 1.2-1.6 eV"

# Better: Include context and constraints
crystalyse analyse "Design lead-free perovskite solar cell materials with good stability and band gaps suitable for single-junction cells"

# Best: Specify application requirements
crystalyse analyse "Find environmentally friendly perovskite alternatives to MAPbI3 for tandem solar cells, prioritising stability and efficiency"
```

### Session Management

```bash
# Use descriptive session names
crystalyse chat -s battery_cathode_screening_2025 -u researcher

# Organise by project
crystalyse chat -s project_solar_perovskites -u team_lead
crystalyse chat -s project_battery_anodes -u team_lead

# Regular cleanup
crystalyse sessions -u researcher  # Review old sessions
```

This comprehensive CLI guide covers all aspects of using CrystaLyse.AI effectively from the command line. For programmatic usage, see the [API Reference](../reference/), and for specific tool details, check the [Tools Documentation](../tools/).