"""
Crystal structure visualisation module using multiple backends.

This module provides comprehensive crystal structure visualisation capabilities
using py3Dmol for interactive 3D web displays and Plotly as a fallback option.
The visualisations are designed to be embedded in HTML reports for materials
discovery workflows.
"""

import json
import tempfile
import os
from typing import Dict, List, Optional, Union, Any
from pathlib import Path
import numpy as np

try:
    import py3Dmol
    HAS_PY3DMOL = True
except ImportError:
    HAS_PY3DMOL = False

try:
    import plotly.graph_objects as go
    HAS_PLOTLY = True
except ImportError:
    HAS_PLOTLY = False

try:
    import ase
    from pymatgen.core import Structure, Lattice, Element
    from pymatgen.io.ase import AseAtomsAdaptor
    HAS_STRUCTURE_LIBS = True
except ImportError:
    HAS_STRUCTURE_LIBS = False


class CrystalVisualiser:
    """Interactive crystal structure visualisation with multiple backends."""
    
    def __init__(self, backend: str = "py3dmol"):
        """Initialise visualiser with preferred backend.
        
        Args:
            backend: 'py3dmol', 'plotly', or 'auto'
        """
        self.backend = backend
        if backend == "auto":
            self.backend = "py3dmol" if HAS_PY3DMOL else "plotly"
        
        if not HAS_STRUCTURE_LIBS:
            raise ImportError("pymatgen and ASE are required for crystal visualisation")
        
        self.adaptor = AseAtomsAdaptor()
        
        # Atomic colour scheme (CPK colours)
        self.element_colours = {
            'H': '#FFFFFF', 'He': '#D9FFFF', 'Li': '#CC80FF', 'Be': '#C2FF00',
            'B': '#FFB5B5', 'C': '#909090', 'N': '#3050F8', 'O': '#FF0D0D',
            'F': '#90E050', 'Ne': '#B3E3F5', 'Na': '#AB5CF2', 'Mg': '#8AFF00',
            'Al': '#BFA6A6', 'Si': '#F0C8A0', 'P': '#FF8000', 'S': '#FFFF30',
            'Cl': '#1FF01F', 'Ar': '#80D1E3', 'K': '#8F40D4', 'Ca': '#3DFF00',
            'Ti': '#BFC2C7', 'Fe': '#E06633', 'Ni': '#50D050', 'Cu': '#C88033',
            'Zn': '#7D80B0', 'As': '#BD80E3', 'Br': '#A62929', 'Kr': '#5CB8D1',
            'Sr': '#00FF00', 'Zr': '#94E0E0', 'Mo': '#54B5B5', 'Ag': '#C0C0C0',
            'I': '#940094', 'Ba': '#00C900', 'La': '#70D4FF', 'Ce': '#FFFFC7',
            'Pb': '#575961', 'Bi': '#9E4FB5', 'U': '#008FFF'
        }
        
        # Atomic radii for visualisation (in Angstroms)
        self.element_radii = {
            'H': 0.31, 'He': 0.28, 'Li': 1.28, 'Be': 0.96, 'B': 0.84,
            'C': 0.76, 'N': 0.71, 'O': 0.66, 'F': 0.57, 'Ne': 0.58,
            'Na': 1.66, 'Mg': 1.41, 'Al': 1.21, 'Si': 1.11, 'P': 1.07,
            'S': 1.05, 'Cl': 1.02, 'Ar': 1.06, 'K': 2.03, 'Ca': 1.76,
            'Ti': 1.70, 'Fe': 1.52, 'Ni': 1.24, 'Cu': 1.32, 'Zn': 1.22,
            'As': 1.19, 'Br': 1.20, 'Kr': 1.16, 'Sr': 1.95, 'Zr': 1.75,
            'Mo': 1.54, 'Ag': 1.72, 'I': 1.39, 'Ba': 2.17, 'La': 2.07,
            'Ce': 2.04, 'Pb': 1.75, 'Bi': 1.48, 'U': 1.96
        }
    
    def visualise_structure(self, structure_input: Union[Dict, str, Path], 
                          view_config: Dict = None) -> Union[Any, go.Figure]:
        """Create interactive visualisation of crystal structure.
        
        Args:
            structure_input: Structure dict, CIF string, or CIF file path
            view_config: Configuration for visualisation
        """
        if self.backend == "py3dmol" and HAS_PY3DMOL:
            return self._create_py3dmol_view(structure_input, view_config)
        elif self.backend == "plotly" and HAS_PLOTLY:
            return self._create_plotly_view(structure_input, view_config)
        else:
            raise ValueError(f"Backend {self.backend} not available")
    
    def _create_py3dmol_view(self, structure_input: Union[Dict, str, Path], 
                           view_config: Dict = None):
        """Create py3Dmol visualisation (recommended for HTML export)."""
        if not HAS_PY3DMOL:
            raise ImportError("py3Dmol is required for this backend")
        
        config = view_config or {
            'width': 800, 
            'height': 600,
            'style': 'ball_and_stick',
            'show_unit_cell': True
        }
        
        # Create viewer
        view = py3Dmol.view(width=config['width'], height=config['height'])
        
        # Add structure
        if isinstance(structure_input, (str, Path)):
            # CIF file or string
            if Path(structure_input).exists():
                cif_content = Path(structure_input).read_text()
            else:
                cif_content = structure_input
            view.addModel(cif_content, 'cif')
        else:
            # Structure dict - convert to CIF first
            cif_content = self._dict_to_cif(structure_input)
            view.addModel(cif_content, 'cif')
        
        # Apply styling
        if config['style'] == 'stick':
            view.setStyle({'stick': {'radius': 0.1}})
        elif config['style'] == 'sphere':
            view.setStyle({'sphere': {}})
        elif config['style'] == 'ball_and_stick':
            view.setStyle({'stick': {'radius': 0.1}, 'sphere': {'scale': 0.3}})
        
        # Add unit cell if requested
        if config.get('show_unit_cell', True):
            view.addUnitCell()
        
        # Set camera
        view.zoomTo()
        view.rotate(90, 'y')
        
        return view
    
    def _create_plotly_view(self, structure_input: Union[Dict, str, Path], 
                          view_config: Dict = None) -> go.Figure:
        """Create Plotly-based visualisation (fallback option)."""
        if not HAS_PLOTLY:
            raise ImportError("Plotly is required for this backend")
        
        # Convert input to structure dict
        if isinstance(structure_input, dict):
            structure_dict = structure_input
        else:
            # Load from CIF and convert
            if isinstance(structure_input, (str, Path)) and Path(structure_input).exists():
                structure = Structure.from_file(structure_input)
            else:
                # Assume it's a CIF string
                with tempfile.NamedTemporaryFile(mode='w', suffix='.cif', delete=False) as f:
                    f.write(str(structure_input))
                    temp_path = f.name
                structure = Structure.from_file(temp_path)
                os.unlink(temp_path)
            structure_dict = self._structure_to_dict(structure)
        
        # Convert to ASE Atoms
        atoms = ase.Atoms(
            numbers=structure_dict["numbers"],
            positions=structure_dict["positions"],
            cell=structure_dict["cell"],
            pbc=structure_dict.get("pbc", [True, True, True])
        )
        
        # Create Plotly figure
        fig = go.Figure()
        
        positions = atoms.get_positions()
        symbols = atoms.get_chemical_symbols()
        
        # Group by element for colouring
        elements = list(set(symbols))
        
        for element in elements:
            mask = [s == element for s in symbols]
            element_positions = positions[mask]
            
            colour = self.element_colours.get(element, '#808080')
            size = self.element_radii.get(element, 1.0) * 20  # Scale for visibility
            
            fig.add_trace(go.Scatter3d(
                x=element_positions[:, 0],
                y=element_positions[:, 1], 
                z=element_positions[:, 2],
                mode='markers',
                name=element,
                marker=dict(
                    size=size,
                    colour=colour,
                    line=dict(width=1, colour='black')
                )
            ))
        
        # Add unit cell edges
        cell_edges = self._get_cell_edges(atoms.cell)
        for edge in cell_edges:
            fig.add_trace(go.Scatter3d(
                x=edge[:, 0],
                y=edge[:, 1],
                z=edge[:, 2],
                mode='lines',
                line=dict(colour='grey', width=2),
                showlegend=False
            ))
        
        fig.update_layout(
            title=f"Crystal Structure: {atoms.get_chemical_formula()}",
            scene=dict(
                xaxis_title="X (Å)",
                yaxis_title="Y (Å)", 
                zaxis_title="Z (Å)",
                aspectmode='data'
            ),
            width=800,
            height=600
        )
        
        return fig
    
    def _get_cell_edges(self, cell):
        """Generate unit cell edge lines for visualisation."""
        # Unit cell vertices
        vertices = np.array([
            [0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 1, 0],  # Bottom face
            [0, 0, 1], [1, 0, 1], [1, 1, 1], [0, 1, 1]   # Top face
        ])
        
        # Transform to real space
        real_vertices = vertices @ cell
        
        # Define edges (pairs of vertex indices)
        edges = [
            (0, 1), (1, 2), (2, 3), (3, 0),  # Bottom face
            (4, 5), (5, 6), (6, 7), (7, 4),  # Top face
            (0, 4), (1, 5), (2, 6), (3, 7)   # Vertical edges
        ]
        
        edge_lines = []
        for start, end in edges:
            edge_lines.append(np.array([real_vertices[start], real_vertices[end]]))
        
        return edge_lines
    
    def _dict_to_cif(self, structure_dict: Dict) -> str:
        """Convert structure dictionary to CIF string."""
        # Convert dict to pymatgen Structure then to CIF
        lattice = Lattice(structure_dict["cell"])
        species = [Element.from_Z(z) for z in structure_dict["numbers"]]
        coords = structure_dict["positions"]
        
        structure = Structure(lattice, species, coords, coords_are_cartesian=True)
        return structure.to(fmt="cif")
    
    def _structure_to_dict(self, structure: Structure) -> Dict:
        """Convert pymatgen Structure to dictionary."""
        return {
            "cell": structure.lattice.matrix.tolist(),
            "positions": structure.cart_coords.tolist(),
            "numbers": [site.specie.Z for site in structure],
            "symbols": [str(site.specie) for site in structure],
            "formula": structure.formula,
            "volume": float(structure.volume),
            "pbc": [True, True, True]
        }
    
    def create_multi_structure_report(self, structures: List[Dict], 
                                    composition: str) -> str:
        """Create comprehensive HTML report with multiple structures."""
        if not HAS_PY3DMOL:
            return self._create_plotly_report(structures, composition)
        
        html_parts = []
        
        # Header with 3Dmol.js
        html_parts.append(f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Crystal Structures for {composition}</title>
            <script src="https://3Dmol.org/build/3Dmol-min.js"></script>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }}
                .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 10px; margin-bottom: 20px; }}
                .structure-container {{ margin: 20px 0; border: 1px solid #ddd; padding: 20px; background-color: white; border-radius: 10px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }}
                .structure-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-top: 15px; }}
                .analysis-table {{ width: 100%; border-collapse: collapse; margin-top: 10px; }}
                .analysis-table th, .analysis-table td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                .analysis-table th {{ background-color: #f8f9fa; font-weight: bold; }}
                .viewer-container {{ border: 1px solid #ccc; border-radius: 5px; }}
                .success {{ color: #28a745; font-weight: bold; }}
                .error {{ color: #dc3545; font-weight: bold; }}
                .formula {{ font-family: 'Courier New', monospace; background-color: #e9ecef; padding: 2px 5px; border-radius: 3px; }}
            </style>
        </head>
        <body>
        <div class="header">
            <h1>Crystal Structure Analysis: {composition}</h1>
            <p>Generated by CrystaLyse.AI with Chemeleon CSP</p>
        </div>
        """)
        
        # Add each structure
        for i, struct in enumerate(structures):
            viewer_id = f"viewer_{i}"
            
            # Clean CIF content for JavaScript
            cif_content = struct.get('cif', '').replace('`', '\\`').replace('$', '\\$')
            
            html_parts.append(f"""
            <div class="structure-container">
                <h2>Structure {i+1}</h2>
                <div class="structure-grid">
                    <div>
                        <h3>3D Visualisation</h3>
                        <div class="viewer-container">
                            <div id="{viewer_id}" style="width: 100%; height: 400px;"></div>
                        </div>
                        <script>
                            let viewer_{i} = $3Dmol.createViewer('{viewer_id}');
                            viewer_{i}.addModel(`{cif_content}`, 'cif');
                            viewer_{i}.setStyle({{'stick': {{radius: 0.1}}, 'sphere': {{scale: 0.3}}}});
                            viewer_{i}.addUnitCell();
                            viewer_{i}.zoomTo();
                            viewer_{i}.render();
                        </script>
                    </div>
                    <div>
                        <h3>Structural Analysis</h3>
                        {self._create_analysis_table(struct.get('analysis', {}))}
                    </div>
                </div>
            </div>
            """)
        
        html_parts.append("</body></html>")
        return "\n".join(html_parts)
    
    def _create_plotly_report(self, structures: List[Dict], composition: str) -> str:
        """Create HTML report using Plotly backend."""
        if not HAS_PLOTLY:
            return "<html><body><h1>No visualisation libraries available</h1></body></html>"
        
        import plotly.io as pio
        
        html_parts = []
        html_parts.append(f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Crystal Structures for {composition}</title>
            <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
        </head>
        <body>
        <h1>Crystal Structure Analysis: {composition}</h1>
        """)
        
        for i, struct in enumerate(structures):
            if 'structure' in struct:
                fig = self._create_plotly_view(struct['structure'])
                html_parts.append(f"<h2>Structure {i+1}</h2>")
                html_parts.append(pio.to_html(fig, include_plotlyjs=False, div_id=f"plot_{i}"))
                html_parts.append(self._create_analysis_table(struct.get('analysis', {})))
        
        html_parts.append("</body></html>")
        return "\n".join(html_parts)
    
    def _create_analysis_table(self, analysis: Dict) -> str:
        """Create HTML table for structure analysis."""
        if not analysis:
            return "<p class='error'>No analysis data available</p>"
        
        rows = []
        if 'formula' in analysis:
            rows.append(f"<tr><td>Formula</td><td><span class='formula'>{analysis['formula']}</span></td></tr>")
        if 'volume' in analysis:
            rows.append(f"<tr><td>Volume</td><td>{analysis['volume']:.2f} ų</td></tr>")
        if 'density' in analysis:
            rows.append(f"<tr><td>Density</td><td>{analysis['density']:.2f} g/cm³</td></tr>")
        
        if 'lattice' in analysis:
            lattice = analysis['lattice']
            rows.append(f"<tr><td>a</td><td>{lattice.get('a', 'N/A'):.3f} Å</td></tr>")
            rows.append(f"<tr><td>b</td><td>{lattice.get('b', 'N/A'):.3f} Å</td></tr>")
            rows.append(f"<tr><td>c</td><td>{lattice.get('c', 'N/A'):.3f} Å</td></tr>")
            rows.append(f"<tr><td>α</td><td>{lattice.get('alpha', 'N/A'):.2f}°</td></tr>")
            rows.append(f"<tr><td>β</td><td>{lattice.get('beta', 'N/A'):.2f}°</td></tr>")
            rows.append(f"<tr><td>γ</td><td>{lattice.get('gamma', 'N/A'):.2f}°</td></tr>")
        
        if 'symmetry' in analysis:
            symmetry = analysis['symmetry']
            rows.append(f"<tr><td>Space Group</td><td><strong>{symmetry.get('space_group', 'N/A')}</strong></td></tr>")
            rows.append(f"<tr><td>Crystal System</td><td>{symmetry.get('crystal_system', 'N/A')}</td></tr>")
            if 'point_group' in symmetry:
                rows.append(f"<tr><td>Point Group</td><td>{symmetry['point_group']}</td></tr>")
        
        if not rows:
            return "<p class='error'>No structural data available</p>"
        
        return f'<table class="analysis-table"><tbody>{"".join(rows)}</tbody></table>'
    
    def save_interactive_view(self, structure_input: Union[Dict, str, Path], 
                             output_path: Path, title: str = "Crystal Structure"):
        """Save standalone interactive visualisation."""
        view = self.visualise_structure(structure_input)
        
        if hasattr(view, '_make_html'):  # py3Dmol
            html_content = view._make_html()
            output_path.write_text(html_content)
        elif hasattr(view, 'write_html'):  # Plotly
            view.write_html(str(output_path))
        else:
            raise ValueError("Unable to save visualisation")
        
        return output_path


def generate_crystal_viewer(structure_cif: str, composition: str = "Unknown") -> str:
    """
    Generate a standalone HTML viewer for a crystal structure.
    
    This function creates a simple HTML page with 3DMol.js visualisation
    that can be opened directly in a browser.
    
    Args:
        structure_cif: CIF format string of the crystal structure
        composition: Chemical composition/formula for the title
        
    Returns:
        HTML content as string
    """
    # Clean the CIF content for JavaScript embedding
    clean_cif = structure_cif.replace('`', '\\`').replace('$', '\\$').replace('\\', '\\\\')
    
    html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>CrystaLyse.AI - {composition}</title>
    <script src="https://3Dmol.org/build/3Dmol-min.js"></script>
    <style>
        body {{
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 15px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            overflow: hidden;
        }}
        .header {{
            background: linear-gradient(135deg, #2c3e50 0%, #34495e 100%);
            color: white;
            padding: 20px;
            text-align: center;
        }}
        .header h1 {{
            margin: 0;
            font-size: 2em;
        }}
        .header p {{
            margin: 10px 0 0 0;
            opacity: 0.8;
        }}
        .viewer-section {{
            padding: 20px;
        }}
        .viewer-container {{
            border: 2px solid #e0e0e0;
            border-radius: 10px;
            margin: 20px 0;
            background: #f8f9fa;
        }}
        .controls {{
            background: #f1f3f4;
            padding: 15px;
            border-radius: 5px;
            margin-bottom: 15px;
            text-align: center;
        }}
        .control-button {{
            background: #4285f4;
            color: white;
            border: none;
            padding: 8px 16px;
            margin: 0 5px;
            border-radius: 5px;
            cursor: pointer;
            font-size: 14px;
        }}
        .control-button:hover {{
            background: #3367d6;
        }}
        .info-panel {{
            background: #e8f5e8;
            border-left: 4px solid #4caf50;
            padding: 15px;
            margin: 15px 0;
        }}
        .formula {{
            font-family: 'Courier New', monospace;
            background: #e9ecef;
            padding: 3px 6px;
            border-radius: 3px;
            font-weight: bold;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Crystal Structure Viewer</h1>
            <p>Formula: <span class="formula">{composition}</span></p>
            <p>Generated by CrystaLyse.AI</p>
        </div>
        
        <div class="viewer-section">
            <div class="info-panel">
                <strong>Viewer Controls:</strong>
                <ul style="margin: 10px 0;">
                    <li><strong>Rotate:</strong> Click and drag</li>
                    <li><strong>Zoom:</strong> Mouse wheel or pinch</li>
                    <li><strong>Pan:</strong> Right-click and drag</li>
                    <li><strong>Reset View:</strong> Use the reset button below</li>
                </ul>
            </div>
            
            <div class="controls">
                <button class="control-button" onclick="resetView()">Reset View</button>
                <button class="control-button" onclick="toggleStyle()">Toggle Style</button>
                <button class="control-button" onclick="toggleUnitCell()">Toggle Unit Cell</button>
                <button class="control-button" onclick="toggleFullscreen()">Fullscreen</button>
            </div>
            
            <div class="viewer-container">
                <div id="viewer" style="width: 100%; height: 500px;"></div>
            </div>
        </div>
    </div>

    <script>
        let viewer = $3Dmol.createViewer("viewer", {{
            backgroundColor: 'white'
        }});
        
        let currentStyle = 'ball_and_stick';
        let showUnitCell = true;
        
        // Add the structure
        viewer.addModel(`{clean_cif}`, 'cif');
        
        // Set initial style
        setMoleculeStyle();
        
        // Add unit cell
        viewer.addUnitCell();
        
        // Set initial view
        viewer.zoomTo();
        viewer.render();
        
        function setMoleculeStyle() {{
            if (currentStyle === 'ball_and_stick') {{
                viewer.setStyle({{}}, {{
                    'stick': {{radius: 0.15, color: 'grey'}}, 
                    'sphere': {{scale: 0.4}}
                }});
            }} else if (currentStyle === 'stick') {{
                viewer.setStyle({{}}, {{
                    'stick': {{radius: 0.2}}
                }});
            }} else if (currentStyle === 'sphere') {{
                viewer.setStyle({{}}, {{
                    'sphere': {{scale: 0.8}}
                }});
            }}
            viewer.render();
        }}
        
        function resetView() {{
            viewer.zoomTo();
            viewer.render();
        }}
        
        function toggleStyle() {{
            if (currentStyle === 'ball_and_stick') {{
                currentStyle = 'stick';
            }} else if (currentStyle === 'stick') {{
                currentStyle = 'sphere';
            }} else {{
                currentStyle = 'ball_and_stick';
            }}
            setMoleculeStyle();
        }}
        
        function toggleUnitCell() {{
            viewer.removeAllShapes();
            if (showUnitCell) {{
                showUnitCell = false;
            }} else {{
                viewer.addUnitCell();
                showUnitCell = true;
            }}
            viewer.render();
        }}
        
        function toggleFullscreen() {{
            const container = document.querySelector('.container');
            const viewer_div = document.getElementById('viewer');
            
            if (!document.fullscreenElement) {{
                container.requestFullscreen().then(() => {{
                    viewer_div.style.height = '80vh';
                    viewer.resize();
                }});
            }} else {{
                document.exitFullscreen().then(() => {{
                    viewer_div.style.height = '500px';
                    viewer.resize();
                }});
            }}
        }}
        
        // Handle fullscreen changes
        document.addEventListener('fullscreenchange', function() {{
            const viewer_div = document.getElementById('viewer');
            if (!document.fullscreenElement) {{
                viewer_div.style.height = '500px';
            }}
            viewer.resize();
        }});
        
        // Auto-resize on window resize
        window.addEventListener('resize', function() {{
            viewer.resize();
        }});
    </script>
</body>
</html>
    """
    
    return html_content