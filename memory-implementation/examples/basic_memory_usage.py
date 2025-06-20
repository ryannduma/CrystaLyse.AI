"""
Basic Memory System Usage Example

Demonstrates how to use the CrystaLyse.AI memory system components
including dual working memory, scratchpad, and caching.
"""

import asyncio
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from crystalyse_memory import create_dual_memory, get_all_tools
from crystalyse_memory.short_term import ConversationManager, SessionContextManager


async def demonstrate_dual_working_memory():
    """Demonstrate the dual working memory system."""
    print("=== Dual Working Memory Demonstration ===\n")
    
    # Create dual working memory for a session
    session_id = "demo_session_001"
    user_id = "demo_user"
    
    dual_memory = create_dual_memory(
        session_id=session_id,
        user_id=user_id,
        max_cache_age_hours=24
    )
    
    print(f"Created dual memory for session: {session_id}")
    
    # 1. Demonstrate scratchpad usage
    print("\n1. Scratchpad Reasoning Workspace:")
    
    # Start with a plan
    initial_plan = """
    1. Validate NaCl composition using SMACT
    2. Generate crystal structure using Chemeleon
    3. Calculate formation energy using MACE
    4. Analyse stability and properties
    """
    dual_memory.update_plan(initial_plan)
    print("✓ Initial plan written to scratchpad")
    
    # Add reasoning steps
    dual_memory.log_reasoning_step(
        "NaCl is a simple ionic compound. Expecting cubic structure (rock salt type)."
    )
    
    dual_memory.log_observation(
        "SMACT validation shows Na+ and Cl- are charge balanced (1:1 ratio)."
    )
    
    dual_memory.log_progress(
        "Completed SMACT validation. Moving to structure generation."
    )
    
    # Read current scratchpad
    scratchpad_content = dual_memory.read_scratchpad()
    print(f"Scratchpad has {len(scratchpad_content)} characters of reasoning")
    
    # 2. Demonstrate computational caching
    print("\n2. Computational Caching:")
    
    # Cache a mock SMACT result
    smact_result = {
        "formula": "NaCl",
        "feasible": True,
        "confidence": 0.95,
        "charge_balance": True
    }
    
    cache_key = dual_memory.cache_smact_result("NaCl", smact_result)
    print(f"✓ Cached SMACT result for NaCl")
    
    # Retrieve it
    cached_result = dual_memory.get_smact_result("NaCl")
    if cached_result:
        print(f"✓ Retrieved cached SMACT: feasible = {cached_result['feasible']}")
    
    # Cache a mock Chemeleon structure
    structure_data = {
        "formula": "NaCl",
        "structures": [
            {
                "space_group": "Fm-3m",
                "lattice_parameters": [5.64, 5.64, 5.64, 90, 90, 90],
                "num_atoms": 8
            }
        ]
    }
    
    dual_memory.cache_chemeleon_structure("NaCl", structure_data)
    print("✓ Cached Chemeleon structure for NaCl")
    
    # Cache a mock MACE energy
    energy_data = {
        "energy_per_atom": -1.234,
        "forces": "calculated",
        "stress": "calculated"
    }
    
    dual_memory.cache_mace_energy("NaCl_structure_1", energy_data)
    print("✓ Cached MACE energy calculation")
    
    # 3. Get statistics
    print("\n3. Memory Statistics:")
    stats = dual_memory.get_stats()
    
    cache_stats = stats.get("computational_cache", {})
    scratchpad_stats = stats.get("reasoning_scratchpad", {})
    
    print(f"Cache entries: {cache_stats.get('memory_entries', 0)}")
    print(f"Scratchpad steps: {scratchpad_stats.get('total_steps', 0)}")
    print(f"Scratchpad file: {dual_memory.get_scratchpad_file_path()}")
    
    # 4. Conclude the session
    dual_memory.conclude_query(
        "Successfully validated NaCl composition, generated structure, and calculated energy. "
        "NaCl shows stable ionic bonding with formation energy of -1.234 eV/atom."
    )
    
    print("\n✓ Session concluded with final reasoning")
    
    # Export session summary
    summary = dual_memory.export_session_summary()
    print(f"\nSession Summary: {summary['session_summary']['session_id']}")
    
    return dual_memory


async def demonstrate_conversation_manager():
    """Demonstrate conversation management."""
    print("\n=== Conversation Manager Demonstration ===\n")
    
    # Create conversation manager
    conv_manager = ConversationManager(
        redis_url="redis://localhost:6379",
        max_history_length=100
    )
    
    # Initialize (will fall back to local storage if Redis unavailable)
    await conv_manager.initialize()
    print("✓ Conversation manager initialised")
    
    session_id = "demo_session_001"
    user_id = "demo_user"
    
    # Add some conversation messages
    await conv_manager.add_message(
        session_id=session_id,
        user_id=user_id,
        role="user",
        content="I need to find a stable perovskite with high conductivity"
    )
    
    await conv_manager.add_message(
        session_id=session_id,
        user_id=user_id,
        role="assistant",
        content="I'll help you find stable perovskites. Let me start by checking SMACT feasibility for some candidates.",
        metadata={"tools_planned": ["smact", "chemeleon", "mace"]}
    )
    
    await conv_manager.add_message(
        session_id=session_id,
        user_id=user_id,
        role="assistant",
        content="Found 3 feasible perovskite compositions: BaTiO3, SrTiO3, CaTiO3"
    )
    
    print("✓ Added conversation messages")
    
    # Retrieve conversation history
    history = await conv_manager.get_history(session_id, limit=10)
    print(f"✓ Retrieved {len(history)} messages from conversation history")
    
    for i, msg in enumerate(history, 1):
        print(f"  {i}. {msg.role}: {msg.content[:50]}...")
    
    # Get context summary
    context = await conv_manager.get_context_summary(session_id, max_tokens=500)
    print(f"\nContext summary ({len(context)} characters):")
    print(context[:200] + "..." if len(context) > 200 else context)
    
    await conv_manager.close()
    return conv_manager


