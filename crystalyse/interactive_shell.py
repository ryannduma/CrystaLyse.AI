#!/usr/bin/env python3
"""
CrystaLyse.AI Interactive Shell

An enhanced interactive shell for CrystaLyse.AI that provides a conversational
interface for materials discovery with session management, history, and
real-time visualisation capabilities.

Features:
    - Interactive command prompt with history and auto-suggestions
    - Session management for maintaining context across queries
    - Real-time streaming analysis with progress indicators
    - Built-in commands for mode switching, viewing results, and help
    - Browser-based 3D structure visualisation
    - Export capabilities for analysis results
"""

import asyncio
import json
import os
import tempfile
import webbrowser
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

try:
    from prompt_toolkit import prompt
    from prompt_toolkit.history import FileHistory
    from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
    from prompt_toolkit.completion import WordCompleter
except ImportError:
    print("Error: prompt_toolkit is required for interactive shell")
    print("Install with: pip install prompt-toolkit")
    raise

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.syntax import Syntax
from rich.columns import Columns
from rich.text import Text

from .unified_agent import CrystaLyseUnifiedAgent, AgentConfig
from .config import config


BANNER = """
    ▄████▄   ██▀███ ▓██   ██▓  ██████ ▄▄▄█████▓ ▄▄▄       ██▓   ▓██   ██▓  ██████ ▓█████
    ▒██▀ ▀█  ▓██ ▒ ██▒▒██  ██▒▒██    ▒ ▓  ██▒ ▓▒▒████▄    ▓██▒    ▒██  ██▒▒██    ▒ ▓█   ▀
    ▒▓█    ▄ ▓██ ░▄█ ▒ ▒██ ██░░ ▓██▄   ▒ ▓██░ ▒░▒██  ▀█▄  ▒██░     ▒██ ██░░ ▓██▄   ▒███
    ▒▓▓▄ ▄██▒▒██▀▀█▄   ░ ▐██▓░  ▒   ██▒░ ▓██▓ ░ ░██▄▄▄▄██ ▒██░     ░ ▐██▓░  ▒   ██▒▒▓█  ▄
    ▒ ▓███▀ ░░██▓ ▒██▒ ░ ██▒▓░▒██████▒▒  ▒██▒ ░  ▓█   ▓██▒░██████▒ ░ ██▒▓░▒██████▒▒░▒████▒
    ░ ░▒ ▒  ░░ ▒▓ ░▒▓░  ██▒▒▒ ▒ ▒▓▒ ▒ ░  ▒ ░░    ▒▒   ▓▒█░░ ▒░▓  ░  ██▒▒▒ ▒ ▒▓▒ ▒ ░░░ ▒░ ░
      ░  ▒     ░▒ ░ ▒░▓██ ░▒░ ░ ░▒  ░ ░    ░      ▒   ▒▒ ░░ ░ ▒  ░▓██ ░▒░ ░ ░▒  ░ ░ ░ ░  ░
    ░          ░░   ░ ▒ ▒ ░░  ░  ░  ░    ░        ░   ▒     ░ ░   ▒ ▒ ░░  ░  ░  ░     ░
    ░ ░         ░     ░ ░           ░                 ░  ░    ░  ░░ ░           ░     ░  ░
    ░                 ░ ░                                         ░ ░

    Materials Intelligence at Your Fingertips
    Version 1.0.0 | Mode: rigorous | Auto-view: OFF

    Quick Start:
    • "Design a new battery cathode"
    • "Find materials with band gap 2-3 eV"
    • /help for all commands

    Available Commands:
    • /help         - Show detailed help          • /mode         - Switch analysis modes
    • /view         - View structure in 3D        • /export       - Export session data
    • /history      - Show analysis history       • /clear        - Clear the screen
    • /status       - Show system status          • /examples     - Show example queries
    • /exit         - Exit the shell
"""

