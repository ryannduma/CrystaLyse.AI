
import json
import os
from pathlib import Path
import pytest
import tempfile

from visualization_mcp.tools import create_creative_visualization, create_rigorous_visualization, create_3dmol_visualization

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
_symmetry_equiv_pos_as_xyz
  'x,y,z'
  '-x,-y,z'
  '-x,y,-z'
  'x,-y,-z'
  'z,x,y'
  '-z,-x,y'
  '-z,x,-y'
  'z,-x,-y'
  'y,z,x'
  '-y,-z,x'
  '-y,z,-x'
  'y,-z,-x'
  'y,x,-z'
  '-y,-x,-z'
  '-y,x,z'
  'y,-x,z'
  'x,z,-y'
  '-x,-z,-y'
  '-x,z,y'
  'x,-z,y'
  '-x,-y,-z'
  'x,y,-z'
  'x,-y,z'
  '-x,y,z'
  '-z,-x,-y'
  'z,x,-y'
  'z,-x,y'
  '-z,x,y'
  '-y,-z,-x'
  'y,z,-x'
  'y,-z,x'
  '-y,z,x'
  '-y,-x,z'
  'y,x,z'
  'y,-x,-z'
  '-y,x,-z'
  '-x,-z,y'
  'x,z,y'
  'x,-z,-y'
  '-x,z,-y'
loop_
  _atom_site_label
  _atom_site_type_symbol
  _atom_site_fract_x
  _atom_site_fract_y
  _atom_site_fract_z
  Li1  Li  0.0  0.0  0.0
  F1   F   0.5  0.5  0.5
"""

SAMPLE_NACL_CIF = """
data_test
_cell_length_a 5.0
_cell_length_b 5.0
_cell_length_c 5.0
_cell_angle_alpha 90.0
_cell_angle_beta 90.0
_cell_angle_gamma 90.0
loop_
_atom_site_label
_atom_site_fract_x
_atom_site_fract_y
_atom_site_fract_z
Na1 0.0 0.0 0.0
Cl1 0.5 0.5 0.5
"""


@pytest.fixture
def temp_dir():
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir

def test_creative_visualization(temp_dir):
    result_str = create_creative_visualization(SAMPLE_CIF, "LiF", temp_dir, "Test Structure")
    result = json.loads(result_str)
    
    assert result["status"] == "success"
    output_path = Path(result["output_path"])
    assert output_path.exists()
    assert output_path.name == "LiF_3dmol.html"
    assert output_path.read_text().startswith("<!DOCTYPE html>")

def test_rigorous_visualization(temp_dir):
    result_str = create_rigorous_visualization(SAMPLE_CIF, "LiF", temp_dir, "Test Analysis")
    result = json.loads(result_str)

    assert result["status"] == "success"
    
    # Check structure visualization
    structure_viz = result["structure_visualization"]
    assert structure_viz["status"] == "success"
    html_path = Path(structure_viz["output_path"])
    assert html_path.exists()
    assert html_path.name == "LiF_3dmol.html"

    # Check analysis suite
    analysis_suite = result["analysis_suite"]
    assert analysis_suite["status"] == "success"
    analysis_dir = Path(analysis_suite["analysis_dir"])
    assert analysis_dir.exists()
    assert analysis_dir.name == "LiF_analysis"
    
    # Check for at least one analysis file
    assert len(analysis_suite["analysis_files"]) > 0
    cif_saved = False
    for file_path_str in analysis_suite["analysis_files"]:
        file_path = Path(file_path_str)
        assert file_path.exists()
        if file_path.suffix == ".pdf":
            assert file_path.stat().st_size > 0
        if file_path.suffix == ".cif":
            cif_saved = True
    assert cif_saved, "CIF file was not saved in the analysis suite"


def test_vesta_colors(temp_dir):
    """Test VESTA color configuration."""
    result_str = create_3dmol_visualization(
        SAMPLE_NACL_CIF, "NaCl", temp_dir, color_scheme="vesta"
    )
    result = json.loads(result_str)
    
    assert result["status"] == "success"
    html_path = Path(result["output_path"])
    assert html_path.exists()

    with open(html_path, 'r') as f:
        html_content = f.read()
    
    # Check for VESTA-specific colors (example: Na should be #F9DC3C, Cl should be #31FC02)
    # Note: pymatviz ELEM_COLORS_VESTA has Na as (0.976, 0.863, 0.235) -> #f9dc3c
    # and Cl as (0.192, 0.988, 0.008) -> #31fc02
    assert 'viewer.setColorByElement("Na", "#f9dc3c");' in html_content
    assert 'viewer.setColorByElement("Cl", "#31fc02");' in html_content
