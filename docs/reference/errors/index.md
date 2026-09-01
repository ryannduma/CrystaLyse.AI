# Error Reference

Comprehensive reference for Crystalyse error codes, messages, and troubleshooting guidance.

## Overview

Crystalyse provides detailed error information to help diagnose and resolve issues quickly. Errors are categorised by source and include specific guidance for resolution.

## Error Categories

### Exit Codes

Crystalyse itself produces only two exit codes. Code `2` comes from the CLI framework's own
usage-error handling:

| Code | Category | Description |
|------|----------|-------------|
| 0 | Success | Command completed successfully - including a discovery that failed or timed out, which is reported in the results panel rather than through the exit status |
| 1 | Error | `crystalyse setup` could not download the data files, `crystalyse models check` found a missing API key, or an unhandled exception was caught by the top-level handler |
| 2 | Usage | Unknown option, missing argument, or a global option placed after the command |

There are no dedicated codes for configuration, API, MCP or timeout failures.

### Exception Types

The structured error surface is the tool error hierarchy in `crystalyse.tools.errors`:

| Exception | Base | Raised for |
|-----------|------|------------|
| `CrystaLyseToolError` | `Exception` | Any tool failure; carries `recoverable`, `fallback` and `retry_after` |
| `ValidationError` | `CrystaLyseToolError` | Validation-specific failures |
| `ComputationError` | `CrystaLyseToolError` | Computation and calculation failures |
| `ResourceUnavailableError` | `CrystaLyseToolError` | A model or checkpoint is unavailable |

Configuration and model resolution add three more:

| Exception | Base | Raised for |
|-----------|------|------------|
| `crystalyse.config.model_overrides.ModelOverrideError` | `ValueError` | An invalid `[models.*]` table in `config.toml` - unknown field, bad `backend`/`reasoning_effort` value, missing required field, or an attempt to override a capability field on a built-in entry |
| `RuntimeError` | - | `ModelConfig.validate_env()` when the entry's API-key variable is unset |
| `ValueError` | - | `resolve_mode_name()` when the mode string is not recognised |

## Common Error Types

### API Errors

#### Missing API Key
```
ModelConfig 'openai_o4_mini' requires env var 'OPENAI_API_KEY', but it is not set.
```

**Cause**: The selected backbone's API-key environment variable is not set (raised as a
`RuntimeError` when the model is resolved, and surfaced by the CLI as
`❌ An unexpected error occurred: …` with exit code 1)
**Diagnose**: `crystalyse models check`
**Solution**:
```bash
export OPENAI_API_KEY="..."         # OpenAI-backed entries (the defaults)
export ANTHROPIC_API_KEY="..."      # anthropic_claude_* entries
export OPENROUTER_API_KEY="..."     # openrouter_* entries
export MISTRAL_API_KEY="..."        # mistral_large

# Make them permanent - on zsh use ~/.zshenv, because ~/.zshrc is
# interactive-only and these must be real environment variables
echo 'export OPENAI_API_KEY="..."' >> ~/.zshenv
```
There is no `.env` support in the codebase. The message ends with `See docs/models.md for setup.`;
that page does not exist - use the [Configuration Reference](../config/index.md) instead.

#### Authentication Rejected by the Provider
```
❌ An unexpected error occurred: <provider authentication error>
```

**Cause**: The key is set but the provider rejected it. Crystalyse performs no key-format
validation - `validate_env()` only checks that the variable is non-empty - so a malformed key
fails at the provider, not locally.
**Solution**:
1. Check the key has not expired or been revoked
2. Confirm the key belongs to the provider you selected with `--model`
3. Generate a new key from the provider's dashboard

#### Rate Limiting and Connection Failures

Provider rate limits, timeouts and outages surface with the provider SDK's own message, wrapped by
the top-level handler:

```
❌ An unexpected error occurred: <provider message>
Check crystalyse.log for details.
```

**Solution**:
1. Wait for the rate-limit window to reset, or switch to a cheaper backbone
   (`--model anthropic_claude_haiku`, `--model openai_gpt4o_mini`)
2. Use `--mode explore` for shorter runs
3. Check the provider's status page and your network connection

### MCP Server Errors

#### Server Directory Not Found
```
FileNotFoundError: MCP server directory not found: <path>/chemistry-unified-server/src
```

**Cause**: The MCP server trees are missing from the expected location beside the installed
package
**Solution**: install them from `dev/`
```bash
pip install -e ./dev/chemistry-unified-server
pip install -e ./dev/chemistry-creative-server
pip install -e ./dev/visualization-mcp-server
```

#### Interpreter Not Found
```
FileNotFoundError: Python executable not found: <command>. Set CRYSTALYSE_PYTHON_PATH
environment variable if using a specific conda environment.
```

**Cause**: The interpreter used to launch the servers is not on `PATH`
**Solution**: `export CRYSTALYSE_PYTHON_PATH="/path/to/env/bin/python"` (honoured by the
`chemistry_unified` server)

#### Server Failed to Start
```
⚠️ Could not start chemistry_unified server: <details>
```

