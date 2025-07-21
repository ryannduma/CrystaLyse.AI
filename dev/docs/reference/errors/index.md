# Error Reference

Comprehensive reference for CrystaLyse.AI error codes, messages, and troubleshooting guidance.

## Overview

CrystaLyse.AI provides detailed error information to help diagnose and resolve issues quickly. Errors are categorised by source and include specific guidance for resolution.

## Error Categories

### Exit Codes

Standard process exit codes used by CrystaLyse.AI:

| Code | Category | Description |
|------|----------|-------------|
| 0 | Success | Command completed successfully |
| 1 | General Error | Unspecified error occurred |
| 2 | Invalid Input | Invalid command or arguments |
| 3 | Configuration Error | Configuration file or settings issue |
| 4 | API Error | OpenAI API connection or authentication issue |
| 5 | MCP Server Error | MCP server connection or tool failure |
| 6 | Analysis Timeout | Analysis exceeded time limits |
| 7 | Memory Error | Insufficient memory for operation |
| 8 | File Error | File system access or permission issue |

## Common Error Types

### API Errors

#### Missing API Key
```
Error: OpenAI API key not found
```

**Cause**: `OPENAI_API_KEY` environment variable not set
**Solution**:
```bash
export OPENAI_API_KEY="sk-your-key-here"
echo 'export OPENAI_API_KEY="sk-your-key-here"' >> ~/.bashrc
```

#### Invalid API Key
```
Error: Authentication failed - invalid API key
```

**Cause**: API key is malformed or expired
**Solution**:
1. Verify key format starts with `sk-`
2. Check key hasn't expired
3. Generate new key from OpenAI dashboard

#### API Rate Limiting
```
Error: Rate limit exceeded - please retry after 60s
```

**Cause**: Too many requests to OpenAI API
**Solution**:
1. Wait for rate limit reset
2. Consider upgrading API plan
3. Use creative mode for faster queries

#### API Connection Timeout
```
Error: Request timeout - OpenAI API unreachable
```

**Cause**: Network connectivity or API service issues
**Solution**:
1. Check internet connection
2. Verify API service status
3. Retry with longer timeout

### MCP Server Errors

#### Server Not Found
```
Error: MCP server 'chemistry_unified' not found
```

**Cause**: MCP server not installed or not in PATH
**Solution**:
```bash
pip install -e ./chemistry-unified-server
pip install -e ./chemistry-creative-server
pip install -e ./visualization-mcp-server
```

#### Server Connection Failed
```
Error: Failed to connect to chemistry_unified server
```

**Cause**: Server process failed to start or crashed
**Solution**:
1. Check server dependencies installed
2. Verify Python environment activated
3. Review server logs for details

#### Tool Execution Failed
```
Error: SMACT validation tool failed with error: [details]
```

**Cause**: Specific tool within MCP server encountered error
**Solution**:
1. Check tool-specific dependencies
2. Verify input format and constraints
3. Review detailed error message

### Configuration Errors

#### Invalid Configuration File
```
Error: Invalid YAML syntax in config file line 15
```

**Cause**: Malformed YAML in configuration file
**Solution**:
1. Check YAML syntax and indentation
2. Validate file with YAML parser
3. Compare with reference configuration

#### Missing Configuration
```
Error: Configuration file not found at ~/.crystalyse/config.yaml
```

**Cause**: Configuration file missing or wrong location
**Solution**:
1. Create default configuration
2. Check file permissions
3. Verify file path

#### Invalid Configuration Values
```
Error: Invalid value 'invalid_mode' for analysis.default_mode
```

**Cause**: Configuration contains invalid values
**Solution**:
1. Check valid options in documentation
2. Update configuration with correct values
3. Validate configuration syntax

### Analysis Errors

#### Analysis Timeout
```
Error: Analysis exceeded maximum time limit (600s)
```

**Cause**: Analysis taking too long to complete
**Solution**:
1. Use creative mode for faster results
2. Reduce structure samples
3. Simplify query or break into parts

#### Insufficient Memory
```
Error: Insufficient memory for structure generation
```

**Cause**: System running out of RAM during analysis
**Solution**:
1. Reduce batch size and structure samples
2. Close other memory-intensive applications
3. Use systems with more RAM

#### Invalid Query
```
Error: Unable to parse materials query: [details]
```

**Cause**: Query format not recognised by analysis system
**Solution**:
1. Use clear, specific materials terminology
2. Check query examples in documentation
3. Break complex queries into simpler parts

### Session Errors

#### Session Not Found
```
Error: Session 'project_name' not found for user 'researcher'
```

**Cause**: Session doesn't exist or incorrect user/session ID
**Solution**:
1. List available sessions: `crystalyse sessions -u researcher`
2. Check session ID spelling
3. Verify user ID is correct

