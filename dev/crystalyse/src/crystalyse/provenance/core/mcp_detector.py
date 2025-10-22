"""
MCP Tool Detection from SDK wrapped outputs
"""

import json
from typing import Any, Optional, Dict
import logging

logger = logging.getLogger(__name__)


class MCPDetector:
    """
    Detects actual MCP tool names from SDK-wrapped outputs.
    
    The OpenAI Agents SDK wraps MCP tools, making them appear as "unknown_tool"
    in events. This detector identifies the actual tool by parsing output structure.
    """
    
    # Known tool signatures based on output structure
    # Updated for Phase 1.5 architecture with Pydantic models
    TOOL_SIGNATURES = {
        # Original tools
        "comprehensive_materials_analysis": [
            "generated_structures",
            "energy_calculations"
        ],
        "creative_discovery_pipeline": [
            "generated_structures",
            "analysis_mode",
            "pipeline_steps"
        ],

        # Phase 1.5 SMACT tools
        "validate_composition": [
            "is_valid",
            "charge_balanced",
            "electronegativity_test"
        ],
        "estimate_band_gap": [
            "band_gap_ev",
            "band_gap_estimate",
            "confidence"
        ],
        "predict_dopants": [
            "n_type_dopants",
            "p_type_dopants",
            "species"
        ],
        "smact_validate_fast": [
            "is_valid",
            "reason",
            "composition"
        ],
        "generate_ml_representation": [
            "representation",
            "composition",
            "vector_length"
        ],
        "filter_compositions": [
            "valid_compositions",
            "invalid_compositions",
            "total_processed"
        ],

        # Phase 1.5 Chemeleon tools
        "generate_crystal_csp": [
            "success",
            "formula",
            "predicted_structures",
            "checkpoint_used"
        ],

        # Phase 1.5 MACE tools
        "calculate_formation_energy": [
            "formation_energy",
            "energy_per_atom",
            "total_energy",
            "composition"
        ],
        "relax_structure": [
            "relaxed_structure",
            "initial_energy",
            "final_energy",
            "relaxation_steps"
        ],
        "calculate_stress": [
            "stress_tensor",
            "pressure",
            "von_mises_stress"
        ],
        "fit_equation_of_state": [
            "bulk_modulus",
            "bulk_modulus_derivative",
            "equilibrium_volume"
        ],
        "list_foundation_models": [
            "models",
            "total_models"
        ],

        # Phase 1.5 PyMatgen tools
        "analyze_space_group": [
            "space_group",
            "number",
            "crystal_system",
            "point_group"
        ],
        "calculate_energy_above_hull": [
            "energy_above_hull",
            "is_stable",
            "is_metastable",
            "decomposition_products"
        ],
        "analyze_coordination": [
            "site_environments",
            "average_coordination"
        ],
        "analyze_oxidation_states": [
            "oxidation_states",
            "is_valid",
            "charge_balanced"
        ],

        # Phase 1.5 Visualization tools
        "save_structure_as_cif": [
            "success",
            "file_path",
            "structure_info"
        ],
        "visualize_structure": [
            "visualization_url",
            "structure_data"
        ]
    }
    
    @classmethod
    def detect_tool(cls, output: Any) -> Optional[str]:
        """
        Detect MCP tool from output structure.
        
        Args:
            output: Tool output (can be string, dict, or wrapped response)
            
        Returns:
            Detected tool name or None
        """
        try:
            # Parse the output to get actual data
            data = cls._unwrap_output(output)
            
            if not isinstance(data, dict):
                return None
            
            # Check for explicit tool indicators
            if "server_type" in data:
                if data["server_type"] == "chemistry-creative-server":
                    return "creative_discovery_pipeline"
                elif data["server_type"] == "chemistry-unified-server":
                    return "comprehensive_materials_analysis"
            
            # Check analysis mode for creative pipeline
            if data.get("analysis_mode") == "creative":
                return "creative_discovery_pipeline"
            
            # Match against known signatures
            data_keys = set(data.keys())
            best_match = None
            best_score = 0
            
            for tool_name, signature_keys in cls.TOOL_SIGNATURES.items():
                # Count matching keys
                matches = sum(1 for key in signature_keys if key in data_keys)
                score = matches / len(signature_keys)
                
                if score > best_score:
                    best_score = score
                    best_match = tool_name
            
            # Require at least 50% match
            if best_score >= 0.5:
                return best_match
            
            # Fallback detection for specific patterns
            if "generated_structures" in data and "energy_calculations" in data:
                # Both present indicates comprehensive analysis
                return "comprehensive_materials_analysis"
            elif "generated_structures" in data:
                # Just structures might be creative mode
                return "creative_discovery_pipeline"
            
            return None
            
        except Exception as e:
            logger.debug(f"Failed to detect MCP tool: {e}")
            return None
    
    @classmethod
    def _unwrap_output(cls, output: Any) -> Dict:
        """
        Unwrap SDK response structure to get actual data.
        
        The SDK may wrap responses in:
        {
            "type": "text",
            "text": "{actual_json_here}",
            "annotations": null,
            "meta": null
        }
        """
        if not output:
            return {}
        
        # Handle dict responses
        if isinstance(output, dict):
            # Check if it's an SDK wrapper
            if output.get("type") == "text" and "text" in output:
                # Extract and parse the text field
                text_content = output["text"]
                if isinstance(text_content, str):
                    try:
                        return json.loads(text_content)
                    except json.JSONDecodeError:
                        return {"raw_text": text_content}
                else:
                    return text_content
            else:
                # Already unwrapped
                return output
        
        # Handle string responses
        elif isinstance(output, str):
            try:
                parsed = json.loads(output)
                # Check if the parsed result is also wrapped
                if isinstance(parsed, dict) and parsed.get("type") == "text":
                    return cls._unwrap_output(parsed)
                return parsed
            except json.JSONDecodeError:
                return {"raw_text": output}
        
        return {}
    
    @classmethod
    def get_tool_category(cls, tool_name: str) -> str:
        """
        Get category of the tool for metrics grouping.

        Returns:
            Tool category (generation, validation, calculation, visualization, analysis)
        """
        categories = {
            # Original tools
            "comprehensive_materials_analysis": "analysis",
            "creative_discovery_pipeline": "generation",

            # Phase 1.5 SMACT tools
            "validate_composition": "validation",
            "estimate_band_gap": "calculation",
            "predict_dopants": "analysis",
            "smact_validate_fast": "validation",
            "generate_ml_representation": "analysis",
            "filter_compositions": "validation",

            # Phase 1.5 Chemeleon tools
            "generate_crystal_csp": "generation",

            # Phase 1.5 MACE tools
            "calculate_formation_energy": "calculation",
            "relax_structure": "optimization",
            "calculate_stress": "calculation",
            "fit_equation_of_state": "calculation",
            "list_foundation_models": "utility",

            # Phase 1.5 PyMatgen tools
            "analyze_space_group": "analysis",
            "calculate_energy_above_hull": "calculation",
            "analyze_coordination": "analysis",
            "analyze_oxidation_states": "validation",

            # Phase 1.5 Visualization tools
            "save_structure_as_cif": "visualization",
            "visualize_structure": "visualization"
        }
        return categories.get(tool_name, "other")