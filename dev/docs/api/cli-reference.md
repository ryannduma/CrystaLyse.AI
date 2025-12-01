# CLI Reference - CrystaLyse.AI v1.0.0

## Command Overview

```bash
crystalyse [GLOBAL_OPTIONS] COMMAND [COMMAND_OPTIONS]
```

## Global Options

- `--project, -p`: Project name for workspace (default: crystalyse_session)
- `--mode`: Agent operating mode (adaptive, creative, rigorous) (default: adaptive)
- `--model`: Language model to use (default: None - auto-select)
- `--version`: Show version and exit
- `--verbose, -v`: Enable verbose output
- `--help`: Show help message and exit

## Commands

### `discover`
Run a single, non-interactive discovery query. Ideal for scripting.

```bash
crystalyse discover [QUERY] [OPTIONS]
```

**Arguments:**
- `QUERY`: Natural language materials query (required)

**Examples:**
```bash
crystalyse discover "Find perovskites for solar cells" --mode rigorous
crystalyse discover "Battery cathode materials" --project battery_research
```

### `chat`
Start an interactive chat session for materials discovery.

```bash
crystalyse chat [OPTIONS]
```

**Options:**
- `--user, -u`: User ID for personalized experience (default: default)
- `--session, -s`: Session name for organization (default: None)

**Features:**
- Adaptive clarification based on expertise level
- Cross-session learning and personalization
- Mode switching and smart defaults

**Examples:**
```bash
crystalyse chat --user alice --session battery_project
crystalyse chat  # Quick start with defaults
```

### `user-stats`
Display learning statistics and preferences for a user.

```bash
crystalyse user-stats [OPTIONS]
```

**Options:**
- `--user, -u`: User ID to show stats for (default: default)

**Example:**
```bash
crystalyse user-stats --user alice
crystalyse analyse "High-entropy alloys" --mode rigorous --timeout 600
```

### `chat`
Start interactive research session.

```bash
crystalyse chat [OPTIONS]
```

**Options:**
- `--user, -u`: User ID (required for session management)
- `--session, -s`: Session ID (creates new if doesn't exist)
- `--mode, -m`: Analysis mode (creative, rigorous, adaptive)
- `--model`: Model to use (default: gpt-4o)

**Examples:**
```bash
crystalyse chat -u researcher1 -s battery_project
crystalyse chat -u alice -s solar_cells -m rigorous
crystalyse chat -u bob --session catalyst_design --mode creative
```

### `resume`
Resume existing session.

```bash
crystalyse resume [SESSION_ID] [OPTIONS]
```

**Arguments:**
- `SESSION_ID`: Session to resume (required)

**Options:**  
- `--user, -u`: User ID (required)

**Examples:**
```bash
crystalyse resume battery_project -u researcher1
crystalyse resume my_session --user alice
```

### `sessions`  
List user sessions.

```bash
crystalyse sessions [OPTIONS]
```

**Options:**
- `--user, -u`: User ID (required)
- `--verbose, -v`: Show detailed session information

**Examples:**
```bash
crystalyse sessions -u researcher1
crystalyse sessions --user alice --verbose
```

### `demo`
Run demonstration session.

```bash
crystalyse demo [OPTIONS]
```

**Options:**
- `--mode, -m`: Analysis mode (default: rigorous)
- `--quick`: Run abbreviated demo

**Examples:**
```bash
crystalyse demo
crystalyse demo --mode creative --quick
```

### `status`
Check system health.

```bash
crystalyse status [OPTIONS]
```

**Options:**
- `--verbose, -v`: Detailed health information
- `--servers`: Check MCP server status

**Examples:**
```bash
crystalyse status
crystalyse status --verbose --servers
```

## In-Session Commands

When in an interactive chat session, these commands are available:

### `/history`
Display conversation history.
```bash
/history [--limit 10]
```

### `/clear`  
Clear current conversation context.
```bash
/clear [--confirm]
```

### `/undo`
Remove last interaction from conversation.
```bash
/undo
```

### `/sessions`
List all sessions for current user.
```bash
/sessions
```

### `/switch`
Switch analysis mode mid-session.
```bash
/switch creative
/switch rigorous  
/switch adaptive
```

### `/save`
Save important information to memory.
```bash
/save "LiCoO2 formation energy: -2.45 eV"
/save "Need to explore Ni substitution" --section "Research Notes"
```

### `/search`
Search memory and previous discoveries.
```bash
/search "formation energy"
/search "perovskite solar"
```

### `/help`
Show available commands and usage.
```bash
/help
/help save  # Help for specific command
```

### `/exit`
Save session and exit.
```bash
/exit
```

## Configuration

### Environment Variables
- `OPENAI_API_KEY`: OpenAI API key (required)
- `CRYSTALYSE_USER`: Default user ID
- `CRYSTALYSE_MODE`: Default analysis mode
- `CRYSTALYSE_MODEL`: Default model
- `CRYSTALYSE_TIMEOUT`: Default timeout in seconds

### Config File
Location: `~/.crystalyse/config.json`

```json
{
  "default_user": "researcher1",
  "default_mode": "adaptive", 
  "default_model": "gpt-4o",
  "timeouts": {
    "creative": 120,
    "rigorous": 300,
    "adaptive": 180
  },
  "memory": {
    "max_cache_size": 1000,
    "cache_expiry_days": 30
  }
}
```

## Exit Codes

- `0`: Success
- `1`: General error
- `2`: Invalid arguments
- `3`: API authentication error
- `4`: Tool timeout error
- `5`: Server connection error

## Output Formats

### Standard Output
Human-readable formatted results with:
- Rich console formatting
- Progress indicators  
- Structured result presentation
- Error messages with context

### Dual Output Mode
When using `--dual-output`, generates:
- `results.json`: Machine-readable structured data
- `results.md`: Human-readable Markdown report
- `visualizations/`: 3D molecular views and plots

### JSON Schema
```json
{
  "query": "string",
  "mode": "creative|rigorous|adaptive",
  "timestamp": "ISO-8601",
  "results": {
    "materials": [...],
    "validation": {...},
    "energies": {...},
    "visualizations": [...]
  },
  "metadata": {
    "execution_time": "number",
    "tools_used": [...],
    "confidence": "number"
  }
}
```