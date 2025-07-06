#!/usr/bin/env python3
"""
Universal CIF Visualizer for CrystaLyse.AI

This module provides comprehensive CIF visualization capabilities inspired by the 
user's scaffold. It includes:
1. Universal HTML crystal viewer
2. Individual CIF to HTML conversion
3. Batch processing capabilities
4. Gallery generation for multiple structures

Usage:
    # Create universal viewer
    python -m crystalyse.output.universal_cif_visualizer create-viewer output.html
    
    # Convert single CIF to HTML
    python -m crystalyse.output.universal_cif_visualizer convert structure.cif
    
    # Create gallery from directory
    python -m crystalyse.output.universal_cif_visualizer gallery /path/to/cif/files
"""

import re
import sys
import math
import json
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional


class UniversalCIFVisualizer:
    """Universal CIF visualization system for CrystaLyse.AI."""
    
    def __init__(self):
        self.universal_viewer_template = self._get_universal_viewer_template()
    
    def create_universal_viewer(self, output_path: str) -> None:
        """Create a universal CIF viewer HTML file."""
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(self.universal_viewer_template)
        print(f"✅ Universal CIF viewer created: {output_path}")
    
    def convert_cif_to_html(self, cif_path: str, output_path: Optional[str] = None) -> str:
        """Convert a single CIF file to HTML visualization."""
        cif_file = Path(cif_path)
        if not cif_file.exists():
            raise FileNotFoundError(f"CIF file not found: {cif_path}")
        
        # Read CIF content
        with open(cif_file, 'r', encoding='utf-8') as f:
            cif_content = f.read()
        
        # Parse CIF data
        cif_data = self.parse_cif_data(cif_content)
        
        # Determine output filename
        if output_path is None:
            output_path = cif_file.parent / f"{cif_file.stem}_visualization.html"
        
        # Generate HTML
        html_content = self.create_individual_html(cif_content, cif_data, cif_file.name)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"✅ HTML visualization created: {output_path}")
        return str(output_path)
    
    def create_gallery(self, cif_directory: str, output_dir: Optional[str] = None) -> str:
        """Create a gallery of all CIF files in a directory."""
        cif_dir = Path(cif_directory)
        if not cif_dir.is_dir():
            raise NotADirectoryError(f"Directory not found: {cif_directory}")
        
        if output_dir is None:
            output_dir = cif_dir / 'crystal_gallery'
        else:
            output_dir = Path(output_dir)
        
        output_dir.mkdir(exist_ok=True)
        
        # Find all CIF files
        cif_files = list(cif_dir.glob('*.cif'))
        if not cif_files:
            print("No CIF files found in the directory.")
            return str(output_dir)
        
        print(f"Found {len(cif_files)} CIF files. Processing...")
        
        structures = []
        
        for i, cif_file in enumerate(cif_files, 1):
            print(f"[{i}/{len(cif_files)}] Processing: {cif_file.name}")
            
            try:
                with open(cif_file, 'r', encoding='utf-8') as f:
                    cif_content = f.read()
                
                cif_data = self.parse_cif_data(cif_content)
                
                # Create individual HTML file
                html_filename = f"{cif_file.stem}.html"
                html_path = output_dir / html_filename
                
                html_content = self.create_individual_html(cif_content, cif_data, cif_file.name, gallery_mode=True)
                
                with open(html_path, 'w', encoding='utf-8') as f:
                    f.write(html_content)
                
                structures.append({
                    'filename': html_filename,
                    'original_filename': cif_file.name,
                    'formula': cif_data['formula'],
                    'space_group': cif_data['space_group'],
                    'crystal_system': cif_data['crystal_system'],
                    'volume': cif_data['volume'] or 'N/A'
                })
                
            except Exception as e:
                print(f"   ⚠️  Error processing {cif_file.name}: {e}")
        
        # Generate index page
        print("\\nGenerating gallery index...")
        self.create_gallery_index(structures, output_dir)
        
        print(f"\\n✅ Gallery created successfully!")
        print(f"📁 Output directory: {output_dir}")
        print(f"🌐 Open {output_dir}/index.html to view the gallery")
        
        return str(output_dir)
    
    def parse_cif_data(self, cif_content: str) -> Dict[str, Any]:
        """Parse CIF content and extract key structural information."""
        data = {
            'formula': 'Unknown',
            'cell_a': None,
            'cell_b': None,
            'cell_c': None,
            'angle_alpha': None,
            'angle_beta': None,
            'angle_gamma': None,
            'space_group': 'Unknown',
            'crystal_system': 'Unknown',
            'volume': None,
            'density': None
        }
        
        # Parse cell parameters
        patterns = {
            'cell_a': r'_cell_length_a\s+([\d.]+)',
            'cell_b': r'_cell_length_b\s+([\d.]+)',
            'cell_c': r'_cell_length_c\s+([\d.]+)',
            'angle_alpha': r'_cell_angle_alpha\s+([\d.]+)',
            'angle_beta': r'_cell_angle_beta\s+([\d.]+)',
            'angle_gamma': r'_cell_angle_gamma\s+([\d.]+)'
        }
        
        for key, pattern in patterns.items():
            match = re.search(pattern, cif_content, re.IGNORECASE)
            if match:
                data[key] = float(match.group(1))
        
        # Parse space group
        space_group_match = re.search(
            r'_space_group_name_H-M_alt\s+["\']([^"\']+)["\']|_symmetry_space_group_name_H-M\s+["\']([^"\']+)["\']', 
            cif_content, 
            re.IGNORECASE
        )
        if space_group_match:
            data['space_group'] = space_group_match.group(1) or space_group_match.group(2)
        
        # Determine crystal system
        crystal_system_match = re.search(r'_space_group_crystal_system\s+(\w+)', cif_content, re.IGNORECASE)
        if crystal_system_match:
            data['crystal_system'] = crystal_system_match.group(1)
        else:
            # Try to infer from angles and cell parameters
            if all(data[k] is not None for k in ['angle_alpha', 'angle_beta', 'angle_gamma']):
                angles = [data['angle_alpha'], data['angle_beta'], data['angle_gamma']]
                if all(abs(a - 90) < 0.01 for a in angles):
                    if data['cell_a'] and data['cell_b'] and data['cell_c']:
                        if abs(data['cell_a'] - data['cell_b']) < 0.01 and abs(data['cell_b'] - data['cell_c']) < 0.01:
                            data['crystal_system'] = 'cubic'
                        elif abs(data['cell_a'] - data['cell_b']) < 0.01:
                            data['crystal_system'] = 'tetragonal'
                        else:
                            data['crystal_system'] = 'orthorhombic'
        
        # Extract chemical formula
        formula_match = re.search(r'_chemical_formula_sum\s+["\']([^"\']+)["\']', cif_content, re.IGNORECASE)
        if formula_match:
            data['formula'] = formula_match.group(1).strip()
        else:
            # Try to derive from atom sites
            atom_types = {}
            atom_lines = re.findall(r'^([A-Z][a-z]?)\d*\s+[\d.-]+\s+[\d.-]+\s+[\d.-]+', cif_content, re.MULTILINE)
            for atom in atom_lines:
                atom_types[atom] = atom_types.get(atom, 0) + 1
            if atom_types:
                formula_parts = []
                for atom, count in sorted(atom_types.items()):
                    if count > 1:
                        formula_parts.append(f"{atom}{count}")
                    else:
                        formula_parts.append(atom)
                data['formula'] = ''.join(formula_parts)
        
        # Calculate volume
        if all(data[k] is not None for k in ['cell_a', 'cell_b', 'cell_c', 'angle_alpha', 'angle_beta', 'angle_gamma']):
            a, b, c = data['cell_a'], data['cell_b'], data['cell_c']
            alpha = math.radians(data['angle_alpha'])
            beta = math.radians(data['angle_beta'])
            gamma = math.radians(data['angle_gamma'])
            
            volume = a * b * c * math.sqrt(
                1 - math.cos(alpha)**2 - math.cos(beta)**2 - math.cos(gamma)**2 
                + 2 * math.cos(alpha) * math.cos(beta) * math.cos(gamma)
            )
            data['volume'] = round(volume, 2)
        
        # Parse density if available
        density_match = re.search(r'_exptl_crystal_density_diffrn\s+([\d.]+)', cif_content, re.IGNORECASE)
        if density_match:
            data['density'] = float(density_match.group(1))
        
        return data
    
    def create_individual_html(self, cif_content: str, cif_data: Dict[str, Any], filename: str, gallery_mode: bool = False) -> str:
        """Create HTML visualization for individual crystal structure."""
        formula_html = re.sub(r'(\d+)', r'<sub>\1</sub>', cif_data['formula'])
        escaped_cif = cif_content.replace('\\\\', '\\\\\\\\').replace('`', '\\\\`').replace('${', '\\\\${')
        
        back_link = ''
        if gallery_mode:
            back_link = '<a href="index.html" class="back-link">← Back to Gallery</a>'
        
        html_template = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8" />
    <title>Crystal Structure: {cif_data['formula']}</title>
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
        .back-link {{
            color: #fff;
            text-decoration: none;
            margin-bottom: 10px;
            display: inline-block;
        }}
        .back-link:hover {{
            text-decoration: underline;
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
            grid-template-columns: minmax(320px, 1fr) 1fr;
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
        .viewer-container #viewer {{
            width: 100%;
            height: 100%;
        }}
        .viewer-container canvas {{
            position: absolute !important;
            inset: 0;
            width: 100% !important;
            height: 100% !important;
        }}
        .analysis-table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 10px;
        }}
        .analysis-table td {{
            border: 1px solid #ddd;
            padding: 8px;
            text-align: left;
        }}
        .analysis-table td:first-child {{
            background-color: #f8f9fa;
            font-weight: bold;
        }}
        @media (max-width: 768px) {{
            .structure-grid {{
                grid-template-columns: 1fr;
            }}
        }}
    </style>