#### Session Database Locked
```
Error: Cannot access session database - file locked
```

**Cause**: Another CrystaLyse.AI process accessing database
**Solution**:
1. Wait for other process to complete
2. Check for hung processes
3. Restart if necessary

#### Session Corruption
```
Error: Session database corrupted - cannot read session data
```

**Cause**: Database file corrupted or incomplete
**Solution**:
1. Backup existing database if possible
2. Reset database: `rm ~/.crystalyse/sessions.db`
3. Start fresh sessions

### Installation Errors

#### Python Version Incompatible
```
Error: CrystaLyse.AI requires Python 3.11 or higher (found 3.9.2)
```

**Cause**: Python version too old
**Solution**:
```bash
conda create -n crystalyse python=3.11
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

Enable detailed error information:

```bash
crystalyse --verbose analyse "query"
crystalyse -v chat -u user
```

### Debug Mode

Enable comprehensive debugging:

```bash
export CRYSTALYSE_DEBUG="true"
crystalyse analyse "query"
```

### Log Analysis

Check log files for detailed error information:

```bash
# View recent logs
tail -f ~/.crystalyse/crystalyse.log

# Search for specific errors
grep "ERROR" ~/.crystalyse/crystalyse.log
```

## Error Recovery

### Automatic Recovery

CrystaLyse.AI includes automatic recovery for:

- **Temporary API failures**: Automatic retry with exponential backoff
- **MCP server restart**: Automatic server restart on failure
- **Memory management**: Automatic cleanup of temporary files

### Manual Recovery

#### Reset Configuration
```bash
# Backup current config
cp ~/.crystalyse/config.yaml ~/.crystalyse/config.yaml.backup

# Reset to defaults
rm ~/.crystalyse/config.yaml
crystalyse config show  # Generates default config
```

#### Clear Cache
```bash
# Clear analysis cache
rm -rf ~/.crystalyse/cache/*

# Clear session data (caution: loses conversation history)
rm ~/.crystalyse/sessions.db
```

#### Restart MCP Servers
```bash
# MCP servers restart automatically, but can be forced by:
# Simply running a new command - servers will restart if needed
crystalyse config show
```

## Reporting Errors

### Information to Include

When reporting errors, provide:

1. **Error message**: Complete error text
2. **Command used**: Exact command that caused error
3. **Environment**: Operating system, Python version
4. **Configuration**: Output of `crystalyse config show`
5. **Logs**: Relevant log entries

### Example Error Report

```
Environment:
- OS: Ubuntu 22.04
- Python: 3.11.5
- CrystaLyse.AI: v1.0.0

Command:
crystalyse analyse "Find battery materials" --mode rigorous

Error:
Error: MCP server 'chemistry_unified' connection failed

Configuration:
chemistry_unified: ❌ Unavailable
chemistry_creative: ✅ Available  
visualization: ✅ Available

Logs:
2025-01-15 14:30:25 ERROR: Failed to start chemistry_unified server
2025-01-15 14:30:25 ERROR: ModuleNotFoundError: No module named 'smact'
```

## Prevention Strategies

### Environment Management

Use isolated environments:
```bash
conda create -n crystalyse python=3.11
conda activate crystalyse
pip install -e .
```

### Configuration Validation

Regularly validate configuration:
```bash
crystalyse config show
crystalyse config test-servers
```

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
# Set in shell profile
echo 'export OPENAI_API_KEY="sk-..."' >> ~/.bashrc

# Check key is set
echo $OPENAI_API_KEY | head -c 10
```

## Error Code Reference

### Complete Error Code List

| Code | Category | Message Pattern | Severity |
|------|----------|----------------|----------|
| E001 | API | "OpenAI API key not found" | Critical |
| E002 | API | "Authentication failed" | Critical |
| E003 | API | "Rate limit exceeded" | Warning |
| E004 | API | "Request timeout" | Warning |
| E101 | MCP | "MCP server not found" | Critical |
| E102 | MCP | "Server connection failed" | Critical |
| E103 | MCP | "Tool execution failed" | Error |
| E201 | Config | "Invalid configuration file" | Error |
| E202 | Config | "Configuration file not found" | Warning |
| E203 | Config | "Invalid configuration values" | Error |
| E301 | Analysis | "Analysis timeout" | Warning |
| E302 | Analysis | "Insufficient memory" | Error |
| E303 | Analysis | "Invalid query" | Error |
| E401 | Session | "Session not found" | Error |
| E402 | Session | "Database locked" | Warning |
| E403 | Session | "Session corrupted" | Critical |

## See Also

- [Installation Guide](../../guides/installation.md) - Setup troubleshooting
- [CLI Reference](../cli/index.md) - Command usage
- [Configuration Reference](../config/index.md) - Configuration options
- [Troubleshooting Guide](../../guides/troubleshooting.md) - General issues