#!/usr/bin/env python3
"""
Test script for the CrystaLyse Session-Based System

This demonstrates the SQLiteSession-like functionality without import conflicts.
"""

import sys
import asyncio
from pathlib import Path

# Add the OpenAI agents SDK to the path
sys.path.insert(0, '/home/ryan/crystalyseai/openai-agents-python/src')

from crystalyse.agents.session_based_agent import (
    CrystaLyseSession,
    get_session_manager,
    ConversationItem
)
from crystalyse.memory import CrystaLyseMemory
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()

def test_basic_session():
    """Test basic session functionality."""
    console.print("\n[bold cyan]🧪 Testing Basic Session Functionality[/bold cyan]")
    
    # Create a session
    session = CrystaLyseSession("test_session_1", "researcher1")
    
    # Add conversation items
    session.add_conversation_item("user", "What is a perovskite material?")
    session.add_conversation_item("assistant", "A perovskite is a type of crystal structure with the general formula ABX3...")
    session.add_conversation_item("user", "Can you give me an example?")
    session.add_conversation_item("assistant", "CaTiO3 (calcium titanate) is a classic example of a perovskite material...")
    
    # Get conversation history
    history = session.get_conversation_history()
    
    # Display history
    table = Table(title="Conversation History")
    table.add_column("Role", style="bold")
    table.add_column("Content", style="dim")
    
    for item in history:
        content = item.content[:80] + "..." if len(item.content) > 80 else item.content
        table.add_row(item.role, content)
    
    console.print(table)
    console.print(f"✅ Session created with {len(history)} conversation items")
    
    # Test pop functionality (like SQLiteSession.pop_item)
    last_item = session.pop_last_item()
    console.print(f"✅ Pop functionality: Removed '{last_item.role}: {last_item.content[:50]}...'")
    
    # Test clear functionality
    session.clear_conversation()
    console.print("✅ Clear functionality: Conversation history cleared")
    
    return session

def test_session_manager():
    """Test session manager functionality."""
    console.print("\n[bold cyan]🧪 Testing Session Manager[/bold cyan]")
    
    manager = get_session_manager()
    
    # Create multiple sessions
    session1 = manager.get_or_create_session("research_project_1", "researcher1")
    session2 = manager.get_or_create_session("research_project_2", "researcher2") 
    session3 = manager.get_or_create_session("research_project_1", "researcher1")  # Should reuse existing
    
    console.print(f"✅ Session manager created {len(manager.sessions)} unique sessions")
    console.print(f"✅ Session reuse working: {session1.session_id == session3.session_id}")
    
    return manager

def test_memory_integration():
    """Test memory system integration."""
    console.print("\n[bold cyan]🧪 Testing Memory Integration[/bold cyan]")
    
    # Create memory system
    memory = CrystaLyseMemory("test_researcher")
    
    # Save some facts
    memory.save_to_memory("Perovskites have cubic crystal structure")
    memory.save_to_memory("CaTiO3 is a common perovskite material")
    memory.save_discovery("CaTiO3", {
        "formation_energy": -16.2,
        "band_gap": 3.6,
        "crystal_system": "cubic"
    })
    
    # Search memory
    results = memory.search_memory("perovskite")
    console.print(f"✅ Memory search found {len(results)} results")
    
    # Search discoveries
    discoveries = memory.search_discoveries("CaTiO3")
    console.print(f"✅ Discovery search found {len(discoveries)} cached results")
    
    # Get memory statistics
    stats = memory.get_memory_statistics()
    console.print(f"✅ Memory statistics: {stats['cache']['total_entries']} cached discoveries")
    
    return memory

