"""Unit tests for discovery cache.

Tests the SQLite-backed computation cache with parameters_hash support.
"""

from __future__ import annotations

from pathlib import Path

from crystalyse.memory.discovery_cache import (
    CachedDiscovery,
    DiscoveryCache,
    _hash_params,
)


class TestHashParams:
    """Tests for _hash_params helper function."""

    def test_empty_dict_hash(self) -> None:
        """Test hashing empty dict."""
        h = _hash_params({})
        assert isinstance(h, str)
        assert len(h) == 16

    def test_deterministic_hash(self) -> None:
        """Test that same params produce same hash."""
        params = {"model": "medium", "temperature": 0.5}
        h1 = _hash_params(params)
        h2 = _hash_params(params)
        assert h1 == h2

    def test_order_independent_hash(self) -> None:
        """Test that dict order doesn't affect hash."""
        h1 = _hash_params({"a": 1, "b": 2})
        h2 = _hash_params({"b": 2, "a": 1})
        assert h1 == h2

    def test_different_params_different_hash(self) -> None:
        """Test that different params produce different hash."""
        h1 = _hash_params({"model": "small"})
        h2 = _hash_params({"model": "large"})
        assert h1 != h2


class TestDiscoveryCache:
    """Tests for DiscoveryCache class."""

    def test_cache_creation(self, tmp_path: Path) -> None:
        """Test creating a discovery cache."""
        db_path = tmp_path / "test.db"
        cache = DiscoveryCache(db_path=db_path)
        assert cache is not None
        assert db_path.exists()

    def test_put_and_get(self, tmp_path: Path) -> None:
        """Test storing and retrieving a result."""
        db_path = tmp_path / "test.db"
        cache = DiscoveryCache(db_path=db_path)

        result = {"energy": -5.2, "converged": True}
        cache.put("LiFePO4", "mace_energy", result)

        retrieved = cache.get("LiFePO4", "mace_energy")
        assert retrieved is not None
        assert retrieved["energy"] == -5.2
        assert retrieved["converged"] is True

    def test_get_returns_none_on_miss(self, tmp_path: Path) -> None:
        """Test that get returns None for missing entries."""
        db_path = tmp_path / "test.db"
        cache = DiscoveryCache(db_path=db_path)

        result = cache.get("NonExistent", "mace_energy")
        assert result is None

    def test_params_differentiation(self, tmp_path: Path) -> None:
        """Test that different params are cached separately."""
        db_path = tmp_path / "test.db"
        cache = DiscoveryCache(db_path=db_path)

        # Cache with medium model
        cache.put(
            "LiFePO4",
            "mace_energy",
            {"energy": -5.2},
            params={"model": "medium"},
        )

        # Cache with large model
        cache.put(
            "LiFePO4",
            "mace_energy",
            {"energy": -5.25},
            params={"model": "large"},
        )

        # Retrieve both
        medium = cache.get("LiFePO4", "mace_energy", {"model": "medium"})
        large = cache.get("LiFePO4", "mace_energy", {"model": "large"})

        assert medium["energy"] == -5.2
        assert large["energy"] == -5.25

    def test_search(self, tmp_path: Path) -> None:
        """Test searching by formula pattern."""
        db_path = tmp_path / "test.db"
        cache = DiscoveryCache(db_path=db_path)

        # Add some entries
        cache.put("LiFePO4", "mace_energy", {"energy": -5.2})
        cache.put("LiCoO2", "mace_energy", {"energy": -4.8})
        cache.put("BaTiO3", "mace_energy", {"energy": -6.1})

        # Search for Li compounds
        results = cache.search("Li")
        assert len(results) == 2
        formulas = {r.formula for r in results}
        assert "LiFePO4" in formulas
        assert "LiCoO2" in formulas

    def test_search_limit(self, tmp_path: Path) -> None:
        """Test that search respects limit."""
        db_path = tmp_path / "test.db"
        cache = DiscoveryCache(db_path=db_path)

        for i in range(10):
            cache.put(f"Li{i}O", "test", {"i": i})

        results = cache.search("Li", limit=3)
        assert len(results) == 3

    def test_get_all_for_formula(self, tmp_path: Path) -> None:
        """Test getting all computations for a formula."""
        db_path = tmp_path / "test.db"
        cache = DiscoveryCache(db_path=db_path)

        # Add multiple computation types for same formula
        cache.put("LiFePO4", "mace_energy", {"energy": -5.2})
        cache.put("LiFePO4", "smact_validity", {"valid": True})
        cache.put("LiFePO4", "chemeleon_structure", {"spacegroup": "Pnma"})

        results = cache.get_all_for_formula("LiFePO4")
        assert len(results) == 3
        types = {r.computation_type for r in results}
        assert types == {"mace_energy", "smact_validity", "chemeleon_structure"}

    def test_get_by_type(self, tmp_path: Path) -> None:
        """Test getting results by computation type."""
        db_path = tmp_path / "test.db"
        cache = DiscoveryCache(db_path=db_path)

        cache.put("LiFePO4", "mace_energy", {"energy": -5.2})
        cache.put("LiCoO2", "mace_energy", {"energy": -4.8})
        cache.put("BaTiO3", "smact_validity", {"valid": True})

        results = cache.get_by_type("mace_energy")
        assert len(results) == 2

    def test_delete(self, tmp_path: Path) -> None:
        """Test deleting a cached result."""
        db_path = tmp_path / "test.db"
        cache = DiscoveryCache(db_path=db_path)

        cache.put("LiFePO4", "mace_energy", {"energy": -5.2})
        assert cache.get("LiFePO4", "mace_energy") is not None

        deleted = cache.delete("LiFePO4", "mace_energy")
        assert deleted is True
        assert cache.get("LiFePO4", "mace_energy") is None

    def test_delete_nonexistent(self, tmp_path: Path) -> None:
        """Test deleting nonexistent entry returns False."""
        db_path = tmp_path / "test.db"
        cache = DiscoveryCache(db_path=db_path)

        deleted = cache.delete("NonExistent", "mace_energy")
        assert deleted is False

    def test_clear(self, tmp_path: Path) -> None:
        """Test clearing all entries."""
        db_path = tmp_path / "test.db"
        cache = DiscoveryCache(db_path=db_path)

        cache.put("A", "test", {"a": 1})
        cache.put("B", "test", {"b": 2})
        cache.put("C", "test", {"c": 3})

        count = cache.clear()
        assert count == 3
        assert cache.stats()["total"] == 0

    def test_stats(self, tmp_path: Path) -> None:
        """Test getting cache statistics."""
        db_path = tmp_path / "test.db"
        cache = DiscoveryCache(db_path=db_path)

        cache.put("A", "mace_energy", {"a": 1})
        cache.put("B", "mace_energy", {"b": 2})
        cache.put("C", "smact_validity", {"c": 3})

        stats = cache.stats()
        assert stats["total"] == 3
        assert stats["by_type"]["mace_energy"] == 2
        assert stats["by_type"]["smact_validity"] == 1

    def test_upsert_behavior(self, tmp_path: Path) -> None:
        """Test that put updates existing entries."""
        db_path = tmp_path / "test.db"
        cache = DiscoveryCache(db_path=db_path)

        cache.put("LiFePO4", "mace_energy", {"energy": -5.0})
        cache.put("LiFePO4", "mace_energy", {"energy": -5.2})

        result = cache.get("LiFePO4", "mace_energy")
        assert result["energy"] == -5.2

        # Should still be only one entry
        assert cache.stats()["total"] == 1


class TestCachedDiscovery:
    """Tests for CachedDiscovery dataclass."""

    def test_attributes(self) -> None:
        """Test CachedDiscovery has correct attributes."""
        discovery = CachedDiscovery(
            formula="LiFePO4",
            computation_type="mace_energy",
            parameters_hash="abc123",
            result={"energy": -5.2},
            created_at="2024-01-15 10:30:00",
        )

        assert discovery.formula == "LiFePO4"
        assert discovery.computation_type == "mace_energy"
        assert discovery.parameters_hash == "abc123"
        assert discovery.result["energy"] == -5.2
        assert discovery.created_at == "2024-01-15 10:30:00"