**Cause**: The server process failed to launch or crashed during connection
**Where**: Logged as a warning - visible with `--verbose` and in `crystalyse.log`
**Effect**: The run continues **without** that server, so its tools are simply unavailable
**Solution**:
1. Check the server's dependencies are installed
2. Verify the correct Python environment is active
3. Review `crystalyse.log` for the underlying exception

#### Tool Execution Failed
```
CrystaLyseToolError: All tools in chain failed: <tool>: <error>; <tool>: <error>
```

**Cause**: Every tool in a `FallbackChain` raised
**Solution**:
1. Check tool-specific dependencies
2. Verify input format and constraints
3. Review the per-tool errors listed in the message

### Configuration Errors

Configuration is TOML, at `~/.crystalyse/config.toml` (user) and
`<project>/.crystalyse/config.toml` (project).

#### Missing Configuration File

A missing config file is **not** an error - built-in defaults are used and the run proceeds. A
project root is created on demand by `ensure_crystalyse_root()`, which writes a commented
`config.toml` template.

#### Unparseable Configuration File
```
WARNING  Failed to parse /path/.crystalyse/config.toml: <tomllib error>
```

**Cause**: Malformed TOML
**Effect**: Logged as a warning; the file is treated as empty
**Solution**: fix the TOML syntax - a settings key that silently does nothing usually means the
file failed to parse

#### Invalid Model Override
```
❌ An unexpected error occurred: [models.openai_o3] in /path/.crystalyse/config.toml: cannot
override capability field(s) ['backend'] on the built-in entry 'openai_o3'. Those describe what
the model can do and are code-owned; define a new [models.*] entry instead if you need different
capabilities.
```

The exception is `ModelOverrideError`, and its message always has the form
`[models.<name>] in <path>: <reason>`.

**Cause**: An invalid `[models.*]` table - an unknown field, a bad `backend` or
`reasoning_effort` value, a new entry missing `backend`/`model_id`/`api_key_env_var`, or a
capability field set on a built-in entry
**Effect**: Start-up aborts. Unlike the runtime settings, model overrides are never silently
skipped
**Solution**: follow the message's field list, or define a new entry rather than changing a
built-in's capabilities - see the
[Configuration Reference](../config/index.md)

#### Invalid Mode
```
ValueError: Unknown mode 'invalid'. Valid modes: adaptive, auto, creative, explore, rigorous,
validate
```

**Cause**: An unrecognised `--mode` or `default_mode` value
**Solution**: use a canonical name - `explore`, `validate` or `auto`. `creative`, `rigorous` and
`adaptive` still resolve but emit a `DeprecationWarning` and are removed in v2.0

### Analysis Errors

#### Analysis Timeout
```
╭──────── Discovery Failed ────────╮
│ Error: The operation timed out.  │
╰──────────────────────────────────╯
```

**Cause**: The run exceeded the mode's timeout - 120 s for `explore`, 180 s for `auto`, 300 s for
`validate`. These are hard-coded and not configurable
**Note**: The process still exits 0; the failure is reported in the results panel
**Solution**:
1. Use `--mode explore` for faster results
2. Simplify the query or break it into parts
3. Choose a faster backbone with `--model`

#### Discovery Failed
```
╭──────── Discovery Failed ────────╮
│ Error: <exception message>       │
╰──────────────────────────────────╯
```

**Cause**: Any exception raised inside the agent run, reported as `status: failed`
**Solution**: read the message, then check `crystalyse.log` for the traceback

### Conversation Memory

Chat history is stored by the Agents SDK in a SQLite database at
`~/.crystalyse/sessions/<project>_<session>_<mode>.db`. There is no `sessions` command, no
session listing and no `resume` command: continuing previous work means re-running `chat` with the
same project, session and mode.

#### Memory Disabled
```
WARNING  SQLiteSession not available - conversation memory disabled
```

**Cause**: The installed `openai-agents` build does not expose `SQLiteSession`
**Effect**: The session still runs; history simply is not persisted
**Solution**: check the `openai-agents` version against the pins in `pyproject.toml`

#### Resetting Memory

```bash
# Inside a session
/memory show     # session ID and database size
/memory clear    # delete and recreate this session's database

# Or from the shell
rm ~/.crystalyse/sessions/<project>_<session>_<mode>.db
```

### Installation Errors

#### Python Version

There is no runtime Python-version check, so a too-old interpreter fails at import time instead
(for example on `tomllib` or `StrEnum`, both 3.11+). The project is developed and tested on
Python 3.12.

```bash
conda create -n crystalyse python=3.12
conda activate crystalyse
```

#### Dependency Installation Failed
```
Error: Failed to install required dependencies
```

**Cause**: Package installation issues
**Solution**:
1. Update pip: `pip install --upgrade pip`
2. Check internet connection
3. Install in clean environment

#### Import Errors
```
Error: No module named 'crystalyse'
```

**Cause**: Package not installed or wrong environment
**Solution**:
1. Activate correct environment: `conda activate crystalyse`
2. Reinstall package: `pip install -e .`
3. Check Python path

## Error Diagnosis

### Verbose Mode