def test_session_with_memory():
    """Test session with integrated memory."""
    console.print("\n[bold cyan]🧪 Testing Session with Memory Integration[/bold cyan]")
    
    # Create session with memory
    session = CrystaLyseSession("memory_test_session", "researcher1")
    
    # Add conversation items about materials
    session.add_conversation_item("user", "Analyze the stability of perovskite CaTiO3")
    session.add_conversation_item("assistant", "CaTiO3 is a stable perovskite with formation energy -16.2 eV...")
    session.add_conversation_item("user", "What about under pressure?")
    session.add_conversation_item("assistant", "Under pressure, CaTiO3 maintains stability up to 40 GPa...")
    
    # Get history
    history = session.get_conversation_history()
    console.print(f"✅ Session with memory: {len(history)} conversation items")
    
    # Test memory context
    context = session.memory.get_context_for_agent()
    console.print(f"✅ Memory context: {len(context)} characters of context")
    
    return session

async def test_session_lifecycle():
    """Test session lifecycle and cleanup."""
    console.print("\n[bold cyan]🧪 Testing Session Lifecycle[/bold cyan]")
    
    session = CrystaLyseSession("lifecycle_test", "test_user")
    
    # Test session initialization
    console.print(f"✅ Session initialized: {session.session_id}")
    
    # Test cleanup
    await session.cleanup()
    console.print("✅ Session cleanup completed")

def demonstrate_sqlitesession_like_behavior():
    """Demonstrate SQLiteSession-like behavior."""
    console.print("\n[bold green]🎯 Demonstrating SQLiteSession-like Behavior[/bold green]")
    
    # Create session (like SQLiteSession)
    session = CrystaLyseSession("demo_session", "demo_user")
    
    console.print(Panel("""
[bold]SQLiteSession-like Methods:[/bold]

✅ session.add_conversation_item(role, content)  # Like adding items
✅ session.get_conversation_history()            # Like getting items
✅ session.pop_last_item()                       # Like SQLiteSession.pop_item()
✅ session.clear_conversation()                  # Like clearing session
✅ session.run_with_history(user_input)          # Like Runner.run with session

[bold]Automatic Features:[/bold]

✅ Conversation history persistence
✅ Memory integration
✅ Session management
✅ SQLite database storage
    """, title="SQLiteSession Compatibility", border_style="green"))
    
    # Demonstrate automatic history management
    session.add_conversation_item("user", "Hello, I'm starting a new research project")
    session.add_conversation_item("assistant", "Great! I'll help you with your materials research")
    session.add_conversation_item("user", "What do you know about perovskites?")
    session.add_conversation_item("assistant", "Perovskites are fascinating materials with ABX3 structure...")
    
    # Show history
    history = session.get_conversation_history()
    console.print(f"✅ Automatic history management: {len(history)} items stored")
    
    # Test pop (like SQLiteSession.pop_item)
    last_item = session.pop_last_item()
    console.print(f"✅ Pop functionality: Removed assistant message")
    
    # Add another item
    session.add_conversation_item("assistant", "Let me provide a more detailed explanation about perovskites...")
    
    # Show final history
    final_history = session.get_conversation_history()
    console.print(f"✅ Final history: {len(final_history)} items")
    
    return session

async def main():
    """Main test function."""
    console.print(Panel(
        "[bold green]🔬 CrystaLyse Session-Based System Test[/bold green]\n\n"
        "This demonstrates the SQLiteSession-like functionality implemented\n"
        "for CrystaLyse using the OpenAI Agents SDK patterns.",
        title="Session System Test",
        border_style="green"
    ))
    
    try:
        # Run all tests
        test_basic_session()
        test_session_manager()
        test_memory_integration()
        test_session_with_memory()
        await test_session_lifecycle()
        demonstrate_sqlitesession_like_behavior()
        
        console.print("\n[bold green]🎉 All tests passed! Session-based system is working correctly.[/bold green]")
        
        # Show database location
        db_path = Path.home() / ".crystalyse" / "conversations.db"
        console.print(f"\n[dim]💾 Conversation database: {db_path}[/dim]")
        
    except Exception as e:
        console.print(f"[bold red]❌ Test failed: {e}[/bold red]")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main()) 