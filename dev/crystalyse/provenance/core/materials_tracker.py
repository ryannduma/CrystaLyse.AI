"""
Materials tracking and extraction from tool outputs.

Enhanced for Phase 1.5 with Pydantic model support.
"""

import json
import logging
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class Material:
    """
    Represents a discovered material with enhanced Phase 1.5 metadata.
    """

    composition: str
    formula: str | None = None
    formation_energy: float | None = None
    energy_unit: str = "eV/atom"
    structure_id: str | None = None
    space_group: str | None = None
    lattice_params: dict | None = None
    cif_saved: bool = False
    cif_path: str | None = None
    source_tool: str | None = None
    timestamp: str | None = None

    # Phase 1.5 additions
    energy_above_hull: float | None = None
    is_stable: bool | None = None
    band_gap: float | None = None
    bulk_modulus: float | None = None
    stress_tensor: list[list[float]] | None = None
    dopants: dict[str, list[str]] | None = None
    oxidation_states: dict[str, float] | None = None
    coordination_environments: list[dict] | None = None
    confidence: float | None = None
    method: str | None = None  # e.g., "mace-mp-0", "chemeleon"

    def to_dict(self) -> dict:
        """Convert to dictionary, excluding None values."""
        data = asdict(self)
        return {k: v for k, v in data.items() if v is not None}

    @property
    def has_energy(self) -> bool:
        """Check if material has energy data."""
        return self.formation_energy is not None