HELP_TEXT = """
CrystaLyse.AI Interactive Shell Help

BASIC USAGE:
  Simply type what kind of material you're looking for:
  
  Examples:
    "Design a cathode for sodium-ion batteries"
    "Find lead-free ferroelectric materials"
    "Suggest photovoltaic semiconductors"
    "Create a multiferroic material"

ANALYSIS MODES:
  • rigorous  - SMACT validation + MACE energy calculations + structure generation
  • creative  - AI-driven exploration with chemical intuition only
  
  Switch modes with: /mode creative  or  /mode rigorous

COMMANDS:
  /help              - Show this help message
  /mode [MODE]       - Set analysis mode (creative/rigorous)
  /view [FORMULA]    - Open structure viewer in browser
                       Without formula: shows latest structures
                       With formula: shows specific composition (e.g., /view CaTiO3)
  /export [FILE]     - Export session to JSON file
  /history           - Show your analysis history
  /clear             - Clear the screen
  /status            - Show API and system status
  /examples          - Show example queries
  /exit              - Exit the shell

STRUCTURE VIEWING:
  • /view            - View latest generated structures
  • /view CuInSe2    - View structures for specific composition
  • Auto-regenerates structures if needed using Chemeleon CSP

TIPS:
  • Be specific about the application (batteries, solar cells, etc.)
  • Mention any constraints (lead-free, low-cost, etc.)
  • Use Ctrl+C to interrupt long analyses
  • Up/down arrows browse command history
  • Tab completion works for commands
  • Rigorous mode saves CIF files and generates HTML visualisations
"""

EXAMPLE_QUERIES = [
    "Design a high-capacity cathode for lithium-ion batteries",
    "Find non-toxic semiconductors for solar cells",
    "Create lead-free ferroelectric materials",
    "Suggest magnetic materials for data storage",
    "Design transparent conductors for displays",
    "Find superconducting materials",
    "Create lightweight structural alloys",
    "Design thermoelectric materials",
    "Find photocatalysts for water splitting",
    "Create multiferroic materials"
]


