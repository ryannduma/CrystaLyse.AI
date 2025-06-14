"""
Enhanced CrystaLyse agent with integrated visualization and storage capabilities.

This module extends the basic CrystaLyseAgent with automatic crystal structure
visualization, storage management, and comprehensive reporting functionality.
It provides a complete end-to-end materials discovery workflow from composition
generation to interactive 3D structure visualization.
"""

import json
import re
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Union

from .main_agent import CrystaLyseAgent
try:
    from ..config import get_agent_config
    from ..visualization import CrystalVisualizer, StructureStorage
except ImportError:
    from config import get_agent_config
    from visualization import CrystalVisualizer, StructureStorage


class EnhancedCrystaLyseAgent(CrystaLyseAgent):
    """
    Enhanced materials discovery agent with integrated visualization and storage.
    
    This class extends the base CrystaLyseAgent to automatically generate crystal
    structures, create interactive visualizations, and manage file storage for
    a complete materials discovery workflow.
    """
    
    def __init__(self, model: str = None, temperature: float = None, 
                 use_chem_tools: bool = False, storage_dir: str = None,
                 auto_visualize: bool = True, auto_store: bool = True):
        """Initialize enhanced agent with visualization and storage capabilities.
        
        Args:
            model: OpenAI model to use
            temperature: Temperature for generation
            use_chem_tools: Enable SMACT validation tools
            storage_dir: Directory for storing structures and reports
            auto_visualize: Automatically generate visualizations
            auto_store: Automatically store results
        """
        super().__init__(model, temperature, use_chem_tools)
        
        # Initialize visualization and storage systems
        self.auto_visualize = auto_visualize
        self.auto_store = auto_store
        
        if auto_visualize:
            self.visualizer = CrystalVisualizer(backend="py3dmol")
        
        if auto_store:
            self.storage = StructureStorage(storage_dir)
        
        # Session tracking
        self.session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    async def analyze_with_visualization(self, query: str, 
                                       num_structures_per_composition: int = 3,
                                       generate_report: bool = True) -> Dict[str, Any]:
        """Perform complete materials discovery with visualization and storage.
        
        Args:
            query: Materials discovery query
            num_structures_per_composition: Number of structures to generate per composition
            generate_report: Generate HTML visualization report
        
        Returns:
            Enhanced result dictionary with visualization and storage information
        """
        # Run standard analysis
        analysis_result = await self.analyze(query)
        
        # Extract composition information from the result
        compositions = self._extract_compositions_from_result(analysis_result)
        
        result = {
            'query': query,
            'analysis_result': analysis_result,
            'session_id': self.session_id,
            'timestamp': datetime.now().isoformat(),
            'compositions': [],
            'visualization_reports': [],
            'storage_info': {}
        }
        
        if not compositions:
            result['error'] = "No compositions found in analysis result"
            return result
        
        # Process each composition
        for composition in compositions:
            comp_result = await self._process_composition(
                composition, 
                num_structures_per_composition
            )
            result['compositions'].append(comp_result)
            
            # Generate visualization report if requested
            if generate_report and comp_result.get('structures'):
                report_path = self._generate_visualization_report(
                    composition, 
                    comp_result['structures']
                )
                if report_path:
                    result['visualization_reports'].append(str(report_path))
        
        # Store session summary
        if self.auto_store:
            result['storage_info'] = self._store_session_summary(result)
        
        return result
    
    async def _process_composition(self, composition: str, 
                                 num_structures: int) -> Dict[str, Any]:
        """Process a single composition: generate structures, analyze, and store.
        
        Args:
            composition: Chemical composition (e.g., "CaTiO3")
            num_structures: Number of structures to generate
        
        Returns:
            Dictionary with composition processing results
        """
        comp_result = {
            'composition': composition,
            'structures': [],
            'success': False,
            'error': None,
            'storage_paths': []
        }
        
        try:
            # Generate crystal structures using Chemeleon
            if self.use_chem_tools:
                # In rigorous mode, structures should already be generated by the agent
                # Extract them from previous tool calls if available
                structures = await self._generate_structures_via_tools(composition, num_structures)
            else:
                # In creative mode, generate structures directly
                structures = await self._generate_structures_via_tools(composition, num_structures)
            
            if structures:
                comp_result['structures'] = structures
                comp_result['success'] = True
                
                # Store structures if auto-storage is enabled
                if self.auto_store:
                    storage_info = self.storage.store_structures(
                        composition=composition,
                        structures=structures,
                        analysis_params={
                            'num_structures': num_structures,
                            'model': self.model,
                            'temperature': self.temperature,
                            'use_chem_tools': self.use_chem_tools
                        },
                        session_id=self.session_id
                    )
                    comp_result['storage_paths'] = storage_info['cif_paths']
            else:
                comp_result['error'] = "Failed to generate crystal structures"
                
        except Exception as e:
            comp_result['error'] = str(e)
        
        return comp_result
    
    async def _generate_structures_via_tools(self, composition: str, 
                                           num_structures: int) -> List[Dict]:
        """Generate crystal structures using Chemeleon tools directly.
        
        This method simulates the structure generation that should happen
        within the agent's tool calls.
        """
        # Import the Chemeleon tools directly
        try:
            import sys
            chemeleon_path = self.chemeleon_path / "src"
            if str(chemeleon_path) not in sys.path:
                sys.path.append(str(chemeleon_path))
            
            from chemeleon_mcp.tools import generate_crystal_csp, analyse_structure
            
            # Generate structures
            result_str = generate_crystal_csp(
                formulas=composition,
                num_samples=num_structures,
                output_format="both"  # Get both dict and CIF
            )
            
            result = json.loads(result_str)
            
            if result.get('success'):
                structures = result.get('structures', [])
                
                # Analyze each structure
                for struct in structures:
                    if 'structure' in struct:
                        try:
                            analysis_str = analyse_structure(
                                structure_dict=struct['structure'],
                                calculate_symmetry=True
                            )
                            struct['analysis'] = json.loads(analysis_str)
                        except Exception as e:
                            struct['analysis'] = {'error': str(e)}
                
                return structures
            else:
                return []
                
        except Exception as e:
            print(f"Error generating structures: {e}")
            return []
    
    def _extract_compositions_from_result(self, result: str) -> List[str]:
        """Extract chemical compositions from analysis result.
        
        Args:
            result: Agent analysis result text
        
        Returns:
            List of identified chemical compositions
        """
        # Common chemical formula patterns
        patterns = [
            r'\b[A-Z][a-z]?[0-9]*(?:[A-Z][a-z]?[0-9]*)*\b',  # Basic chemical formulas
            r'\b[A-Z][a-z]?\d*[A-Z][a-z]?\d*[A-Z][a-z]?\d*\b',  # Multi-element compounds
        ]
        
        compositions = set()
        
        for pattern in patterns:
            matches = re.findall(pattern, result)
            for match in matches:
                # Filter out common false positives
                if (len(match) > 2 and 
                    not match.isdigit() and 
                    not match.isupper() and
                    any(c.isupper() for c in match) and
                    any(c.islower() for c in match)):
                    compositions.add(match)
        
        # Also look for explicitly mentioned formulas
        formula_indicators = [
            r'(?:formula|composition|compound)[:=\s]+([A-Z][a-z]?[0-9]*(?:[A-Z][a-z]?[0-9]*)*)',
            r'([A-Z][a-z]?[0-9]*(?:[A-Z][a-z]?[0-9]*)*)\s+(?:is|as|for)\s+(?:a|an|the)',
        ]
        
        for pattern in formula_indicators:
            matches = re.findall(pattern, result, re.IGNORECASE)
            compositions.update(matches)
        
        # Filter and validate compositions
        valid_compositions = []
        for comp in compositions:
            if self._is_valid_composition(comp):
                valid_compositions.append(comp)
        
        return list(valid_compositions)[:5]  # Limit to 5 compositions
    
    def _is_valid_composition(self, composition: str) -> bool:
        """Validate if a string represents a reasonable chemical composition."""
        # Basic validation rules
        if len(composition) < 2 or len(composition) > 20:
            return False
        
        # Must start with uppercase letter
        if not composition[0].isupper():
            return False
        
        # Must contain at least one other element
        if not any(c.isupper() for c in composition[1:]):
            return False
        
        # Common element symbols (partial list)
        common_elements = {
            'H', 'He', 'Li', 'Be', 'B', 'C', 'N', 'O', 'F', 'Ne',
            'Na', 'Mg', 'Al', 'Si', 'P', 'S', 'Cl', 'Ar', 'K', 'Ca',
            'Sc', 'Ti', 'V', 'Cr', 'Mn', 'Fe', 'Co', 'Ni', 'Cu', 'Zn',
            'Ga', 'Ge', 'As', 'Se', 'Br', 'Kr', 'Rb', 'Sr', 'Y', 'Zr',
            'Nb', 'Mo', 'Tc', 'Ru', 'Rh', 'Pd', 'Ag', 'Cd', 'In', 'Sn',
            'Sb', 'Te', 'I', 'Xe', 'Cs', 'Ba', 'La', 'Ce', 'Pr', 'Nd',
            'Pm', 'Sm', 'Eu', 'Gd', 'Tb', 'Dy', 'Ho', 'Er', 'Tm', 'Yb',
            'Lu', 'Hf', 'Ta', 'W', 'Re', 'Os', 'Ir', 'Pt', 'Au', 'Hg',
            'Tl', 'Pb', 'Bi', 'Po', 'At', 'Rn', 'Fr', 'Ra', 'Ac', 'Th',
            'Pa', 'U', 'Np', 'Pu'
        }
        
        # Extract elements using regex
        elements = re.findall(r'[A-Z][a-z]?', composition)
        
        # Check if at least half of the elements are known
        known_elements = sum(1 for elem in elements if elem in common_elements)
        return known_elements >= len(elements) * 0.5
    
    def _generate_visualization_report(self, composition: str, 
                                     structures: List[Dict]) -> Optional[Path]:
        """Generate HTML visualization report for a composition.
        
        Args:
            composition: Chemical composition
            structures: List of structure dictionaries
        
        Returns:
            Path to generated report file
        """
        if not self.auto_visualize or not structures:
            return None
        
        try:
            # Generate HTML report
            html_content = self.visualizer.create_multi_structure_report(
                structures, composition
            )
            
            # Store the report
            if self.auto_store:
                report_path = self.storage.store_visualization_report(
                    composition, html_content
                )
                return report_path
            else:
                # Save to temporary location
                output_dir = Path("temp_reports")
                output_dir.mkdir(exist_ok=True)
                report_path = output_dir / f"{composition}_report.html"
                report_path.write_text(html_content)
                return report_path
                
        except Exception as e:
            print(f"Error generating visualization report: {e}")
            return None
    
    def _store_session_summary(self, result: Dict) -> Dict:
        """Store session summary information.
        
        Args:
            result: Session result dictionary
        
        Returns:
            Storage information
        """
        if not self.auto_store:
            return {}
        
        try:
            # Create session summary
            summary = {
                'session_id': self.session_id,
                'timestamp': result['timestamp'],
                'query': result['query'],
                'model_config': {
                    'model': self.model,
                    'temperature': self.temperature,
                    'use_chem_tools': self.use_chem_tools
                },
                'compositions_processed': [c['composition'] for c in result['compositions']],
                'total_structures': sum(len(c.get('structures', [])) for c in result['compositions']),
                'visualization_reports': result['visualization_reports']
            }
            
            # Save session summary
            session_file = self.storage.base_dir / "sessions" / f"{self.session_id}.json"
            session_file.parent.mkdir(exist_ok=True)
            session_file.write_text(json.dumps(summary, indent=2))
            
            return {
                'session_file': str(session_file),
                'storage_stats': self.storage.get_storage_stats()
            }
            
        except Exception as e:
            return {'error': str(e)}
    
    def get_session_history(self) -> List[Dict]:
        """Get history of all sessions.
        
        Returns:
            List of session summaries
        """
        if not self.auto_store:
            return []
        
        sessions_dir = self.storage.base_dir / "sessions"
        if not sessions_dir.exists():
            return []
        
        sessions = []
        for session_file in sessions_dir.glob("*.json"):
            try:
                session_data = json.loads(session_file.read_text())
                sessions.append(session_data)
            except (json.JSONDecodeError, FileNotFoundError):
                continue
        
        # Sort by timestamp
        sessions.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        return sessions
    
    def export_session_results(self, session_id: str = None, 
                             export_format: str = "all") -> Dict[str, List[Path]]:
        """Export results from a specific session.
        
        Args:
            session_id: Session to export (if None, uses current session)
            export_format: Format to export ('cif', 'json', 'html', 'all')
        
        Returns:
            Dictionary with exported file paths by type
        """
        if not self.auto_store:
            return {}
        
        if session_id is None:
            session_id = self.session_id
        
        # Find session data
        session_file = self.storage.base_dir / "sessions" / f"{session_id}.json"
        if not session_file.exists():
            return {}
        
        try:
            session_data = json.loads(session_file.read_text())
            compositions = session_data.get('compositions_processed', [])
            
            exported_files = {'cif': [], 'json': [], 'html': []}
            
            # Export each composition
            for composition in compositions:
                if export_format in ['cif', 'all']:
                    cif_files = self.storage.export_structures(
                        composition, 'cif', 
                        self.storage.base_dir / "exports" / session_id
                    )
                    exported_files['cif'].extend(cif_files)
                
                if export_format in ['json', 'all']:
                    json_files = self.storage.export_structures(
                        composition, 'json',
                        self.storage.base_dir / "exports" / session_id
                    )
                    exported_files['json'].extend(json_files)
            
            # Copy HTML reports
            if export_format in ['html', 'all']:
                html_reports = session_data.get('visualization_reports', [])
                export_html_dir = self.storage.base_dir / "exports" / session_id / "reports"
                export_html_dir.mkdir(parents=True, exist_ok=True)
                
                for report_path in html_reports:
                    if Path(report_path).exists():
                        dest_path = export_html_dir / Path(report_path).name
                        dest_path.write_text(Path(report_path).read_text())
                        exported_files['html'].append(dest_path)
            
            return exported_files
            
        except (json.JSONDecodeError, FileNotFoundError):
            return {}