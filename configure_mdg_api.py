#!/usr/bin/env python3
"""
Configure the system to use OPENAI_MDG_API_KEY and test o3 model with tool usage scoring
"""

import os
import asyncio
import sys
from pathlib import Path

# Add the project to Python path
sys.path.insert(0, str(Path(__file__).parent))

from agents.models.openai_provider import OpenAIProvider
from agents import Agent, Runner
from agents.model_settings import ModelSettings
from agents.run import RunConfig
from agents.mcp import MCPServerStdio
from crystalyse.config import config
from crystalyse.unified_agent import assess_progress, explore_alternatives, ask_clarifying_questions

async def setup_mdg_provider():
    """Setup OpenAI provider with MDG API key"""
    mdg_api_key = os.getenv("OPENAI_MDG_API_KEY")
    if not mdg_api_key:
        print("❌ OPENAI_MDG_API_KEY not found!")
        return None
    
    print(f"✅ Using MDG API key: {mdg_api_key[:20]}...")
    provider = OpenAIProvider(api_key=mdg_api_key)
    return provider

async def test_o3_with_tool_scoring():
    """Test o3 model with comprehensive tool usage scoring"""
    print("🧪 Testing o3 Model with Tool Usage Scoring")
    print("=" * 60)
    
    # Setup MDG provider
    provider = await setup_mdg_provider()
    if not provider:
        return False
    
    try:
        # Test queries that SHOULD use tools
        test_queries = [
            {
                "query": "Find 3 stable compositions for sodium-ion battery cathodes using SMACT validation, then predict their crystal structures with Chemeleon, and calculate their formation energies with MACE.",
                "expected_tools": ["smact", "chemeleon", "mace"],
                "description": "Comprehensive battery materials workflow"
            },
            {
                "query": "Validate the composition NaFePO4 using SMACT tools and if valid, generate its crystal structure with Chemeleon CSP.",
                "expected_tools": ["smact", "chemeleon"],
                "description": "SMACT validation + structure prediction"
            },
            {
                "query": "Calculate the formation energy of LiCoO2 using MACE force fields.",
                "expected_tools": ["mace"],
                "description": "MACE energy calculation"
            },
            {
                "query": "Use Chemeleon to predict crystal structures for CaTiO3 perovskite.",
                "expected_tools": ["chemeleon"],
                "description": "Chemeleon structure prediction"
            }
        ]
        
        results = []
        
        for i, test_case in enumerate(test_queries, 1):
            print(f"\n🔬 Test {i}: {test_case['description']}")
            print(f"📝 Query: {test_case['query']}")
            print(f"🎯 Expected tools: {test_case['expected_tools']}")
            
            # Setup MCP servers
            mcp_context = setup_mcp_servers()
            async with mcp_context as mcp_servers:
                
                # Create o3 agent with MDG provider
                agent = Agent(
                    name="CrystaLyse-o3",
                    model="o3",
                    instructions="""You are CrystaLyse.AI, a materials science research agent. 
                    You MUST use the available computational tools to answer queries. 
                    Always use SMACT for composition validation, Chemeleon for structure prediction, 
                    and MACE for energy calculations when appropriate. Do not just provide theoretical answers.""",
                    tools=[assess_progress, explore_alternatives, ask_clarifying_questions],
                    mcp_servers=mcp_servers,
                    model_settings=ModelSettings()  # No temperature for o3
                )
                
                # Run the query
                run_config = RunConfig(
                    model_provider=provider,
                    workflow_name="o3-tool-usage-test"
                )
                
                result = await Runner.run(
                    starting_agent=agent,
                    input=test_case['query'],
                    max_turns=10,
                    run_config=run_config
                )
                
                # Score tool usage
                tool_score = score_tool_usage(result, test_case['expected_tools'])
                
                results.append({
                    "test": test_case['description'],
                    "tool_score": tool_score,
                    "tools_used": extract_tools_used(result),
                    "expected_tools": test_case['expected_tools'],
                    "success": tool_score['score'] > 0.5,  # 50% threshold
                    "response_preview": str(result.final_output)[:200] + "..."
                })
                
                print(f"🎯 Tool Usage Score: {tool_score['score']:.2f}")
                print(f"🔧 Tools Used: {tool_score['tools_used']}")
                print(f"✅ Expected: {tool_score['expected_tools']}")
                print(f"{'✅ PASS' if tool_score['score'] > 0.5 else '❌ FAIL'}")
        
        # Generate final report
        generate_tool_usage_report(results)
        
        # Overall success rate
        total_tests = len(results)
        passed_tests = sum(1 for r in results if r['success'])
        success_rate = (passed_tests / total_tests) * 100
        
        print(f"\n🏆 FINAL RESULTS:")
        print(f"📊 Overall Tool Usage Success Rate: {success_rate:.1f}% ({passed_tests}/{total_tests})")
        print(f"🎯 Threshold: 50% tool usage score required to pass")
        
        if success_rate >= 75:
            print("🎉 o3 model EXCELLENT at tool usage!")
            return True
        elif success_rate >= 50:
            print("✅ o3 model GOOD at tool usage")
            return True
        else:
            print("❌ o3 model POOR at tool usage - needs improvement")
            return False
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        print(traceback.format_exc())
        return False

