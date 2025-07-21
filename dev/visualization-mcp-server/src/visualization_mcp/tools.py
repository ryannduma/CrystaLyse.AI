"""Visualization tools for CrystaLyse.AI"""

import json
import sys
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
import logging

logger = logging.getLogger(__name__)

# Import browser session manager
try:
    from .browser_pool import batch_save_figures, optimize_pymatviz_performance
    BROWSER_POOL_AVAILABLE = True
except ImportError:
    BROWSER_POOL_AVAILABLE = False
    logger.warning("Browser session manager not available - using individual sessions")

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
        # Check if visualization already exists
        output_path = Path(output_dir) / f"{formula}_3dmol.html"
        if output_path.exists():
            result = {
                "type": "3dmol_visualization",
                "status": "success",
                "output_path": str(output_path),
                "formula": formula,
                "visualization_type": "interactive_html",
                "sharing": "easy",
                "description": f"Fast 3Dmol.js visualization for {formula} (cached)",
                "cached": True
            }
            logger.info(f"✅ 3Dmol.js visualization found (cached): {output_path}")
            return json.dumps(result)
        
        # Fix import path to avoid circular imports
        current_dir = Path(__file__).parent
        crystalyse_root = current_dir.parent.parent.parent / "crystalyse"
        if str(crystalyse_root) not in sys.path:
            sys.path.insert(0, str(crystalyse_root))
        
        # Import existing visualizer
        from crystalyse.output.universal_cif_visualizer import UniversalCIFVisualizer
        
        visualizer = UniversalCIFVisualizer(color_scheme=color_scheme)
        
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
            "description": f"Fast 3Dmol.js visualization for {formula}",
            "cached": False
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
    Create comprehensive pymatviz analysis suite with headless compatibility.
    
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
        # Check if analysis suite already exists
        analysis_dir = Path(output_dir) / f"{formula}_analysis"
        required_files = [
            analysis_dir / f"{formula}.cif",
            analysis_dir / f"XRD_Pattern_{formula}.pdf",
            analysis_dir / f"RDF_Analysis_{formula}.pdf",
            analysis_dir / f"Coordination_Analysis_{formula}.pdf"
        ]
        
        if analysis_dir.exists() and all(f.exists() for f in required_files):
            # Return cached result
            existing_files = [str(f) for f in required_files if f.exists()]
            # Also check for optional 3D structure file
            struct_3d_path = analysis_dir / f"3D_Structure_{formula}.pdf"
            if struct_3d_path.exists():
                existing_files.append(str(struct_3d_path))
            
            result = {
                "type": "pymatviz_analysis_suite",
                "status": "success",
                "analysis_dir": str(analysis_dir),
                "analysis_files": existing_files,
                "formula": formula,
                "visualization_type": "comprehensive_analysis",
                "sharing": "professional",
                "description": f"Comprehensive materials analysis suite for {formula} (cached)",
                "cached": True,
                "component_results": {
                    "xrd_pattern": "cached",
                    "rdf_analysis": "cached",
                    "coordination_analysis": "cached",
                    "3d_structure": "cached" if struct_3d_path.exists() else "not_available"
                }
            }
            logger.info(f"✅ pymatviz analysis suite found (cached): {analysis_dir}")
            return json.dumps(result)
        
        import pymatviz as pmv
        from pymatviz.enums import ElemColorScheme
        from pymatgen.core import Structure
        import os

        # Parse structure
        structure = Structure.from_str(cif_content, fmt="cif")
        analysis_dir.mkdir(exist_ok=True)

        # Save the CIF file (only if it doesn't exist)
        cif_path = analysis_dir / f"{formula}.cif"
        if not cif_path.exists():
            with open(cif_path, "w") as f:
                f.write(cif_content)
            logger.info(f"CIF file created: {cif_path}")
        else:
            logger.info(f"CIF file already exists: {cif_path}")

        # Select color scheme
        if color_scheme == "vesta":
            elem_colors = ElemColorScheme.vesta
        elif color_scheme == "jmol":
            elem_colors = ElemColorScheme.jmol
        else:
            elem_colors = ElemColorScheme.jmol  # Default fallback

        # Set professional theme
        pmv.set_plotly_template("pymatviz_white")

        # Configure headless environment for better WebGL compatibility
        os.environ.setdefault("DISPLAY", ":99")
        
        # Apply browser session optimizations
        if BROWSER_POOL_AVAILABLE:
            # Browser session manager will handle optimization
            pass
        else:
            # Fallback kaleido configuration
            try:
                import kaleido
                if hasattr(kaleido, 'config') and hasattr(kaleido.config, 'scope'):
                    kaleido.config.scope.chromium.disable_features = [
                        "VizDisplayCompositor",
                        "UseOzonePlatform",
                        "WebGL",
                        "WebGL2"
                    ]
                    kaleido.config.scope.chromium.timeout = 30
            except (ImportError, AttributeError):
                pass

        # Create analysis suite with optimized browser session management
        analysis_files = [str(cif_path)]
        visualization_results = {}
        
        # Define all potential visualization files
        struct_3d_path = analysis_dir / f"3D_Structure_{formula}.pdf"
        xrd_path = analysis_dir / f"XRD_Pattern_{formula}.pdf"
        rdf_path = analysis_dir / f"RDF_Analysis_{formula}.pdf"
        coord_path = analysis_dir / f"Coordination_Analysis_{formula}.pdf"
        
        # Check if ALL visualizations already exist (smart detection)
        all_viz_files = [struct_3d_path, xrd_path, rdf_path, coord_path]
        all_exist = all(f.exists() for f in all_viz_files)
        
        if all_exist:
            logger.info(f"✅ All visualizations already exist for {formula}, returning cached results")
            return json.dumps({
                "type": "pymatviz_analysis_suite",
                "status": "success",
                "analysis_dir": str(analysis_dir),
                "analysis_files": [str(cif_path)] + [str(f) for f in all_viz_files],
                "formula": formula,
                "visualization_type": "comprehensive_analysis",
                "sharing": "professional",
                "description": f"Comprehensive materials analysis suite for {formula} (all cached)",
                "cached": True,
                "component_results": {
                    "xrd_pattern": "cached",
                    "rdf_analysis": "cached",
                    "coordination_analysis": "cached",
                    "3d_structure": "cached"
                }
            })
        
        # Apply performance optimizations
        if BROWSER_POOL_AVAILABLE:
            optimize_pymatviz_performance()
        
        # Create all figures in memory first (batch preparation)
        logger.info(f"🎨 Creating visualizations for {formula} using optimized browser session")
        figures_to_save = []
        
        # Check which visualizations need to be created
        pending_visualizations = []
        for viz_path in all_viz_files:
            if not viz_path.exists():
                viz_type = viz_path.stem.split('_')[0].lower()
                pending_visualizations.append((viz_type, viz_path))
        
        logger.info(f"Creating {len(pending_visualizations)} new visualizations for {formula}")

        # Create all figures in memory first (Phase 1: Figure Generation)
        logger.info("📊 Phase 1: Creating figures in memory...")
        
        # Create figures for pending visualizations
        for viz_type, viz_path in pending_visualizations:
            try:
                figure = None
                viz_name = viz_path.stem.split('_', 1)[0].lower()
                
                if viz_name == '3d':
                    figure = pmv.structure_3d_plotly(
                        structure, 
                        elem_colors=elem_colors,
                        show_bonds=True
                    )
                    figure.update_layout(title=dict(text=f"3D Structure: {formula}", x=0.5))
                    visualization_results["3d_structure"] = "prepared"
                    
                elif viz_name == 'xrd':
                    figure = pmv.xrd_pattern(structure, annotate_peaks=5)
                    figure.update_layout(title=dict(text=f"XRD Pattern: {formula}", x=0.5))
                    visualization_results["xrd_pattern"] = "prepared"
                    
                elif viz_name == 'rdf':
                    figure = pmv.element_pair_rdfs(structure)
                    figure.update_layout(title=dict(text=f"RDF Analysis: {formula}", x=0.5))
                    visualization_results["rdf_analysis"] = "prepared"
                    
                elif viz_name == 'coordination':
                    figure = pmv.coordination_hist(structure)
                    figure.update_layout(title=dict(text=f"Coordination Analysis: {formula}", x=0.5))
                    visualization_results["coordination_analysis"] = "prepared"
                
                if figure is not None:
                    figures_to_save.append((figure, str(viz_path)))
                    logger.info(f"  ✅ {viz_name.upper()} figure prepared")
                    
            except Exception as e:
                logger.warning(f"❌ Failed to create {viz_type} figure: {e}")
                viz_key = viz_type.replace('_structure', '_structure').replace('_pattern', '_pattern').replace('_analysis', '_analysis')
                if viz_key not in visualization_results:
                    visualization_results[viz_key] = f"failed: {e}"
        
        # Phase 2: Batch Save All Figures Using Single Browser Session
        if figures_to_save:
            logger.info(f"🚀 Phase 2: Saving {len(figures_to_save)} figures using single browser session...")
            
            if BROWSER_POOL_AVAILABLE:
                # Use optimized browser session manager
                save_results = batch_save_figures(figures_to_save)
                
                # Update results based on save outcomes
                for viz_path, result in save_results.items():
                    viz_name = Path(viz_path).stem.split('_', 1)[0].lower()
                    
                    if viz_name == '3d':
                        visualization_results["3d_structure"] = "success" if result == "success" else result
                    elif viz_name == 'xrd':
                        visualization_results["xrd_pattern"] = "success" if result == "success" else result
                    elif viz_name == 'rdf':
                        visualization_results["rdf_analysis"] = "success" if result == "success" else result
                    elif viz_name == 'coordination':
                        visualization_results["coordination_analysis"] = "success" if result == "success" else result
                    
                    if result == "success":
                        analysis_files.append(viz_path)
                        
                logger.info(f"✅ Batch save completed with single browser session")
                
            else:
                # Fallback to individual saves (less efficient)
                logger.warning("Browser session manager not available, using individual saves")
                
                for figure, viz_path in figures_to_save:
                    try:
                        pmv.save_fig(figure, viz_path)
                        analysis_files.append(viz_path)
                        
                        viz_name = Path(viz_path).stem.split('_', 1)[0].lower()
                        if viz_name == '3d':
                            visualization_results["3d_structure"] = "success"
                        elif viz_name == 'xrd':
                            visualization_results["xrd_pattern"] = "success"
                        elif viz_name == 'rdf':
                            visualization_results["rdf_analysis"] = "success"
                        elif viz_name == 'coordination':
                            visualization_results["coordination_analysis"] = "success"
                            
                    except Exception as e:
                        logger.error(f"Failed to save {viz_path}: {e}")
        
        # Add cached results for files that already existed
        for viz_path in all_viz_files:
            if viz_path.exists() and str(viz_path) not in analysis_files:
                analysis_files.append(str(viz_path))
                
                viz_name = viz_path.stem.split('_', 1)[0].lower()
                if viz_name == '3d':
                    visualization_results["3d_structure"] = "cached"
                elif viz_name == 'xrd':
                    visualization_results["xrd_pattern"] = "cached"
                elif viz_name == 'rdf':
                    visualization_results["rdf_analysis"] = "cached"
                elif viz_name == 'coordination':
                    visualization_results["coordination_analysis"] = "cached"

        result = {
            "type": "pymatviz_analysis_suite",
            "status": "success",
            "analysis_dir": str(analysis_dir),
            "analysis_files": analysis_files,
            "formula": formula,
            "visualization_type": "comprehensive_analysis",
            "sharing": "professional",
            "description": f"Comprehensive materials analysis suite for {formula}",
            "component_results": visualization_results,
            "cached": False
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