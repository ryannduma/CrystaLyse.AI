# MCP Server Integration Guide for CrystaLyse.AI

**How to Successfully Integrate New MCP Servers into CrystaLyse**

This guide captures the proven patterns and lessons learned from successfully integrating the SMACT MCP server into CrystaLyse.AI's dual-mode system.

---

## 🏆 Proven Success Pattern

The SMACT MCP integration succeeded by using a **low-level MCP protocol implementation** instead of higher-level frameworks that caused compatibility issues.

### Key Success Factors

1. **Low-Level MCP Implementation**: Used `mcp.server.lowlevel.Server` instead of FastMCP
2. **Async Context Manager Pattern**: Proper lifecycle management with `MCPServerStdio`
3. **Proper Error Handling**: Graceful failures with informative messages
4. **Tool Schema Validation**: Well-defined input/output schemas
5. **Dual-Mode Architecture**: Clear separation between tool-constrained and creative modes

---

## 📁 Required Project Structure

```
your-mcp-server/
├── src/
│   └── your_mcp/
│       ├── __init__.py
│       ├── server_fixed.py      # Low-level MCP implementation
│       └── tools.py             # Tool functions (optional)
├── pyproject.toml
└── README.md
```

---

## 🔧 Step 1: Low-Level MCP Server Implementation

### Template: server_fixed.py

```python
"""Your MCP Server using working low-level pattern."""

import sys
import json
from pathlib import Path
import anyio
import mcp.types as types
from mcp.server.lowlevel import Server

# Add your library to the path if needed
LIBRARY_PATH = Path(__file__).parent.parent.parent.parent / "your-library"
sys.path.insert(0, str(LIBRARY_PATH))

def main():
    """Main MCP server entry point."""
    app = Server("your-server-name")
    
    @app.list_tools()
    async def list_tools() -> list[types.Tool]:
        """List all available tools."""
        print("🔧 list_tools() called!")
        
        return [
            types.Tool(
                name="your_tool_name",
                description="Description of what your tool does",
                inputSchema={
                    "type": "object",
                    "required": ["param1"],
                    "properties": {
                        "param1": {
                            "type": "string",
                            "description": "Parameter description"
                        },
                        "param2": {
                            "type": "integer", 
                            "description": "Optional parameter",
                            "default": 10
                        }
                    }
                }
            ),
            # Add more tools here...
        ]
    
    @app.call_tool()
    async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
        """Handle tool calls."""
        print(f"🎯 call_tool() called with: {name}, {arguments}")
        
        try:
            if name == "your_tool_name":
                result = your_tool_function(arguments["param1"], arguments.get("param2", 10))
            else:
                result = {"error": f"Unknown tool: {name}"}
                
            return [types.TextContent(type="text", text=json.dumps(result))]
            
        except Exception as e:
            error_result = {
                "error": f"Tool execution failed: {str(e)}",
                "tool": name,
                "arguments": arguments
            }
            return [types.TextContent(type="text", text=json.dumps(error_result))]
    
    # Run the server
    anyio.run(app.run, sys.stdin.buffer, sys.stdout.buffer)

def your_tool_function(param1: str, param2: int = 10):
    """Your actual tool implementation."""
    # Implement your tool logic here
    return {"result": f"Processed {param1} with {param2}"}

if __name__ == "__main__":
    main()
```

### Critical Requirements

1. **Use `mcp.server.lowlevel.Server`** - NOT FastMCP or other frameworks
2. **Async decorators**: `@app.list_tools()` and `@app.call_tool()`
3. **Proper error handling**: Wrap tool execution in try/catch
4. **JSON serialization**: Return results as JSON strings in TextContent
5. **Entry point**: Use `anyio.run(app.run, sys.stdin.buffer, sys.stdout.buffer)`

---

## 🔌 Step 2: Agent Integration Pattern

### Add MCP Support to Your Agent

```python
from agents import Agent, Runner
from agents.mcp import MCPServerStdio
from pathlib import Path

class YourAgent:
    def __init__(self, model: str = "gpt-4o", use_tools: bool = False):
        self.model = model
        self.use_tools = use_tools
        self.mcp_server_path = Path(__file__).parent.parent / "your-mcp-server"
        
    async def analyze(self, query: str) -> str:
        """Analyze with optional MCP tool integration."""
        
        if self.use_tools:
            # Rigorous mode with MCP tools
            async with MCPServerStdio(
                name="Your Tools",
                params={
                    "command": "python", 
                    "args": ["-m", "your_mcp.server_fixed"],
                    "cwd": str(self.mcp_server_path)
                },
                cache_tools_list=False,
                client_session_timeout_seconds=10
            ) as mcp_server:
                
                agent = Agent(
                    name="Your Agent (Tool Mode)",
                    model=self.model,
                    instructions=YOUR_TOOL_PROMPT,
                    mcp_servers=[mcp_server],
                )
                
                result = await Runner.run(agent, query)
                return result.data
        else:
            # Creative mode without tools
            agent = Agent(
                name="Your Agent (Creative Mode)",
                model=self.model,
                instructions=YOUR_CREATIVE_PROMPT,
            )
            
            result = await Runner.run(agent, query)
            return result.data
```

### Key Integration Points

1. **Async Context Manager**: Use `async with MCPServerStdio(...) as mcp_server:`
2. **Server Parameters**: Specify command, args, and cwd correctly
3. **Timeout Settings**: Set reasonable timeout values
4. **Cache Control**: Use `cache_tools_list=False` for reliability
5. **Dual Mode Support**: Separate creative and tool-constrained modes

---

## Step 3: System Prompts for Dual Modes

### Creative Mode Prompt