async def demonstrate_session_context():
    """Demonstrate session context management."""
    print("\n=== Session Context Manager Demonstration ===\n")
    
    # Create session context manager
    session_manager = SessionContextManager()
    
    session_id = "demo_session_001"
    user_id = "demo_user"
    
    # Create session
    session_state = session_manager.create_session(
        user_id=user_id,
        session_id=session_id,
        initial_context={
            "research_focus": "perovskites",
            "agent_mode": "rigorous"
        }
    )
    
    print(f"✓ Created session: {session_state.session_id}")
    print(f"  Research focus: {session_state.research_focus}")
    print(f"  Agent mode: {session_state.agent_mode}")
    
    # Start a query
    session_manager.start_query(
        session_id=session_id,
        query="Find stable perovskites with high electrical conductivity",
        research_focus="electronic_materials"
    )
    
    # Log some tool usage
    session_manager.log_tool_usage(session_id, "smact")
    session_manager.log_tool_usage(session_id, "chemeleon")
    session_manager.log_tool_usage(session_id, "mace")
    
    # Add discovered materials
    session_manager.add_discovered_material(session_id, "BaTiO3")
    session_manager.add_discovered_material(session_id, "SrTiO3")
    
    # Get session statistics
    stats = session_manager.get_session_statistics(session_id)
    if stats:
        print(f"\nSession Statistics:")
        print(f"  Duration: {stats['duration_minutes']} minutes")
        print(f"  Queries: {stats['query_count']}")
        print(f"  Tools used: {stats['tools_used']}")
        print(f"  Materials found: {stats['materials_discovered']}")
    
    # Get agent context
    agent_context = session_manager.get_context_for_agent(session_id)
    print(f"\nAgent Context keys: {list(agent_context.keys())}")
    
    session_manager.close()
    return session_manager


async def demonstrate_memory_tools():
    """Demonstrate memory tools for agent integration."""
    print("\n=== Memory Tools Demonstration ===\n")
    
    # Get all available tools
    all_tools = get_all_tools()
    
    print(f"Available tools: {len(all_tools)}")
    
    memory_tools = [name for name in all_tools.keys() if 'cache' in name or 'memory' in name]
    scratchpad_tools = [name for name in all_tools.keys() if 'scratchpad' in name or 'plan' in name]
    
    print(f"\nMemory tools ({len(memory_tools)}):")
    for tool in memory_tools:
        print(f"  - {tool}")
    
    print(f"\nScratchpad tools ({len(scratchpad_tools)}):")
    for tool in scratchpad_tools:
        print(f"  - {tool}")
    
    # Create dual memory for context
    dual_memory = create_dual_memory("tool_demo", "demo_user")
    context = {"dual_working_memory": dual_memory}
    
    # Demonstrate a few tools
    print(f"\n--- Tool Usage Examples ---")
    
    # Use scratchpad tools
    from crystalyse_memory.tools.scratchpad_tools import write_to_scratchpad, read_scratchpad
    
    result = write_to_scratchpad(
        "Starting tool demonstration with basic memory operations",
        "plan",
        context
    )
    print(f"write_to_scratchpad: {result}")
    
    result = read_scratchpad(context)
    print(f"read_scratchpad: {result[:100]}...")
    
    # Use memory tools
    from crystalyse_memory.tools.memory_tools import cache_smact_feasibility, get_smact_feasibility
    
    mock_result = {"formula": "NaCl", "feasible": True, "confidence": 0.99}
    
    result = cache_smact_feasibility("NaCl", mock_result, context)
    print(f"cache_smact_feasibility: {result}")
    
    result = get_smact_feasibility("NaCl", context)
    print(f"get_smact_feasibility: {result}")
    
    dual_memory.cleanup()


async def main():
    """Main demonstration function."""
    print("CrystaLyse.AI Memory System - Basic Usage Examples")
    print("=" * 60)
    
    try:
        # Run demonstrations
        dual_memory = await demonstrate_dual_working_memory()
        await demonstrate_conversation_manager()
        await demonstrate_session_context()
        await demonstrate_memory_tools()
        
        print("\n" + "=" * 60)
        print("✅ All demonstrations completed successfully!")
        print("\nNext steps:")
        print("1. Integrate memory tools with OpenAI Agents SDK")
        print("2. Configure Redis for production usage")
        print("3. Implement long-term memory components")
        print("4. Add comprehensive error handling and monitoring")
        
        # Cleanup
        dual_memory.cleanup()
        
    except Exception as e:
        print(f"\n❌ Error during demonstration: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())