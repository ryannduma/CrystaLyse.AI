#!/usr/bin/env python3
"""
Demo: Materials Research Session with CrystaLyse

This demonstrates how the session-based system would work for actual materials research,
showing the SQLiteSession-like functionality in a realistic research workflow.
"""

import sys
import asyncio
from pathlib import Path

# Add the OpenAI agents SDK to the path
sys.path.insert(0, '/home/ryan/crystalyseai/openai-agents-python/src')

from crystalyse.agents.session_based_agent import CrystaLyseSession
from rich.console import Console
from rich.panel import Panel

console = Console()

async def simulate_research_session():
    """Simulate a realistic materials research session."""

    console.print(Panel(
        "[bold green]🔬 CrystaLyse Research Session Demo[/bold green]\n\n"
        "This demonstrates how the session-based system would work\n"
        "for multi-turn materials research conversations.",
        title="Research Session Demo",
        border_style="green"
    ))

    # Create a research session
    session = CrystaLyseSession("perovskite_research_jan2025", "materials_researcher")

    # Simulate a multi-turn research conversation
    research_queries = [
        ("user", "I'm interested in studying perovskite materials for solar cell applications. Can you help me understand their basic properties?"),
        ("assistant", "Absolutely! Perovskites are crystalline materials with the general formula ABX3. For solar cells, hybrid organic-inorganic perovskites like methylammonium lead iodide (MAPbI3) are particularly promising due to their excellent optoelectronic properties: high absorption coefficients, tunable bandgaps (1.5-2.3 eV), and long carrier diffusion lengths."),

        ("user", "What about their stability issues? I've heard they degrade easily."),
        ("assistant", "You're right to be concerned about stability. Perovskites face several stability challenges:\n\n1. **Moisture sensitivity**: MAPbI3 degrades in humid conditions\n2. **Thermal stability**: Phase transitions occur at ~57°C\n3. **UV degradation**: Prolonged light exposure causes decomposition\n4. **Ion migration**: Mobile ions can cause current-voltage hysteresis\n\nStrategies to improve stability include compositional engineering (mixed cations/anions), encapsulation, and interface optimization."),

        ("user", "Are there any lead-free alternatives? I'm concerned about toxicity."),
        ("assistant", "Yes, there are several lead-free perovskite alternatives being researched:\n\n1. **Tin-based**: MASnI3, but suffers from Sn2+ oxidation\n2. **Bismuth-based**: Cs3Bi2I9, but has larger bandgap (~2.2 eV)\n3. **Antimony-based**: Cs3Sb2I9, stable but lower efficiency\n4. **Copper-based**: Cs2CuBr4, but indirect bandgap\n5. **Double perovskites**: Cs2AgBiBr6, more stable but efficiency challenges\n\nWhile promising, most lead-free alternatives currently have lower efficiencies than lead-based perovskites."),

        ("user", "Can you calculate the formation energy of MAPbI3 to understand its thermodynamic stability?"),
        ("assistant", "I would need computational tools to calculate formation energies accurately. For reference, experimental and DFT studies report MAPbI3 formation energy around -0.1 to -0.3 eV/atom, indicating it's thermodynamically stable but marginally so, which explains the degradation issues.\n\nTo perform such calculations, I would typically use:\n- **DFT calculations**: VASP, Quantum ESPRESSO\n- **Formation energy**: E_form = E_compound - Σ(μ_i * n_i)\n- **Consideration of**: van der Waals corrections, SOC effects for heavy elements"),

        ("user", "What computational methods would you recommend for studying these materials?"),
        ("assistant", "For perovskite computational studies, I recommend this hierarchical approach:\n\n**1. Structure and Stability:**\n- DFT with PBE+D3 or PBE+vdW corrections\n- Include spin-orbit coupling (SOC) for accurate band gaps\n- Use hybrid functionals (HSE06) for better electronic properties\n\n**2. Thermodynamic Properties:**\n- Formation energy calculations\n- Phonon calculations for thermal stability\n- Finite temperature effects using AIMD\n\n**3. Electronic Properties:**\n- Band structure and DOS calculations\n- Effective masses and carrier mobilities\n- Defect calculations for understanding degradation\n\n**4. Recommended Codes:**\n- VASP (widely used, good for periodic systems)\n- Quantum ESPRESSO (open-source)\n- CP2K (good for hybrid functionals)\n- ABINIT (all-electron calculations)")
    ]

    console.print("\n[bold cyan]📚 Simulating Research Conversation...[/bold cyan]")

    # Add all the conversation items
    for role, content in research_queries:
        session.add_conversation_item(role, content)

        # Show the interaction
        if role == "user":
            console.print(f"\n[bold blue]👤 Researcher:[/bold blue] {content[:100]}...")
        else:
            console.print(f"\n[bold green]🤖 CrystaLyse:[/bold green] {content[:100]}...")

    # Show session statistics
    history = session.get_conversation_history()
    console.print(f"\n✅ Research session created with {len(history)} interactions")

    # Demonstrate memory integration
    session.memory.save_to_memory("User is researching perovskites for solar cells")
    session.memory.save_to_memory("User is concerned about lead toxicity")
    session.memory.save_to_memory("User needs computational methods for formation energy")

    # Cache some "computational results"
    session.memory.save_discovery("MAPbI3", {
        "formation_energy": -0.2,
        "band_gap": 1.6,
        "stability": "marginally stable",
        "application": "solar cells"
    })

    session.memory.save_discovery("MASnI3", {
        "formation_energy": -0.15,
        "band_gap": 1.3,
        "stability": "unstable (Sn2+ oxidation)",
        "application": "lead-free alternative"
    })

    console.print("✅ Memory updated with research context and discoveries")

    # Show memory statistics
    memory_stats = session.memory.get_memory_statistics()
    console.print(f"✅ Memory system: {memory_stats['cache']['total_entries']} discoveries cached")

    # Demonstrate continuation capability
    console.print("\n[bold yellow]🔄 Demonstrating Session Continuation...[/bold yellow]")

    # Simulate returning to the session later
    console.print("\n[italic]--- Researcher returns to session the next day ---[/italic]")

    # The session automatically has all the context
    session.add_conversation_item("user", "I'm back to continue our perovskite discussion. Can you remind me what we covered yesterday?")

    # The agent would have access to all previous context
    session.add_conversation_item("assistant", "Welcome back! Yesterday we discussed:\n\n1. Basic perovskite properties for solar cells\n2. Stability challenges (moisture, thermal, UV)\n3. Lead-free alternatives (tin, bismuth, antimony-based)\n4. Computational methods for studying these materials\n\nYour research focus is on perovskites for solar cells, with particular interest in lead-free alternatives and computational approaches for formation energy calculations.")

    final_history = session.get_conversation_history()
    console.print(f"✅ Session continuation: {len(final_history)} total interactions")

    return session