Enable detailed error information. `--verbose` is a global option, so it precedes the command:

```bash
crystalyse --verbose discover "query"
crystalyse -v chat -u user
```

### Debug Mode

Pass the debug flag through to the MCP server processes:

```bash
export CRYSTALYSE_DEBUG="true"
crystalyse discover "query"
```

### Model and Key Diagnosis

```bash
crystalyse models check    # which provider keys are set; exits 1 if any are missing
crystalyse models list     # the effective registry, and where each entry came from
```

### Log Analysis

The log handler writes to `crystalyse.log` in the **current working directory** - the same file
the CLI points at when it reports an unexpected error:

```bash
# View recent logs
tail -f ./crystalyse.log

# Search for specific errors
grep "ERROR" ./crystalyse.log
```

## Error Recovery

### Automatic Recovery

Crystalyse includes automatic recovery at the tool level only:

- **`with_retry`**: retries `ComputationError` and `ResourceUnavailableError` up to three times
  with exponential backoff, then returns the exception's `fallback` value if it has one
- **`FallbackChain`**: tries a list of tools in order and raises
  `CrystaLyseToolError(recoverable=False)` only when every one has failed

There is no automatic MCP server restart and no automatic temporary-file cleanup. A server that
fails to start is logged and skipped for the rest of the run.

### Manual Recovery

#### Reset Configuration
```bash
# Back up the current config
cp .crystalyse/config.toml .crystalyse/config.toml.backup

# Start over: an absent file means built-in defaults, and the commented template
# is rewritten the next time a project root is scaffolded
rm .crystalyse/config.toml

# Confirm the registry is back to built-ins
crystalyse models list
```

#### Clear Caches
```bash
# Chemeleon checkpoints (~604 MB, re-downloaded on next use)
rm -rf ~/.cache/crystalyse/chemeleon_checkpoints

# Phase-diagram data (re-fetch with `crystalyse setup`)
rm -rf ~/.cache/crystalyse

# MACE foundation models
rm -rf ~/.cache/mace

# Conversation memory (caution: loses chat history)
rm ~/.crystalyse/sessions/*.db
```

#### Restart MCP Servers

MCP servers are started per agent run, so ending the session and issuing a new command starts
fresh server processes. There is no restart command.

## Reporting Errors

### Information to Include

When reporting errors, provide:

1. **Error message**: Complete error text
2. **Command used**: Exact command that caused error
3. **Environment**: Operating system, Python version
4. **Model setup**: Output of `crystalyse models list` and `crystalyse models check`
5. **Logs**: Relevant entries from `./crystalyse.log`

### Example Error Report

```
Environment:
- OS: Ubuntu 22.04
- Python: 3.12.4
- Crystalyse: v1.0.0-dev

Command:
crystalyse discover "Find battery materials" --mode validate

Error:
⚠️ Could not start chemistry_unified server: ModuleNotFoundError: No module named 'smact'

Model setup (crystalyse models check):
  ✓ openai_o4_mini — OPENAI_API_KEY is set
  ✗ anthropic_claude_opus — ANTHROPIC_API_KEY is NOT set

Logs:
2025-01-15 14:30:25 ERROR: Failed to start chemistry_unified server
2025-01-15 14:30:25 ERROR: ModuleNotFoundError: No module named 'smact'
```

## Prevention Strategies

### Environment Management

Use isolated environments:
```bash
conda create -n crystalyse python=3.12
conda activate crystalyse
pip install -e .
```

### Configuration Validation

Check the model registry and keys before a long run:
```bash
crystalyse models check
crystalyse models list
```

Inside a session, `/mcp status` and `/tools` report which servers and tools came up.

### Resource Monitoring

Monitor system resources:
```bash
# Check memory usage
htop

# Check disk space
df -h

# Check GPU usage (if applicable)
nvidia-smi
```

### API Key Management

Secure API key handling:
```bash
# Set in the shell startup file that non-interactive shells also read
echo 'export OPENAI_API_KEY="..."' >> ~/.zshenv

# Check key is set
echo $OPENAI_API_KEY | head -c 10
```

## Error Code Reference

Crystalyse assigns no `E###` identifiers. Errors are identified by exception type and message:

| Source | Exception / output | Exit code |
|--------|--------------------|-----------|
| Missing API key for a registry entry | `RuntimeError` from `ModelConfig.validate_env()` | 1 |
| Unknown mode string | `ValueError` from `resolve_mode_name()` | 1 |
| Invalid `[models.*]` table | `ModelOverrideError` | 1 |
| `crystalyse models check` with a missing key | `typer.Exit(code=1)` | 1 |
| `crystalyse setup` download failure | `typer.Exit(code=1)` | 1 |
| Tool failure inside a run | `CrystaLyseToolError` and subclasses | 0 (reported in the results panel) |
| Agent timeout | `status: failed`, `"The operation timed out."` | 0 |
| Bad command line | Usage error from the CLI framework | 2 |

## See Also

- [Installation Guide](../../guides/installation.md) - Setup troubleshooting
- [CLI Reference](../cli/index.md) - Command usage
- [Configuration Reference](../config/index.md) - Configuration options
