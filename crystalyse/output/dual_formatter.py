"""
Dual output formatter for CrystaLyse.AI query results.

This module provides functionality to generate both JSON and Markdown output files
for individual query results, similar to the comprehensive test results format.

The output format includes:
- Structured JSON file (raw_result.json) with full computational data
- Human-readable Markdown report (report.md) with formatted analysis
- Automatic directory creation with timestamped naming
"""

import json
import re
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
from .universal_cif_visualizer import UniversalCIFVisualizer

logger = logging.getLogger(__name__)


class DualOutputFormatter:
    """
    Generates dual JSON/Markdown output for CrystaLyse.AI query results.
    
    Creates a directory structure similar to comprehensive test results:
    - query_results_YYYY_MM_DD_HHMMSS/
      - raw_result.json
      - report.md
    """
    
    def __init__(self, base_output_dir: str = "query_results"):
        """
        Initialise the dual output formatter.
        
        Args:
            base_output_dir: Base directory for all query results
        """
        self.base_output_dir = Path(base_output_dir)
        self.cif_visualizer = UniversalCIFVisualizer()
        
    def create_query_output(self, 
                           query: str, 
                           result: Dict[str, Any], 
                           execution_time: float,
                           model: str = "unknown",
                           mode: str = "unknown") -> Path:
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
            tool_validation=tool_validation
        )
        
        # Write files
        report_path = output_dir / "report.md"
        json_path = output_dir / "raw_result.json"
        
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report_content)
            
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        
        # Extract and save CIF files if available
        cif_count, extracted_cifs = self._save_cif_files(result, output_dir)
        
        # Create HTML visualizations for CIF files using universal visualizer
        html_count = self._save_html_visualizations_universal(output_dir, extracted_cifs)
        
        # Log extraction results for debugging
        if cif_count == 0:
            logger.warning(f"No CIF files extracted from result. Mode: {mode}, Tool calls: {tool_validation['tool_calls_count']}")
            # Check if computational tools were used but CIFs not extracted
            computational_tools = ['batch_discovery_pipeline', 'generate_crystal_csp', 'smact_validity']
            tools_used = tool_validation.get('tools_used', [])
            if any(tool in str(tools_used) for tool in computational_tools):
                logger.warning("Computational tools were used but no CIFs extracted - check extraction logic")
        
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
            
            updated_report = re.sub(
                r"\d+ CIF files found",
                status_line,
                report_content
            )
            with open(report_path, "w", encoding="utf-8") as f:
                f.write(updated_report)
            
        return output_dir
    
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
        slug = re.sub(r'[^\w\s-]', '', query.lower())
        slug = re.sub(r'[-\s]+', '_', slug)
        
        # Truncate if too long
        if len(slug) > max_length:
            slug = slug[:max_length].rstrip('_')
            
        return slug or "query"
    
    def _generate_tool_validation(self, result: Dict[str, Any]) -> Dict[str, Any]:
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
            "hallucination_risk": "low" if not tool_validation.get("potential_hallucination", False) else "high",
            "needs_computation": tool_validation.get("needs_computation", False),
            "potential_hallucination": tool_validation.get("potential_hallucination", False),
            "critical_failure": tool_validation.get("critical_failure", False),
            "smact_used": tool_validation.get("smact_used", False),
            "chemeleon_used": tool_validation.get("chemeleon_used", False),
            "mace_used": tool_validation.get("mace_used", False),
            "contains_computational_results": tool_validation.get("contains_computational_results", False)
        }
        
        return validation_data
    
    def _create_markdown_report(self,
                               query: str,
                               result: Dict[str, Any],
                               execution_time: float,
                               model: str,
                               mode: str,
                               tool_validation: Dict[str, Any]) -> str:
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
- **Status**: {result.get('status', 'unknown')}
- **Execution Time**: {execution_time:.2f} seconds
- **Model Used**: {model}
- **Mode**: {mode}
- **Total Items**: {result.get('metrics', {}).get('total_items', 0)}