class MaterialsTracker:
    """
    Extracts and tracks materials from MCP tool outputs.
    Handles various output formats from different tools.
    """

    def __init__(self):
        self.materials: list[Material] = []
        self._compositions_seen = set()
        # Track unique materials by composition for deduplication
        self._unique_materials: dict[str, Material] = {}
        # Store orphaned energy data when composition is unknown
        self._orphaned_energy_data = None

    def _normalize_composition(self, composition: str) -> str:
        """
        Normalize composition string to handle different element orderings.
        E.g., "LiCoO2" and "CoLiO2" both become "CoLiO2" (alphabetical order).
        """
        import re

        # Parse elements and their counts from the formula
        elements = {}
        # Match element symbols followed by optional numbers
        pattern = r"([A-Z][a-z]?)(\d*)"
        matches = re.findall(pattern, composition)

        for element, count in matches:
            count = int(count) if count else 1
            if element in elements:
                elements[element] += count
            else:
                elements[element] = count

        # Rebuild formula in alphabetical order
        sorted_elements = sorted(elements.keys())
        normalized = ""
        for element in sorted_elements:
            count = elements[element]
            if count == 1:
                normalized += element
            else:
                normalized += f"{element}{count}"

        return normalized

    def extract_from_output(self, output: Any, tool_name: str | None = None) -> list[Material]:
        """
        Extract materials from tool output.

        Args:
            output: Raw tool output (may be wrapped)
            tool_name: Name of the MCP tool

        Returns:
            List of extracted materials
        """
        materials = []

        try:
            # Parse the output
            data = self._parse_output(output)

            if not isinstance(data, dict):
                return materials

            # Extract based on tool type
            if tool_name in ["comprehensive_materials_analysis", "creative_discovery_pipeline"]:
                materials = self._extract_from_comprehensive(data)
            elif tool_name == "calculate_energy_mace":
                materials = self._extract_from_mace(data)
            elif tool_name == "generate_structures":
                materials = self._extract_from_generation(data)

            # Phase 1.5 tools
            elif tool_name == "calculate_formation_energy":
                materials = self._extract_from_phase15_mace_energy(data)
            elif tool_name == "generate_crystal_csp":
                materials = self._extract_from_phase15_chemeleon(data)
            elif tool_name == "calculate_energy_above_hull":
                materials = self._extract_from_phase15_pymatgen_hull(data)
            elif tool_name == "analyze_space_group":
                materials = self._extract_from_phase15_space_group(data)
            elif tool_name == "predict_dopants":
                materials = self._extract_from_phase15_dopants(data)
            elif tool_name == "estimate_band_gap":
                materials = self._extract_from_phase15_band_gap(data)
            elif tool_name == "calculate_stress":
                materials = self._extract_from_phase15_stress(data)
            elif tool_name == "fit_equation_of_state":
                materials = self._extract_from_phase15_eos(data)

            # SMACT validation tools
            elif tool_name == "smact_validate_fast":
                materials = self._extract_from_smact_validate_fast(data)
            elif tool_name == "validate_composition":
                materials = self._extract_from_validate_composition(data)
            elif tool_name == "filter_compositions":
                materials = self._extract_from_filter_compositions(data)

            # If no specific extraction method, try generic
            if not materials:
                # Try generic extraction as fallback
                materials = self._extract_generic(data)

            # Add source tool and timestamp
            for material in materials:
                if tool_name:
                    material.source_tool = tool_name
                if not material.timestamp:
                    material.timestamp = datetime.now().isoformat()

            # Track materials with deduplication
            for mat in materials:
                self.materials.append(mat)  # Keep all for complete history

                # Normalize composition for deduplication
                normalized_comp = self._normalize_composition(mat.composition)
                self._compositions_seen.add(normalized_comp)

                # Apply orphaned energy data if we have it and this material lacks energy
                if self._orphaned_energy_data and mat.formation_energy is None:
                    mat.formation_energy = self._orphaned_energy_data.get("formation_energy")
                    mat.energy_unit = self._orphaned_energy_data.get("energy_unit", "eV/atom")
                    if not mat.method:
                        mat.method = self._orphaned_energy_data.get("method", "mace")
                    # Clear orphaned data after using it
                    self._orphaned_energy_data = None

                # Merge into unique materials using normalized composition as key
                if normalized_comp in self._unique_materials:
                    # Merge data from new material into existing
                    existing = self._unique_materials[normalized_comp]
                    self._merge_materials(existing, mat)
                else:
                    # First time seeing this composition - normalize it in the material
                    mat.composition = normalized_comp
                    mat.formula = normalized_comp if mat.formula else None
                    self._unique_materials[normalized_comp] = mat

        except Exception as e:
            logger.error(f"Failed to extract materials: {e}")

        return materials

    def _merge_materials(self, existing: Material, new: Material) -> None:
        """
        Merge data from new material into existing material.
        Prioritizes non-None values and accumulates information.
        """
        # Update with new data if existing is None
        if existing.formation_energy is None and new.formation_energy is not None:
            existing.formation_energy = new.formation_energy
            existing.energy_unit = new.energy_unit

        if existing.energy_above_hull is None and new.energy_above_hull is not None:
            existing.energy_above_hull = new.energy_above_hull

        if existing.is_stable is None and new.is_stable is not None:
            existing.is_stable = new.is_stable

        if existing.band_gap is None and new.band_gap is not None:
            existing.band_gap = new.band_gap

        if existing.bulk_modulus is None and new.bulk_modulus is not None:
            existing.bulk_modulus = new.bulk_modulus

        if existing.space_group is None and new.space_group is not None:
            existing.space_group = new.space_group
            existing.lattice_params = new.lattice_params

        if existing.stress_tensor is None and new.stress_tensor is not None:
            existing.stress_tensor = new.stress_tensor

        if existing.dopants is None and new.dopants is not None:
            existing.dopants = new.dopants

        if existing.oxidation_states is None and new.oxidation_states is not None:
            existing.oxidation_states = new.oxidation_states

        # Update confidence if higher
        if new.confidence is not None and (
            existing.confidence is None or new.confidence > existing.confidence
        ):
            existing.confidence = new.confidence

        # Track multiple source tools
        if new.source_tool and new.source_tool != existing.source_tool:
            if not hasattr(existing, "all_source_tools"):
                existing.all_source_tools = [existing.source_tool]
            if new.source_tool not in existing.all_source_tools:
                existing.all_source_tools.append(new.source_tool)

    def _parse_output(self, output: Any) -> dict:
        """Parse and unwrap output."""
        if not output:
            return {}

        # Handle SDK wrapper
        if isinstance(output, dict):
            if output.get("type") == "text" and "text" in output:
                content = output["text"]
                if isinstance(content, str):
                    try:
                        return json.loads(content)
                    except Exception:
                        return {}
                return content
            return output

        # Handle string
        if isinstance(output, str):
            try:
                parsed = json.loads(output)
                # Check if wrapped
                if isinstance(parsed, dict) and parsed.get("type") == "text":
                    return self._parse_output(parsed)
                return parsed
            except Exception:
                return {}

        return {}

    def _extract_from_comprehensive(self, data: dict) -> list[Material]:
        """Extract from comprehensive_materials_analysis output."""
        materials = []

        # Build energy lookup from energy_calculations
        energy_lookup = {}
        if "energy_calculations" in data:
            for calc in data["energy_calculations"]:
                struct_id = calc.get("structure_id")
                if struct_id:
                    energy_lookup[struct_id] = calc.get("formation_energy")

        # Extract structures
        if "generated_structures" in data:
            for comp_data in data["generated_structures"]:
                composition = comp_data.get("composition", "")

                for idx, struct in enumerate(comp_data.get("structures", [])):
                    # Generate structure ID if not present
                    struct_id = struct.get("structure_id") or f"{composition}_struct_{idx + 1}"

                    # Get energy from lookup or structure
                    formation_energy = (
                        energy_lookup.get(struct_id)
                        or struct.get("formation_energy")
                        or struct.get("energy")
                    )

                    material = Material(
                        composition=composition,
                        formula=struct.get("formula", composition),
                        formation_energy=formation_energy,
                        structure_id=struct_id,
                        space_group=struct.get("space_group"),
                        cif_saved=struct.get("cif_saved", False),
                        lattice_params=struct.get("lattice"),
                    )
                    materials.append(material)

        # Also check for direct materials list
        if "materials" in data:
            for mat_data in data["materials"]:
                material = Material(
                    composition=mat_data.get("composition", ""),
                    formula=mat_data.get("formula"),
                    formation_energy=mat_data.get("formation_energy"),
                    structure_id=mat_data.get("structure_id"),
                    space_group=mat_data.get("space_group"),
                )
                materials.append(material)

        return materials

    def _extract_from_mace(self, data: dict) -> list[Material]:
        """Extract from MACE energy calculation."""
        materials = []

        if "formation_energy" in data:
            material = Material(
                composition=data.get("composition", "unknown"),
                formation_energy=data["formation_energy"],
                structure_id=data.get("structure_id"),
            )
            materials.append(material)

        return materials

    def _extract_from_generation(self, data: dict) -> list[Material]:
        """Extract from structure generation output."""
        materials = []

        if "structures" in data:
            for struct in data["structures"]:
                material = Material(
                    composition=struct.get("composition", ""),
                    formula=struct.get("formula"),
                    space_group=struct.get("space_group"),
                    lattice_params=struct.get("lattice"),
                )
                materials.append(material)

        return materials

    def _extract_generic(self, data: dict) -> list[Material]:
        """Generic extraction for unknown formats - enhanced to catch more patterns."""
        materials = []

        # Look for formula or composition fields (handle both naming conventions)
        composition = data.get("formula") or data.get("composition")

        if composition:
            material = Material(
                composition=composition,
                formula=composition,
                formation_energy=data.get("formation_energy"),
                energy_above_hull=data.get("energy_above_hull"),
                is_stable=data.get("stable") or data.get("is_stable"),
                band_gap=data.get("band_gap") or data.get("band_gap_ev"),
                space_group=data.get("space_group") or data.get("space_group_symbol"),
                method="generic",
                confidence=data.get("confidence"),
            )

            # Only add if we have meaningful data beyond just composition
            # or if it's explicitly marked as valid/stable
            if (
                material.formation_energy is not None
                or material.is_stable is not None
                or material.band_gap is not None
                or material.space_group is not None
                or data.get("smact_valid")
                or data.get("is_valid")
            ):
                materials.append(material)

        return materials

    # Phase 1.5 extraction methods
    def _extract_from_phase15_mace_energy(self, data: dict) -> list[Material]:
        """Extract from Phase 1.5 MACE energy calculation."""
        materials = []
        if "formation_energy" in data:
            # Try multiple fields to find composition
            composition = (
                data.get("composition")
                or data.get("formula")
                or data.get("material")
                or data.get("structure_formula")
            )

            # Don't create a material if we don't know the composition
            # This prevents creating orphaned "unknown" materials
            if not composition:
                logger.warning(
                    "MACE energy calculation missing composition - energy will be merged when composition known"
                )
                # Store the energy data temporarily (could be picked up later)
                self._orphaned_energy_data = {
                    "formation_energy": data["formation_energy"],
                    "energy_unit": data.get("unit", "eV/atom"),
                    "method": "mace",
                    "confidence": data.get("confidence", 1.0),
                }
                return materials

            material = Material(
                composition=composition,
                formula=composition,
                formation_energy=data["formation_energy"],
                energy_unit=data.get("unit", "eV/atom"),
                method="mace",
                confidence=data.get("confidence", 1.0),
            )
            materials.append(material)
        return materials

    def _extract_from_phase15_chemeleon(self, data: dict) -> list[Material]:
        """Extract from Phase 1.5 Chemeleon CSP generation."""
        materials = []
        if data.get("success") and "predicted_structures" in data:
            for idx, struct in enumerate(data["predicted_structures"]):
                material = Material(
                    composition=data.get("formula", ""),
                    formula=struct.get("formula", data.get("formula")),
                    structure_id=f"chemeleon_{idx}",
                    space_group=struct.get("space_group"),
                    lattice_params=struct.get("lattice"),
                    confidence=struct.get("confidence", 1.0),
                    method="chemeleon",
                    cif_saved=struct.get("cif_saved", False),
                    cif_path=struct.get("cif_path"),
                )
                materials.append(material)
        return materials

    def _extract_from_phase15_pymatgen_hull(self, data: dict) -> list[Material]:
        """Extract from Phase 1.5 PyMatgen hull analysis."""
        materials = []
        if "composition" in data:
            material = Material(
                composition=data["composition"],
                energy_above_hull=data.get("energy_above_hull"),
                is_stable=data.get("is_stable", False),
                method="pymatgen_hull",
            )
            materials.append(material)
        return materials

    def _extract_from_phase15_space_group(self, data: dict) -> list[Material]:
        """Extract from Phase 1.5 space group analysis."""
        materials = []
        if "space_group" in data:
            material = Material(
                composition=data.get("composition", "unknown"),
                space_group=data["space_group"],
                lattice_params={
                    "crystal_system": data.get("crystal_system"),
                    "point_group": data.get("point_group"),
                    "number": data.get("number"),
                },
                method="pymatgen_symmetry",
            )
            materials.append(material)
        return materials

    def _extract_from_phase15_dopants(self, data: dict) -> list[Material]:
        """Extract from Phase 1.5 dopant prediction."""
        materials = []
        if "composition" in data:
            material = Material(
                composition=data["composition"],
                dopants={
                    "n_type": data.get("n_type_dopants", [])[:5],
                    "p_type": data.get("p_type_dopants", [])[:5],
                },
                method="smact_dopants",
            )
            materials.append(material)
        return materials

    def _extract_from_phase15_band_gap(self, data: dict) -> list[Material]:
        """Extract from Phase 1.5 band gap estimation."""
        materials = []
        if "band_gap" in data:
            material = Material(
                composition=data.get("composition", "unknown"),
                band_gap=data["band_gap"],
                confidence=data.get("confidence"),
                method="smact_band_gap",
            )
            materials.append(material)
        return materials

    def _extract_from_phase15_stress(self, data: dict) -> list[Material]:
        """Extract from Phase 1.5 stress calculation."""
        materials = []
        if "stress_tensor" in data:
            material = Material(
                composition=data.get("composition", "unknown"),
                stress_tensor=data["stress_tensor"],
                method="mace_stress",
            )
            materials.append(material)
        return materials

    def _extract_from_phase15_eos(self, data: dict) -> list[Material]:
        """Extract from Phase 1.5 EOS fitting."""
        materials = []
        if "bulk_modulus" in data:
            material = Material(
                composition=data.get("composition", "unknown"),
                bulk_modulus=data["bulk_modulus"],
                method="mace_eos",
            )
            materials.append(material)
        return materials

    # Additional SMACT extraction methods for Phase 1.5
    def _extract_from_smact_validate_fast(self, data: dict) -> list[Material]:
        """Extract from SMACT fast validation tool."""
        materials = []
        formula = data.get("formula")

        if formula and (data.get("smact_valid") or data.get("stable")):
            material = Material(
                composition=formula,
                formula=formula,
                is_stable=data.get("stable"),
                method="smact_validation",
                confidence=1.0 if data.get("smact_valid") else 0.5,
            )

            # Add additional fields if present
            if "electronegativity_difference" in data:
                material.oxidation_states = {
                    "electronegativity_diff": data["electronegativity_difference"]
                }

            materials.append(material)

        return materials

    def _extract_from_validate_composition(self, data: dict) -> list[Material]:
        """Extract from validate_composition tool."""
        materials = []
        composition = data.get("composition")

        if composition and data.get("is_valid"):
            material = Material(
                composition=composition,
                formula=composition,
                is_stable=data.get("charge_balanced"),
                method="smact_validation",
                confidence=1.0 if data.get("is_valid") else 0.0,
            )
            materials.append(material)

        return materials

    def _extract_from_filter_compositions(self, data: dict) -> list[Material]:
        """Extract from filter_compositions tool."""
        materials = []

        # Extract valid compositions
        for comp in data.get("valid_compositions", []):
            if isinstance(comp, str):
                material = Material(
                    composition=comp,
                    formula=comp,
                    is_stable=True,  # Marked as valid by filter
                    method="smact_filter",
                )
                materials.append(material)

        return materials

    def get_summary(self) -> dict[str, Any]:
        """Get summary statistics of tracked materials - reports unique materials."""
        # Use unique materials for accurate counts
        unique_materials = list(self._unique_materials.values())
        total = len(unique_materials)
        with_energy = sum(1 for m in unique_materials if m.has_energy)

        energies = [m.formation_energy for m in unique_materials if m.has_energy]

        summary = {
            "total_materials": total,  # Now reports unique materials count
            "unique_compositions": len(self._compositions_seen),
            "materials_with_energy": with_energy,
            "energy_coverage": (with_energy / max(total, 1)) * 100,
            "total_observations": len(self.materials),  # Track total including duplicates
        }

        if energies:
            summary.update(
                {
                    "min_energy": min(energies),
                    "max_energy": max(energies),
                    "avg_energy": sum(energies) / len(energies),
                }
            )

        return summary

    def to_catalog(self) -> list[dict]:
        """Export unique materials as catalog."""
        return [m.to_dict() for m in self._unique_materials.values()]

    def to_enhanced_catalog(self) -> dict[str, Any]:
        """
        Export materials as an enhanced catalog with metadata and statistics.

        Returns:
            Dictionary containing unique materials, metadata, and summary statistics
        """
        # Use unique materials for the main catalog
        unique_materials = list(self._unique_materials.values())

        # Group unique materials by method/tool
        by_method = {}
        for material in unique_materials:
            method = material.method or "unknown"
            if method not in by_method:
                by_method[method] = []
            by_method[method].append(material.to_dict())

        # Calculate statistics
        stats = self.get_summary()
        stats["methods_used"] = list(by_method.keys())

        # Count materials with specific properties (from unique materials)
        stats["materials_with_band_gap"] = sum(
            1 for m in unique_materials if m.band_gap is not None
        )
        stats["materials_with_dopants"] = sum(1 for m in unique_materials if m.dopants)
        stats["stable_materials"] = sum(1 for m in unique_materials if m.is_stable is True)
        stats["materials_with_stress"] = sum(
            1 for m in unique_materials if m.stress_tensor is not None
        )

        return {
            "version": "1.5.0",
            "timestamp": datetime.now().isoformat(),
            "total_materials": len(unique_materials),
            "materials": self.to_catalog(),
            "materials_by_method": by_method,
            "statistics": stats,
            "unique_compositions": list(self._compositions_seen),
        }

    def save_catalog(self, path: str, enhanced: bool = True) -> None:
        """
        Save materials catalog to JSON file.

        Args:
            path: Path to save the catalog
            enhanced: If True, save enhanced catalog with metadata
        """
        import json
        from pathlib import Path

        catalog_path = Path(path)
        catalog_path.parent.mkdir(parents=True, exist_ok=True)

        if enhanced:
            catalog_data = self.to_enhanced_catalog()
        else:
            catalog_data = self.to_catalog()

        with open(catalog_path, "w") as f:
            json.dump(catalog_data, f, indent=2, default=str)
