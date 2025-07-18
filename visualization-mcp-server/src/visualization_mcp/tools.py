"""Visualization tools for CrystaLyse.AI"""

import json
import sys
from pathlib import Path
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

def create_3dmol_visualization(
    cif_content: str,
    formula: str,
    output_dir: str,
    title: str = "Crystal Structure",
    color_scheme: str = "vesta"
) -> str:
    """
    Create fast 3Dmol.js visualization for creative mode.
    
    Args:
        cif_content: CIF file content as string
        formula: Chemical formula for naming
        output_dir: Directory to save visualization
        title: Title for the visualization
        color_scheme: Color scheme for the visualization (e.g., 'vesta', 'cpk')
    
    Returns:
        JSON string with visualization details
    """
    try:
        # Fix import path to avoid circular imports
        current_dir = Path(__file__).parent
        crystalyse_root = current_dir.parent.parent.parent / "crystalyse"
        if str(crystalyse_root) not in sys.path:
            sys.path.insert(0, str(crystalyse_root))
        
        # Import existing visualizer
        from crystalyse.output.universal_cif_visualizer import UniversalCIFVisualizer
        
        visualizer = UniversalCIFVisualizer(color_scheme=color_scheme)
        output_path = Path(output_dir) / f"{formula}_3dmol.html"
        
        # Create HTML visualization
        cif_data = visualizer.parse_cif_data(cif_content)
        html_content = visualizer.create_individual_html(cif_content, cif_data, title)
        
        with open(output_path, 'w') as f:
            f.write(html_content)
        
        result = {
            "type": "3dmol_visualization",
            "status": "success",
            "output_path": str(output_path),
            "formula": formula,
            "visualization_type": "interactive_html",
            "sharing": "easy",
            "description": f"Fast 3Dmol.js visualization for {formula}"
        }
        
        logger.info(f"✅ 3Dmol.js visualization created: {output_path}")
        return json.dumps(result)
        
    except Exception as e:
        error_result = {
            "type": "3dmol_visualization",
            "status": "error",
            "error": str(e),
            "formula": formula
        }
        logger.error(f"❌ 3Dmol.js visualization failed: {e}")
        return json.dumps(error_result)

def create_pymatviz_analysis_suite(
    cif_content: str,
    formula: str,
    output_dir: str,
    title: str = "Crystal Structure Analysis",
    color_scheme: str = "vesta"
) -> str:
    """
    Create comprehensive pymatviz analysis suite (XRD, RDF, coordination analysis).
    
    Args:
        cif_content: CIF file content as string
        formula: Chemical formula for naming
        output_dir: Directory to save analysis files
        title: Title for the analysis
        color_scheme: Color scheme for the visualization (e.g., 'vesta', 'jmol')
    
    Returns:
        JSON string with analysis details
    """
    try:
        import pymatviz as pmv
        from pymatviz.enums import ElemColorScheme
        from pymatgen.core import Structure
        
        # Parse structure
        structure = Structure.from_str(cif_content, fmt="cif")
        analysis_dir = Path(output_dir) / f"{formula}_analysis"
        analysis_dir.mkdir(exist_ok=True)
        
        # Save the CIF file
        cif_path = analysis_dir / f"{formula}.cif"
        with open(cif_path, "w") as f:
            f.write(cif_content)
        
        # Select color scheme
        if color_scheme == "vesta":
            elem_colors = ElemColorScheme.vesta
        elif color_scheme == "jmol":
            elem_colors = ElemColorScheme.jmol
        else:
            elem_colors = ElemColorScheme.jmol  # Default fallback

        # Set professional theme
        pmv.set_plotly_template("pymatviz_white")
        
        # Create analysis suite
        analysis_files = [str(cif_path)]

        # 3D structure visualization
        try:
            struct_3d_fig = pmv.structure_3d_plotly(
                structure, 
                elem_colors=elem_colors,
                show_bonds=True
            )
            struct_3d_fig.update_layout(title=dict(text=f"3D Structure: {formula}", x=0.5))
            struct_3d_path = analysis_dir / f"{formula}_structure_3d.pdf"
            pmv.save_fig(struct_3d_fig, str(struct_3d_path))
            analysis_files.append(str(struct_3d_path))
        except Exception as e:
            logger.warning(f"3D structure visualization failed: {e}")
        
        # XRD Pattern
        try:
            xrd_fig = pmv.xrd_pattern(structure, annotate_peaks=5)
            xrd_fig.update_layout(title=dict(text=f"XRD Pattern: {formula}", x=0.5))
            xrd_path = analysis_dir / f"{formula}_xrd.pdf"
            pmv.save_fig(xrd_fig, str(xrd_path))
            analysis_files.append(str(xrd_path))
        except Exception as e:
            logger.warning(f"XRD generation failed: {e}")
        
        # Radial Distribution Function
        try:
            rdf_fig = pmv.element_pair_rdfs(structure)
            rdf_fig.update_layout(title=dict(text=f"RDF Analysis: {formula}", x=0.5))
            rdf_path = analysis_dir / f"{formula}_rdf.pdf"
            pmv.save_fig(rdf_fig, str(rdf_path))
            analysis_files.append(str(rdf_path))
        except Exception as e:
            logger.warning(f"RDF generation failed: {e}")
        
        # Coordination Environment
        try:
            coord_fig = pmv.coordination_hist(structure)
            coord_fig.update_layout(title=dict(text=f"Coordination Analysis: {formula}", x=0.5))
            coord_path = analysis_dir / f"{formula}_coordination.pdf"
            pmv.save_fig(coord_fig, str(coord_path))
            analysis_files.append(str(coord_path))
        except Exception as e:
            logger.warning(f"Coordination analysis failed: {e}")
        
        result = {
            "type": "pymatviz_analysis_suite",
            "status": "success",
            "analysis_dir": str(analysis_dir),
            "analysis_files": analysis_files,
            "formula": formula,
            "visualization_type": "comprehensive_analysis",
            "sharing": "professional",
            "description": f"Comprehensive materials analysis suite for {formula}"
        }
        
        logger.info(f"✅ pymatviz analysis suite created: {analysis_dir}")
        return json.dumps(result)
        
    except Exception as e:
        error_result = {
            "type": "pymatviz_analysis_suite",
            "status": "error",
            "error": str(e),
            "formula": formula
        }
        logger.error(f"❌ pymatviz analysis suite failed: {e}")
        return json.dumps(error_result)