class CrystaLyseShell:
    """
    Interactive shell for CrystaLyse.AI materials discovery.
    
    Provides a conversational interface with session management,
    command history, and real-time analysis capabilities.
    """
    
    def __init__(self):
        self.console = Console()
        self.history_file = Path.home() / '.crystalyse_history'
        self.history = FileHistory(str(self.history_file))
        self.mode = 'rigorous'
        self.current_structures = []  # Store multiple structures
        self.current_compositions = []  # Store compositions from latest analysis
        self.current_result = None
        self.session_history: List[Dict[str, Any]] = []
        self.agent: Optional[CrystaLyseUnifiedAgent] = None
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Simplified for unified agent (no visualisation dependencies for now)
        # self.storage = StructureStorage(Path.cwd() / "crystalyse_storage")
        # self.visualiser = CrystalVisualiser(backend="py3dmol")
        
        # Command completer
        commands = [
            '/help', '/mode', '/view', '/export', '/history', 
            '/clear', '/status', '/examples', '/exit'
        ]
        self.completer = WordCompleter(commands + EXAMPLE_QUERIES)
        
    async def initialise_agent(self) -> bool:
        """Initialise the unified CrystaLyse agent."""
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            self.console.print("[red]Error: OpenAI API key not found![/red]")
            self.console.print("Set OPENAI_API_KEY environment variable.")
            return False
            
        try:
            # Configure agent based on mode
            if self.mode == 'rigorous':
                agent_config = AgentConfig(
                    model="o4-mini",
                    mode="rigorous",
                    temperature=0.3,
                    enable_smact=True,
                    enable_chemeleon=True,
                    enable_mace=True,
                    max_turns=20
                )
            else:  # creative mode
                agent_config = AgentConfig(
                    model="o4-mini",
                    mode="creative", 
                    temperature=0.7,
                    enable_smact=False,  # Knowledge-based only
                    enable_chemeleon=False,
                    enable_mace=False,
                    max_turns=15
                )
            
            self.agent = CrystaLyseUnifiedAgent(agent_config)
            return True
        except Exception as e:
            self.console.print(f"[red]Error initialising unified agent: {e}[/red]")
            return False
    
    async def start(self):
        """Start the interactive shell."""
        # Create dynamic banner with current mode
        dynamic_banner = BANNER.replace("Mode: rigorous", f"Mode: {self.mode}")
        self.console.print(dynamic_banner, style="cyan")
        
        # Initialise agent quietly
        if not await self.initialise_agent():
            return
        
        # Main interaction loop
        while True:
            try:
                # Get user input with prompt
                mode_emoji = "[R]" if self.mode == "rigorous" else "[C]"
                user_input = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: prompt(
                        f'{mode_emoji} crystalyse ({self.mode}) > ',
                        history=self.history,
                        auto_suggest=AutoSuggestFromHistory(),
                        completer=self.completer,
                    )
                )
                
                if not user_input.strip():
                    continue
                    
                if user_input.strip().startswith('/'):
                    await self.handle_command(user_input.strip())
                else:
                    await self.analyse_query(user_input.strip())
                    
            except KeyboardInterrupt:
                self.console.print("\n[yellow]Analysis interrupted. Type /exit to quit.[/yellow]")
                continue
            except EOFError:
                break
                
        self.console.print("\n[cyan]Goodbye! Happy materials discovery![/cyan]")
    
    async def handle_command(self, command: str):
        """Handle shell commands."""
        parts = command.split()
        cmd = parts[0].lower()
        
        if cmd == '/help':
            self.console.print(Panel(HELP_TEXT, title="Help", border_style="blue"))
            
        elif cmd == '/mode':
            if len(parts) > 1:
                new_mode = parts[1].lower()
                if new_mode in ['creative', 'rigorous']:
                    if new_mode != self.mode:
                        self.mode = new_mode
                        # Reinitialise agent with new mode settings
                        self.console.print(f"[yellow]Switching to {self.mode} mode...[/yellow]")
                        if await self.initialise_agent():
                            self.console.print(f"[green]Mode set to: {self.mode}[/green]")
                            if self.mode == 'rigorous':
                                self.console.print("[cyan]Rigorous mode: SMACT validation + MACE energy calculations enabled[/cyan]")
                            else:
                                self.console.print("[cyan]Creative mode: AI-driven exploration with chemical intuition[/cyan]")
                        else:
                            self.console.print("[red]Failed to initialise agent for new mode[/red]")
                    else:
                        self.console.print(f"[yellow]Already in {self.mode} mode[/yellow]")
                else:
                    self.console.print("[red]Invalid mode. Use 'creative' or 'rigorous'[/red]")
            else:
                self.console.print(f"[cyan]Current mode: {self.mode}[/cyan]")
                self.console.print("Available modes:")
                self.console.print("  • rigorous - SMACT validation + MACE energy calculations")
                self.console.print("  • creative - AI-driven exploration with chemical intuition")
                
        elif cmd == '/view':
            # Handle optional composition argument
            composition = parts[1] if len(parts) > 1 else None
            await self.view_structure(composition)
            
        elif cmd == '/export':
            filename = parts[1] if len(parts) > 1 else f"crystalyse_session_{self.session_id}.json"
            await self.export_session(filename)
            
        elif cmd == '/history':
            self.show_history()
            
        elif cmd == '/clear':
            os.system('clear' if os.name == 'posix' else 'cls')
            self.console.print(BANNER, style="cyan")
            
        elif cmd == '/status':
            self.show_status()
            
        elif cmd == '/examples':
            self.show_examples()
            
        elif cmd == '/exit':
            if self.session_history:
                self.console.print("[yellow]Save session before exiting? (y/n)[/yellow]")
                try:
                    # Simple input without confirm() to avoid asyncio conflicts
                    save_choice = input().strip().lower()
                    if save_choice in ['y', 'yes']:
                        await self.export_session(f"crystalyse_session_{self.session_id}.json")
                except EOFError:
                    pass  # User pressed Ctrl+D, just exit
            raise EOFError
            
        else:
            self.console.print(f"[red]Unknown command: {cmd}[/red]")
            self.console.print("Type /help for available commands")
    
    async def analyse_query(self, query: str):
        """Analyse a materials discovery query."""
        if not self.agent:
            self.console.print("[red]Agent not initialised[/red]")
            return
            
        # Display query
        self.console.print(Panel(query, title=f"Query ({self.mode} mode)", border_style="blue"))
        
        # Run analysis with progress
        try:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                console=self.console
            ) as progress:
                task = progress.add_task(f"Analysing query in {self.mode} mode...", total=None)
                
                result = await self.agent.discover_materials(query, trace_workflow=False)
                progress.remove_task(task)
                
            # Store results
            self.current_result = result
            if result and isinstance(result, dict) and 'structure' in result:
                self.current_structure = result['structure']
                
            # Add to session history
            self.session_history.append({
                'timestamp': datetime.now().isoformat(),
                'query': query,
                'mode': self.mode,
                'result': result
            })
            
            # Display results
            await self.display_results(result)
            
        except Exception as e:
            import traceback
            self.console.print(f"[red]Analysis failed: {e}[/red]")
            self.console.print(f"[dim]Error type: {type(e).__name__}[/dim]")
            # In debug mode, show more details
            if os.getenv("CRYSTALYSE_DEBUG", "false").lower() == "true":
                self.console.print(f"[dim]Traceback: {traceback.format_exc()}[/dim]")
    
    async def display_results(self, result):
        """Display analysis results from unified agent."""
        if not result:
            self.console.print("[yellow]No results returned[/yellow]")
            return
        
        # Handle unified agent response format
        if isinstance(result, dict):
            if result.get('status') == 'completed':
                discovery_result = result.get('discovery_result', '')
                self.console.print(Panel(
                    str(discovery_result), 
                    title="Materials Discovery Results", 
                    border_style="green"
                ))
                
                # Display metrics
                metrics = result.get('metrics', {})
                if metrics:
                    self.console.print(f"\n[dim]Completed in {metrics.get('elapsed_time', 0):.2f}s using {metrics.get('model', 'unknown')} in {metrics.get('mode', 'unknown')} mode[/dim]")
                    
            elif result.get('status') == 'failed':
                error_msg = result.get('error', 'Unknown error')
                self.console.print(Panel(
                    f"Analysis failed: {error_msg}", 
                    title="Error", 
                    border_style="red"
                ))
            else:
                # Fallback display
                self.console.print(Panel(
                    str(result), 
                    title="Analysis Results", 
                    border_style="yellow"
                ))
        else:
            # String result
            self.console.print(Panel(
                str(result), 
                title="Analysis Results", 
                border_style="green"
            ))
            
    async def _extract_and_store_structures(self, result_text: str):
        """Extract structures and compositions from agent result text."""
        import re
        
        # Try to extract compositions from the text
        # Look for common chemical formula patterns
        composition_patterns = [
            r'\b([A-Z][a-z]?(?:\d+)?(?:[A-Z][a-z]?(?:\d+)?)*)\b',  # Basic chemical formulas
            r'#### \d+\.\s*([A-Z][a-z]?\d*(?:[A-Z][a-z]?\d*)*)',  # Numbered section headers
            r'(?:formula|composition|compound)[:=\s]+([A-Z][a-z]?\d*(?:[A-Z][a-z]?\d*)*)',  # Explicit mentions
        ]
        
        found_compositions = set()
        for pattern in composition_patterns:
            matches = re.findall(pattern, result_text, re.IGNORECASE)
            for match in matches:
                # Filter out common false positives
                if (len(match) >= 2 and 
                    not match.isdigit() and 
                    any(c.isupper() for c in match) and
                    match not in ['PDF', 'CSP', 'DFT', 'MACE', 'CIF', 'API']):
                    found_compositions.add(match)
        
        # Filter to likely chemical compositions
        valid_compositions = []
        for comp in found_compositions:
            if self._is_likely_composition(comp):
                valid_compositions.append(comp)
        
        self.current_compositions = valid_compositions[:5]  # Limit to 5
        
        # Try to extract CIF data if present in the result
        # Look for CIF-like content or structure data
        cif_pattern = r'data_\w+\s+_cell_length_a\s+[\d\.]+'
        
        if re.search(cif_pattern, result_text, re.DOTALL):
            # Direct CIF content found
            cif_matches = re.findall(r'(data_\w+.*?)(?=data_\w+|\Z)', result_text, re.DOTALL)
            for i, cif_content in enumerate(cif_matches):
                if len(self.current_compositions) > i:
                    structure_dict = {
                        'cif': cif_content.strip(),
                        'formula': self.current_compositions[i],
                        'structure': {},  # Would need proper parsing for MACE
                        'analysis': self._extract_structure_analysis(result_text, i)
                    }
                    self.current_structures.append(structure_dict)
        else:
            # No direct CIF, but we have compositions - try to generate placeholder structures
            # This will allow the /view command to work by regenerating structures
            for comp in self.current_compositions:
                structure_dict = {
                    'composition': comp,
                    'formula': comp,
                    'placeholder': True,  # Mark as placeholder
                    'analysis': self._extract_structure_analysis(result_text, len(self.current_structures))
                }
                self.current_structures.append(structure_dict)
        
        # Store structures if we have any
        if self.current_structures and self.current_compositions:
            await self._store_extracted_structures()
    
    def _is_likely_composition(self, comp: str) -> bool:
        """Check if string is likely a chemical composition."""
        if len(comp) < 2 or len(comp) > 15:
            return False
        
        # Must start with uppercase
        if not comp[0].isupper():
            return False
        
        # Must have at least one more element (another uppercase letter)
        if not any(c.isupper() for c in comp[1:]):
            return False
        
        # Common element symbols
        elements = ['H', 'He', 'Li', 'Be', 'B', 'C', 'N', 'O', 'F', 'Ne', 'Na', 'Mg', 'Al', 'Si', 'P', 'S', 'Cl', 'Ar', 'K', 'Ca', 'Sc', 'Ti', 'V', 'Cr', 'Mn', 'Fe', 'Co', 'Ni', 'Cu', 'Zn', 'Ga', 'Ge', 'As', 'Se', 'Br', 'Kr', 'Rb', 'Sr', 'Y', 'Zr', 'Nb', 'Mo', 'Tc', 'Ru', 'Rh', 'Pd', 'Ag', 'Cd', 'In', 'Sn', 'Sb', 'Te', 'I', 'Xe', 'Cs', 'Ba', 'La', 'Ce', 'Pr', 'Nd', 'Pm', 'Sm', 'Eu', 'Gd', 'Tb', 'Dy', 'Ho', 'Er', 'Tm', 'Yb', 'Lu', 'Hf', 'Ta', 'W', 'Re', 'Os', 'Ir', 'Pt', 'Au', 'Hg', 'Tl', 'Pb', 'Bi', 'Po', 'At', 'Rn', 'Fr', 'Ra', 'Ac', 'Th', 'Pa', 'U', 'Np', 'Pu']
        
        # Extract potential element symbols
        import re
        potential_elements = re.findall(r'[A-Z][a-z]?', comp)
        valid_elements = sum(1 for elem in potential_elements if elem in elements)
        
        return valid_elements >= len(potential_elements) * 0.7  # At least 70% valid elements
    
    def _extract_structure_analysis(self, text: str, structure_index: int) -> Dict:
        """Extract structure analysis from text."""
        # Look for lattice parameters, space group, etc.
        import re
        
        analysis = {}
        
        # Try to find space group
        sg_pattern = r'Space Group:\s*(\w+)'
        sg_matches = re.findall(sg_pattern, text)
        if len(sg_matches) > structure_index:
            analysis['space_group'] = sg_matches[structure_index]
        
        # Try to find lattice parameters
        lattice_pattern = r'a\s*=\s*([\d\.]+)\s*Å.*?b\s*=\s*([\d\.]+)\s*Å.*?c\s*=\s*([\d\.]+)\s*Å'
        lattice_matches = re.findall(lattice_pattern, text, re.DOTALL)
        if len(lattice_matches) > structure_index:
            a, b, c = lattice_matches[structure_index]
            analysis['lattice'] = {'a': float(a), 'b': float(b), 'c': float(c)}
        
        return analysis
    
    async def _store_extracted_structures(self):
        """Store extracted structures using the storage system."""
        try:
            for i, comp in enumerate(self.current_compositions):
                if i < len(self.current_structures):
                    structures_for_comp = [self.current_structures[i]]
                    
                    # Store structures
                    self.storage.store_structures(
                        composition=comp,
                        structures=structures_for_comp,
                        analysis_params={
                            'model': self.agent.model if self.agent else 'unknown',
                            'mode': self.mode,
                            'session_id': self.session_id,
                            'temperature': self.agent.temperature if self.agent else 0.7
                        },
                        session_id=self.session_id
                    )
                    
                    # Generate HTML report if we have actual structure data
                    if not structures_for_comp[0].get('placeholder', False):
                        html_content = self.visualiser.create_multi_structure_report(
                            structures_for_comp, comp
                        )
                        self.storage.store_visualisation_report(comp, html_content)
                    
        except Exception as e:
            self.console.print(f"[yellow]Warning: Could not store structures: {e}[/yellow]")
    
    async def view_structure(self, composition: str = None):
        """Open structure viewer for specified composition or latest structures."""
        try:
            # Determine which structures to view
            if composition:
                # View specific composition
                structures = self.storage.get_structures_for_composition(composition)
                if not structures:
                    self.console.print(f"[yellow]No structures found for {composition}[/yellow]")
                    # Try to regenerate structures for this composition
                    await self._regenerate_structures_for_composition(composition)
                    return
                target_composition = composition
            else:
                # View latest structures from current session
                if not self.current_compositions:
                    self.console.print("[yellow]No structures available. Run an analysis first.[/yellow]")
                    return
                
                # Use the first composition from the latest analysis
                target_composition = self.current_compositions[0]
                structures = self.storage.get_structures_for_composition(target_composition)
                
                if not structures and self.current_structures:
                    # Use in-memory structures if storage doesn't have them yet
                    structures = [s for s in self.current_structures if s.get('composition') == target_composition or s.get('formula') == target_composition]
            
            if not structures:
                self.console.print("[yellow]No structure data available for visualisation.[/yellow]")
                return
            
            # Check if we need to regenerate structures (if they're placeholders)
            structure_to_view = structures[0]
            if structure_to_view.get('placeholder', False) or 'cif' not in structure_to_view:
                await self._regenerate_structures_for_composition(target_composition)
                return
            
            # Generate HTML viewer
            html_content = self._generate_structure_viewer(structures, target_composition)
            
            # Save to temporary file and open
            with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as f:
                f.write(html_content)
                temp_path = f.name
                
            webbrowser.open(f'file://{temp_path}')
            self.console.print(f"[green]Structure viewer opened in browser for {target_composition}[/green]")
            self.console.print(f"[dim]Structures: {len(structures)} | File: {temp_path}[/dim]")
            
        except Exception as e:
            self.console.print(f"[red]Error opening structure viewer: {e}[/red]")
            import traceback
            if os.getenv("CRYSTALYSE_DEBUG", "false").lower() == "true":
                self.console.print(f"[dim]Traceback: {traceback.format_exc()}[/dim]")
    
    async def _regenerate_structures_for_composition(self, composition: str):
        """Regenerate crystal structures for a specific composition."""
        self.console.print(f"[yellow]Generating crystal structures for {composition}...[/yellow]")
        
        try:
            # Use Chemeleon to generate structures directly
            query = f"Generate 3 crystal structures for {composition} using Chemeleon CSP tools. Include CIF data for visualisation."
            
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=self.console
            ) as progress:
                task = progress.add_task(f"Generating structures for {composition}...", total=None)
                
                # Run the agent to generate structures
                result = await self.agent.analyse(query)
                progress.remove_task(task)
            
            # Extract CIF data from the result
            await self._extract_and_store_structures(result)
            
            # Try to view the structures again
            structures = self.storage.get_structures_for_composition(composition)
            if structures and not structures[0].get('placeholder', False):
                html_content = self._generate_structure_viewer(structures, composition)
                
                with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as f:
                    f.write(html_content)
                    temp_path = f.name
                    
                webbrowser.open(f'file://{temp_path}')
                self.console.print(f"[green]Structure viewer opened for {composition}[/green]")
            else:
                self.console.print(f"[yellow]Could not generate viewable structures for {composition}[/yellow]")
                
        except Exception as e:
            self.console.print(f"[red]Error generating structures: {e}[/red]")
    
    def _generate_structure_viewer(self, structures: List[Dict], composition: str) -> str:
        """Generate HTML viewer for structures."""
        if len(structures) == 1 and 'cif' in structures[0]:
            # Single structure - use simple viewer
            return generate_crystal_viewer(structures[0]['cif'], composition)
        else:
            # Multiple structures - use comprehensive report
            return self.visualiser.create_multi_structure_report(structures, composition)
    
    async def export_session(self, filename: str):
        """Export the current session to a JSON file."""
        if not self.session_history:
            self.console.print("[yellow]No analysis history to export[/yellow]")
            return
            
        try:
            export_data = {
                'session_id': self.session_id,
                'export_time': datetime.now().isoformat(),
                'mode': self.mode,
                'total_queries': len(self.session_history),
                'history': self.session_history
            }
            
            with open(filename, 'w') as f:
                json.dump(export_data, f, indent=2, default=str)
                
            self.console.print(f"[green]Session exported to: {filename}[/green]")
            
        except Exception as e:
            self.console.print(f"[red]Export failed: {e}[/red]")
    
    def show_history(self):
        """Display analysis history."""
        if not self.session_history:
            self.console.print("[yellow]No analysis history[/yellow]")
            return
            
        history_table = Table(title="Analysis History")
        history_table.add_column("Time", style="cyan")
        history_table.add_column("Mode", style="yellow")
        history_table.add_column("Query", style="green")
        history_table.add_column("Composition", style="magenta")
        
        for entry in self.session_history[-10:]:  # Show last 10
            timestamp = datetime.fromisoformat(entry['timestamp']).strftime("%H:%M:%S")
            query = entry['query'][:50] + "..." if len(entry['query']) > 50 else entry['query']
            composition = entry['result'].get('composition', 'N/A') if entry['result'] else 'N/A'
            
            history_table.add_row(timestamp, entry['mode'], query, str(composition))
            
        self.console.print(history_table)
    
    def show_status(self):
        """Display system status."""
        rate_limits = verify_rate_limits()
        
        status_table = Table(title="CrystaLyse.AI Status")
        status_table.add_column("Component", style="cyan")
        status_table.add_column("Status", style="green")
        
        # API Status
        api_status = "Connected" if rate_limits["mdg_api_configured"] else "Not configured"
        status_table.add_row("API Connection", api_status)
        
        # Agent status and configuration
        if self.agent:
            config = self.agent.get_agent_configuration()
            mode_desc = f"[R] {self.mode}" if self.mode == "rigorous" else f"[C] {self.mode}"
            if config.get('use_chem_tools'):
                mode_desc += " + SMACT"
            if config.get('enable_mace'):
                mode_desc += " + MACE"
            status_table.add_row("Analysis Agent", "Ready")
            status_table.add_row("Current Mode", mode_desc)
        else:
            status_table.add_row("Analysis Agent", "Not initialised")
            status_table.add_row("Current Mode", f"[R] {self.mode}" if self.mode == "rigorous" else f"[C] {self.mode}")
        
        # Session info
        status_table.add_row("Session ID", self.session_id)
        status_table.add_row("Queries This Session", str(len(self.session_history)))
        
        # Structure storage status
        storage_stats = self.storage.get_storage_stats()
        status_table.add_row("Stored Compositions", str(storage_stats['total_compositions']))
        status_table.add_row("Total Structures", str(storage_stats['total_structures']))
        status_table.add_row("CIF Files", str(storage_stats['total_cif_files']))
        
        # Current session structures
        current_structures = len(self.current_structures) if self.current_structures else 0
        current_comps = len(self.current_compositions) if self.current_compositions else 0
        status_table.add_row("Current Structures", f"{current_structures} structures, {current_comps} compositions")
        
        self.console.print(status_table)
        
        # Show available compositions if any
        if storage_stats['compositions']:
            comp_text = ", ".join(storage_stats['compositions'][-5:])  # Show last 5
            if len(storage_stats['compositions']) > 5:
                comp_text = f"...{comp_text} (showing latest 5)"
            self.console.print(f"\n[cyan]Available compositions: {comp_text}[/cyan]")
            self.console.print("[dim]Use /view [composition] to visualise specific structures[/dim]")
    
    def show_examples(self):
        """Display example queries."""
        self.console.print(Panel(
            "\n".join(f"• {example}" for example in EXAMPLE_QUERIES),
            title="Example Queries",
            border_style="blue"
        ))


def main():
    """Main entry point for the interactive shell."""
    shell = CrystaLyseShell()
    asyncio.run(shell.start())


if __name__ == '__main__':
    main()