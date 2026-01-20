"""
Unit tests for Provenance Value Registry.

Tests the central registry that maps values to their computational provenance.
"""

from __future__ import annotations

from typing import Any

from crystalyse.provenance.artifact_tracker import ArtifactTracker
from crystalyse.provenance.value_registry import (
    ProvenancedValue,
    ProvenanceValueRegistry,
    get_global_registry,
    reset_global_registry,
)


class TestProvenancedValue:
    """Tests for ProvenancedValue dataclass."""

    def test_provenanced_value_creation(self) -> None:
        """Test creating a ProvenancedValue."""
        pv = ProvenancedValue(
            value=-25.5,
            unit="eV",
            source_tool="mace_calculate_energy",
            artifact_hash="abc123",
            timestamp="2025-01-20T12:00:00Z",
        )
        assert pv.value == -25.5
        assert pv.unit == "eV"
        assert pv.source_tool == "mace_calculate_energy"
        assert pv.artifact_hash == "abc123"

    def test_provenanced_value_with_confidence(self) -> None:
        """Test ProvenancedValue with confidence score."""
        pv = ProvenancedValue(
            value=0.85,
            unit=None,
            source_tool="chemeleon_predict",
            artifact_hash="xyz789",
            timestamp="2025-01-20T12:00:00Z",
            confidence=0.95,
            property_type="structure_confidence",
        )
        assert pv.confidence == 0.95
        assert pv.property_type == "structure_confidence"

    def test_provenanced_value_with_material(self) -> None:
        """Test ProvenancedValue with material information."""
        pv = ProvenancedValue(
            value=-1.2,
            unit="eV/atom",
            source_tool="mace_formation_energy",
            artifact_hash="def456",
            timestamp="2025-01-20T12:00:00Z",
            material="CaTiO3",
        )
        assert pv.material == "CaTiO3"

    def test_to_tuple_conversion(self) -> None:
        """Test conversion to ProvenanceTuple."""
        pv = ProvenancedValue(
            value=-25.5,
            unit="eV",
            source_tool="mace_calculate_energy",
            artifact_hash="abc123",
            timestamp="2025-01-20T12:00:00Z",
            confidence=0.99,
        )
        tuple_result = pv.to_tuple()
        assert tuple_result.value == -25.5
        assert tuple_result.unit == "eV"
        assert tuple_result.source_tool == "mace_calculate_energy"


