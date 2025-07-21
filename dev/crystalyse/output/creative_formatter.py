"""Creative mode specific output formatter for CrystaLyse.AI"""

import json
import re
import logging
from pathlib import Path
from typing import Dict, List, Any, Tuple

logger = logging.getLogger(__name__)

class CreativeFormatter:
    """Handles output formatting specifically for creative mode"""
    
    def __init__(self):
        self.logger = logger
    
    def extract_cif_files_creative(self, result: Dict[str, Any], output_dir: Path) -> Tuple[int, Dict[str, Dict[str, str]]]:
        """
        Extract CIF files from creative mode results.
        
        Args:
            result: Full result dictionary from agent
            output_dir: Directory to save CIF files to
            
        Returns:
            Tuple of (number of CIF files saved, extracted CIF data)
        """
        cif_count = 0
        extracted_cifs = {}
        
        # Create CIF subdirectory
        cif_dir = output_dir / "cif_files"
        
        # Look specifically for creative_discovery_pipeline output in new_items
        new_items = result.get("new_items", [])
        logger.info(f"Creative formatter: checking {len(new_items)} items")
        
        for i, item in enumerate(new_items):
            item_str = str(item) if not isinstance(item, str) else item
            
            # Debug: check what's in each item
            has_tool_output = "ToolCallOutputItem" in item_str
            has_creative = "creative_discovery_pipeline" in item_str
            has_cifs = "most_stable_cifs" in item_str
            
            logger.info(f"Item {i}: ToolCallOutputItem={has_tool_output}, creative_pipeline={has_creative}, most_stable_cifs={has_cifs}")
            
            # Look for creative_discovery_pipeline output with most_stable_cifs
            if (has_tool_output and has_creative and has_cifs):
                
                logger.info(f"Found creative pipeline output in new_items[{i}]")
                
                try:
                    # Extract most_stable_cifs section
                    msc_start = item_str.find('most_stable_cifs')
                    if msc_start == -1:
                        continue
                    
                    # Find the opening brace after most_stable_cifs
                    colon_pos = item_str.find(':', msc_start)
                    if colon_pos == -1:
                        continue
                    
                    opening_brace = item_str.find('{', colon_pos)
                    if opening_brace == -1:
                        continue
                    
                    # Find the matching closing brace by counting braces
                    brace_count = 1
                    pos = opening_brace + 1
                    while brace_count > 0 and pos < len(item_str):
                        if item_str[pos] == '{':
                            brace_count += 1
                        elif item_str[pos] == '}':
                            brace_count -= 1
                        pos += 1
                    
                    if brace_count == 0:
                        # Extract the most_stable_cifs content
                        msc_content = item_str[opening_brace:pos]
                        
                        # Extract compositions and their CIF data
                        cif_data = self._extract_cif_data_from_content(msc_content)
                        
                        if cif_data:
                            if cif_count == 0:
                                cif_dir.mkdir(exist_ok=True)
                            
                            for comp, cif_content in cif_data.items():
                                # Save CIF file
                                cif_filename = f"{comp}_most_stable.cif"
                                cif_path = cif_dir / cif_filename
                                
                                try:
                                    # Clean up the CIF content
                                    clean_cif = self._clean_cif_content(cif_content)
                                    
                                    with open(cif_path, "w", encoding="utf-8") as f:
                                        f.write(clean_cif)
                                    cif_count += 1
                                    
                                    # Store for HTML generation
                                    extracted_cifs[comp] = {
                                        "cif": clean_cif,
                                        "filename": cif_filename,
                                        "source": "creative_mode"
                                    }
                                    logger.info(f"Extracted CIF for {comp} from creative mode output")
                                    
                                except Exception as write_error:
                                    logger.error(f"Failed to write CIF for {comp}: {write_error}")
                
                except Exception as e:
                    logger.error(f"Failed to extract CIF data from creative mode output: {e}")
                    continue
        
        return cif_count, extracted_cifs
    
    def _extract_cif_data_from_content(self, content: str) -> Dict[str, str]:
        """
        Extract composition-CIF pairs from most_stable_cifs content.
        
        Args:
            content: The most_stable_cifs section content
            
        Returns:
            Dictionary mapping composition to CIF content
        """
        cif_data = {}
        
        # Find all composition entries - handle the specific escaping pattern
        # Pattern: \\"CompName\\": { (with various levels of escaping)
        patterns = [
            r'\\\\"([A-Za-z0-9]+)\\\\": \{',   # Standard pattern
            r'\\\\n\\s+\\\\"([A-Za-z0-9]+)\\\\": \{',  # With newline and spacing
            r'"([A-Za-z0-9]+)":\\s*\{',        # Less escaped version
        ]
        
        compositions = []
        for pattern in patterns:
            matches = re.findall(pattern, content)
            compositions.extend(matches)
        
        # Remove duplicates while preserving order
        compositions = list(dict.fromkeys(compositions))
        
        for comp in compositions:
            # Find the start of this composition's data with various patterns
            comp_patterns = [
                f'\\\\"{comp}\\\\"',
                f'"{comp}"',
                f'\\\\n\\s+\\\\"{comp}\\\\"'
            ]
            
            comp_start = -1
            for pattern in comp_patterns:
                pos = content.find(pattern)
                if pos != -1:
                    comp_start = pos
                    break
            
            if comp_start == -1:
                logger.debug(f"Could not find composition start for {comp}")
                continue
            
            # Find the CIF field within this composition with various patterns
            cif_patterns = [
                '\\\\"cif\\\\": \\\\"',
                '"cif": "',
                '\\\\n\\s+\\\\"cif\\\\": \\\\"'
            ]
            
            cif_start = -1
            cif_marker_used = None
            for pattern in cif_patterns:
                pos = content.find(pattern, comp_start)
                if pos != -1:
                    cif_start = pos
                    cif_marker_used = pattern
                    break
            
            if cif_start == -1:
                logger.debug(f"Could not find CIF field for {comp}")
                continue
            
            # Start of actual CIF content
            content_start = cif_start + len(cif_marker_used)
            
            # Find the end of the CIF content - look for the closing quote of the cif field
            # The pattern is: "cif": "content", so we need to find the quote before the comma
            end_pos = self._find_cif_end(content, content_start)
            
            if end_pos != -1:
                cif_content = content[content_start:end_pos]
                cif_data[comp] = cif_content
                logger.debug(f"Extracted {len(cif_content)} characters of CIF data for {comp}")
        
        return cif_data
    
    def _find_cif_end(self, content: str, start_pos: int) -> int:
        """
        Find the end position of CIF content in escaped JSON.
        
        Args:
            content: Full content string
            start_pos: Starting position to search from
            
        Returns:
            End position of CIF content, or -1 if not found
        """
        # Look for various possible end markers
        end_markers = [
            '\\\\",\\\\n',  # Most common: quote, comma, newline
            '\\\\"\\\\n',   # Quote, newline
            '\\\\"}',       # End of object
            '\\\\"\\\\,',   # Quote, comma (alternative format)
            '\\\\"\\\\}',   # Quote, end of object
        ]
        
        end_pos = -1
        for marker in end_markers:
            pos = content.find(marker, start_pos)
            if pos != -1:
                if end_pos == -1 or pos < end_pos:
                    end_pos = pos
        
        return end_pos
    
    def _clean_cif_content(self, cif_content: str) -> str:
        """
        Clean up escaped CIF content to produce valid CIF format.
        
        Args:
            cif_content: Raw escaped CIF content
            
        Returns:
            Cleaned CIF content
        """
        clean_cif = cif_content
        
        # Handle various levels of escaping common in JSON strings
        # Start with the most complex patterns first
        clean_cif = clean_cif.replace('\\\\\\\\n', '\n')  # Four backslashes + n -> newline
        clean_cif = clean_cif.replace('\\\\n', '\n')      # Two backslashes + n -> newline
        clean_cif = clean_cif.replace('\\n', '\n')        # Backslash + n -> newline
        
        # Handle escaped quotes
        clean_cif = clean_cif.replace('\\\\\\\\\\\\\\"', '"')  # Many escaped quotes
        clean_cif = clean_cif.replace('\\\\\\"', '"')          # Three backslashes + quote
        clean_cif = clean_cif.replace('\\"', '"')              # Backslash + quote
        
        # Handle escaped backslashes
        clean_cif = clean_cif.replace('\\\\\\\\', '\\')  # Four backslashes -> one
        clean_cif = clean_cif.replace('\\\\', '\\')      # Two backslashes -> one
        
        # Clean up any remaining artifacts
        clean_cif = clean_cif.strip()
        
        return clean_cif