```python
YOUR_CREATIVE_PROMPT = """You are an expert agent with deep domain knowledge.

**Workflow:**
1. Analyze the user's requirements
2. Use your knowledge and intuition to generate solutions
3. Provide creative but grounded recommendations

**IMPORTANT:** Always end your response with:

*"These outputs are based on my knowledge and intuition. For extra rigor 
and computational validation, use tool-enabled mode to verify with 
computational tools."*
"""
```

### Tool-Constrained Mode Prompt

```python
YOUR_TOOL_PROMPT = """You are an expert agent with access to computational tools.

**Workflow:**
1. Analyze the user's requirements
2. Generate candidate solutions
3. MANDATORY: Validate ALL solutions using available tools
4. Only recommend solutions that pass tool validation
5. Show actual tool outputs as evidence

**Available Tools:**
- your_tool_name: Description of what it does
- another_tool: Description of another tool

**Remember:** Use tools to ensure rigorous validation. Only recommend 
solutions that pass computational verification.
"""
```

---

## Step 4: Testing Strategy

### 1. Direct MCP Client Test

Create `test_mcp_direct.py`:

```python
import asyncio
from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

async def test_mcp_direct():
    server_params = StdioServerParameters(
        command="python",
        args=["-m", "your_mcp.server_fixed"],
        cwd="path/to/your-mcp-server"
    )
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            # List tools
            tools = await session.list_tools()
            print(f"Tools: {[tool.name for tool in tools.tools]}")
            
            # Test tool call
            result = await session.call_tool("your_tool_name", {"param1": "test"})
            print(f"Result: {result}")

if __name__ == "__main__":
    asyncio.run(test_mcp_direct())
```

### 2. Dual-Mode System Test

Create `test_dual_mode.py`:

```python
import asyncio
from your_agent import YourAgent

async def test_dual_mode():
    query = "Your test query here"
    
    # Test creative mode
    creative_agent = YourAgent(use_tools=False)
    creative_result = await creative_agent.analyze(query)
    print("Creative:", creative_result)
    
    # Test tool mode
    tool_agent = YourAgent(use_tools=True)
    tool_result = await tool_agent.analyze(query)
    print("Tool-constrained:", tool_result)

if __name__ == "__main__":
    asyncio.run(test_dual_mode())
```

### 3. Deployment Test

Create `test_deployment.py`:

```python
import os
import asyncio
from your_agent import YourAgent

async def test_deployment():
    # Check API key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ API key not found!")
        return False
    
    # Basic functionality test
    agent = YourAgent()
    result = await agent.analyze("Simple test query")
    
    if result:
        print("✅ Deployment test passed!")
        return True
    else:
        print("❌ Deployment test failed!")
        return False

if __name__ == "__main__":
    asyncio.run(test_deployment())
```

---

## Step 5: Package Configuration

### pyproject.toml

```toml
[build-system]
requires = ["setuptools>=61.0"]
build-backend = "setuptools.build_meta"

[project]
name = "your-mcp-server"
version = "0.1.0"
dependencies = [
    "mcp>=1.0.0",
    "anyio>=4.0.0",
    # Add your dependencies
]

[project.scripts]
your-mcp = "your_mcp.server_fixed:main"
```

### Installation

```bash
# Install your MCP server
pip install -e ./your-mcp-server

# Test installation
python -c "from your_mcp.server_fixed import main; print('MCP server available')"
```

---

## Common Pitfalls to Avoid

### ❌ What NOT to Do

1. **Don't use FastMCP**: Causes compatibility issues with OpenAI Agents SDK
2. **Don't mix async/sync**: Use proper async patterns throughout
3. **Don't ignore error handling**: Always wrap tool calls in try/catch
4. **Don't use relative imports**: Use absolute paths for library imports
5. **Don't cache aggressively**: Use `cache_tools_list=False` for reliability

### ✅ What TO Do

1. **Use low-level MCP**: `mcp.server.lowlevel.Server`
2. **Proper async context management**: `async with MCPServerStdio(...)`
3. **Comprehensive error handling**: Graceful failures with informative messages
4. **Clear tool schemas**: Well-defined input/output schemas
5. **Dual-mode architecture**: Separate creative and tool-constrained modes

---

## Debugging Guide

### Common Issues and Solutions

1. **MCP Connection Failed**
   ```bash
   # Test MCP server directly
   python -m your_mcp.server_fixed
   
   # Check server path
   python -c "from pathlib import Path; print(Path('your-mcp-server').absolute())"
   ```

2. **Tool Not Found**
   ```python
   # Verify tool registration
   async with MCPServerStdio(...) as server:
       tools = await server.list_tools()
       print([tool.name for tool in tools])
   ```

3. **Import Errors**
   ```python
   # Check Python path
   import sys
   print(sys.path)
   
   # Test library import
   try:
       import your_library
       print("✅ Library imported successfully")
   except ImportError as e:
       print(f"❌ Import error: {e}")
   ```

---

## Success Checklist

Before deploying your MCP integration:

- [ ] MCP server uses low-level implementation
- [ ] All tools have proper input/output schemas
- [ ] Error handling is comprehensive
- [ ] Direct MCP client test passes
- [ ] Dual-mode system test passes
- [ ] Deployment test passes
- [ ] Agent prompts include tool usage instructions
- [ ] Documentation is complete

---

## Success Metrics

Your MCP integration is successful when:

1. **Direct MCP test shows all tools available**
2. **Agent can list and call all MCP tools**
3. **Tool-constrained mode shows validation outputs**
4. **Creative mode includes advisory note**
5. **Error handling is graceful and informative**

---

**Based on the successful SMACT MCP integration that achieved 100% reliability with 4 working tools and seamless dual-mode operation.**