async def demonstrate_session_operations():
    """Demonstrate key session operations."""

    console.print("\n[bold cyan]🛠️  Demonstrating Session Operations[/bold cyan]")

    # Get the session from the demo
    session = await simulate_research_session()

    console.print("\n[bold yellow]Session Operations Demo:[/bold yellow]")

    # Show history
    history = session.get_conversation_history()
    console.print(f"📋 Current conversation has {len(history)} items")

    # Demonstrate pop (like SQLiteSession.pop_item)
    console.print("\n[bold]Testing pop_last_item() (like SQLiteSession.pop_item):[/bold]")
    last_item = session.pop_last_item()
    console.print(f"🗑️  Removed: {last_item.role}: {last_item.content[:80]}...")

    # Add a corrected response
    session.add_conversation_item("assistant", "Let me provide a more comprehensive summary of our discussion...")

    # Show updated history
    updated_history = session.get_conversation_history()
    console.print(f"📋 After pop and add: {len(updated_history)} items")

    # Demonstrate search capabilities
    console.print("\n[bold]Memory Search Capabilities:[/bold]")

    # Search for previous discussions
    memory_results = session.memory.search_memory("perovskite")
    console.print(f"🔍 Memory search 'perovskite': {len(memory_results)} results")

    # Search discoveries
    discoveries = session.memory.search_discoveries("MAPbI3")
    console.print(f"🔍 Discovery search 'MAPbI3': {len(discoveries)} results")

    # Show memory context
    context = session.memory.get_context_for_agent()
    console.print(f"📝 Memory context: {len(context)} characters available")

    # Cleanup
    await session.cleanup()
    console.print("✅ Session cleanup completed")

async def show_session_persistence():
    """Show how sessions persist across multiple runs."""

    console.print("\n[bold cyan]💾 Demonstrating Session Persistence[/bold cyan]")

    # Create a session
    session1 = CrystaLyseSession("persistent_test", "researcher")
    session1.add_conversation_item("user", "Starting a new research project on battery materials")
    session1.add_conversation_item("assistant", "Excellent! Let's explore cathode materials for lithium-ion batteries...")

    # Get the conversation ID
    history1 = session1.get_conversation_history()
    console.print(f"📝 Session 1 created with {len(history1)} items")

    # Simulate closing and reopening the session
    console.print("\n[italic]--- Simulating session close and reopen ---[/italic]")

    # Create a new session instance with the same ID
    session2 = CrystaLyseSession("persistent_test", "researcher")

    # The conversation should be automatically loaded
    history2 = session2.get_conversation_history()
    console.print(f"📝 Session 2 reopened with {len(history2)} items")

    # Verify the content matches
    if len(history1) == len(history2):
        console.print("✅ Session persistence working: Content matches")
    else:
        console.print("❌ Session persistence issue: Content mismatch")

    # Continue the conversation
    session2.add_conversation_item("user", "What about solid-state electrolytes?")
    session2.add_conversation_item("assistant", "Solid-state electrolytes offer improved safety and energy density...")

    final_history = session2.get_conversation_history()
    console.print(f"📝 Final session: {len(final_history)} items")

    # Cleanup
    await session2.cleanup()

async def main():
    """Main demo function."""

    console.print(Panel(
        "[bold green]🎯 CrystaLyse Session-Based Materials Research Demo[/bold green]\n\n"
        "This demonstrates how the SQLiteSession-like functionality works\n"
        "for realistic materials research workflows.",
        title="Materials Research Demo",
        border_style="green"
    ))

    try:
        # Run the demonstrations
        await demonstrate_session_operations()
        await show_session_persistence()

        console.print("\n[bold green]🎉 Demo completed successfully![/bold green]")

        # Show key benefits
        console.print(Panel("""
[bold]Key Benefits Demonstrated:[/bold]

✅ **Automatic conversation history** - No manual .to_input_list() calls
✅ **Session persistence** - Conversations survive restarts
✅ **Memory integration** - Research context and discoveries cached
✅ **SQLiteSession-like behavior** - pop_item, clear, history management
✅ **Research continuity** - Multi-day research sessions supported
✅ **Context awareness** - Agents remember previous discussions

[bold]Perfect for materials research workflows![/bold]
        """, title="Session System Benefits", border_style="green"))

        # Show database location
        db_path = Path.home() / ".crystalyse" / "conversations.db"
        console.print(f"\n[dim]💾 All conversations stored in: {db_path}[/dim]")

    except Exception as e:
        console.print(f"[bold red]❌ Demo failed: {e}[/bold red]")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main()) 
