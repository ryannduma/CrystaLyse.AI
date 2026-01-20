"""
Dual output formatter for Crystalyse query results.

This module provides functionality to generate both JSON and Markdown output files
for individual query results, similar to the comprehensive test results format.

The output format includes:
- Structured JSON file (raw_result.json) with full computational data
- Human-readable Markdown report (report.md) with formatted analysis
- Automatic directory creation with timestamped naming
"""

import json
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from .universal_cif_visualizer import UniversalCIFVisualizer

logger = logging.getLogger(__name__)


class DualOutputFormatter:
    """
    Generates dual JSON/Markdown output for Crystalyse query results.

    Creates a directory structure similar to comprehensive test results:
    - query_results_YYYY_MM_DD_HHMMSS/
      - raw_result.json
      - report.md
    """

    def __init__(self, base_output_dir: str = None):
        """
        Initialise the dual output formatter.

        Args:
            base_output_dir: Base directory for all query results
        """
        if base_output_dir is None:
            # Use all-runtime-output directory in project root
            current_file = Path(__file__)
            project_root = current_file.parent.parent.parent
            base_output_dir = project_root / "all-runtime-output"
        self.base_output_dir = Path(base_output_dir)
        self.cif_visualizer = UniversalCIFVisualizer()

    def _is_valid_cif_content(self, cif_content: str) -> bool:
        """
        Validate that CIF content appears to be complete and well-formed.

        Args:
            cif_content: Raw CIF content string

        Returns:
            True if content appears valid, False otherwise
        """
        if not cif_content or len(cif_content.strip()) < 20:
            return False

        # Check for essential CIF elements
        essential_elements = [
            "_chemical_formula",  # Some form of chemical formula
            "_cell_length_a",  # Unit cell parameters
            "_atom_site",  # Atomic positions
        ]

        # Must have at least 2 of 3 essential elements
        found_elements = sum(1 for element in essential_elements if element in cif_content)
        if found_elements < 2:
            logger.warning(
                f"CIF validation failed: only {found_elements}/3 essential elements found"
            )
            return False

        # Check for obvious corruption markers
        corruption_markers = [
            "data_image0\\n_chemical_formula_structural",  # Truncated header
            '\\\\\\\\"',  # Excessive escaping
            "ToolCallOutputItem",  # Extraction artifacts
        ]

        for marker in corruption_markers:
            if marker in cif_content and len(cif_content) < 100:
                logger.warning(
                    f"CIF validation failed: corruption marker '{marker}' found in short content"
                )
                return False

        # Must not end abruptly with escape characters
        stripped = cif_content.strip()
        if stripped.endswith("\\\\") and len(stripped) < 50:
            logger.warning(
                "CIF validation failed: content ends with escape character and is very short"
            )
            return False

        return True

    def _robust_string_cleanup(self, content: str) -> str:
        """
        Robustly clean up escaped string content from various JSON sources.

        Args:
            content: Raw string content with potential escaping

        Returns:
            Cleaned string content
        """
        if not isinstance(content, str):
            return str(content)

        # Start with the original content
        clean_content = content

        # Handle multiple levels of JSON escaping systematically
        escape_patterns = [
            # Handle newlines (from most specific to least)
            ("\\\\\\\\\\\\\\\\n", "\\n"),  # 8 backslashes + n -> newline
            ("\\\\\\\\\\\\n", "\\n"),  # 6 backslashes + n -> newline
            ("\\\\\\\\n", "\\n"),  # 4 backslashes + n -> newline
            ("\\\\n", "\\n"),  # 2 backslashes + n -> newline
            # Handle quotes (from most specific to least)
            ('\\\\\\\\\\\\\\\\"', '"'),  # 8 backslashes + quote -> quote
            ('\\\\\\\\\\\\"', '"'),  # 6 backslashes + quote -> quote
            ('\\\\\\\\"', '"'),  # 4 backslashes + quote -> quote
            ('\\\\\\\\"\\\\\\\\"\\\\\\\\\n', "\\n"),  # Multiple escaped quotes
            ('\\\\"', '"'),  # 2 backslashes + quote -> quote
            # Handle backslashes themselves
            ("\\\\\\\\\\\\\\\\", "\\\\\\\\"),  # 8 backslashes -> 2 backslashes
            ("\\\\\\\\\\\\", "\\\\"),  # 6 backslashes -> 1 backslash
            ("\\\\\\\\", "\\\\"),  # 4 backslashes -> 1 backslash
        ]

        # Apply escape pattern replacements
        for pattern, replacement in escape_patterns:
            clean_content = clean_content.replace(pattern, replacement)

        # Additional cleanup for common artifacts
        artifact_patterns = [
            ("\\\\r\\\\n", "\\n"),  # Windows line endings
            ("\\\\r", "\\n"),  # Mac line endings
            ("\\\\t", " "),  # Tabs to spaces
        ]

        for pattern, replacement in artifact_patterns:
            clean_content = clean_content.replace(pattern, replacement)

        return clean_content

    def _extract_cif_from_json_structure(
        self, data: dict, source_description: str
    ) -> dict[str, dict[str, str]]:
        """
        Extract CIF content from various JSON structure formats.

        Args:
            data: Parsed JSON data structure
            source_description: Description of the data source for logging

        Returns:
            Dictionary mapping composition names to CIF data
        """
        extracted_cifs = {}

        # Method 1: Check for most_stable_cifs
        if "most_stable_cifs" in data:
            most_stable_cifs = data["most_stable_cifs"]
            logger.info(f"Found most_stable_cifs in {source_description}")

            for comp, cif_data in most_stable_cifs.items():
                if isinstance(cif_data, dict) and "cif" in cif_data:
                    cif_content = self._robust_string_cleanup(cif_data["cif"])

                    if self._is_valid_cif_content(cif_content):
                        structure_id = cif_data.get("structure_id", f"{comp}_stable")
                        extracted_cifs[comp] = {
                            "cif": cif_content,
                            "filename": f"{comp}_most_stable.cif",
                            "structure_id": structure_id,
                            "source": source_description,
                        }
                        logger.info(
                            f"Successfully extracted valid CIF for {comp} from {source_description}"
                        )
                    else:
                        logger.warning(
                            f"Skipping invalid CIF content for {comp} from {source_description}"
                        )

        # Method 2: Check for generated_structures (creative mode)
        if "generated_structures" in data:
            structures_data = data["generated_structures"]
            logger.info(f"Found generated_structures in {source_description}")

            for comp_data in structures_data:
                if isinstance(comp_data, dict) and "structures" in comp_data:
                    composition = comp_data.get("composition", "unknown")
                    for j, struct in enumerate(comp_data["structures"]):
                        if isinstance(struct, dict) and "cif" in struct:
                            cif_content = self._robust_string_cleanup(struct["cif"])

                            if self._is_valid_cif_content(cif_content):
                                formula = struct.get("formula", composition)
                                sample_idx = struct.get("sample_index", j)
                                struct_id = f"{formula}_struct_{sample_idx}"

                                extracted_cifs[formula] = {
                                    "cif": cif_content,
                                    "filename": f"{struct_id}.cif",
                                    "structure_id": struct_id,
                                    "source": source_description,
                                }
                                logger.info(
                                    f"Successfully extracted valid CIF for {formula} from {source_description}"
                                )
                            else:
                                logger.warning(
                                    f"Skipping invalid CIF content for structure {j} in {composition}"
                                )

        # Method 3: Check for direct structures array
        if "structures" in data and isinstance(data["structures"], list):
            structures = data["structures"]
            logger.info(f"Found direct structures array in {source_description}")

            for j, struct in enumerate(structures):
                if isinstance(struct, dict) and "cif" in struct:
                    cif_content = self._robust_string_cleanup(struct["cif"])

                    if self._is_valid_cif_content(cif_content):
                        formula = struct.get("formula", struct.get("composition", f"structure_{j}"))
                        struct_id = struct.get("id", f"{formula}_struct_{j + 1}")

                        extracted_cifs[formula] = {
                            "cif": cif_content,
                            "filename": f"{struct_id}.cif",
                            "structure_id": struct_id,
                            "source": source_description,
                        }
                        logger.info(
                            f"Successfully extracted valid CIF for {formula} from {source_description}"
                        )
                    else:
                        logger.warning(f"Skipping invalid CIF content for structure {j}")

        # Method 4: Check for individual structure object (new individual tool format)
        if "cif" in data and isinstance(data, dict):
            logger.info(f"Found individual structure object in {source_description}")
            cif_content = self._robust_string_cleanup(data["cif"])

            if self._is_valid_cif_content(cif_content):
                formula = data.get("formula", data.get("composition", "unknown"))
                struct_id = data.get("id", f"{formula}_struct_1")

                extracted_cifs[formula] = {
                    "cif": cif_content,
                    "filename": f"{struct_id}.cif",
                    "structure_id": struct_id,
                    "source": source_description,
                }
                logger.info(
                    f"Successfully extracted valid CIF for {formula} from {source_description}"
                )
            else:
                logger.warning(
                    f"Skipping invalid CIF content for individual structure in {source_description}"
                )

        return extracted_cifs

    def _extract_cif_from_list_structure(
        self, data: list, source_description: str
    ) -> dict[str, dict[str, str]]:
        """
        Extract CIF content from array-based structure formats (new individual tool format).

        Args:
            data: List of structure data items
            source_description: Description of the data source for logging

        Returns:
            Dictionary mapping composition names to CIF data
        """
        extracted_cifs = {}
        logger.info(f"Processing {len(data)} structures from {source_description}")

        for j, struct in enumerate(data):
            if isinstance(struct, dict) and "cif" in struct:
                cif_content = self._robust_string_cleanup(struct["cif"])

                if self._is_valid_cif_content(cif_content):
                    formula = struct.get("formula", struct.get("composition", f"structure_{j}"))
                    struct.get("id", f"{formula}_struct_{j + 1}")
                    sample_idx = struct.get("sample_idx", j)

                    # Use the structure ID if provided, otherwise generate one
                    if "id" in struct:
                        final_id = struct["id"]
                        filename = f"{final_id}.cif"
                    else:
                        final_id = f"{formula}_struct_{sample_idx}"
                        filename = f"{final_id}.cif"

                    extracted_cifs[final_id] = {
                        "cif": cif_content,
                        "filename": filename,
                        "structure_id": final_id,
                        "source": source_description,
                    }
                    logger.info(
                        f"Successfully extracted valid CIF for {final_id} from {source_description}"
                    )
                else:
                    logger.warning(
                        f"Skipping invalid CIF content for structure {j} in {source_description}"
                    )

        return extracted_cifs

    def create_query_output(
        self,
        query: str,
        result: dict[str, Any],
        execution_time: float,
        model: str = "unknown",
        mode: str = "unknown",
    ) -> Path:
        """
        Create dual JSON/Markdown output for a query result.

        Args:
            query: The original user query
            result: Full result dictionary from agent.discover_materials()
            execution_time: Time taken for query execution
            model: Model used (e.g., "o4-mini", "o3")
            mode: Mode used (e.g., "creative", "rigorous")

        Returns:
            Path to the created directory
        """
        # Create timestamped directory
        timestamp = datetime.now().strftime("%Y_%m_%d_%H%M%S")
        query_slug = self._create_query_slug(query)
        output_dir = self.base_output_dir / f"{query_slug}_{timestamp}"
        output_dir.mkdir(parents=True, exist_ok=True)

        # Generate tool validation data
        tool_validation = self._generate_tool_validation(result)

        # Create Markdown report
        report_content = self._create_markdown_report(
            query=query,
            result=result,
            execution_time=execution_time,
            model=model,
            mode=mode,
            tool_validation=tool_validation,
        )

        # Write files
        report_path = output_dir / "report.md"
        json_path = output_dir / "raw_result.json"

        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report_content)

        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)

        # Extract and save CIF files if available (mode-aware)
        cif_count, extracted_cifs = self._save_cif_files_mode_aware(result, output_dir, mode)

        # Create HTML visualizations for CIF files using universal visualizer
        html_count = self._save_html_visualizations_universal(output_dir, extracted_cifs)

        # Log extraction results for debugging
        if cif_count == 0:
            logger.warning(
                f"No CIF files extracted from result. Mode: {mode}, Tool calls: {tool_validation['tool_calls_count']}"
            )
            # Check if computational tools were used but CIFs not extracted
            computational_tools = [
                "batch_discovery_pipeline",
                "generate_crystal_csp",
                "smact_validity",
            ]
            tools_used = tool_validation.get("tools_used", [])
            if any(tool in str(tools_used) for tool in computational_tools):
                logger.warning(
                    "Computational tools were used but no CIFs extracted - check extraction logic"
                )

        # Update report with actual CIF file count and visualization info
        if cif_count > 0 or html_count > 0:
            # Replace the CIF count in the report
            import re

            status_text = []
            if cif_count > 0:
                status_text.append(f"{cif_count} CIF files saved (in cif_files/)")
            if html_count > 0:
                status_text.append(f"{html_count} HTML visualizations created (in visualizations/)")

            status_line = ", ".join(status_text)

            updated_report = re.sub(r"\d+ CIF files found", status_line, report_content)
            with open(report_path, "w", encoding="utf-8") as f:
                f.write(updated_report)

        return output_dir

    def _save_cif_files_mode_aware(
        self, result: dict[str, Any], output_dir: Path, mode: str
    ) -> tuple[int, dict[str, dict[str, str]]]:
        """
        Extract and save CIF files using mode-specific logic.

        Args:
            result: Full result dictionary from agent
            output_dir: Directory to save CIF files to
            mode: Analysis mode ("creative" or "rigorous")

        Returns:
            Number of CIF files saved and extracted CIF data
        """
        if mode == "creative":
            # Use creative formatter for creative mode
            from crystalyse.output.creative_formatter import CreativeFormatter

            creative_formatter = CreativeFormatter()
            return creative_formatter.extract_cif_files_creative(result, output_dir)
        else:
            # Use regular extraction for rigorous mode
            return self._save_cif_files(result, output_dir)

    def _create_query_slug(self, query: str, max_length: int = 50) -> str:
        """
        Create a filesystem-safe slug from a query string.

        Args:
            query: The original query string
            max_length: Maximum length of the slug

        Returns:
            Filesystem-safe slug
        """
        # Remove special characters and replace spaces with underscores
        slug = re.sub(r"[^\w\s-]", "", query.lower())
        slug = re.sub(r"[-\s]+", "_", slug)

        # Truncate if too long
        if len(slug) > max_length:
            slug = slug[:max_length].rstrip("_")

        return slug or "query"

    def _generate_tool_validation(self, result: dict[str, Any]) -> dict[str, Any]:
        """
        Generate tool validation data from result.

        This mimics the validation logic from the comprehensive test system
        but works with individual query results.

        Args:
            result: Result dictionary from agent

        Returns:
            Tool validation dictionary
        """
        tool_validation = result.get("tool_validation", {})
        metrics = result.get("metrics", {})

        # Extract basic validation info
        validation_data = {
            "tool_calls_count": metrics.get("tool_calls", 0),
            "tools_used": tool_validation.get("tools_used", []),
            "validation_passed": not tool_validation.get("potential_hallucination", False),
            "hallucination_risk": "low"
            if not tool_validation.get("potential_hallucination", False)
            else "high",
            "needs_computation": tool_validation.get("needs_computation", False),
            "potential_hallucination": tool_validation.get("potential_hallucination", False),
            "critical_failure": tool_validation.get("critical_failure", False),
            "smact_used": tool_validation.get("smact_used", False),
            "chemeleon_used": tool_validation.get("chemeleon_used", False),
            "mace_used": tool_validation.get("mace_used", False),
            "contains_computational_results": tool_validation.get(
                "contains_computational_results", False
            ),
        }

        return validation_data

    def _create_markdown_report(
        self,
        query: str,
        result: dict[str, Any],
        execution_time: float,
        model: str,
        mode: str,
        tool_validation: dict[str, Any],
    ) -> str:
        """
        Create the Markdown report content.

        Args:
            query: Original user query
            result: Full result dictionary
            execution_time: Execution time in seconds
            model: Model used
            mode: Mode used
            tool_validation: Tool validation data

        Returns:
            Formatted Markdown content
        """
        # Extract key information
        response_text = str(result.get("discovery_result", ""))
        compositions = self._extract_compositions(response_text)
        cif_files = self._extract_cif_files(response_text)

        # Create sanitised query title
        query_title = query[:80] + "..." if len(query) > 80 else query

        report = f"""# {query_title}

## Query
{query}

## Analysis Results

### Execution Summary
- **Status**: {result.get("status", "unknown")}
- **Execution Time**: {execution_time:.2f} seconds
- **Model Used**: {model}
- **Mode**: {mode}
- **Total Items**: {result.get("metrics", {}).get("total_items", 0)}

### Tool Usage Validation
- **Tool Calls Made**: {tool_validation["tool_calls_count"]}
- **Tools Actually Used**: {", ".join(tool_validation.get("tools_used", [])) if tool_validation.get("tools_used") else "unknown"}
- **Validation Passed**: {"✅" if tool_validation["validation_passed"] else "❌"}
- **Hallucination Risk**: {tool_validation["hallucination_risk"]}
- **Needs Computation**: {"Yes" if tool_validation.get("needs_computation", False) else "No"}
- **Potential Hallucination**: {"Yes" if tool_validation.get("potential_hallucination", False) else "No"}
- **Critical Failure**: {"Yes" if tool_validation.get("critical_failure", False) else "No"}

"""

        # Add success indicator if tools are working properly
        if (
            tool_validation["validation_passed"]
            and tool_validation["tool_calls_count"] > 0
            and not tool_validation.get("potential_hallucination", False)
        ):
            tools_used_str = (
                ", ".join(tool_validation.get("tools_used", []))
                if tool_validation.get("tools_used")
                else "MCP tools"
            )
            report += f"""
### ✅ Tool Usage Success
- **All tools working correctly**
- **No hallucination detected**
- **{tool_validation["tool_calls_count"]} computational tools called successfully**
- **Agent properly using: {tools_used_str}**

"""

        # Add validation issues if any
        if not tool_validation["validation_passed"] or tool_validation.get(
            "potential_hallucination", False
        ):
            report += f"""
### ⚠️ Validation Issues
Tool usage validation detected potential issues

**Detailed Analysis:**
- Query requires computation: {tool_validation.get("needs_computation", "Unknown")}
- Tools actually called: {tool_validation["tool_calls_count"]}
- Hallucination detected: {tool_validation.get("potential_hallucination", False)}
- Critical failure: {tool_validation.get("critical_failure", False)}

"""

        # Add main response
        report += f"""
### Agent Response
{response_text}

### Discovered Compositions
{", ".join(compositions) if compositions else "None extracted"}

### CIF Files Generated
{len(cif_files)} CIF files found

"""

        # Add error details if failed
        if result.get("status") == "failed":
            report += f"""
### Error Details
{result.get("error", "Unknown error")}

"""

        # Add performance metrics
        if "metrics" in result:
            metrics = result["metrics"]
            infrastructure_stats = metrics.get("infrastructure_stats", {})

            report += f"""
### Performance Metrics
- **Tool Calls**: {metrics.get("tool_calls", 0)}
- **Raw Responses**: {metrics.get("raw_responses", 0)}
- **Infrastructure Stats**: {json.dumps(infrastructure_stats, indent=2) if infrastructure_stats else "Not available"}

"""

        return report

    def _extract_compositions(self, text: str) -> list[str]:
        """
        Extract chemical compositions from text.

        Args:
            text: Text to search for compositions

        Returns:
            List of found chemical compositions
        """
        # Pattern for chemical formulas (e.g., Li2CO3, NaFePO4, etc.)
        composition_pattern = r"\b[A-Z][a-z]?(?:\d+)?(?:[A-Z][a-z]?(?:\d+)?)*\b"

        # Find all matches
        matches = re.findall(composition_pattern, text)

        # Filter out common words that might match the pattern
        common_words = {
            "Na",
            "Al",
            "Si",
            "Ca",
            "Mg",
            "Fe",
            "Li",
            "Co",
            "Ni",
            "Mn",
            "Ti",
            "O",
            "H",
            "N",
            "C",
            "S",
            "P",
            "Cl",
            "Br",
            "F",
            "I",
        }
        filtered_matches = []

        for match in matches:
            # Keep if it's longer than 2 characters or if it contains numbers
            if len(match) > 2 or any(char.isdigit() for char in match):
                # Additional check: make sure it's not just a common element symbol
                if not (len(match) <= 2 and match in common_words):
                    filtered_matches.append(match)

        # Remove duplicates and sort
        unique_compositions = sorted(set(filtered_matches))

        return unique_compositions

    def _extract_cif_files(self, text: str) -> list[str]:
        """
        Extract CIF file references from text.

        Args:
            text: Text to search for CIF files

        Returns:
            List of found CIF file references
        """
        # Pattern for CIF file mentions
        cif_pattern = r"\b\w+\.cif\b"

        # Find all CIF file mentions
        cif_files = re.findall(cif_pattern, text, re.IGNORECASE)

        # Remove duplicates
        unique_cif_files = list(set(cif_files))

        return unique_cif_files

    def _save_cif_files(
        self, result: dict[str, Any], output_dir: Path
    ) -> tuple[int, dict[str, dict[str, str]]]:
        """
        Extract and save CIF files from the result using robust parsing methods.

        Args:
            result: Full result dictionary from agent
            output_dir: Directory to save CIF files to

        Returns:
            Number of CIF files saved and extracted CIF data
        """
        cif_count = 0
        extracted_cifs = {}
        cif_dir = output_dir / "cif_files"

        logger.info("Starting robust CIF extraction from result data")

        # Method 1: Extract from new_items with structured approach
        new_items = result.get("new_items", [])
        for i, item in enumerate(new_items):
            # Handle structured tool call outputs
            if isinstance(item, dict) and item.get("type") == "tool_call_output":
                output = item.get("output", {})

                # Case 1: JSON string in text field
                if isinstance(output, dict) and "text" in output:
                    try:
                        text_content = output["text"]
                        parsed_data = json.loads(text_content)
                        logger.info(f"Successfully parsed JSON from tool_call_output[{i}]")

                        # Extract using unified helper method
                        item_cifs = self._extract_cif_from_json_structure(
                            parsed_data, f"tool_call_output[{i}]"
                        )
                        extracted_cifs.update(item_cifs)

                    except json.JSONDecodeError as e:
                        logger.warning(f"Failed to parse JSON in tool_call_output[{i}]: {e}")

                # Case 2: Direct structured output (dict)
                elif isinstance(output, dict):
                    item_cifs = self._extract_cif_from_json_structure(
                        output, f"structured_output[{i}]"
                    )
                    extracted_cifs.update(item_cifs)

                # Case 3: Array output (new individual tool format)
                elif isinstance(output, list):
                    logger.info(
                        f"Found array output in tool_call_output[{i}] with {len(output)} items"
                    )

                    # Check if this is an array of structures with text/cif data
                    structures_to_process = []
                    for j, output_item in enumerate(output):
                        if isinstance(output_item, dict):
                            # Check for text field containing JSON
                            if "text" in output_item:
                                try:
                                    struct_data = json.loads(output_item["text"])
                                    if isinstance(struct_data, dict) and "cif" in struct_data:
                                        structures_to_process.append(struct_data)
                                        logger.info(f"Found structure data in array item {j}")
                                except json.JSONDecodeError:
                                    logger.warning(f"Failed to parse JSON in array item {j}")
                            # Direct structure data
                            elif "cif" in output_item:
                                structures_to_process.append(output_item)

                    if structures_to_process:
                        item_cifs = self._extract_cif_from_list_structure(
                            structures_to_process, f"array_output[{i}]"
                        )
                        extracted_cifs.update(item_cifs)

            # Handle string representations with fallback parsing
            elif isinstance(item, str) and "ToolCallOutputItem" in item:
                self._extract_from_string_representation(item, i, extracted_cifs)

        # Method 2: Extract from direct tool_calls
        tool_calls = result.get("tool_calls", [])
        for i, call in enumerate(tool_calls):
            if isinstance(call, dict) and "output" in call:
                output = call.get("output", {})
                if isinstance(output, dict):
                    item_cifs = self._extract_cif_from_json_structure(output, f"tool_calls[{i}]")
                    extracted_cifs.update(item_cifs)

        # Method 3: Extract from raw_response (legacy support)
        raw_response = result.get("raw_response", {})
        if isinstance(raw_response, dict):
            raw_items = raw_response.get("new_items", [])
            for i, item in enumerate(raw_items):
                if isinstance(item, dict) and item.get("type") == "tool_output":
                    output = item.get("output", {})
                    if isinstance(output, str):
                        try:
                            output = json.loads(output)
                        except json.JSONDecodeError:
                            continue

                    if isinstance(output, dict):
                        item_cifs = self._extract_cif_from_json_structure(
                            output, f"raw_response[{i}]"
                        )
                        extracted_cifs.update(item_cifs)

        # Save all valid CIF files to disk
        if extracted_cifs:
            cif_dir.mkdir(exist_ok=True)
            logger.info(f"Created CIF directory: {cif_dir}")

            for comp, cif_info in extracted_cifs.items():
                cif_content = cif_info["cif"]
                cif_filename = cif_info["filename"]
                cif_path = cif_dir / cif_filename

                try:
                    with open(cif_path, "w", encoding="utf-8") as f:
                        f.write(cif_content)
                    cif_count += 1
                    logger.info(f"Successfully saved CIF file: {cif_filename}")

                except Exception as e:
                    logger.error(f"Failed to write CIF file {cif_filename}: {e}")
                    # Remove from extracted_cifs if we couldn't save it
                    del extracted_cifs[comp]

        logger.info(
            f"CIF extraction complete: {cif_count} files saved, {len(extracted_cifs)} structures for HTML generation"
        )
        return cif_count, extracted_cifs

    def _extract_from_string_representation(
        self, item_str: str, item_index: int, extracted_cifs: dict[str, dict[str, str]]
    ) -> None:
        """
        Fallback method to extract CIF data from string representations.

        Args:
            item_str: String representation of tool output
            item_index: Index for logging purposes
            extracted_cifs: Dictionary to update with extracted CIF data
        """
        # Try to extract JSON from the string using regex
        if "generated_structures" in item_str or "most_stable_cifs" in item_str:
            # Look for JSON content patterns
            json_patterns = [
                r'{"type":"text","text":"(.*?)","annotations"',  # Wrapped JSON
                r'"text":\s*"({.*?})"',  # Direct JSON in text field
            ]

            for pattern in json_patterns:
                match = re.search(pattern, item_str, re.DOTALL)
                if match:
                    json_text = match.group(1)

                    # Clean up the JSON string
                    json_text = self._robust_string_cleanup(json_text)

                    try:
                        parsed_data = json.loads(json_text)
                        logger.info(
                            f"Successfully parsed JSON from string representation[{item_index}]"
                        )

                        item_cifs = self._extract_cif_from_json_structure(
                            parsed_data, f"string_repr[{item_index}]"
                        )
                        extracted_cifs.update(item_cifs)
                        return  # Success, no need to try other patterns

                    except json.JSONDecodeError as e:
                        logger.warning(
                            f"Failed to parse extracted JSON from string[{item_index}]: {e}"
                        )
                        continue

            logger.warning(f"Could not extract valid JSON from string representation[{item_index}]")

    def _create_html_visualization(self, cif_content: str, formula: str, structure_id: str) -> str:
        """
        Create an HTML visualization of a crystal structure using 3Dmol.js.

        Args:
            cif_content: CIF content as string
            formula: Chemical formula for the title
            structure_id: Structure identifier

        Returns:
            HTML content as string
        """
        # Escape the CIF content for JavaScript
        escaped_cif = cif_content.replace("\\", "\\\\").replace("`", "\\`").replace("${", "\\${")

        html_template = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8" />
    <title>Crystal Structure: {formula}</title>
    <script src="https://3Dmol.org/build/3Dmol-min.js"></script>
    <style>
        body {{
            font-family: Arial, sans-serif;
            margin: 20px;
            background-color: #f5f5f5;
        }}

        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: #fff;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 20px;
        }}

        .structure-container {{
            margin: 20px 0;
            border: 1px solid #ddd;
            padding: 20px;
            background-color: #fff;
            border-radius: 10px;
            box-shadow: 0 2px 5px rgba(0, 0, 0, 0.1);
        }}

        .structure-grid {{
            display: grid;
            grid-template-columns: minmax(400px, 1fr) 1fr;
            gap: 20px;
            margin-top: 15px;
            align-items: start;
        }}

        .viewer-container {{
            position: relative;
            width: 100%;
            height: 400px;
            border: 1px solid #ccc;
            border-radius: 5px;
            overflow: hidden;
        }}

        .viewer-container canvas {{
            position: absolute !important;
            inset: 0;
            width: 100% !important;
            height: 100% !important;
        }}

        .formula {{
            font-family: "Courier New", monospace;
            background-color: #e9ecef;
            padding: 2px 5px;
            border-radius: 3px;
        }}

        .info-section {{
            background-color: #f8f9fa;
            border: 1px solid #ddd;
            border-radius: 5px;
            padding: 15px;
        }}

        .info-section h3 {{
            margin-top: 0;
            color: #333;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🔬 Crystal Structure: {formula}</h1>
        <p>Generated by Crystalyse</p>
        <p>Structure ID: <span class="formula">{structure_id}</span></p>
    </div>

    <div class="structure-container">
        <div class="structure-grid">
            <div class="viewer-container">
                <div id="viewer_0"></div>
            </div>

            <div class="info-section">
                <h3>Structure Information</h3>
                <p><strong>Formula:</strong> <span class="formula">{formula}</span></p>
                <p><strong>Structure ID:</strong> {structure_id}</p>
                <p><strong>Generated by:</strong> Crystalyse with Chemeleon CSP</p>

                <h4>Controls:</h4>
                <ul>
                    <li>Mouse drag: Rotate structure</li>
                    <li>Mouse wheel: Zoom in/out</li>
                    <li>Right-click drag: Pan</li>
                </ul>

                <h4>Visualization:</h4>
                <ul>
                    <li>Atoms shown as spheres</li>
                    <li>Bonds shown as sticks</li>
                    <li>Unit cell outline visible</li>
                </ul>
            </div>
        </div>
    </div>

    <script>
        document.addEventListener("DOMContentLoaded", function() {{
            const viewer_0 = $3Dmol.createViewer("viewer_0");
            viewer_0.addModel(`{escaped_cif}`, "cif");
            viewer_0.setStyle({{stick: {{radius: 0.1}}, sphere: {{scale: 0.3}}}});
            viewer_0.addUnitCell();
            viewer_0.zoomTo();
            viewer_0.render();
        }});
    </script>
</body>
</html>"""
        return html_template

    def _save_html_visualizations(
        self, result: dict[str, Any], output_dir: Path, extracted_cifs: dict[str, dict[str, str]]
    ) -> int:
        """
        Create HTML visualizations for CIF files.

        Args:
            result: Full result dictionary from agent
            output_dir: Directory to save HTML files to

        Returns:
            Number of HTML files created
        """
        html_count = 0

        # Create HTML subdirectory
        html_dir = output_dir / "visualizations"

        # Look for most stable CIFs in tool calls
        tool_calls = result.get("tool_calls", [])

        for call in tool_calls:
            if isinstance(call, dict) and "output" in call:
                output = call.get("output", {})
                if isinstance(output, dict):
                    # Process most stable CIFs
                    most_stable_cifs = output.get("most_stable_cifs", {})
                    for comp, cif_data in most_stable_cifs.items():
                        if isinstance(cif_data, dict) and "cif" in cif_data:
                            if html_count == 0:  # Create dir on first HTML
                                html_dir.mkdir(exist_ok=True)

                            cif_content = cif_data["cif"]
                            structure_id = cif_data.get("structure_id", f"{comp}_stable")

                            html_content = self._create_html_visualization(
                                cif_content, comp, structure_id
                            )

                            html_filename = f"{comp}_most_stable_visualization.html"
                            html_path = html_dir / html_filename

                            with open(html_path, "w", encoding="utf-8") as f:
                                f.write(html_content)
                            html_count += 1

        return html_count

    def _save_html_visualizations_universal(
        self, output_dir: Path, extracted_cifs: dict[str, dict[str, str]]
    ) -> int:
        """
        Create HTML visualizations for CIF files using the universal visualizer.

        Args:
            output_dir: Directory to save HTML files to
            extracted_cifs: Dictionary of extracted CIF data from _save_cif_files

        Returns:
            Number of HTML files created
        """
        html_count = 0

        # Create HTML subdirectory if we have CIFs to process
        if extracted_cifs:
            html_dir = output_dir / "visualizations"
            html_dir.mkdir(exist_ok=True)

            # Process extracted CIF data
            for comp, cif_info in extracted_cifs.items():
                cif_content = cif_info["cif"]
                source = cif_info.get("source", "unknown")

                # Parse CIF data using universal visualizer
                cif_data = self.cif_visualizer.parse_cif_data(cif_content)

                # Create HTML content using universal visualizer
                html_content = self.cif_visualizer.create_individual_html(
                    cif_content, cif_data, f"{comp} ({source})"
                )

                html_filename = f"{comp}_visualization.html"
                html_path = html_dir / html_filename

                with open(html_path, "w", encoding="utf-8") as f:
                    f.write(html_content)
                html_count += 1

                logger.info(f"Created enhanced HTML visualization: {html_filename}")

        return html_count


def create_dual_output(
    query: str,
    result: dict[str, Any],
    execution_time: float,
    model: str = "unknown",
    mode: str = "unknown",
    output_dir: str = "query_results",
) -> Path:
    """
    Convenience function to create dual JSON/Markdown output.

    Args:
        query: The original user query
        result: Full result dictionary from agent.discover_materials()
        execution_time: Time taken for query execution
        model: Model used (e.g., "o4-mini", "o3")
        mode: Mode used (e.g., "creative", "rigorous")
        output_dir: Base directory for output

    Returns:
        Path to the created directory
    """
    formatter = DualOutputFormatter(output_dir)
    return formatter.create_query_output(query, result, execution_time, model, mode)