def create_creative_visualization(
    cif_content: str,
    formula: str,
    output_dir: str,
    title: str = "Crystal Structure",
    color_scheme: str = "vesta"
) -> str:
    """
    Create creative mode visualization (3Dmol.js only).
    
    Args:
        cif_content: CIF file content as string
        formula: Chemical formula for naming
        output_dir: Directory to save visualization
        title: Title for the visualization
        color_scheme: Color scheme for the visualization
    
    Returns:
        JSON string with visualization details
    """
    return create_3dmol_visualization(cif_content, formula, output_dir, title, color_scheme=color_scheme)

def create_rigorous_visualization(
    cif_content: str,
    formula: str,
    output_dir: str,
    title: str = "Crystal Structure",
    color_scheme: str = "vesta"
) -> str:
    """
    Create rigorous mode visualization (3Dmol.js + pymatviz analysis suite).
    
    Args:
        cif_content: CIF file content as string
        formula: Chemical formula for naming
        output_dir: Directory to save visualization
        title: Title for the visualization
        color_scheme: Color scheme for the visualization
    
    Returns:
        JSON string with visualization details
    """
    try:
        # Create 3Dmol.js structure visualization
        structure_result = create_3dmol_visualization(cif_content, formula, output_dir, title, color_scheme=color_scheme)
        structure_data = json.loads(structure_result)
        
        # Create pymatviz analysis suite
        analysis_result = create_pymatviz_analysis_suite(cif_content, formula, output_dir, title, color_scheme=color_scheme)
        analysis_data = json.loads(analysis_result)
        
        # Combine results
        combined_result = {
            "type": "rigorous_visualization",
            "status": "success",
            "structure_visualization": structure_data,
            "analysis_suite": analysis_data,
            "formula": formula,
            "visualization_type": "comprehensive",
            "sharing": "professional_and_interactive",
            "description": f"Complete visualization suite for {formula}: interactive structure view + comprehensive analysis"
        }
        
        logger.info(f"✅ Rigorous visualization suite created for {formula}")
        return json.dumps(combined_result)
        
    except Exception as e:
        error_result = {
            "type": "rigorous_visualization",
            "status": "error",
            "error": str(e),
            "formula": formula
        }
        logger.error(f"❌ Rigorous visualization failed: {e}")
        return json.dumps(error_result)

def create_mode_aligned_visualization(
    cif_content: str,
    formula: str,
    output_dir: str,
    mode: str = "creative",
    title: str = "Crystal Structure",
    color_scheme: str = "vesta"
) -> str:
    """
    Create mode-aligned visualization automatically.
    
    Args:
        cif_content: CIF file content as string
        formula: Chemical formula for naming
        output_dir: Directory to save visualization
        mode: Analysis mode ("creative" or "rigorous")
        title: Title for the visualization
        color_scheme: Color scheme for the visualization
    
    Returns:
        JSON string with visualization details
    """
    if mode == "rigorous":
        return create_rigorous_visualization(cif_content, formula, output_dir, title, color_scheme=color_scheme)
    else:
        return create_creative_visualization(cif_content, formula, output_dir, title, color_scheme=color_scheme)