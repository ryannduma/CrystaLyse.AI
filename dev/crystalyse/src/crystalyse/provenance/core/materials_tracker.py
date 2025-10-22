"""
Materials tracking and extraction from tool outputs.

Enhanced for Phase 1.5 with Pydantic model support.
"""

import json
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict, field
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


@dataclass
class Material:
    """
    Represents a discovered material with enhanced Phase 1.5 metadata.
    """
    composition: str
    formula: Optional[str] = None
    formation_energy: Optional[float] = None
    energy_unit: str = "eV/atom"
    structure_id: Optional[str] = None
    space_group: Optional[str] = None
    lattice_params: Optional[Dict] = None
    cif_saved: bool = False
    cif_path: Optional[str] = None
    source_tool: Optional[str] = None
    timestamp: Optional[str] = None

    # Phase 1.5 additions
    energy_above_hull: Optional[float] = None
    is_stable: Optional[bool] = None
    band_gap: Optional[float] = None
    bulk_modulus: Optional[float] = None
    stress_tensor: Optional[List[List[float]]] = None
    dopants: Optional[Dict[str, List[str]]] = None
    oxidation_states: Optional[Dict[str, float]] = None
    coordination_environments: Optional[List[Dict]] = None
    confidence: Optional[float] = None
    method: Optional[str] = None  # e.g., "mace-mp-0", "chemeleon"
    
    def to_dict(self) -> Dict:
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
        self.materials: List[Material] = []
        self._compositions_seen = set()
    
    def extract_from_output(self, output: Any, tool_name: Optional[str] = None) -> List[Material]:
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
            else:
                # Try generic extraction
                materials = self._extract_generic(data)
            
            # Add source tool and timestamp
            for material in materials:
                if tool_name:
                    material.source_tool = tool_name
                if not material.timestamp:
                    material.timestamp = datetime.now().isoformat()
            
            # Track materials
            self.materials.extend(materials)
            for mat in materials:
                self._compositions_seen.add(mat.composition)
            
        except Exception as e:
            logger.error(f"Failed to extract materials: {e}")
        
        return materials
    
    def _parse_output(self, output: Any) -> Dict:
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
                    except:
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
            except:
                return {}
        
        return {}
    
    def _extract_from_comprehensive(self, data: Dict) -> List[Material]:
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
                    struct_id = struct.get("structure_id") or f"{composition}_struct_{idx+1}"
                    
                    # Get energy from lookup or structure
                    formation_energy = (
                        energy_lookup.get(struct_id) or 
                        struct.get("formation_energy") or
                        struct.get("energy")
                    )
                    
                    material = Material(
                        composition=composition,
                        formula=struct.get("formula", composition),
                        formation_energy=formation_energy,
                        structure_id=struct_id,
                        space_group=struct.get("space_group"),
                        cif_saved=struct.get("cif_saved", False),
                        lattice_params=struct.get("lattice")
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
                    space_group=mat_data.get("space_group")
                )
                materials.append(material)
        
        return materials
    
    def _extract_from_mace(self, data: Dict) -> List[Material]:
        """Extract from MACE energy calculation."""
        materials = []
        
        if "formation_energy" in data:
            material = Material(
                composition=data.get("composition", "unknown"),
                formation_energy=data["formation_energy"],
                structure_id=data.get("structure_id")
            )
            materials.append(material)
        
        return materials
    
    def _extract_from_generation(self, data: Dict) -> List[Material]:
        """Extract from structure generation output."""
        materials = []
        
        if "structures" in data:
            for struct in data["structures"]:
                material = Material(
                    composition=struct.get("composition", ""),
                    formula=struct.get("formula"),
                    space_group=struct.get("space_group"),
                    lattice_params=struct.get("lattice")
                )
                materials.append(material)
        
        return materials
    
    def _extract_generic(self, data: Dict) -> List[Material]:
        """Generic extraction for unknown formats."""
        materials = []

        # Look for common patterns
        if "composition" in data and "formation_energy" in data:
            material = Material(
                composition=data["composition"],
                formation_energy=data.get("formation_energy")
            )
            materials.append(material)

        return materials

    # Phase 1.5 extraction methods
    def _extract_from_phase15_mace_energy(self, data: Dict) -> List[Material]:
        """Extract from Phase 1.5 MACE energy calculation."""
        materials = []
        if "formation_energy" in data:
            material = Material(
                composition=data.get("composition", "unknown"),
                formation_energy=data["formation_energy"],
                energy_unit=data.get("unit", "eV/atom"),
                method="mace",
                confidence=data.get("confidence", 1.0)
            )
            materials.append(material)
        return materials

    def _extract_from_phase15_chemeleon(self, data: Dict) -> List[Material]:
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
                    cif_path=struct.get("cif_path")
                )
                materials.append(material)
        return materials

    def _extract_from_phase15_pymatgen_hull(self, data: Dict) -> List[Material]:
        """Extract from Phase 1.5 PyMatgen hull analysis."""
        materials = []
        if "composition" in data:
            material = Material(
                composition=data["composition"],
                energy_above_hull=data.get("energy_above_hull"),
                is_stable=data.get("is_stable", False),
                method="pymatgen_hull"
            )
            materials.append(material)
        return materials

    def _extract_from_phase15_space_group(self, data: Dict) -> List[Material]:
        """Extract from Phase 1.5 space group analysis."""
        materials = []
        if "space_group" in data:
            material = Material(
                composition=data.get("composition", "unknown"),
                space_group=data["space_group"],
                lattice_params={
                    "crystal_system": data.get("crystal_system"),
                    "point_group": data.get("point_group"),
                    "number": data.get("number")
                },
                method="pymatgen_symmetry"
            )
            materials.append(material)
        return materials

    def _extract_from_phase15_dopants(self, data: Dict) -> List[Material]:
        """Extract from Phase 1.5 dopant prediction."""
        materials = []
        if "composition" in data:
            material = Material(
                composition=data["composition"],
                dopants={
                    "n_type": data.get("n_type_dopants", [])[:5],
                    "p_type": data.get("p_type_dopants", [])[:5]
                },
                method="smact_dopants"
            )
            materials.append(material)
        return materials

    def _extract_from_phase15_band_gap(self, data: Dict) -> List[Material]:
        """Extract from Phase 1.5 band gap estimation."""
        materials = []
        if "band_gap" in data:
            material = Material(
                composition=data.get("composition", "unknown"),
                band_gap=data["band_gap"],
                confidence=data.get("confidence"),
                method="smact_band_gap"
            )
            materials.append(material)
        return materials

    def _extract_from_phase15_stress(self, data: Dict) -> List[Material]:
        """Extract from Phase 1.5 stress calculation."""
        materials = []
        if "stress_tensor" in data:
            material = Material(
                composition=data.get("composition", "unknown"),
                stress_tensor=data["stress_tensor"],
                method="mace_stress"
            )
            materials.append(material)
        return materials

    def _extract_from_phase15_eos(self, data: Dict) -> List[Material]:
        """Extract from Phase 1.5 EOS fitting."""
        materials = []
        if "bulk_modulus" in data:
            material = Material(
                composition=data.get("composition", "unknown"),
                bulk_modulus=data["bulk_modulus"],
                method="mace_eos"
            )
            materials.append(material)
        return materials
    
    def get_summary(self) -> Dict[str, Any]:
        """Get summary statistics of tracked materials."""
        total = len(self.materials)
        with_energy = sum(1 for m in self.materials if m.has_energy)
        
        energies = [m.formation_energy for m in self.materials if m.has_energy]
        
        summary = {
            "total_materials": total,
            "unique_compositions": len(self._compositions_seen),
            "materials_with_energy": with_energy,
            "energy_coverage": (with_energy / max(total, 1)) * 100
        }
        
        if energies:
            summary.update({
                "min_energy": min(energies),
                "max_energy": max(energies),
                "avg_energy": sum(energies) / len(energies)
            })
        
        return summary
    
    def to_catalog(self) -> List[Dict]:
        """Export materials as enhanced catalog with Phase 1.5 metadata."""
        return [m.to_dict() for m in self.materials]

    def to_enhanced_catalog(self) -> Dict[str, Any]:
        """
        Export materials as an enhanced catalog with metadata and statistics.

        Returns:
            Dictionary containing materials, metadata, and summary statistics
        """
        # Group materials by method/tool
        by_method = {}
        for material in self.materials:
            method = material.method or "unknown"
            if method not in by_method:
                by_method[method] = []
            by_method[method].append(material.to_dict())

        # Calculate statistics
        stats = self.get_summary()
        stats["methods_used"] = list(by_method.keys())

        # Count materials with specific properties
        stats["materials_with_band_gap"] = sum(
            1 for m in self.materials if m.band_gap is not None
        )
        stats["materials_with_dopants"] = sum(
            1 for m in self.materials if m.dopants
        )
        stats["stable_materials"] = sum(
            1 for m in self.materials if m.is_stable is True
        )
        stats["materials_with_stress"] = sum(
            1 for m in self.materials if m.stress_tensor is not None
        )

        return {
            "version": "1.5.0",
            "timestamp": datetime.now().isoformat(),
            "total_materials": len(self.materials),
            "materials": self.to_catalog(),
            "materials_by_method": by_method,
            "statistics": stats,
            "unique_compositions": list(self._compositions_seen)
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

        with open(catalog_path, 'w') as f:
            json.dump(catalog_data, f, indent=2, default=str)