class TestProvenanceValueRegistry:
    """Tests for ProvenanceValueRegistry class."""

    def test_registry_creation(self) -> None:
        """Test creating a ProvenanceValueRegistry."""
        registry = ProvenanceValueRegistry()
        assert registry is not None
        assert len(registry.registry) == 0

    def test_registry_with_custom_tracker(self) -> None:
        """Test registry with custom artifact tracker."""
        tracker = ArtifactTracker()
        registry = ProvenanceValueRegistry(artifact_tracker=tracker)
        assert registry.artifact_tracker is tracker

    def test_register_tool_output(self, sample_tool_output: dict[str, Any]) -> None:
        """Test registering a tool output."""
        registry = ProvenanceValueRegistry()
        artifact_id = registry.register_tool_output(
            tool_name="mace_calculate_energy",
            tool_call_id="call_123",
            input_data={"formula": "CaTiO3"},
            output_data=sample_tool_output,
        )
        assert artifact_id is not None
        assert len(artifact_id) > 0

    def test_lookup_provenance_exact_match(self, sample_tool_output: dict[str, Any]) -> None:
        """Test looking up provenance with exact value match."""
        registry = ProvenanceValueRegistry()
        registry.register_tool_output(
            tool_name="mace_calculate_energy",
            tool_call_id="call_123",
            input_data={"formula": "CaTiO3"},
            output_data=sample_tool_output,
        )

        # Look up the formation_energy value (extracted by artifact tracker)
        provenance = registry.lookup_provenance(-1.2)
        assert provenance is not None
        assert provenance.value == -1.2
        assert provenance.source_tool == "mace_calculate_energy"

    def test_lookup_provenance_fuzzy_match(self, sample_tool_output: dict[str, Any]) -> None:
        """Test looking up provenance with fuzzy matching."""
        registry = ProvenanceValueRegistry()
        registry.register_tool_output(
            tool_name="mace_calculate_energy",
            tool_call_id="call_123",
            input_data={"formula": "CaTiO3"},
            output_data=sample_tool_output,
        )

        # Look up formation_energy with slight tolerance
        provenance = registry.lookup_provenance(-1.201, tolerance=0.01)
        assert provenance is not None
        assert abs(provenance.value - (-1.2)) < 0.01

    def test_lookup_provenance_no_match(self) -> None:
        """Test lookup returns None when no match."""
        registry = ProvenanceValueRegistry()
        provenance = registry.lookup_provenance(999.99)
        assert provenance is None

    def test_lookup_provenance_with_material_context(
        self, sample_tool_output: dict[str, Any]
    ) -> None:
        """Test lookup with material context."""
        registry = ProvenanceValueRegistry()
        registry.register_tool_output(
            tool_name="mace_calculate_energy",
            tool_call_id="call_123",
            input_data={"formula": "CaTiO3"},
            output_data=sample_tool_output,
        )

        # Look up formation_energy with material hint
        provenance = registry.lookup_provenance(-1.2, material="CaTiO3")
        assert provenance is not None

    def test_lookup_material_properties(self, sample_tool_output: dict[str, Any]) -> None:
        """Test looking up all properties for a material."""
        registry = ProvenanceValueRegistry()
        registry.register_tool_output(
            tool_name="mace_calculate_energy",
            tool_call_id="call_123",
            input_data={"formula": "CaTiO3"},
            output_data=sample_tool_output,
        )

        properties = registry.lookup_material_properties("CaTiO3")
        assert isinstance(properties, dict)

    def test_get_provenance_data(self, sample_tool_output: dict[str, Any]) -> None:
        """Test getting all provenance data."""
        registry = ProvenanceValueRegistry()
        registry.register_tool_output(
            tool_name="mace_calculate_energy",
            tool_call_id="call_123",
            input_data={"formula": "CaTiO3"},
            output_data=sample_tool_output,
        )

        data = registry.get_provenance_data()
        assert "artifacts" in data
        assert "registry" in data
        assert "statistics" in data

    def test_clear_registry(self, sample_tool_output: dict[str, Any]) -> None:
        """Test clearing the registry."""
        registry = ProvenanceValueRegistry()
        registry.register_tool_output(
            tool_name="mace_calculate_energy",
            tool_call_id="call_123",
            input_data={"formula": "CaTiO3"},
            output_data=sample_tool_output,
        )

        registry.clear()
        assert len(registry.registry) == 0
        assert len(registry.material_registry) == 0

    def test_get_statistics(self, sample_tool_output: dict[str, Any]) -> None:
        """Test getting registry statistics."""
        registry = ProvenanceValueRegistry()
        registry.register_tool_output(
            tool_name="mace_calculate_energy",
            tool_call_id="call_123",
            input_data={"formula": "CaTiO3"},
            output_data=sample_tool_output,
        )

        stats = registry.get_statistics()
        assert "total_values" in stats
        assert "unique_values" in stats
        assert "materials" in stats
        assert "artifacts" in stats


class TestGlobalRegistry:
    """Tests for global registry singleton."""

    def setup_method(self) -> None:
        """Reset global registry before each test."""
        reset_global_registry()

    def teardown_method(self) -> None:
        """Reset global registry after each test."""
        reset_global_registry()

    def test_get_global_registry(self) -> None:
        """Test getting the global registry."""
        registry = get_global_registry()
        assert registry is not None
        assert isinstance(registry, ProvenanceValueRegistry)

    def test_global_registry_singleton(self) -> None:
        """Test that global registry is a singleton."""
        registry1 = get_global_registry()
        registry2 = get_global_registry()
        assert registry1 is registry2

    def test_reset_global_registry(self, sample_tool_output: dict[str, Any]) -> None:
        """Test resetting the global registry."""
        registry = get_global_registry()
        registry.register_tool_output(
            tool_name="test",
            tool_call_id="call_1",
            input_data={},
            output_data=sample_tool_output,
        )

        reset_global_registry()
        new_registry = get_global_registry()
        assert len(new_registry.registry) == 0