### Tool Usage Validation
- **Tool Calls Made**: {tool_validation['tool_calls_count']}
- **Tools Actually Used**: {', '.join(tool_validation.get('tools_used', [])) if tool_validation.get('tools_used') else 'unknown'}
- **Validation Passed**: {'✅' if tool_validation['validation_passed'] else '❌'}
- **Hallucination Risk**: {tool_validation['hallucination_risk']}
- **Needs Computation**: {'Yes' if tool_validation.get('needs_computation', False) else 'No'}
- **Potential Hallucination**: {'Yes' if tool_validation.get('potential_hallucination', False) else 'No'}
- **Critical Failure**: {'Yes' if tool_validation.get('critical_failure', False) else 'No'}

"""

        # Add success indicator if tools are working properly
        if (tool_validation['validation_passed'] and 
            tool_validation['tool_calls_count'] > 0 and 
            not tool_validation.get('potential_hallucination', False)):
            
            tools_used_str = ', '.join(tool_validation.get('tools_used', [])) if tool_validation.get('tools_used') else 'MCP tools'
            report += f"""
### ✅ Tool Usage Success
- **All tools working correctly**
- **No hallucination detected**
- **{tool_validation['tool_calls_count']} computational tools called successfully**
- **Agent properly using: {tools_used_str}**

"""

        # Add validation issues if any
        if not tool_validation['validation_passed'] or tool_validation.get('potential_hallucination', False):
            report += f"""
### ⚠️ Validation Issues
Tool usage validation detected potential issues

**Detailed Analysis:**
- Query requires computation: {tool_validation.get('needs_computation', 'Unknown')}
- Tools actually called: {tool_validation['tool_calls_count']}
- Hallucination detected: {tool_validation.get('potential_hallucination', False)}
- Critical failure: {tool_validation.get('critical_failure', False)}

"""

        # Add main response
        report += f"""
### Agent Response
{response_text}

### Discovered Compositions
{', '.join(compositions) if compositions else 'None extracted'}

### CIF Files Generated
{len(cif_files)} CIF files found

"""

        # Add error details if failed
        if result.get('status') == 'failed':
            report += f"""
### Error Details
{result.get('error', 'Unknown error')}

"""

        # Add performance metrics
        if 'metrics' in result:
            metrics = result['metrics']
            infrastructure_stats = metrics.get('infrastructure_stats', {})
            
            report += f"""
### Performance Metrics
- **Tool Calls**: {metrics.get('tool_calls', 0)}
- **Raw Responses**: {metrics.get('raw_responses', 0)}
- **Infrastructure Stats**: {json.dumps(infrastructure_stats, indent=2) if infrastructure_stats else 'Not available'}

