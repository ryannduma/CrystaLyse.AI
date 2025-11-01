"""
Tests for the simplified CrystaLyse visualization tools.
"""
import json
from pathlib import Path
import pytest
import tempfile
import sys

# HACK: Force the src directory onto the path to solve persistent import errors.
# This is a workaround for a stubborn packaging issue.
# In a real project, we would fix the packaging itself.
# Get the absolute path to the project root to build the correct path.
project_root = Path(__file__).parent.parent.parent
vis_server_src_path = project_root / "visualization-mcp-server" / "src"
if str(vis_server_src_path) not in sys.path:
    sys.path.insert(0, str(vis_server_src_path))

from visualization_mcp.tools import save_cif_file

# Sample CIF content for testing
SAMPLE_CIF = """
data_LiF
_symmetry_space_group_name_H-M   'Fm-3m'
_cell_length_a   4.026
_cell_length_b   4.026
_cell_length_c   4.026
_cell_angle_alpha   90
_cell_angle_beta    90
_cell_angle_gamma   90
loop_
  _atom_site_label
  _atom_site_type_symbol
  _atom_site_fract_x
  _atom_site_fract_y
  _atom_site_fract_z
  Li1  Li  0.0  0.0  0.0
  F1   F   0.5  0.5  0.5
"""

@pytest.fixture
def temp_dir():
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir

def test_save_cif_file(temp_dir):
    """
    Tests the core functionality of saving a CIF file.
    """
    result_str = save_cif_file(SAMPLE_CIF, "LiF", temp_dir)
    result = json.loads(result_str)

    assert result["status"] == "success"
    assert "output_path" in result
    
    output_path = Path(result["output_path"])
    assert output_path.exists()
    assert output_path.name == "LiF.cif"
    
    # Verify the content of the saved file
    saved_content = output_path.read_text()
    assert saved_content.strip() == SAMPLE_CIF.strip()

def test_save_cif_file_error(temp_dir):
    """
    Tests that the tool handles errors gracefully (e.g., invalid path).
    """
    # Pass an invalid output directory (a file path) to trigger an error
    invalid_dir = Path(temp_dir) / "file.txt"
    invalid_dir.touch()
    
    result_str = save_cif_file(SAMPLE_CIF, "LiF", str(invalid_dir))
    result = json.loads(result_str)

    assert result["status"] == "error"
    assert "error" in result
    assert "File exists" in result["error"]
