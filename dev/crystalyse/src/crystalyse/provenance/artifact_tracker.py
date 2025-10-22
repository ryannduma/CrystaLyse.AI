"""
Artifact Tracking System for Render Gate
=========================================
Tracks computational artifacts with hashing to enable provenance verification
of material property values in LLM outputs.
"""

import hashlib
import json
from typing import Any, Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime
import re
import logging

logger = logging.getLogger(__name__)


@dataclass
class Artifact:
    """
    Computational artifact with unique hash.
    Represents a single computational result from an MCP tool.
    """
    tool_name: str
    tool_call_id: str
    input_hash: str
    output_hash: str
    timestamp: str

    # The actual values
    raw_output: Any
    extracted_values: List['ExtractedValue'] = field(default_factory=list)

    # Metadata
    confidence: Optional[float] = None
    method: Optional[str] = None  # e.g., "mace-mp-0", "chemeleon"

    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization."""
        return {
            "tool_name": self.tool_name,
            "tool_call_id": self.tool_call_id,
            "input_hash": self.input_hash,
            "output_hash": self.output_hash,
            "timestamp": self.timestamp,
            "confidence": self.confidence,
            "method": self.method,
            "values": [v.to_dict() for v in self.extracted_values]
        }


@dataclass
class ExtractedValue:
    """
    A specific numerical value extracted from an artifact.
    """
    value: float
    original_string: str  # Original representation (e.g., "-3.45")
    unit: Optional[str] = None
    property_type: Optional[str] = None  # formation_energy, band_gap, etc.
    context: Optional[str] = None  # Additional context

    def to_dict(self) -> Dict:
        return asdict(self)

    def matches(self, other_value: float, tolerance: float = 0.01) -> bool:
        """Check if this value matches another within tolerance."""
        return abs(self.value - other_value) < tolerance


class ArtifactTracker:
    """
    Tracks all computational artifacts and their extracted values.
    Enables reverse lookup from values to their provenance.
    """

    def __init__(self):
        self.artifacts: Dict[str, Artifact] = {}  # artifact_id -> Artifact
        self.value_index: Dict[float, List[str]] = {}  # value -> [artifact_ids]
        self.tool_outputs: Dict[str, str] = {}  # tool_call_id -> artifact_id

    def register_tool_output(
        self,
        tool_name: str,
        tool_call_id: str,
        input_data: Any,
        output_data: Any,
        timestamp: Optional[str] = None
    ) -> str:
        """
        Register a tool output and extract values.

        Returns:
            Artifact ID (the output hash)
        """
        # Generate hashes
        input_hash = self._generate_hash(input_data)
        output_hash = self._generate_hash(output_data)

        # Create artifact
        artifact = Artifact(
            tool_name=tool_name,
            tool_call_id=tool_call_id,
            input_hash=input_hash,
            output_hash=output_hash,
            timestamp=timestamp or datetime.now().isoformat(),
            raw_output=output_data
        )

        # Extract numerical values
        artifact.extracted_values = self._extract_values(output_data, tool_name)

        # Store artifact
        artifact_id = output_hash
        self.artifacts[artifact_id] = artifact
        self.tool_outputs[tool_call_id] = artifact_id

        # Index values for reverse lookup
        for extracted in artifact.extracted_values:
            if extracted.value not in self.value_index:
                self.value_index[extracted.value] = []
            self.value_index[extracted.value].append(artifact_id)

        logger.info(
            f"Registered artifact from {tool_name}: {len(artifact.extracted_values)} values extracted"
        )

        return artifact_id

    def lookup_value(
        self,
        value: float,
        tolerance: float = 0.01
    ) -> List[Tuple[Artifact, ExtractedValue]]:
        """
        Look up provenance for a numerical value.

        Args:
            value: The numerical value to look up
            tolerance: Tolerance for fuzzy matching

        Returns:
            List of (Artifact, ExtractedValue) tuples that match
        """
        matches = []

        # Check exact matches first
        if value in self.value_index:
            for artifact_id in self.value_index[value]:
                artifact = self.artifacts[artifact_id]
                for extracted in artifact.extracted_values:
                    if extracted.value == value:
                        matches.append((artifact, extracted))

        # Fuzzy matching within tolerance
        for test_value, artifact_ids in self.value_index.items():
            if abs(test_value - value) < tolerance and test_value != value:
                for artifact_id in artifact_ids:
                    artifact = self.artifacts[artifact_id]
                    for extracted in artifact.extracted_values:
                        if extracted.matches(value, tolerance):
                            matches.append((artifact, extracted))

        return matches

    def _generate_hash(self, data: Any) -> str:
        """Generate SHA256 hash for data."""
        if isinstance(data, (dict, list)):
            data_str = json.dumps(data, sort_keys=True, default=str)
        else:
            data_str = str(data)

        return hashlib.sha256(data_str.encode()).hexdigest()[:16]

    def _extract_values(self, output_data: Any, tool_name: str) -> List[ExtractedValue]:
        """
        Extract numerical values from tool output.
        """
        extracted = []

        # Handle OpenAI SDK wrapper format: {"type": "text", "text": "{JSON}"}
        if isinstance(output_data, dict) and output_data.get("type") == "text" and "text" in output_data:
            try:
                output_data = json.loads(output_data["text"])
            except (json.JSONDecodeError, TypeError):
                # If parsing fails, continue with original data
                pass

        if isinstance(output_data, dict):
            # Extract based on known patterns for each tool

            # Formation energy
            if "formation_energy" in output_data:
                extracted.append(ExtractedValue(
                    value=float(output_data["formation_energy"]),
                    original_string=str(output_data["formation_energy"]),
                    unit=output_data.get("unit", "eV/atom"),
                    property_type="formation_energy"
                ))

            # Energy per atom (often same as formation energy but explicitly listed)
            if "energy_per_atom" in output_data and output_data["energy_per_atom"] is not None:
                extracted.append(ExtractedValue(
                    value=float(output_data["energy_per_atom"]),
                    original_string=str(output_data["energy_per_atom"]),
                    unit=output_data.get("unit", "eV/atom"),
                    property_type="energy_per_atom"
                ))

            # Total energy (system total)
            if "total_energy" in output_data and output_data["total_energy"] is not None:
                extracted.append(ExtractedValue(
                    value=float(output_data["total_energy"]),
                    original_string=str(output_data["total_energy"]),
                    unit=output_data.get("unit", "eV"),
                    property_type="total_energy"
                ))

            # Band gap
            if "band_gap" in output_data:
                extracted.append(ExtractedValue(
                    value=float(output_data["band_gap"]),
                    original_string=str(output_data["band_gap"]),
                    unit=output_data.get("unit", "eV"),
                    property_type="band_gap"
                ))
            elif "band_gap_ev" in output_data and output_data["band_gap_ev"] is not None:
                extracted.append(ExtractedValue(
                    value=float(output_data["band_gap_ev"]),
                    original_string=str(output_data["band_gap_ev"]),
                    unit="eV",
                    property_type="band_gap"
                ))

            # Energy above hull
            if "energy_above_hull" in output_data:
                extracted.append(ExtractedValue(
                    value=float(output_data["energy_above_hull"]),
                    original_string=str(output_data["energy_above_hull"]),
                    unit="eV/atom",
                    property_type="energy_above_hull"
                ))

            # Bulk modulus
            if "bulk_modulus" in output_data:
                extracted.append(ExtractedValue(
                    value=float(output_data["bulk_modulus"]),
                    original_string=str(output_data["bulk_modulus"]),
                    unit="GPa",
                    property_type="bulk_modulus"
                ))

            # Lattice parameters
            if "lattice_params" in output_data:
                lattice = output_data["lattice_params"]
                if isinstance(lattice, dict):
                    for param in ['a', 'b', 'c']:
                        if param in lattice:
                            extracted.append(ExtractedValue(
                                value=float(lattice[param]),
                                original_string=str(lattice[param]),
                                unit="Å",
                                property_type=f"lattice_{param}"
                            ))

            # Space group number
            if "space_group_number" in output_data:
                extracted.append(ExtractedValue(
                    value=float(output_data["space_group_number"]),
                    original_string=str(output_data["space_group_number"]),
                    unit=None,
                    property_type="space_group_number"
                ))
            elif "number" in output_data:  # PyMatgen style
                extracted.append(ExtractedValue(
                    value=float(output_data["number"]),
                    original_string=str(output_data["number"]),
                    unit=None,
                    property_type="space_group_number"
                ))

            # Stress tensor components
            if "stress_tensor" in output_data:
                tensor = output_data["stress_tensor"]
                if isinstance(tensor, list) and len(tensor) == 3:
                    for i, row in enumerate(tensor):
                        if isinstance(row, list) and len(row) == 3:
                            for j, val in enumerate(row):
                                extracted.append(ExtractedValue(
                                    value=float(val),
                                    original_string=str(val),
                                    unit="GPa",
                                    property_type=f"stress_{i}{j}"
                                ))

            # Voltage (for battery materials)
            if "voltage" in output_data:
                extracted.append(ExtractedValue(
                    value=float(output_data["voltage"]),
                    original_string=str(output_data["voltage"]),
                    unit="V",
                    property_type="voltage"
                ))

            # Capacity (for battery materials)
            if "capacity" in output_data:
                extracted.append(ExtractedValue(
                    value=float(output_data["capacity"]),
                    original_string=str(output_data["capacity"]),
                    unit=output_data.get("capacity_unit", "mAh/g"),
                    property_type="capacity"
                ))

            # Handle nested structures
            if "structures" in output_data:
                for struct in output_data["structures"]:
                    if isinstance(struct, dict):
                        nested_values = self._extract_values(struct, tool_name)
                        extracted.extend(nested_values)

        # Also extract from string outputs (for older tools)
        elif isinstance(output_data, str):
            extracted.extend(self._extract_from_string(output_data))

        return extracted

    def _extract_from_string(self, text: str) -> List[ExtractedValue]:
        """
        Extract numerical values from string output using regex.
        """
        extracted = []

        # Pattern for scientific notation and regular numbers with units
        patterns = [
            (r'formation\s+energy.*?(-?\d+\.?\d*)\s*(eV)', 'formation_energy'),
            (r'band\s*gap.*?(\d+\.?\d*)\s*(eV)', 'band_gap'),
            (r'lattice.*?(\d+\.?\d*)\s*(Å|angstrom)', 'lattice_parameter'),
            (r'bulk\s+modulus.*?(\d+\.?\d*)\s*(GPa)', 'bulk_modulus'),
            (r'space\s+group.*?(\d+)', 'space_group_number', None),
        ]

        for pattern, prop_type, *default_unit in patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                value_str = match.group(1)
                unit = match.group(2) if len(match.groups()) > 1 else default_unit[0] if default_unit else None

                try:
                    value = float(value_str)
                    extracted.append(ExtractedValue(
                        value=value,
                        original_string=value_str,
                        unit=unit,
                        property_type=prop_type
                    ))
                except ValueError:
                    continue

        return extracted

    def get_statistics(self) -> Dict:
        """Get statistics about tracked artifacts."""
        return {
            "total_artifacts": len(self.artifacts),
            "total_values": sum(len(a.extracted_values) for a in self.artifacts.values()),
            "unique_values": len(self.value_index),
            "tools": list(set(a.tool_name for a in self.artifacts.values()))
        }