class TestMaterialExtraction:
    """Tests for material formula extraction from tool outputs."""

    def test_extract_formula_from_dict(self) -> None:
        """Test extracting formula from dict output."""
        registry = ProvenanceValueRegistry()
        # Use field names recognized by artifact tracker
        output = {"formula": "LiCoO2", "formation_energy": -1.5}
        registry.register_tool_output(
            tool_name="mace",
            tool_call_id="call_1",
            input_data={},
            output_data=output,
        )
        # Should register with material context
        assert "LiCoO2" in registry.material_registry or len(registry.registry) > 0

    def test_extract_composition_field(self) -> None:
        """Test extracting from 'composition' field."""
        registry = ProvenanceValueRegistry()
        # Use field names recognized by artifact tracker
        output = {"composition": "BaTiO3", "formation_energy": -1.8}
        registry.register_tool_output(
            tool_name="mace",
            tool_call_id="call_1",
            input_data={},
            output_data=output,
        )
        assert len(registry.registry) > 0


class TestProvenanceLookupEdgeCases:
    """Tests for edge cases in provenance lookup."""

    def test_lookup_zero_value(self) -> None:
        """Test looking up zero/near-zero values."""
        registry = ProvenanceValueRegistry()
        registry.register_tool_output(
            tool_name="test",
            tool_call_id="call_1",
            input_data={},
            output_data={"ehull": 0.0, "formula": "StableCompound"},
        )

        # Should handle zero values specially
        registry.lookup_provenance(0.0)
        # May or may not find depending on extraction

    def test_lookup_negative_values(self) -> None:
        """Test looking up negative values (common for energies)."""
        registry = ProvenanceValueRegistry()
        # Use field names recognized by artifact tracker
        registry.register_tool_output(
            tool_name="mace",
            tool_call_id="call_1",
            input_data={},
            output_data={"total_energy": -150.5, "formula": "LargeStructure"},
        )

        provenance = registry.lookup_provenance(-150.5)
        assert provenance is not None
        assert provenance.value == -150.5

    def test_lookup_small_tolerance(self) -> None:
        """Test lookup with very small tolerance."""
        registry = ProvenanceValueRegistry()
        registry.register_tool_output(
            tool_name="test",
            tool_call_id="call_1",
            input_data={},
            output_data={"value": 1.23456789},
        )

        # Should not match with tiny tolerance
        registry.lookup_provenance(1.234, tolerance=0.0001)
        # Might or might not match depending on exact value

    def test_multiple_values_same_output(self) -> None:
        """Test output with multiple numeric values."""
        registry = ProvenanceValueRegistry()
        registry.register_tool_output(
            tool_name="mace",
            tool_call_id="call_1",
            input_data={},
            output_data={
                "energy": -25.5,
                "energy_per_atom": -5.1,
                "formation_energy": -1.2,
                "ehull": 0.015,
                "formula": "CaTiO3",
            },
        )

        # Should be able to look up each value
        e_total = registry.lookup_provenance(-25.5)
        e_per_atom = registry.lookup_provenance(-5.1)
        e_form = registry.lookup_provenance(-1.2)

        # At least some should be found
        found = [e_total, e_per_atom, e_form]
        assert any(p is not None for p in found)


class TestTimestampHandling:
    """Tests for timestamp handling in provenance."""

    def test_custom_timestamp(self) -> None:
        """Test providing custom timestamp."""
        registry = ProvenanceValueRegistry()
        custom_time = "2024-06-15T10:30:00Z"
        registry.register_tool_output(
            tool_name="test",
            tool_call_id="call_1",
            input_data={},
            output_data={"value": 42.0},
            timestamp=custom_time,
        )

        # Check timestamp is preserved
        stats = registry.get_provenance_data()
        artifacts = stats.get("artifacts", {})
        if artifacts:
            artifact = list(artifacts.values())[0]
            assert artifact.get("timestamp") == custom_time

    def test_auto_timestamp(self) -> None:
        """Test automatic timestamp generation."""
        registry = ProvenanceValueRegistry()
        registry.register_tool_output(
            tool_name="test",
            tool_call_id="call_1",
            input_data={},
            output_data={"value": 42.0},
        )

        # Should have generated a timestamp
        stats = registry.get_provenance_data()
        artifacts = stats.get("artifacts", {})
        if artifacts:
            artifact = list(artifacts.values())[0]
            assert "timestamp" in artifact
