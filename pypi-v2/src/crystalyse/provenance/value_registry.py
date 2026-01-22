"""
Provenance Value Registry
=========================
Central registry that maps values to their computational provenance.
Integrates with the artifact tracker and materials tracker to provide
complete provenance lookup for the render gate.
"""

import logging
import re
from dataclasses import dataclass
from typing import Any

from .artifact_tracker import ArtifactTracker
from .core.materials_tracker import MaterialsTracker
from .render_gate import ProvenanceTuple

logger = logging.getLogger(__name__)


@dataclass
class ProvenancedValue:
    """
    A value with its complete provenance information.
    """

    value: float
    unit: str | None
    source_tool: str
    artifact_hash: str
    timestamp: str
    confidence: float | None = None
    property_type: str | None = None
    material: str | None = None  # e.g., "LiCoO2"

    def to_tuple(self) -> ProvenanceTuple:
        """Convert to ProvenanceTuple for render gate."""
        return ProvenanceTuple(
            value=self.value,
            unit=self.unit,
            source_tool=self.source_tool,
            artifact_hash=self.artifact_hash,
            timestamp=self.timestamp,
            confidence=self.confidence,
        )


class ProvenanceValueRegistry:
    """
    Central registry for all provenanced values.
    Combines artifact tracking with materials tracking.
    """

    def __init__(
        self,
        artifact_tracker: ArtifactTracker | None = None,
        materials_tracker: MaterialsTracker | None = None,
    ):
        """
        Initialize registry with optional trackers.

        Args:
            artifact_tracker: Tracks computational artifacts
            materials_tracker: Tracks discovered materials
        """
        self.artifact_tracker = artifact_tracker or ArtifactTracker()
        self.materials_tracker = materials_tracker

        # Direct value registry for quick lookup
        self.registry: dict[float, list[ProvenancedValue]] = {}

        # Material-specific registry
        self.material_registry: dict[str, list[ProvenancedValue]] = {}

    def register_tool_output(
        self,
        tool_name: str,
        tool_call_id: str,
        input_data: Any,
        output_data: Any,
        timestamp: str | None = None,
    ) -> str:
        """
        Register a tool output and extract all values.

        Returns:
            Artifact ID
        """
        # Register with artifact tracker
        artifact_id = self.artifact_tracker.register_tool_output(
            tool_name=tool_name,
            tool_call_id=tool_call_id,
            input_data=input_data,
            output_data=output_data,
            timestamp=timestamp,
        )

        # Get the artifact
        artifact = self.artifact_tracker.artifacts[artifact_id]

        # Create provenanced values
        for extracted in artifact.extracted_values:
            prov_value = ProvenancedValue(
                value=extracted.value,
                unit=extracted.unit,
                source_tool=tool_name,
                artifact_hash=artifact_id,
                timestamp=artifact.timestamp,
                confidence=artifact.confidence,
                property_type=extracted.property_type,
            )

            # Try to extract material formula
            material = self._extract_material(output_data)
            if material:
                prov_value.material = material

            # Register in main registry
            if extracted.value not in self.registry:
                self.registry[extracted.value] = []
            self.registry[extracted.value].append(prov_value)

            # Register in material registry if applicable
            if material:
                if material not in self.material_registry:
                    self.material_registry[material] = []
                self.material_registry[material].append(prov_value)

        logger.info(f"Registered {len(artifact.extracted_values)} values from {tool_name}")

        return artifact_id

    def lookup_provenance(
        self, value: float, tolerance: float = 0.01, material: str | None = None
    ) -> ProvenanceTuple | None:
        """
        Look up provenance for a value.

        Args:
            value: The numerical value
            tolerance: Tolerance for fuzzy matching
            material: Optional material formula for context

        Returns:
            ProvenanceTuple if found, None otherwise
        """
        # Special handling for zero/near-zero values
        # Use wider tolerance since LLM often rounds to 0
        if abs(value) < 0.01:
            # Search for small values with wider tolerance
            wide_tolerance = 0.5  # Allow matching values up to ±0.5
            for test_value, prov_values in self.registry.items():
                if abs(test_value - value) < wide_tolerance:
                    if material:
                        for prov_value in prov_values:
                            if prov_value.material == material:
                                return prov_value.to_tuple()
                    if prov_values:
                        return prov_values[0].to_tuple()

            # Also check artifact tracker with wider tolerance
            matches = self.artifact_tracker.lookup_value(value, wide_tolerance)
            if matches:
                artifact, extracted = matches[0]
                return ProvenanceTuple(
                    value=extracted.value,
                    unit=extracted.unit,
                    source_tool=artifact.tool_name,
                    artifact_hash=artifact.output_hash,
                    timestamp=artifact.timestamp,
                    confidence=artifact.confidence,
                )

        # Try exact match first
        if value in self.registry:
            candidates = self.registry[value]

            # If material specified, prefer matches for that material
            if material and material in self.material_registry:
                for prov_value in candidates:
                    if prov_value.material == material:
                        return prov_value.to_tuple()

            # Return first match
            if candidates:
                return candidates[0].to_tuple()

        # Fuzzy matching
        for test_value, prov_values in self.registry.items():
            if abs(test_value - value) < tolerance:
                # Prefer material-specific match
                if material:
                    for prov_value in prov_values:
                        if prov_value.material == material:
                            return prov_value.to_tuple()

                # Return first match
                if prov_values:
                    return prov_values[0].to_tuple()

        # Also check artifact tracker directly
        matches = self.artifact_tracker.lookup_value(value, tolerance)
        if matches:
            artifact, extracted = matches[0]
            return ProvenanceTuple(
                value=extracted.value,
                unit=extracted.unit,
                source_tool=artifact.tool_name,
                artifact_hash=artifact.output_hash,
                timestamp=artifact.timestamp,
                confidence=artifact.confidence,
            )

        return None

    def lookup_material_properties(self, material: str) -> dict[str, ProvenancedValue]:
        """
        Get all provenanced properties for a material.

        Args:
            material: Material formula (e.g., "LiCoO2")

        Returns:
            Dictionary of property_type -> ProvenancedValue
        """
        properties = {}

        if material in self.material_registry:
            for prov_value in self.material_registry[material]:
                if prov_value.property_type:
                    # Keep the most recent value for each property
                    if (
                        prov_value.property_type not in properties
                        or prov_value.timestamp > properties[prov_value.property_type].timestamp
                    ):
                        properties[prov_value.property_type] = prov_value

        return properties

    def get_provenance_data(self) -> dict[str, Any]:
        """
        Get all provenance data for render gate.

        Returns:
            Dictionary with provenance information
        """
        # Collect all materials if materials tracker available
        materials = []
        if self.materials_tracker:
            materials = self.materials_tracker.to_catalog()

        return {
            "artifacts": {
                aid: artifact.to_dict() for aid, artifact in self.artifact_tracker.artifacts.items()
            },
            "materials": materials,
            "registry": {
                value: [pv.__dict__ for pv in prov_values]
                for value, prov_values in self.registry.items()
            },
            "statistics": {
                "total_artifacts": len(self.artifact_tracker.artifacts),
                "total_values": len(self.registry),
                "materials_tracked": len(self.material_registry),
            },
        }

    def _extract_material(self, output_data: Any) -> str | None:
        """
        Extract material formula from tool output.
        """
        if isinstance(output_data, dict):
            # Check common fields
            for field in ["formula", "composition", "material", "compound"]:
                if field in output_data:
                    return str(output_data[field])

        elif isinstance(output_data, str):
            # Look for chemical formulas using regex
            # Pattern for chemical formulas like LiCoO2, CaTiO3, etc.
            pattern = r"\b([A-Z][a-z]?(?:\d+)?(?:[A-Z][a-z]?(?:\d+)?)*)\b"
            matches = re.findall(pattern, output_data)

            # Filter to likely chemical formulas
            for match in matches:
                # Must contain at least 2 elements
                elements = re.findall(r"[A-Z][a-z]?", match)
                if len(elements) >= 2:
                    return match

        return None

    def clear(self):
        """Clear all registered values."""
        self.registry.clear()
        self.material_registry.clear()
        self.artifact_tracker = ArtifactTracker()
        logger.info("Provenance registry cleared")

    def get_statistics(self) -> dict:
        """Get registry statistics."""
        return {
            "total_values": len(self.registry),
            "unique_values": len(set(self.registry.keys())),
            "materials": len(self.material_registry),
            "artifacts": self.artifact_tracker.get_statistics(),
        }


# Global registry instance
_global_registry: ProvenanceValueRegistry | None = None


def get_global_registry() -> ProvenanceValueRegistry:
    """Get or create the global provenance value registry."""
    global _global_registry
    if _global_registry is None:
        _global_registry = ProvenanceValueRegistry()
    return _global_registry


def reset_global_registry():
    """Reset the global registry (useful for testing)."""
    global _global_registry
    if _global_registry:
        _global_registry.clear()
    _global_registry = None
