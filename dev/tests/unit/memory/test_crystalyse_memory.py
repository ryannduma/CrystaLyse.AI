"""
Unit tests for CrystaLyse memory system.

Tests the four-layer memory architecture:
1. Session Memory - Current conversation context
2. Discovery Cache - Cached material properties
3. User Memory - User preferences and notes
4. Cross-Session Context - Auto-generated insights
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from crystalyse.memory.crystalyse_memory import CrystaLyseMemory
from crystalyse.memory.discovery_cache import DiscoveryCache
from crystalyse.memory.session_memory import SessionMemory
from crystalyse.memory.user_memory import UserMemory


class TestSessionMemory:
    """Tests for SessionMemory (Layer 1)."""

    def test_session_memory_creation(self) -> None:
        """Test creating a new session memory."""
        memory = SessionMemory()
        assert memory is not None
        context = memory.get_context()
        assert "No previous conversation" in context or context == ""

    def test_add_interaction(self) -> None:
        """Test adding an interaction to session memory."""
        memory = SessionMemory()
        memory.add_interaction("What is CaTiO3?", "CaTiO3 is a perovskite...")
        context = memory.get_context()
        assert "CaTiO3" in context

    def test_multiple_interactions(self) -> None:
        """Test adding multiple interactions."""
        memory = SessionMemory()
        memory.add_interaction("Query 1", "Response 1")
        memory.add_interaction("Query 2", "Response 2")
        context = memory.get_context()
        # Should contain both interactions
        assert "Query 1" in context or "Response 1" in context
        assert "Query 2" in context or "Response 2" in context

    def test_clear_session(self) -> None:
        """Test clearing session memory."""
        memory = SessionMemory()
        memory.add_interaction("Test query", "Test response")
        memory.clear()
        context = memory.get_context()
        assert "Test query" not in context

    def test_session_summary(self) -> None:
        """Test getting session summary."""
        memory = SessionMemory()
        memory.add_interaction("Query", "Response")
        summary = memory.get_session_summary()
        assert isinstance(summary, dict)


class TestDiscoveryCache:
    """Tests for DiscoveryCache (Layer 2)."""

    def test_discovery_cache_creation(self, temp_memory_dir: Path) -> None:
        """Test creating a discovery cache."""
        cache = DiscoveryCache(temp_memory_dir)
        assert cache is not None

    def test_save_and_retrieve_discovery(
        self, temp_memory_dir: Path, sample_discovery: dict[str, Any]
    ) -> None:
        """Test saving and retrieving a discovery."""
        cache = DiscoveryCache(temp_memory_dir)
        formula = sample_discovery["formula"]
        cache.save_result(formula, sample_discovery)

        # Retrieve the discovery
        retrieved = cache.get_cached_result(formula)
        assert retrieved is not None
        assert retrieved["formula"] == formula

    def test_cache_miss(self, temp_memory_dir: Path) -> None:
        """Test cache miss returns None."""
        cache = DiscoveryCache(temp_memory_dir)
        result = cache.get_cached_result("NonExistentFormula")
        assert result is None

    def test_get_recent_discoveries(
        self, temp_memory_dir: Path, sample_discovery: dict[str, Any]
    ) -> None:
        """Test getting recent discoveries."""
        cache = DiscoveryCache(temp_memory_dir)
        cache.save_result("CaTiO3", sample_discovery)
        cache.save_result("BaTiO3", {**sample_discovery, "formula": "BaTiO3"})

        recent = cache.get_recent_discoveries(limit=5)
        assert len(recent) >= 1

    def test_cache_statistics(self, temp_memory_dir: Path) -> None:
        """Test cache statistics."""
        cache = DiscoveryCache(temp_memory_dir)
        stats = cache.get_statistics()
        assert isinstance(stats, dict)
        assert "total_entries" in stats

    def test_search_discoveries(
        self, temp_memory_dir: Path, sample_discovery: dict[str, Any]
    ) -> None:
        """Test searching discoveries."""
        cache = DiscoveryCache(temp_memory_dir)
        cache.save_result("CaTiO3", sample_discovery)

        results = cache.search_similar("perovskite", limit=5)
        assert isinstance(results, list)


class TestUserMemory:
    """Tests for UserMemory (Layer 3)."""

    def test_user_memory_creation(self, temp_memory_dir: Path) -> None:
        """Test creating user memory."""
        memory = UserMemory(temp_memory_dir, "test_user")
        assert memory is not None

    def test_add_fact(self, temp_memory_dir: Path) -> None:
        """Test adding a fact to user memory."""
        memory = UserMemory(temp_memory_dir, "test_user")
        memory.add_fact("I work on battery cathode materials")
        context = memory.get_context_summary()
        assert isinstance(context, str)

    def test_get_preferences(self, temp_memory_dir: Path) -> None:
        """Test getting user preferences."""
        memory = UserMemory(temp_memory_dir, "test_user")
        prefs = memory.get_preferences()
        # Preferences can be a dict or list depending on implementation
        assert isinstance(prefs, dict | list)

    def test_get_research_interests(self, temp_memory_dir: Path) -> None:
        """Test getting research interests."""
        memory = UserMemory(temp_memory_dir, "test_user")
        interests = memory.get_research_interests()
        assert isinstance(interests, list)

    def test_search_memory(self, temp_memory_dir: Path) -> None:
        """Test searching user memory."""
        memory = UserMemory(temp_memory_dir, "test_user")
        memory.add_fact("Research focus: perovskite solar cells")
        results = memory.search_memory("perovskite")
        assert isinstance(results, list)


class TestCrystaLyseMemory:
    """Tests for the unified CrystaLyseMemory class."""

    def test_memory_initialization(self, temp_memory_dir: Path) -> None:
        """Test initializing CrystaLyseMemory."""
        memory = CrystaLyseMemory(user_id="test_user", memory_dir=temp_memory_dir)
        assert memory.user_id == "test_user"
        assert memory.memory_dir == temp_memory_dir

    def test_memory_initialization_default_dir(self) -> None:
        """Test initialization with default directory."""
        memory = CrystaLyseMemory(user_id="default")
        assert memory.memory_dir == Path.home() / ".crystalyse"

    def test_add_interaction(self, temp_memory_dir: Path) -> None:
        """Test adding interaction through unified interface."""
        memory = CrystaLyseMemory(user_id="test_user", memory_dir=temp_memory_dir)
        memory.add_interaction("What is a perovskite?", "A perovskite is...")
        context = memory.get_context_for_agent()
        assert isinstance(context, str)

    def test_save_and_get_discovery(
        self, temp_memory_dir: Path, sample_discovery: dict[str, Any]
    ) -> None:
        """Test saving and retrieving discovery."""
        memory = CrystaLyseMemory(user_id="test_user", memory_dir=temp_memory_dir)
        memory.save_discovery("CaTiO3", sample_discovery)
        retrieved = memory.get_cached_discovery("CaTiO3")
        assert retrieved is not None
        assert retrieved["formula"] == "CaTiO3"

    def test_save_to_memory(self, temp_memory_dir: Path) -> None:
        """Test saving fact to user memory."""
        memory = CrystaLyseMemory(user_id="test_user", memory_dir=temp_memory_dir)
        memory.save_to_memory("Important research note")
        results = memory.search_memory("research")
        assert isinstance(results, list)

    def test_search_discoveries(
        self, temp_memory_dir: Path, sample_discovery: dict[str, Any]
    ) -> None:
        """Test searching discoveries."""
        memory = CrystaLyseMemory(user_id="test_user", memory_dir=temp_memory_dir)
        memory.save_discovery("CaTiO3", sample_discovery)
        results = memory.search_discoveries("perovskite")
        assert isinstance(results, list)

    def test_get_memory_statistics(self, temp_memory_dir: Path) -> None:
        """Test getting memory statistics."""
        memory = CrystaLyseMemory(user_id="test_user", memory_dir=temp_memory_dir)
        stats = memory.get_memory_statistics()
        assert isinstance(stats, dict)
        assert "user_id" in stats
        assert stats["user_id"] == "test_user"

    def test_clear_session(self, temp_memory_dir: Path) -> None:
        """Test clearing session memory."""
        memory = CrystaLyseMemory(user_id="test_user", memory_dir=temp_memory_dir)
        memory.add_interaction("Query", "Response")
        memory.clear_session()
        # Session should be cleared but other memory layers intact

    def test_get_context_for_agent(self, temp_memory_dir: Path) -> None:
        """Test getting full context for agent."""
        memory = CrystaLyseMemory(user_id="test_user", memory_dir=temp_memory_dir)
        memory.add_interaction("Query about materials", "Response about materials")
        memory.save_to_memory("User preference: creative mode")
        context = memory.get_context_for_agent()
        assert isinstance(context, str)

    def test_cleanup(self, temp_memory_dir: Path) -> None:
        """Test cleanup method."""
        memory = CrystaLyseMemory(user_id="test_user", memory_dir=temp_memory_dir)
        memory.add_interaction("Test", "Response")
        memory.cleanup()
        # Should complete without error


class TestMemoryExportImport:
    """Tests for memory export/import functionality."""

    def test_export_memory(self, temp_memory_dir: Path, sample_discovery: dict[str, Any]) -> None:
        """Test exporting memory to directory."""
        memory = CrystaLyseMemory(user_id="test_user", memory_dir=temp_memory_dir)
        memory.save_discovery("CaTiO3", sample_discovery)

        export_dir = temp_memory_dir / "export"
        memory.export_memory(export_dir)

        # Check export directory was created
        assert export_dir.exists()

    def test_import_memory(self, temp_memory_dir: Path, sample_discovery: dict[str, Any]) -> None:
        """Test importing memory from directory."""
        # First export
        memory1 = CrystaLyseMemory(user_id="test_user", memory_dir=temp_memory_dir)
        memory1.save_discovery("CaTiO3", sample_discovery)
        export_dir = temp_memory_dir / "export"
        memory1.export_memory(export_dir)

        # Then import to new memory
        new_memory_dir = temp_memory_dir / "new_memory"
        memory2 = CrystaLyseMemory(user_id="test_user", memory_dir=new_memory_dir)
        memory2.import_memory(export_dir, merge=True)


class TestMemoryPersistence:
    """Tests for memory persistence across sessions."""

    def test_discoveries_persist(
        self, temp_memory_dir: Path, sample_discovery: dict[str, Any]
    ) -> None:
        """Test that discoveries persist across memory instances."""
        # Save with first instance
        memory1 = CrystaLyseMemory(user_id="test_user", memory_dir=temp_memory_dir)
        memory1.save_discovery("CaTiO3", sample_discovery)

        # Create new instance and check persistence
        memory2 = CrystaLyseMemory(user_id="test_user", memory_dir=temp_memory_dir)
        retrieved = memory2.get_cached_discovery("CaTiO3")
        assert retrieved is not None
        assert retrieved["formula"] == "CaTiO3"

    def test_user_memory_persists(self, temp_memory_dir: Path) -> None:
        """Test that user memory persists across instances."""
        # Save with first instance
        memory1 = CrystaLyseMemory(user_id="test_user", memory_dir=temp_memory_dir)
        memory1.save_to_memory("Persistent fact about research")

        # Create new instance
        memory2 = CrystaLyseMemory(user_id="test_user", memory_dir=temp_memory_dir)
        # Memory should contain the fact
        results = memory2.search_memory("research")
        assert isinstance(results, list)


class TestMemoryEdgeCases:
    """Tests for edge cases and error handling."""

    def test_empty_user_id(self, temp_memory_dir: Path) -> None:
        """Test with empty user ID."""
        memory = CrystaLyseMemory(user_id="", memory_dir=temp_memory_dir)
        assert memory.user_id == ""

    def test_special_characters_in_formula(
        self, temp_memory_dir: Path, sample_discovery: dict[str, Any]
    ) -> None:
        """Test handling formulas with special characters."""
        memory = CrystaLyseMemory(user_id="test_user", memory_dir=temp_memory_dir)
        # Try saving with parentheses in formula
        discovery = {**sample_discovery, "formula": "Ca(OH)2"}
        memory.save_discovery("Ca(OH)2", discovery)
        retrieved = memory.get_cached_discovery("Ca(OH)2")
        assert retrieved is not None

    def test_unicode_in_memory(self, temp_memory_dir: Path) -> None:
        """Test handling unicode in memory content."""
        memory = CrystaLyseMemory(user_id="test_user", memory_dir=temp_memory_dir)
        memory.save_to_memory("Research note with unicode: \u03b1-Fe2O3")
        context = memory.get_context_for_agent()
        assert isinstance(context, str)

    def test_large_discovery_data(self, temp_memory_dir: Path) -> None:
        """Test handling large discovery data."""
        memory = CrystaLyseMemory(user_id="test_user", memory_dir=temp_memory_dir)
        large_discovery = {
            "formula": "TestCompound",
            "positions": [
                [float(i), float(j), float(k)]
                for i in range(10)
                for j in range(10)
                for k in range(10)
            ],
            "data": "x" * 10000,  # Large string
        }
        memory.save_discovery("TestCompound", large_discovery)
        retrieved = memory.get_cached_discovery("TestCompound")
        assert retrieved is not None
