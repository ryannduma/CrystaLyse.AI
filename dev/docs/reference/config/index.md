# Configuration Reference

Complete reference for CrystaLyse.AI configuration options, environment variables, and system settings.

## Overview

CrystaLyse.AI can be configured through multiple mechanisms:

- **Environment Variables**: Runtime configuration and API keys
- **Configuration Files**: Persistent settings and preferences
- **Command-line Options**: Per-execution overrides
- **MCP Server Configuration**: Model Context Protocol server settings

## Environment Variables

### Required Variables

#### `OPENAI_API_KEY`
OpenAI API key for model access.

```bash
export OPENAI_API_KEY="sk-your-key-here"
```

**Format**: Must start with `sk-` followed by API key
**Required**: Yes
**Default**: None

### Optional Variables

#### Model Configuration

##### `CRYSTALYSE_MODEL`
Default model to use for analysis.

```bash
export CRYSTALYSE_MODEL="o4-mini"
```

**Options**: `o4-mini`, `o3`, `gpt-4o`, `gpt-4`
**Default**: `o4-mini`
**Recommendation**: `o4-mini` for creative mode, `o3` for rigorous mode

##### `CRYSTALYSE_MAX_TURNS`
Maximum conversation turns per session.

```bash
export CRYSTALYSE_MAX_TURNS="1000"
```

**Type**: Integer
**Default**: 1000
**Range**: 1-10000

#### Performance Configuration

##### `CRYSTALYSE_STRUCTURE_SAMPLES`
Number of structure samples to generate per composition.

```bash
export CRYSTALYSE_STRUCTURE_SAMPLES="5"
```

**Type**: Integer
**Default**: 5
**Range**: 1-20
**Impact**: Higher values = more thorough but slower

##### `CRYSTALYSE_MAX_CANDIDATES`
Maximum number of material candidates to consider.

```bash
export CRYSTALYSE_MAX_CANDIDATES="100"
```

**Type**: Integer
**Default**: 100
**Range**: 1-1000
**Impact**: Higher values = more comprehensive but slower

##### `CRYSTALYSE_BATCH_SIZE`
Batch size for parallel processing.

```bash
export CRYSTALYSE_BATCH_SIZE="10"
```

**Type**: Integer
**Default**: 10
**Range**: 1-50
**Impact**: Higher values = faster but more memory usage

#### Debugging and Development

##### `CRYSTALYSE_DEBUG`
Enable debug mode with detailed logging.

```bash
export CRYSTALYSE_DEBUG="true"
```

**Type**: Boolean (`true`/`false`)
**Default**: `false`
**Impact**: Detailed logs, slower execution

##### `CRYSTALYSE_VERBOSE`
Default verbosity level for commands.

```bash
export CRYSTALYSE_VERBOSE="true"
```

**Type**: Boolean (`true`/`false`)
**Default**: `false`

#### Storage and Caching

##### `CRYSTALYSE_CACHE_DIR`
Directory for caching computational results.

```bash
export CRYSTALYSE_CACHE_DIR="/custom/cache/path"
```

**Type**: Directory path
**Default**: `~/.crystalyse/cache`
**Impact**: Faster repeated analyses

##### `CRYSTALYSE_SESSION_DB`
Path to session database file.

```bash
export CRYSTALYSE_SESSION_DB="/custom/sessions.db"
```

**Type**: File path
**Default**: `~/.crystalyse/sessions.db`

## Configuration Files

### Default Configuration Location

CrystaLyse.AI looks for configuration in:
1. `./crystalyse.yaml` (current directory)
2. `~/.crystalyse/config.yaml` (user directory)
3. `/etc/crystalyse/config.yaml` (system-wide)

### Configuration File Format

