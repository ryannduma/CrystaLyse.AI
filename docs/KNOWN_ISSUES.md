# Known Issues and Common Pitfalls

*Following Agent Laboratory patterns for documenting failure modes*

This document catalogs common issues encountered in CrystaLyse.AI development and deployment. Documenting these pitfalls saves each contributor hours of debugging time.

---

## 🔴 Critical Issues (System-breaking)

### 1. MCP Server Lifecycle Management
**Problem**: Agent creates `MCPServer` objects but never connects them using async context managers.

**Symptom**: "Server not initialized" errors when calling tools.

**Root Cause**: Violates OpenAI Agents SDK best practices by passing unconnected servers to Agent constructor.

**Solution**: Always use `AsyncExitStack` pattern:
```python
async with AsyncExitStack() as stack:
    server = await stack.enter_async_context(MCPServerStdio(...))
    agent = Agent(mcp_servers=[server], ...)
```

**Status**: ✅ **FIXED** in unified agent implementation.

### 2. Configuration Path Mismatches
**Problem**: MCP server paths point to directory root instead of `src` subdirectory.

**Symptom**: "Module not found" errors when starting MCP servers.

**Fix**: Ensure all server paths include `/src`:
```python
"cwd": str(self.base_dir / "smact-mcp-server" / "src")
```

**Status**: ✅ **FIXED** in config.py.

---

## 🟡 High-Impact Issues (Feature-breaking)

### 3. Tool Serialization Failures
**Problem**: "Object of type Composition is not JSON serializable" errors.

**Symptom**: Tools return Python objects that can't be serialized for MCP protocol.

**Workaround**: Convert complex objects to dictionaries before returning:
```python
# BAD:
return Composition("NaCl")

# GOOD:
return {"formula": "NaCl", "elements": ["Na", "Cl"]}
```

**Status**: ⚠️ **ONGOING** - needs systematic fix across all MCP servers.

### 4. Default Model Mismatch
**Problem**: Configuration defaults to Claude model but system uses OpenAI o4-mini.

**Symptom**: Model loading errors or unexpected behavior.

**Status**: ✅ **FIXED** - default model corrected to "o4-mini".

### 5. Interactive Shell Corruption
**Problem**: CLI shell command became non-functional during development.

**Symptom**: Shell fails to start or crashes immediately.

**Root Cause**: Cascading tooling failures corrupted the CLI file during refactoring.

**Status**: 🔴 **ACTIVE** - shell temporarily disabled, needs rebuild.

---

## 🟢 Medium Issues (Performance/UX)

### 6. Missing Tool Caching
**Problem**: MCP servers don't enable tool list caching.

**Impact**: Slower startup times and higher API costs.

**Fix**: Add `cache_tools_list=True` to MCPServerStdio:
```python
MCPServerStdio(
    name="SMACT Server",
    params={...},
    cache_tools_list=True  # Add this
)
```

### 7. No Budget Alerts
**Problem**: Expensive tool calls can drain API budgets without warning.

**Solution**: Use the new telemetry system:
```python
from crystalyse.monitoring.agent_telemetry import check_budget_alerts
alerts = check_budget_alerts(budget=1.0)  # $1 limit
```

### 8. Large Model Loading Time
**Problem**: Chemeleon and MACE models take 10-15 seconds to load.

**Impact**: Poor user experience during first tool call.

**Mitigation**: 
- Warn users about loading time
- Implement model pre-warming
- Add progress indicators

---

## 🐛 Development Pitfalls

### 9. Dependency Hell
**Problem**: MCP servers have complex interdependencies that aren't properly managed.

**Common Error**:
```python
try:
    from smact_mcp.tools import smact_validity
    SMACT_AVAILABLE = True
except ImportError:
    SMACT_AVAILABLE = False  # Silent failure masks issues
```

**Better Pattern**:
```python
try:
    from smact_mcp.tools import smact_validity
    SMACT_AVAILABLE = True
except ImportError as e:
    logger.error(f"SMACT tools unavailable: {e}")
    SMACT_AVAILABLE = False
```

### 10. Accidental Infinite Loops
**Problem**: LLM agents can get stuck in reflection loops.

**Symptom**: Agent makes same tool calls repeatedly without progress.

**Prevention**: 
- Set reasonable `max_turns` limits
- Implement loop detection in tools
- Use early stopping conditions

### 11. Token Explosion
**Problem**: Large context windows cause exponential cost growth.