</head>
<body>
    <div class="header">
        {back_link}
        <h1>Crystal Structure Analysis: {formula_html}</h1>
        <p>Crystal System: {cif_data['crystal_system']} | Space Group: {cif_data['space_group']}</p>
        <p>Source: {filename}</p>
    </div>

    <div class="structure-container">
        <h2>Crystal Structure Details</h2>
        <div class="structure-grid">
            <div>
                <h3>3D Visualisation</h3>
                <div class="viewer-container">
                    <div id="viewer"></div>
                </div>
            </div>
            <div>
                <h3>Structural Analysis</h3>
                <table class="analysis-table">
                    <tbody>
                        <tr><td>Formula</td><td>{formula_html}</td></tr>
                        <tr><td>Space Group</td><td><strong>{cif_data['space_group']}</strong></td></tr>
                        <tr><td>Crystal System</td><td>{cif_data['crystal_system']}</td></tr>'''
        
        # Add structural parameters if available
        if cif_data['volume']:
            html_template += f'''
                        <tr><td>Volume</td><td>{cif_data['volume']} Å<sup>3</sup></td></tr>'''
        
        if cif_data['density']:
            html_template += f'''
                        <tr><td>Density</td><td>{cif_data['density']:.2f} g/cm³</td></tr>'''
        
        if cif_data['cell_a']:
            html_template += f'''
                        <tr><td>a</td><td>{cif_data['cell_a']:.3f} Å</td></tr>'''
        
        if cif_data['cell_b']:
            html_template += f'''
                        <tr><td>b</td><td>{cif_data['cell_b']:.3f} Å</td></tr>'''
        
        if cif_data['cell_c']:
            html_template += f'''
                        <tr><td>c</td><td>{cif_data['cell_c']:.3f} Å</td></tr>'''
        
        if cif_data['angle_alpha']:
            html_template += f'''
                        <tr><td>α</td><td>{cif_data['angle_alpha']:.2f}°</td></tr>'''
        
        if cif_data['angle_beta']:
            html_template += f'''
                        <tr><td>β</td><td>{cif_data['angle_beta']:.2f}°</td></tr>'''
        
        if cif_data['angle_gamma']:
            html_template += f'''
                        <tr><td>γ</td><td>{cif_data['angle_gamma']:.2f}°</td></tr>'''
        
        html_template += f'''
                    </tbody>
                </table>
                
                <h4>Controls:</h4>
                <ul>
                    <li>Mouse drag: Rotate structure</li>
                    <li>Mouse wheel: Zoom in/out</li>
                    <li>Right-click drag: Pan</li>
                </ul>
            </div>
        </div>
    </div>

    <script>
        window.addEventListener('DOMContentLoaded', () => {{
            const viewer = $3Dmol.createViewer("viewer");
            viewer.addModel(`{escaped_cif}`, "cif");
            viewer.setStyle({{ stick: {{ radius: 0.15 }}, sphere: {{ scale: 0.3 }} }});
            viewer.addUnitCell();
            viewer.zoomTo();
            viewer.render();
        }});
    </script>
