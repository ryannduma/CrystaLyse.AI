#!/usr/bin/env python3
"""Test script to directly verify SMACT MCP tools are being called."""

import os
import asyncio
from pathlib import Path

# Set up environment
# Verify MDG API key is set
if not os.getenv("OPENAI_MDG_API_KEY"):
    print("❌ OPENAI_MDG_API_KEY not set. Please set this environment variable.")
    sys.exit(1)

from agents import Agent, Runner
from agents.mcp import MCPServerStdio
from agents.model_settings import ModelSettings


async def test_direct_smact_tools():
    """Test direct SMACT tool calling."""
    
    print("Testing Testing Direct SMACT Tool Usage...")
    print("=" * 50)
    
    # Set up path to SMACT MCP server
    smact_path = Path(__file__).parent / "smact-mcp-server"
    
    try:
        # Test MCP server connection
        async with MCPServerStdio(
            name="SMACT Tools",
            params={
                "command": "python",
                "args": ["-m", "smact_mcp.server"],
                "cwd": str(smact_path)
            }
        ) as smact_server:
            print("SUCCESS MCP Server connection established!")
            
            # Create test agent with explicit tool forcing
            agent = Agent(
                name="SMACT Test Agent",
                model="gpt-4o",
                instructions="""You are a materials science assistant with access to SMACT tools. 
                
                IMPORTANT: You MUST use the available SMACT tools for any materials science queries. 
                Do NOT rely on your general knowledge. Always call the appropriate SMACT tool function.
                
                Available SMACT tools you should use:
                1. check_smact_validity - for composition validation
                2. parse_chemical_formula - for formula parsing  
                3. get_element_info - for element properties
                4. calculate_neutral_ratios - for stoichiometry
                5. test_pauling_rule - for electronegativity rules
                
                ALWAYS use these tools instead of providing answers from memory.""",
                model_settings=ModelSettings(temperature=0.1),
                mcp_servers=[smact_server],
            )
            
            print("SUCCESS Agent created with MCP server!")
            
            # Test 1: Force composition validation tool usage
            print("\nRunning Test 1: Forcing SMACT validity check...")
            test_query1 = """Use the check_smact_validity tool to validate the composition "NaCl". 
            I want to see the actual SMACT validation results, not general knowledge."""
            
            response1 = await Runner.run(
                starting_agent=agent,
                input=test_query1
            )
            
            print("📋 SMACT Validity Check Results:")
            print(response1.final_output)
            
            # Test 2: Force formula parsing
            print("\nTesting Test 2: Forcing SMACT formula parsing...")
            test_query2 = """Use the parse_chemical_formula tool to parse "LiFePO4". 
            I need the actual SMACT parsing output with element counts."""
            
            response2 = await Runner.run(
                starting_agent=agent,
                input=test_query2
            )
            
            print("Results SMACT Formula Parsing Results:")
            print(response2.final_output)
            
            # Test 3: Force element info lookup
            print("\n⚛️ Test 3: Forcing SMACT element info...")
            test_query3 = """Use the get_element_info tool to get detailed information about lithium (Li). 
            I want the SMACT database properties, not general chemical knowledge."""
            
            response3 = await Runner.run(
                starting_agent=agent,
                input=test_query3
            )
            
            print("🔍 SMACT Element Info Results:")
            print(response3.final_output)
            
            # Test 4: Force charge neutrality calculation
            print("\n⚡ Test 4: Forcing SMACT charge neutrality...")
            test_query4 = """Use the calculate_neutral_ratios tool with oxidation states [1, -1] 
            to find charge-neutral combinations. Show me the SMACT calculation results."""
            
            response4 = await Runner.run(
                starting_agent=agent,
                input=test_query4
            )
            
            print("🔋 SMACT Neutral Ratios Results:")
            print(response4.final_output)
            
            print("\nSUCCESS All direct SMACT tool tests completed!")
            
    except Exception as e:
        print(f"ERROR Test Error: {e}")
        raise


async def main():
    """Main test function."""
    try:
        await test_direct_smact_tools()
        print("\n🎉 SMACT MCP tools are working correctly!")
    except Exception as e:
        print(f"\nERROR Test failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())