**Mitigation**:
- Use compact JSON summaries between stages
- Flush chat history after each pipeline stage
- Monitor token usage with telemetry

### 12. GPU Memory Issues
**Problem**: MACE calculations can cause OOM errors.

**Symptom**: "CUDA out of memory" or silent failures.

**Prevention**:
- Batch size limits in configuration
- Memory monitoring in telemetry
- Graceful degradation to CPU

---

## 🔧 Environment Setup Issues

### 13. Missing Python Executable
**Problem**: System can't find Python interpreter.

**Diagnostic**: `which python` returns nothing.

**Fix**: Ensure Python is in PATH or use absolute path in configuration.

### 14. OpenAI API Key Not Set
**Problem**: OPENAI_API_KEY environment variable missing.

**Symptom**: Authentication errors during agent execution.

**Fix**: `export OPENAI_API_KEY="your_key_here"`

### 15. MCP Package Version Conflicts
**Problem**: Different MCP package versions across servers.

**Diagnostic**: Check with `pip list | grep mcp`

**Solution**: Pin versions in requirements.txt

---

## 🧪 Testing Gotchas

### 16. Async Test Patterns
**Problem**: Forgetting to mark tests as async or use proper event loops.

**Common Error**:
```python
def test_agent():  # Missing async
    result = agent.discover_materials("query")  # Missing await
```

**Correct Pattern**:
```python
@pytest.mark.asyncio
async def test_agent():
    result = await agent.discover_materials("query")
```

### 17. Mock MCP Servers
**Problem**: Tests trying to connect to real MCP servers.

**Solution**: Use test doubles:
```python
@pytest.fixture
def mock_mcp_server():
    server = MagicMock()
    server.get_tools.return_value = []
    return server
```

---

## 📊 Performance Patterns

### 18. Sequential vs Parallel Tool Calls
**Problem**: Making tool calls sequentially instead of in parallel.

**Impact**: 3-5x slower execution times.

**Pattern**: Always consider parallel execution:
```python
# BAD:
result1 = await tool1()
result2 = await tool2()

# GOOD:
result1, result2 = await asyncio.gather(tool1(), tool2())
```

### 19. Expensive Self-Evaluation
**Problem**: LLM self-scores are ~2 points too generous and cost tokens.

**Mitigation**: 
- Treat self-reflection as suggestive only
- Use lightweight rule-based critics
- Budget limits on reflection calls

---

## 🎓 Best Practices Learned

### 20. Agent Laboratory Key Lessons

1. **Compartmentalization**: Break workflows into stages with clear handoffs
2. **Human-in-the-Loop**: Co-pilot mode beats fully autonomous (+0.6 score improvement)
3. **Cost Monitoring**: 84% cost reduction came from watching telemetry
4. **Simple Tools**: Thin edit tools (EDIT/REPLACE) have fewer bugs than complex ones
5. **Cheap Rewards**: LLM-scored hill-climbing works surprisingly well

### 21. Materials Science Domain Issues

**Oxidation State Confusion**: 
- P can be +5 (phosphate) or -3 (phosphide)
- Always specify context when generating compositions

**Crystal System Assumptions**:
- Don't assume cubic symmetry for all compounds
- Consider multiple polymorphs per composition

**Energy Scale Confusion**:
- Formation energy vs total energy
- Per-atom vs per-formula-unit normalization

---

## 🚨 Emergency Procedures

### If Agent Gets Stuck in Loop:
1. Check `max_turns` setting
2. Look for repeated tool calls in logs
3. Add early stopping conditions
4. Reset agent state

### If Costs Spike:
1. Check telemetry dashboard
2. Identify expensive tools
3. Kill processes >$0.10/call
4. Review budget alerts

### If MCP Servers Won't Start:
1. Check Python paths in config
2. Verify MCP package installation
3. Test server startup manually: `python -m smact_mcp.server`
4. Check for port conflicts

---

## 📝 Contributing to This Document

When you encounter a new issue:

1. **Document the symptom** - what the user sees
2. **Identify the root cause** - why it happens
3. **Provide a solution** - step-by-step fix
4. **Add prevention tips** - how to avoid it
5. **Update status** - is it fixed, ongoing, or needs work?

**Template**:
```markdown
### N. Issue Title
**Problem**: Brief description

**Symptom**: Observable behavior

**Root Cause**: Technical explanation

**Solution**: 
```code
example fix
```

**Status**: 🔴/🟡/🟢 **STATUS** - description
```

---

*Last updated: December 2024*  
*Contributors: Add your name when you add an issue* 