```yaml
# ~/.crystalyse/config.yaml
model:
  name: "o4-mini"
  temperature: 0.7
  max_tokens: 4000
  timeout: 300

performance:
  structure_samples: 5
  max_candidates: 100
  batch_size: 10
  enable_gpu: true
  parallel_processing: true

analysis:
  default_mode: "creative"
  enable_caching: true
  cache_duration: 86400  # 24 hours

mcp_servers:
  chemistry_unified:
    command: "python"
    args: ["-m", "chemistry_unified.server"]
    cwd: "./chemistry-unified-server/src"
    env:
      PYTHONPATH: "./chemistry-unified-server/src"
  
  chemistry_creative:
    command: "python"
    args: ["-m", "chemistry_creative.server"]
    cwd: "./chemistry-creative-server/src"
    env:
      PYTHONPATH: "./chemistry-creative-server/src"
  
  visualization:
    command: "python"
    args: ["-m", "visualization_mcp.server"]
    cwd: "./visualization-mcp-server/src"
    env:
      PYTHONPATH: "./visualization-mcp-server/src"

logging:
  level: "INFO"
  file: "~/.crystalyse/crystalyse.log"
  max_size: "100MB"
  backup_count: 5

ui:
  theme: "professional"
  enable_colour: true
  progress_bars: true
  rich_output: true

memory:
  type: "file"
  location: "~/.crystalyse/memory"
  max_size: "1GB"
  cleanup_interval: 7  # days
```

## MCP Server Configuration

### Server Definitions

MCP servers are configured in the `mcp_servers` section:

#### Chemistry Unified Server
```yaml
mcp_servers:
  chemistry_unified:
    command: "python"
    args: ["-m", "chemistry_unified.server"]
    cwd: "./chemistry-unified-server/src"
    env:
      PYTHONPATH: "./chemistry-unified-server/src"
      SMACT_DATA_PATH: "./data/smact"
      MACE_MODEL_PATH: "./models/mace"
```

**Tools Provided**:
- SMACT composition validation (via oldmcpservers/smact-mcp-server)
- Chemeleon structure prediction (via oldmcpservers/chemeleon-mcp-server)
- MACE energy calculations (via oldmcpservers/mace-mcp-server)

**Dependencies**: Requires smact-mcp-server, chemeleon-mcp-server, mace-mcp-server to be installed

#### Chemistry Creative Server
```yaml
mcp_servers:
  chemistry_creative:
    command: "python"
    args: ["-m", "chemistry_creative.server"]
    cwd: "./chemistry-creative-server/src"
    env:
      PYTHONPATH: "./chemistry-creative-server/src"
      MACE_MODEL_PATH: "./models/mace"
```

**Tools Provided**:
- Chemeleon structure prediction (via oldmcpservers/chemeleon-mcp-server)
- MACE energy calculations (via oldmcpservers/mace-mcp-server)

**Dependencies**: Requires chemeleon-mcp-server, mace-mcp-server to be installed

#### Visualisation Server
```yaml
mcp_servers:
  visualization:
    command: "python"
    args: ["-m", "visualization_mcp.server"]
    cwd: "./visualization-mcp-server/src"
    env:
      PYTHONPATH: "./visualization-mcp-server/src"
      PYMATVIZ_CONFIG: "./config/pymatviz.yaml"
```

**Tools Provided**:
- 3dmol.js integration
- Pymatviz analysis plots

### Server Status

Check server configuration and status:

```bash
crystalyse config show
```

Expected output:
```
   CrystaLyse.AI Runtime   
       Configuration       
┏━━━━━━━━━━━━━━━┳━━━━━━━━━┓
┃ Setting       ┃ Value   ┃
┡━━━━━━━━━━━━━━━╇━━━━━━━━━┩
│ Default Model │ o4-mini │
│ Max Turns     │ 1000    │
└───────────────┴─────────┘

╭───────────────────────── MCP Server Configurations ──────────────────────────╮
│ chemistry_unified: ✅ Available                                               │
│ chemistry_creative: ✅ Available                                              │
│ visualization: ✅ Available                                                   │
╰────────────────────────────────────────────────────────────────────────────────╯
```

## Performance Configuration

### Memory Optimisation

For systems with limited RAM:

```yaml
performance:
  structure_samples: 3      # Reduced samples
  max_candidates: 50        # Fewer candidates
  batch_size: 5             # Smaller batches
  enable_gpu: false         # CPU-only mode
```

### Speed Optimisation

For faster execution:

```yaml
performance:
  structure_samples: 3      # Minimum samples
  batch_size: 20            # Larger batches
  enable_gpu: true          # GPU acceleration
  parallel_processing: true # Multi-core usage
```

### Quality Optimisation

For highest quality results:

```yaml
performance:
  structure_samples: 10     # More samples
  max_candidates: 200       # More candidates
  batch_size: 5             # Smaller batches for stability
```

## Analysis Mode Configuration

### Default Mode Settings

```yaml
analysis:
  default_mode: "creative"
  mode_specific:
    creative:
      timeout: 120           # 2 minutes
      structure_samples: 5
      quick_screening: true
    
    rigorous:
      timeout: 600           # 10 minutes
      structure_samples: 10
      comprehensive_analysis: true
      generate_reports: true
```

### Tool-Specific Configuration

```yaml
tools:
  smact:
    database_path: "./data/smact"
    screening_level: "standard"
    confidence_threshold: 0.7
  
  chemeleon:
    model_path: "./models/chemeleon"
    num_structures: 5
    space_group_search: "comprehensive"
  
  mace:
    model_path: "./models/mace"
    precision: "high"
    gpu_acceleration: true
    uncertainty_quantification: true
  
  visualization:
    output_format: ["html", "pdf"]
    resolution: "high"
    interactive: true
```

## Session Configuration

### Session Management

```yaml
sessions:
  database_path: "~/.crystalyse/sessions.db"
  max_sessions_per_user: 100
  session_timeout: 86400     # 24 hours
  auto_cleanup: true
  backup_frequency: "daily"

conversation:
  max_turns: 1000
  context_window: 50
  save_frequency: 10         # Save every 10 turns
```

## Logging Configuration

### Log Levels and Output

```yaml
logging:
  level: "INFO"              # DEBUG, INFO, WARNING, ERROR
  format: "detailed"         # simple, detailed, json
  outputs:
    - type: "file"
      path: "~/.crystalyse/crystalyse.log"
      max_size: "100MB"
      backup_count: 5
    - type: "console"
      level: "WARNING"
  
  loggers:
    crystalyse: "INFO"
    mcp_servers: "WARNING"
    analysis: "DEBUG"
```

## Viewing Configuration

### Current Configuration

```bash
# Display all settings
crystalyse config show

# Show specific section
crystalyse config show --section model
crystalyse config show --section mcp_servers
```

### Configuration File Location

```bash
# Show config file path
crystalyse config path
```

## Configuration Validation

### Validation Commands

```bash
# Test configuration
crystalyse config validate

# Test MCP server connections
crystalyse config test-servers

# Test API connectivity
crystalyse config test-api
```

### Common Validation Issues

**Invalid API Key**:
```
❌ OpenAI API key invalid or expired
   Solution: Update OPENAI_API_KEY environment variable
```

**MCP Server Unavailable**:
```
❌ chemistry_unified server not responding
   Solution: Check server installation and dependencies
```

**Configuration Syntax Error**:
```
❌ YAML syntax error in config file line 15
   Solution: Fix YAML formatting in ~/.crystalyse/config.yaml
```

## Advanced Configuration

### Custom MCP Servers

Add custom tool servers:

```yaml
mcp_servers:
  custom_tool:
    command: "python"
    args: ["-m", "custom_tool.server"]
    cwd: "./custom-tool-server"
    capabilities: ["structure_analysis", "property_prediction"]
```

### Multi-Environment Setup

Different configurations for development/production:

```bash
# Development
export CRYSTALYSE_CONFIG="./config/dev.yaml"

# Production  
export CRYSTALYSE_CONFIG="./config/prod.yaml"

# Testing
export CRYSTALYSE_CONFIG="./config/test.yaml"
```

## Troubleshooting Configuration

### Common Issues

**Configuration Not Loading**:
1. Check file permissions
2. Verify YAML syntax
3. Check file path

**MCP Servers Not Starting**:
1. Verify Python environment
2. Check dependencies installed
3. Review server logs

**Performance Issues**:
1. Adjust batch sizes
2. Enable GPU if available
3. Reduce structure samples

### Debug Configuration

Enable debug mode for troubleshooting:

```bash
export CRYSTALYSE_DEBUG="true"
crystalyse config show
```

This provides detailed information about configuration loading and validation.

## See Also

- [Installation Guide](../../guides/installation.md) - Initial setup
- [CLI Reference](../cli/index.md) - Command-line options
- [Error Reference](../errors/index.md) - Configuration error codes
- [Performance Tuning](../../guides/performance.md) - Optimisation guide