</body>
</html>'''
        
        return html_template
    
    def create_gallery_index(self, structures: List[Dict], output_dir: Path) -> None:
        """Generate index page with all crystal structures."""
        cards_html = ""
        
        for structure in structures:
            formula_html = re.sub(r'(\d+)', r'<sub>\1</sub>', structure['formula'])
            
            cards_html += f'''
        <div class="crystal-card">
            <a href="{structure['filename']}" class="card-link">
                <div class="card-header">
                    <h3>{formula_html}</h3>
                    <span class="crystal-system">{structure['crystal_system']}</span>
                </div>
                <div class="card-body">
                    <p><strong>Space Group:</strong> {structure['space_group']}</p>
                    <p><strong>Volume:</strong> {structure['volume']} Å³</p>
                    <p class="filename">{structure['original_filename']}</p>
                </div>
            </a>
        </div>'''
        
        index_html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8" />
    <title>Crystal Structure Gallery - CrystaLyse.AI</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            margin: 0;
            background-color: #f5f5f5;
            padding: 20px;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: #fff;
            padding: 30px;
            border-radius: 10px;
            text-align: center;
            margin-bottom: 30px;
        }}
        .header h1 {{
            margin: 0;
            font-size: 2.5em;
        }}
        .stats {{
            margin-top: 15px;
            font-size: 1.2em;
        }}
        .gallery {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
            gap: 20px;
            margin-top: 20px;
        }}
        .crystal-card {{
            background: #fff;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
            overflow: hidden;
            transition: transform 0.3s, box-shadow 0.3s;
        }}
        .crystal-card:hover {{
            transform: translateY(-5px);
            box-shadow: 0 5px 20px rgba(0, 0, 0, 0.15);
        }}
        .card-link {{
            text-decoration: none;
            color: inherit;
            display: block;
        }}
        .card-header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 15px;
            position: relative;
        }}
        .card-header h3 {{
            margin: 0;
            font-size: 1.5em;
        }}
        .crystal-system {{
            position: absolute;
            top: 15px;
            right: 15px;
            background: rgba(255, 255, 255, 0.2);
            padding: 5px 10px;
            border-radius: 20px;
            font-size: 0.8em;
            text-transform: capitalize;
        }}
        .card-body {{
            padding: 15px;
        }}
        .card-body p {{
            margin: 5px 0;
        }}
        .filename {{
            color: #666;
            font-size: 0.9em;
            margin-top: 10px !important;
            font-style: italic;
        }}
        .filter-bar {{
            background: #fff;
            padding: 15px;
            border-radius: 10px;
            margin-bottom: 20px;
            box-shadow: 0 2px 5px rgba(0, 0, 0, 0.1);
        }}
        .filter-bar input {{
            width: 100%;
            padding: 10px;
            border: 1px solid #ddd;
            border-radius: 5px;
            font-size: 16px;
        }}
        .no-results {{
            text-align: center;
            color: #666;
            font-size: 1.2em;
            margin-top: 50px;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Crystal Structure Gallery</h1>
        <div class="stats">
            {len(structures)} structures • Generated by CrystaLyse.AI • {datetime.now().strftime('%Y-%m-%d %H:%M')}
        </div>
    </div>
    
    <div class="filter-bar">
        <input type="text" id="searchInput" placeholder="Search by formula, space group, or filename..." />
    </div>
    
    <div class="gallery" id="gallery">
        {cards_html}
    </div>
    
    <div class="no-results" id="noResults" style="display: none;">
        No structures found matching your search.
    </div>

    <script>
        const searchInput = document.getElementById('searchInput');
        const gallery = document.getElementById('gallery');
        const noResults = document.getElementById('noResults');
        const cards = document.querySelectorAll('.crystal-card');
        
        searchInput.addEventListener('input', (e) => {{
            const searchTerm = e.target.value.toLowerCase();
            let visibleCount = 0;
            
            cards.forEach(card => {{
                const text = card.textContent.toLowerCase();
                if (text.includes(searchTerm)) {{
                    card.style.display = 'block';
                    visibleCount++;
                }} else {{
                    card.style.display = 'none';
                }}
            }});
            
            noResults.style.display = visibleCount === 0 ? 'block' : 'none';
        }});
    </script>
</body>
</html>'''
        
        with open(output_dir / 'index.html', 'w', encoding='utf-8') as f:
            f.write(index_html)
    
    def _get_universal_viewer_template(self) -> str:
        """Get the universal CIF viewer HTML template."""
        return '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8" />
    <title>Universal Crystal Structure Viewer - CrystaLyse.AI</title>
    <script src="https://3Dmol.org/build/3Dmol-min.js"></script>
    <style>
        /* General styles */
        body {
            font-family: Arial, sans-serif;
            margin: 20px;
            background-color: #f5f5f5;
        }

        /* Header */
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: #fff;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 20px;
        }

        /* File Upload */
        .upload-container {
            margin: 20px 0;
            padding: 20px;
            background-color: #fff;
            border-radius: 10px;
            box-shadow: 0 2px 5px rgba(0, 0, 0, 0.1);
            text-align: center;
        }

        .file-input-wrapper {
            display: inline-block;
            position: relative;
            overflow: hidden;
            background-color: #4CAF50;
            color: white;
            padding: 10px 20px;
            border-radius: 5px;
            cursor: pointer;
            transition: background-color 0.3s;
        }

        .file-input-wrapper:hover {
            background-color: #45a049;
        }

        .file-input-wrapper input[type="file"] {
            position: absolute;
            left: -9999px;
        }

        /* Containers */
        .structure-container {
            margin: 20px 0;
            border: 1px solid #ddd;
            padding: 20px;
            background-color: #fff;
            border-radius: 10px;
            box-shadow: 0 2px 5px rgba(0, 0, 0, 0.1);
            display: none;
        }

        .structure-grid {
            display: grid;
            grid-template-columns: minmax(320px, 1fr) 1fr;
            gap: 20px;
            margin-top: 15px;
            align-items: start;
        }

        /* 3D Viewer */
        .viewer-container {
            position: relative;
            width: 100%;
            height: 400px;
            border: 1px solid #ccc;
            border-radius: 5px;
            overflow: hidden;
        }

        .viewer-container .viewer {
            width: 100%;
            height: 100%;
        }

        .viewer-container canvas {
            position: absolute !important;
            inset: 0;
            width: 100% !important;
            height: 100% !important;
        }

        /* Table */
        .analysis-table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 10px;
        }

        .analysis-table th,
        .analysis-table td {
            border: 1px solid #ddd;
            padding: 8px;
            text-align: left;
        }

        .analysis-table th {
            background-color: #f8f9fa;
            font-weight: bold;
        }

        /* Utility */
        .formula {
            font-family: "Courier New", monospace;
            background-color: #e9ecef;
            padding: 2px 5px;
            border-radius: 3px;
        }

        .error {
            color: #d32f2f;
            margin-top: 10px;
        }

        /* Direct Input */
        .input-method {
            margin: 10px 0;
        }

        .cif-textarea {
            width: 100%;
            height: 200px;
            font-family: monospace;
            font-size: 12px;
            padding: 10px;
            border: 1px solid #ddd;
            border-radius: 5px;
            margin: 10px 0;
        }

        .load-button {
            background-color: #2196F3;
            color: white;
            padding: 10px 20px;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            transition: background-color 0.3s;
        }

        .load-button:hover {
            background-color: #1976D2;
        }

        .tab-buttons {
            display: flex;
            gap: 10px;
            margin-bottom: 20px;
        }

        .tab-button {
            padding: 10px 20px;
            border: 1px solid #ddd;
            background-color: #f5f5f5;
            cursor: pointer;
            border-radius: 5px 5px 0 0;
            transition: all 0.3s;
        }

        .tab-button.active {
            background-color: #fff;
            border-bottom: 1px solid #fff;
            font-weight: bold;
        }

        .tab-content {
            display: none;
        }

        .tab-content.active {
            display: block;
        }
    </style>