"""

        return report
    
    def _extract_compositions(self, text: str) -> List[str]:
        """
        Extract chemical compositions from text.
        
        Args:
            text: Text to search for compositions
            
        Returns:
            List of found chemical compositions
        """
        # Pattern for chemical formulas (e.g., Li2CO3, NaFePO4, etc.)
        composition_pattern = r'\b[A-Z][a-z]?(?:\d+)?(?:[A-Z][a-z]?(?:\d+)?)*\b'
        
        # Find all matches
        matches = re.findall(composition_pattern, text)
        
        # Filter out common words that might match the pattern
        common_words = {'Na', 'Al', 'Si', 'Ca', 'Mg', 'Fe', 'Li', 'Co', 'Ni', 'Mn', 'Ti', 'O', 'H', 'N', 'C', 'S', 'P', 'Cl', 'Br', 'F', 'I'}
        filtered_matches = []
        
        for match in matches:
            # Keep if it's longer than 2 characters or if it contains numbers
            if len(match) > 2 or any(char.isdigit() for char in match):
                # Additional check: make sure it's not just a common element symbol
                if not (len(match) <= 2 and match in common_words):
                    filtered_matches.append(match)
        
        # Remove duplicates and sort
        unique_compositions = sorted(list(set(filtered_matches)))
        
        return unique_compositions
    
    def _extract_cif_files(self, text: str) -> List[str]:
        """
        Extract CIF file references from text.
        
        Args:
            text: Text to search for CIF files
            
        Returns:
            List of found CIF file references
        """
        # Pattern for CIF file mentions
        cif_pattern = r'\b\w+\.cif\b'
        
        # Find all CIF file mentions
        cif_files = re.findall(cif_pattern, text, re.IGNORECASE)
        
        # Remove duplicates
        unique_cif_files = list(set(cif_files))
        
        return unique_cif_files
    
    def _save_cif_files(self, result: Dict[str, Any], output_dir: Path) -> tuple[int, Dict[str, Dict[str, str]]]:
        """
        Extract and save CIF files from the result.
        
        Args:
            result: Full result dictionary from agent
            output_dir: Directory to save CIF files to
            
        Returns:
            Number of CIF files saved and extracted CIF data
        """
        cif_count = 0
        extracted_cifs = {}  # Store extracted CIF data for HTML generation
        
        # Create CIF subdirectory
        cif_dir = output_dir / "cif_files"
        
        # Search for CIF content in various locations
        response_text = str(result.get("discovery_result", ""))
        
        # Look for structure data in tool calls
        tool_calls = result.get("tool_calls", [])
        
        # Also check new_items for ToolCallOutputItem data
        new_items = result.get("new_items", [])
        for i, item in enumerate(new_items):
            # Handle both old string representations and new structured format
            if isinstance(item, dict) and item.get("type") == "tool_call_output":
                # New structured format from _serialize_item
                output = item.get("output", {})
                
                # Check if output has a "text" field containing JSON string
                if isinstance(output, dict) and "text" in output:
                    try:
                        # Parse the JSON string in the text field
                        text_content = output["text"]
                        parsed_data = json.loads(text_content)
                        
                        # Debug: log what keys are available
                        logger.info(f"tool_call_output[{i}] keys: {list(parsed_data.keys()) if isinstance(parsed_data, dict) else 'not a dict'}")
                        
                        # Look for generated_structures in the parsed data (pipeline tools)
                        if "generated_structures" in parsed_data:
                            structures_data = parsed_data["generated_structures"]
                            logger.info(f"Found generated_structures in tool_call_output[{i}]")
                        
                        # Also check for direct structure arrays from individual tools
                        elif isinstance(parsed_data, list) and len(parsed_data) > 0:
                            # Check if this is an array of structures from individual tool (like generate_structures)
                            first_item = parsed_data[0]
                            if isinstance(first_item, dict) and ("cif" in first_item or "numbers" in first_item):
                                structures_data = parsed_data
                                logger.info(f"Found individual tool structure array in tool_call_output[{i}] with {len(parsed_data)} structures")
                            else:
                                structures_data = None
                        else:
                            structures_data = None
                        
                        if structures_data:
                            
                            # Handle both flat structures array and nested composition->structures format
                            structures_to_process = []
                            
                            if isinstance(structures_data, list):
                                # Check if this is a direct array of structures (individual tools)
                                first_item = structures_data[0] if structures_data else {}
                                if isinstance(first_item, dict) and ("cif" in first_item or "numbers" in first_item):
                                    # Direct structure array from individual tools like generate_structures
                                    structures_to_process = structures_data
                                    logger.info(f"Processing {len(structures_data)} structures from individual tool")
                                else:
                                    # Pipeline mode format: array of compositions, each with structures
                                    for comp_data in structures_data:
                                        if isinstance(comp_data, dict) and "structures" in comp_data:
                                            structures_to_process.extend(comp_data["structures"])
                                        elif isinstance(comp_data, dict) and "cif" in comp_data:
                                            # Direct structure object (rigorous mode)
                                            structures_to_process.append(comp_data)
                            elif isinstance(structures_data, dict):
                                # Single composition data
                                if "structures" in structures_data:
                                    structures_to_process.extend(structures_data["structures"])
                            
                            logger.info(f"Found {len(structures_to_process)} total structures to process")
                            
                            if cif_count == 0 and structures_to_process:
                                cif_dir.mkdir(exist_ok=True)
                            
                            for j, struct in enumerate(structures_to_process):
                                if isinstance(struct, dict) and "cif" in struct:
                                    formula = struct.get("formula", struct.get("composition", f"structure_{j}"))
                                    sample_idx = struct.get("sample_index", struct.get("sample_idx", j))
                                    struct_id = struct.get("id", f"{formula}_struct_{sample_idx}")
                                    cif_filename = f"{struct_id}.cif"
                                    cif_path = cif_dir / cif_filename
                                    
                                    cif_content = struct["cif"]
                                    # Clean up heavy JSON escaping in CIF content (especially from creative mode)
                                    clean_cif = cif_content.replace('\\\\n', '\n').replace('\\\\"', '"').replace('\\\\\\\\', '\\')
                                    
                                    with open(cif_path, "w", encoding="utf-8") as f:
                                        f.write(clean_cif)
                                    cif_count += 1
                                    
                                    # Store for HTML generation
                                    extracted_cifs[formula] = {
                                        "cif": clean_cif,
                                        "filename": cif_filename,
                                        "structure_id": struct_id
                                    }
                                    logger.info(f"Extracted CIF for {formula} from tool_call_output")
                                    
                    except json.JSONDecodeError as e:
                        logger.warning(f"Failed to parse JSON in tool_call_output[{i}]: {e}")
                        
                elif isinstance(output, dict):
                    # Check for structures in the output (legacy format)
                    if "structures" in output:
                        structures = output["structures"]
                        logger.info(f"Found {len(structures)} structures in new_items[{i}]")
                        
                        if cif_count == 0 and structures:
                            cif_dir.mkdir(exist_ok=True)
                        
                        for j, struct in enumerate(structures):
                            if isinstance(struct, dict) and "cif" in struct:
                                formula = struct.get("formula", struct.get("composition", f"structure_{j}"))
                                struct_id = struct.get("id", f"{formula}_struct_{j+1}")
                                cif_filename = f"{struct_id}.cif"
                                cif_path = cif_dir / cif_filename
                                
                                cif_content = struct["cif"]
                                # CIF content should already be clean in the new format
                                
                                with open(cif_path, "w", encoding="utf-8") as f:
                                    f.write(cif_content)
                                cif_count += 1
                                
                                # Store for HTML generation
                                extracted_cifs[formula] = {
                                    "cif": cif_content,
                                    "filename": cif_filename,
                                    "structure_id": struct_id
                                }
                                logger.info(f"Extracted CIF for {formula} from structured output")
                    
                    # Check for most_stable_cifs in output
                    if "most_stable_cifs" in output:
                        most_stable_cifs = output["most_stable_cifs"]
                        logger.info(f"Found most_stable_cifs in new_items[{i}]")
                        
                        if cif_count == 0:
                            cif_dir.mkdir(exist_ok=True)
                        
                        for comp, cif_data in most_stable_cifs.items():
                            if isinstance(cif_data, dict) and "cif" in cif_data:
                                cif_content = cif_data["cif"]
                                structure_id = cif_data.get("structure_id", f"{comp}_stable")
                                cif_filename = f"{comp}_most_stable.cif"
                                cif_path = cif_dir / cif_filename
                                
                                with open(cif_path, "w", encoding="utf-8") as f:
                                    f.write(cif_content)
                                cif_count += 1
                                
                                # Store for HTML generation
                                extracted_cifs[comp] = {
                                    "cif": cif_content,
                                    "filename": cif_filename,
                                    "structure_id": structure_id
                                }
                                logger.info(f"Extracted CIF for {comp} from most_stable_cifs")
            
            else:
                # Handle legacy string representations
                item_str = str(item) if not isinstance(item, str) else item
                
                # Log for debugging
                if ("batch_discovery_pipeline" in item_str or 
                    "creative_discovery_pipeline" in item_str or 
                    "most_stable_cifs" in item_str or
                    "generated_structures" in item_str):
                    logger.info(f"Found potential CIF data in new_items[{i}]")
                
                # Handle creative mode string format with generated_structures
                if (isinstance(item, str) and "ToolCallOutputItem" in item and 
                    "generated_structures" in item):
                    logger.info(f"Processing creative mode generated_structures in new_items[{i}]")
                    try:
                        # Simpler approach: extract the JSON content using regex
                        import re
                        # Look for the pattern: {"type":"text","text":"..."}
                        text_pattern = r'{"type":"text","text":"(.*?)","annotations"'
                        match = re.search(text_pattern, item, re.DOTALL)
                        
                        if match:
                            json_text = match.group(1)
                            # Use codecs to properly decode the escaped string
                            try:
                                json_text = json_text.encode().decode('unicode_escape')
                            except UnicodeDecodeError:
                                # Fallback to manual replacements
                                json_text = json_text.replace('\\n', '\n')
                                json_text = json_text.replace('\\"', '"')
                                json_text = json_text.replace('\\\\', '\\')
                            
                            # Parse the JSON
                            try:
                                # Clean up whitespace and potential invisible characters
                                json_text = json_text.strip()
                                # Debug: log first 200 chars of cleaned JSON
                                logger.info(f"JSON text first 200 chars: {repr(json_text[:200])}")
                                parsed_data = json.loads(json_text)
                                logger.info(f"Parsed JSON keys: {list(parsed_data.keys()) if isinstance(parsed_data, dict) else 'not a dict'}")
                                
                                if "generated_structures" in parsed_data:
                                    structures_data = parsed_data["generated_structures"]
                                    logger.info(f"Found {len(structures_data)} compositions in creative mode")
                                    logger.info(f"First composition structure: {type(structures_data[0]) if structures_data else 'empty list'}")
                                    
                                    if cif_count == 0:
                                        cif_dir.mkdir(exist_ok=True)
                                    
                                    # Process creative mode format
                                    for comp_data in structures_data:
                                        if isinstance(comp_data, dict) and "structures" in comp_data:
                                            composition = comp_data.get("composition", "unknown")
                                            for j, struct in enumerate(comp_data["structures"]):
                                                if isinstance(struct, dict) and "cif" in struct:
                                                    formula = struct.get("formula", composition)
                                                    sample_idx = struct.get("sample_index", j)
                                                    struct_id = f"{formula}_struct_{sample_idx}"
                                                    cif_filename = f"{struct_id}.cif"
                                                    cif_path = cif_dir / cif_filename
                                                    
                                                    cif_content = struct["cif"]
                                                    # Clean up CIF content escaping
                                                    clean_cif = cif_content.replace('\\\\n', '\n').replace('\\\\"', '"')
                                                    
                                                    with open(cif_path, "w", encoding="utf-8") as f:
                                                        f.write(clean_cif)
                                                    cif_count += 1
                                                    
                                                    # Store for HTML generation
                                                    extracted_cifs[formula] = {
                                                        "cif": clean_cif,
                                                        "filename": cif_filename,
                                                        "structure_id": struct_id
                                                    }
                                                    logger.info(f"Extracted CIF for {formula} from creative mode string")
                                            
                            except json.JSONDecodeError as e:
                                logger.warning(f"Failed to parse creative mode JSON: {e}")
                                    
                    except Exception as e:
                        logger.warning(f"Failed to process creative mode string: {e}")
                
                # Check for generate_structures output (individual tool calls)
                if (isinstance(item, str) and "ToolCallOutputItem" in item and 
                    "generate_structures" in item):
                    logger.info(f"Found generate_structures output in new_items[{i}]")
                    try:
                        # Extract structures array from generate_structures output
                        structures_start = item.find('"structures": [')
                        if structures_start != -1:
                            # Find the matching closing bracket
                            bracket_count = 1
                            pos = structures_start + len('"structures": [')
                            start_pos = pos - 1
                            
                            while bracket_count > 0 and pos < len(item):
                                if item[pos] == '[':
                                    bracket_count += 1
                                elif item[pos] == ']':
                                    bracket_count -= 1
                                pos += 1
                            
                            if bracket_count == 0:
                                structures_content = item[start_pos:pos]
                                try:
                                    # Clean up the content and parse
                                    clean_content = structures_content.replace('\\\\"', '"')
                                    clean_content = clean_content.replace('\\\\n', '\n')
                                    clean_content = clean_content.replace('\\\\\\\\', '\\\\')
                                    
                                    # Parse as JSON
                                    structures = json.loads(clean_content)
                                    
                                    if cif_count == 0 and structures:
                                        cif_dir.mkdir(exist_ok=True)
                                    
                                    for j, struct in enumerate(structures):
                                        if isinstance(struct, dict) and "cif" in struct:
                                            formula = struct.get("formula", struct.get("composition", f"structure_{j}"))
                                            struct_id = struct.get("id", f"{formula}_struct_{j+1}")
                                            cif_filename = f"{struct_id}.cif"
                                            cif_path = cif_dir / cif_filename
                                            
                                            cif_content = struct["cif"]
                                            # Clean up CIF content
                                            clean_cif = cif_content.replace('\\\\n', '\n')
                                            clean_cif = clean_cif.replace('\\\\"', '"')
                                            clean_cif = clean_cif.replace('\\\\', '\\')
                                            
                                            with open(cif_path, "w", encoding="utf-8") as f:
                                                f.write(clean_cif)
                                            cif_count += 1
                                            
                                            # Store for HTML generation
                                            extracted_cifs[formula] = {
                                                "cif": clean_cif,
                                                "filename": cif_filename,
                                                "structure_id": struct_id
                                            }
                                            logger.info(f"Extracted CIF for {formula} from generate_structures output")
                                            
                                except json.JSONDecodeError as e:
                                    logger.warning(f"Failed to parse structures JSON: {e}")
                                except Exception as e:
                                    logger.warning(f"Failed to extract structures: {e}")
                                    
                    except Exception as e:
                        logger.warning(f"Failed to process generate_structures output: {e}")
            
            if (isinstance(item, str) and "ToolCallOutputItem" in item and 
                ("most_stable_cifs" in item or "creative_discovery_pipeline" in item or "batch_discovery_pipeline" in item)):
                # Extract CIF data from string representation
                try:
                    import re
                    import ast
                    
                    # Find most_stable_cifs section first
                    msc_start = item.find('most_stable_cifs')
                    if msc_start == -1:
                        continue
                    
                    # Find the opening brace of most_stable_cifs
                    opening_brace = item.find('{', msc_start)
                    if opening_brace == -1:
                        continue
                    
                    # Find the matching closing brace
                    brace_count = 1
                    pos = opening_brace + 1
                    while brace_count > 0 and pos < len(item):
                        if item[pos] == '{':
                            brace_count += 1
                        elif item[pos] == '}':
                            brace_count -= 1
                        pos += 1
                    
                    if brace_count == 0:
                        # Extract the most_stable_cifs content
                        msc_content = item[opening_brace:pos]
                        
                        # Use a more flexible approach to extract composition-CIF pairs
                        # First, find all composition keys within most_stable_cifs
                        comp_pattern = r'\\\\"([A-Za-z0-9]+)\\\\": \{'
                        composition_matches = re.findall(comp_pattern, msc_content)
                        
                        matches = []
                        for comp in composition_matches:
                            # For each composition, find its CIF content
                            comp_start = msc_content.find(f'\\\\"{comp}\\\\"')
                            if comp_start != -1:
                                # Find the CIF field
                                cif_start = msc_content.find('\\\\"cif\\\\": \\\\"', comp_start)
                                if cif_start != -1:
                                    content_start = cif_start + len('\\\\"cif\\\\": \\\\"')
                                    # Find the end of the CIF content
                                    # Look for the next field or end of object
                                    end_markers = ['\\\\",\\\\n', '\\\\"\\\\n', '\\\\"}']
                                    end_pos = -1
                                    for marker in end_markers:
                                        pos = msc_content.find(marker, content_start)
                                        if pos != -1:
                                            if end_pos == -1 or pos < end_pos:
                                                end_pos = pos
                                    
                                    if end_pos != -1:
                                        cif_content = msc_content[content_start:end_pos]
                                        matches.append((comp, cif_content))
                        
                        if matches:
                            if cif_count == 0:  # Create dir on first CIF
                                cif_dir.mkdir(exist_ok=True)
                            
                            for comp, cif_content in matches:
                                # Save CIF file
                                cif_filename = f"{comp}_most_stable.cif"
                                cif_path = cif_dir / cif_filename
                                
                                try:
                                    # Clean up the CIF content escaping
                                    clean_cif = cif_content
                                    # Handle various levels of escaping
                                    clean_cif = clean_cif.replace('\\\\\\\\n', '\n')
                                    clean_cif = clean_cif.replace('\\\\n', '\n')
                                    clean_cif = clean_cif.replace('\\\\\\\\\\\\\\"', '"')
                                    clean_cif = clean_cif.replace('\\\\\\"', '"')
                                    clean_cif = clean_cif.replace('\\"', '"')
                                    clean_cif = clean_cif.replace('\\\\', '\\')
                                    
                                    with open(cif_path, "w", encoding="utf-8") as f:
                                        f.write(clean_cif)
                                    cif_count += 1
                                    
                                    # Store for HTML generation
                                    extracted_cifs[comp] = {
                                        "cif": clean_cif,
                                        "filename": cif_filename
                                    }
                                except Exception as write_error:
                                    logger.warning(f"Failed to write CIF for {comp}: {write_error}")
                        
                except Exception as e:
                    logger.warning(f"Failed to extract CIF data from string representation: {e}")
                    continue
        
        # Extract CIF content from tool call outputs
        for call in tool_calls:
            if isinstance(call, dict) and "output" in call:
                output = call.get("output", {})
                if isinstance(output, dict):
                    # Check for most stable CIFs first (highest priority)
                    most_stable_cifs = output.get("most_stable_cifs", {})
                    if most_stable_cifs:
                        cif_dir.mkdir(exist_ok=True)
                        for comp, cif_data in most_stable_cifs.items():
                            if isinstance(cif_data, dict) and "cif" in cif_data:
                                cif_content = cif_data["cif"]
                                structure_id = cif_data.get("structure_id", f"{comp}_stable")
                                cif_filename = f"{comp}_most_stable.cif"
                                cif_path = cif_dir / cif_filename
                                with open(cif_path, "w", encoding="utf-8") as f:
                                    f.write(cif_content)
                                cif_count += 1
                                # Store for HTML generation
                                extracted_cifs[comp] = {
                                    "cif": cif_content,
                                    "structure_id": structure_id,
                                    "source": "tool_output"
                                }
                    
                    # Check for structures in the output
                    structures = output.get("structures", [])
                    if structures:
                        if cif_count == 0:  # Create dir if not already created
                            cif_dir.mkdir(exist_ok=True)
                        for i, struct in enumerate(structures):
                            if isinstance(struct, dict) and "cif" in struct:
                                cif_content = struct["cif"]
                                formula = struct.get("formula", f"unknown_{i}")
                                cif_filename = f"{formula}_struct_{i+1}.cif"
                                cif_path = cif_dir / cif_filename
                                with open(cif_path, "w", encoding="utf-8") as f:
                                    f.write(cif_content)
                                cif_count += 1
                    
                    # Also check for candidates with structure data
                    candidates = output.get("candidates", [])
                    for i, cand in enumerate(candidates):
                        if isinstance(cand, dict) and "cif" in cand:
                            if cif_count == 0:  # Only create dir if we have CIFs
                                cif_dir.mkdir(exist_ok=True)
                            cif_content = cand["cif"]
                            formula = cand.get("formula", f"candidate_{i}")
                            cif_filename = f"{formula}_candidate_{i+1}.cif"
                            cif_path = cif_dir / cif_filename
                            with open(cif_path, "w", encoding="utf-8") as f:
                                f.write(cif_content)
                            cif_count += 1
        
        # Also check raw_response if available
        raw_response = result.get("raw_response", {})
        if isinstance(raw_response, dict):
            new_items = raw_response.get("new_items", [])
            for item in new_items:
                if isinstance(item, dict) and item.get("type") == "tool_output":
                    output = item.get("output", {})
                    if isinstance(output, str):
                        try:
                            output = json.loads(output)
                        except:
                            continue
                    
                    if isinstance(output, dict) and "structures" in output:
                        structures = output["structures"]
                        if structures and cif_count == 0:
                            cif_dir.mkdir(exist_ok=True)
                        for i, struct in enumerate(structures):
                            if isinstance(struct, dict) and "cif" in struct:
                                cif_content = struct["cif"]
                                formula = struct.get("formula", f"structure_{i}")
                                cif_filename = f"{formula}_raw_{i+1}.cif"
                                cif_path = cif_dir / cif_filename
                                with open(cif_path, "w", encoding="utf-8") as f:
                                    f.write(cif_content)
                                cif_count += 1
        
        return cif_count, extracted_cifs
    
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
        escaped_cif = cif_content.replace('\\', '\\\\').replace('`', '\\`').replace('${', '\\${')
        
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
        <p>Generated by CrystaLyse.AI</p>
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
                <p><strong>Generated by:</strong> CrystaLyse.AI with Chemeleon CSP</p>
                
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
    
    def _save_html_visualizations(self, result: Dict[str, Any], output_dir: Path, extracted_cifs: Dict[str, Dict[str, str]]) -> int:
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
    
    def _save_html_visualizations_universal(self, output_dir: Path, extracted_cifs: Dict[str, Dict[str, str]]) -> int:
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
                structure_id = cif_info.get("structure_id", f"{comp}_structure")
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


def create_dual_output(query: str, 
                      result: Dict[str, Any], 
                      execution_time: float,
                      model: str = "unknown",
                      mode: str = "unknown",
                      output_dir: str = "query_results") -> Path:
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