#!/usr/bin/env python3
"""
Inspect the actual result structure to fix tool counting
"""

import asyncio
import sys
from pathlib import Path
import json

# Add path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

async def inspect_result_structure():
    """Inspect what the Runner actually returns."""
    try:
        from crystalyse.agents.unified_agent import CrystaLyse, AgentConfig
        
        print("🔍 Inspecting Runner result structure...")
        print("=" * 60)
        
        # Create a custom agent that exposes the raw result
        class InspectingCrystaLyse(CrystaLyse):
            async def discover_materials(self, query: str, session=None, trace_workflow: bool = True) -> dict:
                """Override to inspect raw result."""
                try:
                    # Run the original logic up to the Runner.run call
                    from contextlib import AsyncExitStack
                    async with AsyncExitStack() as stack:
                        mcp_servers = []
                        from crystalyse.agents.unified_agent import assess_progress, explore_alternatives, ask_clarifying_questions
                        extra_tools = [assess_progress, explore_alternatives, ask_clarifying_questions]
                        
                        # Set up unified chemistry server
                        chemistry_config = self.system_config.get_server_config("chemistry_unified")
                        chemistry_server = await stack.enter_async_context(
                            MCPServerStdio(
                                name="ChemistryUnified",
                                params={
                                    "command": chemistry_config["command"],
                                    "args": chemistry_config["args"],
                                    "cwd": chemistry_config["cwd"],
                                    "env": chemistry_config.get("env", {})
                                }
                            )
                        )
                        mcp_servers.append(chemistry_server)
                        
                        # Create agent
                        from agents import Agent, Runner, gen_trace_id
                        from agents.model_settings import ModelSettings
                        from agents.run import RunConfig
                        from agents.models.openai_provider import OpenAIProvider
                        from agents.mcp import MCPServerStdio
                        import os
                        
                        model_settings = ModelSettings(tool_choice="required")
                        
                        self.agent = Agent(
                            name="CrystaLyse",
                            model=self.model_name,
                            instructions=self.instructions,
                            tools=extra_tools,
                            mcp_servers=mcp_servers,
                            model_settings=model_settings,
                        )
                        
                        # Run and inspect result
                        mdg_api_key = os.getenv("OPENAI_MDG_API_KEY") or os.getenv("OPENAI_API_KEY")
                        model_provider = OpenAIProvider(api_key=mdg_api_key)
                        
                        run_config = RunConfig(
                            trace_id=gen_trace_id(),
                            model_provider=model_provider
                        )
                        
                        result = await Runner.run(
                            starting_agent=self.agent, 
                            input=query, 
                            max_turns=1,  # Single turn for inspection
                            run_config=run_config,
                            max_workers=10,
                            trace_workflow=trace_workflow,
                        )
                        
                        # Inspect the result structure
                        print("Raw result type:", type(result))
                        print("Result attributes:", dir(result))
                        
                        if hasattr(result, 'new_items'):
                            print(f"\nNew items count: {len(result.new_items)}")
                            for i, item in enumerate(result.new_items[:3]):
                                print(f"\nItem {i} type: {type(item)}")
                                print(f"Item {i} attributes: {[attr for attr in dir(item) if not attr.startswith('_')]}")
                                
                                if hasattr(item, 'tool_calls'):
                                    print(f"Item {i} tool_calls: {item.tool_calls}")
                                    if item.tool_calls:
                                        for j, tc in enumerate(item.tool_calls[:2]):
                                            print(f"  Tool call {j}: {tc}")
                        
                        if hasattr(result, 'raw_responses'):
                            print(f"\nRaw responses count: {len(result.raw_responses)}")
                            
                        return {
                            "status": "inspection_complete",
                            "result_type": str(type(result)),
                            "has_new_items": hasattr(result, 'new_items'),
                            "has_tool_calls": any(hasattr(item, 'tool_calls') and item.tool_calls for item in result.new_items) if hasattr(result, 'new_items') else False
                        }
                        
                except Exception as e:
                    print(f"Error during inspection: {e}")
                    import traceback
                    traceback.print_exc()
                    return {"status": "error", "error": str(e)}
        
        # Create agent
        config = AgentConfig(mode="rigorous", max_turns=1)
        agent = InspectingCrystaLyse(agent_config=config)
        
        # Test with simple query
        query = "Use smact_validity to check LiFePO4"
        result = await agent.discover_materials(query)
        
        print("\n" + "=" * 60)
        print("Inspection result:", json.dumps(result, indent=2))
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(inspect_result_structure())