</head>
<body>
    <!-- Header -->
    <div class="header">
        <h1>🔬 Universal Crystal Structure Viewer</h1>
        <p>Load any CIF file to visualise crystal structures | Powered by CrystaLyse.AI</p>
    </div>

    <!-- Input Section -->
    <div class="upload-container">
        <h2>📂 Load Crystal Structure</h2>
        
        <div class="tab-buttons">
            <div class="tab-button active" onclick="switchTab('file')">Upload File</div>
            <div class="tab-button" onclick="switchTab('text')">Paste CIF Data</div>
        </div>

        <div id="file-tab" class="tab-content active">
            <div class="file-input-wrapper">
                <span>Choose CIF File</span>
                <input type="file" id="fileInput" accept=".cif" onchange="handleFileSelect(event)">
            </div>
            <p style="margin-top: 10px; color: #666;">Supported format: .cif</p>
        </div>

        <div id="text-tab" class="tab-content">
            <textarea id="cifTextarea" class="cif-textarea" placeholder="Paste your CIF data here..."></textarea>
            <button class="load-button" onclick="loadFromText()">Load CIF Data</button>
        </div>

        <div id="error-message" class="error"></div>
    </div>

    <!-- Structure Section -->
    <div id="structureContainer" class="structure-container">
        <h2>📊 Crystal Structure</h2>
        <div class="structure-grid">
            <!-- 3D Viewer Column -->
            <div>
                <h3>🧊 3D Visualisation</h3>
                <div class="viewer-container">
                    <div id="viewer" class="viewer"></div>
                </div>
            </div>

            <!-- Analysis Column -->
            <div>
                <h3>📋 Structural Analysis</h3>
                <table class="analysis-table">
                    <tbody id="analysisTableBody">
                        <!-- Data will be populated here -->
                    </tbody>
                </table>
            </div>
        </div>
    </div>

    <!-- JavaScript -->
    <script>
        let viewer = null;

        function switchTab(tab) {
            document.querySelectorAll('.tab-button').forEach(btn => btn.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(content => content.classList.remove('active'));
            
            if (tab === 'file') {
                document.querySelector('.tab-button:nth-child(1)').classList.add('active');
                document.getElementById('file-tab').classList.add('active');
            } else {
                document.querySelector('.tab-button:nth-child(2)').classList.add('active');
                document.getElementById('text-tab').classList.add('active');
            }
        }

        function parseCIF(cifContent) {
            const data = {
                cell_length_a: null,
                cell_length_b: null,
                cell_length_c: null,
                cell_angle_alpha: null,
                cell_angle_beta: null,
                cell_angle_gamma: null,
                space_group: null,
                formula: null,
                volume: null,
                atoms: []
            };

            // Parse cell parameters
            const cellParams = {
                '_cell_length_a': 'cell_length_a',
                '_cell_length_b': 'cell_length_b',
                '_cell_length_c': 'cell_length_c',
                '_cell_angle_alpha': 'cell_angle_alpha',
                '_cell_angle_beta': 'cell_angle_beta',
                '_cell_angle_gamma': 'cell_angle_gamma'
            };

            for (const [cifKey, dataKey] of Object.entries(cellParams)) {
                const regex = new RegExp(`${cifKey}\\\\s+([\\\\d.]+)`, 'i');
                const match = cifContent.match(regex);
                if (match) {
                    data[dataKey] = parseFloat(match[1]);
                }
            }

            // Parse space group
            const spaceGroupRegex = /_space_group_name_H-M_alt\\s+'([^']+)'|_symmetry_space_group_name_H-M\\s+'([^']+)'/i;
            const spaceGroupMatch = cifContent.match(spaceGroupRegex);
            if (spaceGroupMatch) {
                data.space_group = spaceGroupMatch[1] || spaceGroupMatch[2];
            }

            // Calculate volume if we have all cell parameters
            if (data.cell_length_a && data.cell_length_b && data.cell_length_c) {
                const a = data.cell_length_a;
                const b = data.cell_length_b;
                const c = data.cell_length_c;
                const alpha = data.cell_angle_alpha * Math.PI / 180;
                const beta = data.cell_angle_beta * Math.PI / 180;
                const gamma = data.cell_angle_gamma * Math.PI / 180;
                
                data.volume = a * b * c * Math.sqrt(
                    1 - Math.cos(alpha)**2 - Math.cos(beta)**2 - Math.cos(gamma)**2 
                    + 2 * Math.cos(alpha) * Math.cos(beta) * Math.cos(gamma)
                );
            }

            // Extract unique atom types for formula
            const atomTypes = new Set();
            const atomLines = cifContent.match(/^[A-Z][a-z]?\\d*\\s+[\\d.-]+\\s+[\\d.-]+\\s+[\\d.-]+/gm);
            if (atomLines) {
                atomLines.forEach(line => {
                    const atomType = line.match(/^([A-Z][a-z]?)/)[1];
                    atomTypes.add(atomType);
                });
            }
            
            if (atomTypes.size > 0) {
                data.formula = Array.from(atomTypes).sort().join('');
            }

            return data;
        }

        function updateAnalysisTable(cifData) {
            const tbody = document.getElementById('analysisTableBody');
            tbody.innerHTML = '';

            const rows = [
                { label: 'Formula', value: cifData.formula || 'N/A' },
                { label: 'Volume', value: cifData.volume ? `${cifData.volume.toFixed(2)} Å³` : 'N/A' },
                { label: 'a', value: cifData.cell_length_a ? `${cifData.cell_length_a.toFixed(3)} Å` : 'N/A' },
                { label: 'b', value: cifData.cell_length_b ? `${cifData.cell_length_b.toFixed(3)} Å` : 'N/A' },
                { label: 'c', value: cifData.cell_length_c ? `${cifData.cell_length_c.toFixed(3)} Å` : 'N/A' },
                { label: 'α', value: cifData.cell_angle_alpha ? `${cifData.cell_angle_alpha.toFixed(2)}°` : 'N/A' },
                { label: 'β', value: cifData.cell_angle_beta ? `${cifData.cell_angle_beta.toFixed(2)}°` : 'N/A' },
                { label: 'γ', value: cifData.cell_angle_gamma ? `${cifData.cell_angle_gamma.toFixed(2)}°` : 'N/A' },
                { label: 'Space Group', value: cifData.space_group ? `<strong>${cifData.space_group}</strong>` : 'N/A' }
            ];

            rows.forEach(row => {
                const tr = document.createElement('tr');
                tr.innerHTML = `<td>${row.label}</td><td>${row.value}</td>`;
                tbody.appendChild(tr);
            });
        }

        function visualiseCIF(cifContent) {
            // Clear any existing viewer
            if (viewer) {
                viewer.clear();
            }

            // Create new viewer
            viewer = $3Dmol.createViewer("viewer");
            
            // Add the CIF model
            viewer.addModel(cifContent, "cif");
            
            // Set visualisation style
            viewer.setStyle({ 
                stick: { radius: 0.15 }, 
                sphere: { scale: 0.3 } 
            });
            
            // Add unit cell
            viewer.addUnitCell();
            
            // Zoom and render
            viewer.zoomTo();
            viewer.render();

            // Parse CIF data and update table
            const cifData = parseCIF(cifContent);
            updateAnalysisTable(cifData);

            // Show the structure container
            document.getElementById('structureContainer').style.display = 'block';
            document.getElementById('error-message').textContent = '';
        }

        function handleFileSelect(event) {
            const file = event.target.files[0];
            if (!file) return;

            const reader = new FileReader();
            reader.onload = function(e) {
                try {
                    visualiseCIF(e.target.result);
                } catch (error) {
                    document.getElementById('error-message').textContent = 
                        'Error loading CIF file: ' + error.message;
                }
            };
            reader.readAsText(file);
        }

        function loadFromText() {
            const cifContent = document.getElementById('cifTextarea').value.trim();
            if (!cifContent) {
                document.getElementById('error-message').textContent = 'Please paste CIF data first';
                return;
            }

            try {
                visualiseCIF(cifContent);
            } catch (error) {
                document.getElementById('error-message').textContent = 
                    'Error parsing CIF data: ' + error.message;
            }
        }
    </script>
</body>
</html>'''


def main():
    """Command line interface for the universal CIF visualizer."""
    parser = argparse.ArgumentParser(description='Universal CIF Visualizer for CrystaLyse.AI')
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Create universal viewer command
    viewer_parser = subparsers.add_parser('create-viewer', help='Create universal CIF viewer HTML file')
    viewer_parser.add_argument('output', help='Output HTML file path')
    
    # Convert single CIF command
    convert_parser = subparsers.add_parser('convert', help='Convert single CIF file to HTML')
    convert_parser.add_argument('cif_file', help='Input CIF file path')
    convert_parser.add_argument('--output', '-o', help='Output HTML file path')
    
    # Create gallery command
    gallery_parser = subparsers.add_parser('gallery', help='Create gallery from directory of CIF files')
    gallery_parser.add_argument('directory', help='Directory containing CIF files')
    gallery_parser.add_argument('--output', '-o', help='Output directory for gallery')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    visualizer = UniversalCIFVisualizer()
    
    try:
        if args.command == 'create-viewer':
            visualizer.create_universal_viewer(args.output)
        
        elif args.command == 'convert':
            visualizer.convert_cif_to_html(args.cif_file, args.output)
        
        elif args.command == 'gallery':
            visualizer.create_gallery(args.directory, args.output)
    
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()