def setup_mcp_servers():
    """Setup MCP servers context manager"""
    from contextlib import AsyncExitStack
    
    class MCPServersContext:
        def __init__(self):
            self.stack = AsyncExitStack()
            self.servers = []
            
        async def __aenter__(self):
            # Setup SMACT server
            smact_config = config.get_server_config("smact")
            smact_server = await self.stack.enter_async_context(
                MCPServerStdio(
                    name="SMACT",
                    params={
                        "command": smact_config["command"],
                        "args": smact_config["args"],
                        "cwd": smact_config["cwd"],
                        "env": smact_config.get("env", {})
                    }
                )
            )
            self.servers.append(smact_server)
            
            # Setup Chemeleon server
            chemeleon_config = config.get_server_config("chemeleon")
            chemeleon_server = await self.stack.enter_async_context(
                MCPServerStdio(
                    name="Chemeleon",
                    params={
                        "command": chemeleon_config["command"],
                        "args": chemeleon_config["args"],
                        "cwd": chemeleon_config["cwd"],
                        "env": chemeleon_config.get("env", {})
                    }
                )
            )
            self.servers.append(chemeleon_server)
            
            # Setup MACE server
            mace_config = config.get_server_config("mace")
            mace_server = await self.stack.enter_async_context(
                MCPServerStdio(
                    name="MACE",
                    params={
                        "command": mace_config["command"],
                        "args": mace_config["args"],
                        "cwd": mace_config["cwd"],
                        "env": mace_config.get("env", {})
                    }
                )
            )
            self.servers.append(mace_server)
            
            return self.servers
            
        async def __aexit__(self, exc_type, exc_val, exc_tb):
            await self.stack.aclose()
    
    return MCPServersContext()

def extract_tools_used(result):
    """Extract which tools were actually used from the result"""
    tools_used = set()
    
    # Check new_items for tool calls
    for item in result.new_items:
        if hasattr(item, 'tool_calls') and item.tool_calls:
            for tool_call in item.tool_calls:
                tool_name = tool_call.function.name.lower()
                if 'smact' in tool_name:
                    tools_used.add('smact')
                elif 'chemeleon' in tool_name:
                    tools_used.add('chemeleon')
                elif 'mace' in tool_name:
                    tools_used.add('mace')
    
    return list(tools_used)

def score_tool_usage(result, expected_tools):
    """Score how well the agent used the expected tools"""
    tools_used = extract_tools_used(result)
    
    if not expected_tools:
        return {"score": 1.0, "tools_used": tools_used, "expected_tools": expected_tools}
    
    # Calculate intersection and union
    used_set = set(tools_used)
    expected_set = set(expected_tools)
    
    intersection = used_set.intersection(expected_set)
    union = used_set.union(expected_set)
    
    # Jaccard similarity score
    if not union:
        score = 1.0
    else:
        score = len(intersection) / len(union)
    
    # Bonus for using all expected tools
    if expected_set.issubset(used_set):
        score = min(1.0, score + 0.2)
    
    return {
        "score": score,
        "tools_used": tools_used,
        "expected_tools": expected_tools,
        "intersection": list(intersection),
        "missing_tools": list(expected_set - used_set),
        "extra_tools": list(used_set - expected_set)
    }

def generate_tool_usage_report(results):
    """Generate comprehensive tool usage report"""
    report = """
# o3 Model Tool Usage Assessment Report

## Test Results Summary

| Test | Tool Score | Expected Tools | Used Tools | Status |
|------|------------|---------------|------------|--------|
"""
    
    for result in results:
        status = "✅ PASS" if result['success'] else "❌ FAIL"
        report += f"| {result['test']} | {result['tool_score']['score']:.2f} | {', '.join(result['expected_tools'])} | {', '.join(result['tools_used'])} | {status} |\n"
    
    report += f"""
## Detailed Analysis

### Tool Usage Patterns
"""
    
    all_tools = set()
    for result in results:
        all_tools.update(result['tools_used'])
        all_tools.update(result['expected_tools'])
    
    for tool in sorted(all_tools):
        expected_count = sum(1 for r in results if tool in r['expected_tools'])
        used_count = sum(1 for r in results if tool in r['tools_used'])
        usage_rate = (used_count / expected_count * 100) if expected_count > 0 else 0
        
        report += f"- **{tool.upper()}**: Expected {expected_count} times, used {used_count} times ({usage_rate:.1f}% usage rate)\n"
    
    report += """
### Success Criteria
- **Tool Usage Score**: Jaccard similarity between expected and used tools
- **Pass Threshold**: 50% tool usage score
- **Excellent Threshold**: 75% overall success rate

### Scoring Method
1. Jaccard Similarity: |intersection| / |union| of expected vs used tools
2. Bonus points for using all expected tools (+20%)
3. Binary pass/fail based on 50% threshold
"""
    
    with open("o3_tool_usage_report.md", "w") as f:
        f.write(report)
    
    print(f"\n📄 Detailed report saved to: o3_tool_usage_report.md")

if __name__ == "__main__":
    success = asyncio.run(test_o3_with_tool_scoring())
    if success:
        print("\n🎉 o3 model passed tool usage assessment!")
    else:
        print("\n🚨 o3 model failed tool usage assessment")
        sys.exit(1)