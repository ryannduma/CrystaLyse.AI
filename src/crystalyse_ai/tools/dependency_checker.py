"""Dependency checker for CrystaLyse.AI - verifies and installs required components."""

import importlib
import json
import logging
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, List, Any, Optional

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.status import Status
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn

logger = logging.getLogger(__name__)

class DependencyChecker:
    """Comprehensive dependency checker for CrystaLyse.AI."""
    
    def __init__(self, console: Optional[Console] = None):
        self.console = console or Console()
        self.results = {
            "python_packages": {},
            "chemeleon": {"status": "unknown", "details": {}},
            "checkpoints": {"status": "unknown", "details": {}},
            "mcp_servers": {"status": "unknown", "details": {}},
            "overall": {"status": "unknown", "issues": []}
        }
    
    def check_all_dependencies(self, install_missing: bool = False, verbose: bool = False) -> Dict[str, Any]:
        """Check all dependencies and optionally install missing components."""
        
        # Temporarily suppress noisy import warnings during dependency checking
        import_logger = logging.getLogger("crystalyse_ai")
        original_level = import_logger.level
        if not verbose:
            import_logger.setLevel(logging.ERROR)
        
        try:
            return self._check_all_dependencies_impl(install_missing, verbose)
        finally:
            # Restore original logging level
            import_logger.setLevel(original_level)
    
    def _check_all_dependencies_impl(self, install_missing: bool = False, verbose: bool = False) -> Dict[str, Any]:
        """Internal implementation of dependency checking."""
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=self.console
        ) as progress:
            
            main_task = progress.add_task("Checking dependencies...", total=4)
            
            # 1. Check Python packages
            progress.update(main_task, description="Checking Python packages...")
            self._check_python_packages()
            progress.advance(main_task)
            
            # 2. Check Chemeleon installation
            progress.update(main_task, description="Checking Chemeleon installation...")
            self._check_chemeleon_installation(install_missing, verbose)
            progress.advance(main_task)
            
            # 3. Check checkpoints
            progress.update(main_task, description="Checking model checkpoints...")
            self._check_checkpoints(install_missing, verbose)
            progress.advance(main_task)
            
            # 4. Check MCP servers
            progress.update(main_task, description="Checking MCP servers...")
            self._check_mcp_servers()
            progress.advance(main_task)
        
        # Determine overall status
        self._determine_overall_status()
        
        return self.results
    
    def _check_python_packages(self):
        """Check all required Python packages."""
        required_packages = [
            # Core AI and Agent Framework
            "openai",
            "openai-agents",
            
            # Chemistry Core Libraries
            "rdkit",
            "pymatgen",
            "ase",
            
            # AI-Powered Chemistry Tools
            "smact",
            "torch",
            "mace-torch",
            "git",  # gitpython
            
            # Model Context Protocol
            "fastmcp",
            
            # Data Processing
            "numpy",
            "pandas",
            "scipy",
            
            # Type Safety and Validation
            "pydantic",
            
            # CLI and UI
            "click",
            "rich",
            "prompt_toolkit",
            
            # Async and Networking
            "httpx",
            "websockets",
            
            # File and Data Handling
            "yaml",  # PyYAML
            "toml",
            "dotenv",  # python-dotenv
            
            # MCP Server Dependencies
            "uvicorn",
            "fastapi",
            "starlette",
        ]
        
        for package in required_packages:
            try:
                # Handle package name variations
                if package == "openai-agents":
                    import_name = "agents"  # pip: openai-agents, import: agents
                elif package == "git":
                    import_name = "git"  # gitpython
                elif package == "yaml":
                    import_name = "yaml"  # PyYAML
                elif package == "dotenv":
                    import_name = "dotenv"  # python-dotenv
                elif package == "mace-torch":
                    import_name = "mace"  # pip: mace-torch, import: mace
                else:
                    import_name = package
                
                module = importlib.import_module(import_name)
                # Use importlib.metadata for version detection to avoid deprecation warnings
                try:
                    from importlib import metadata
                    # Handle package name variations for metadata lookup
                    metadata_name = package
                    if package == "openai-agents":
                        metadata_name = "openai-agents"
                    elif package == "mace-torch":
                        metadata_name = "mace-torch"
                    elif package == "git":
                        metadata_name = "gitpython"
                    
                    version = metadata.version(metadata_name)
                except (metadata.PackageNotFoundError, Exception):
                    # Fallback to __version__ attribute
                    version = getattr(module, "__version__", "unknown")
                
                self.results["python_packages"][package] = {
                    "status": "available",
                    "version": version
                }
                
            except ImportError as e:
                self.results["python_packages"][package] = {
                    "status": "missing",
                    "error": str(e)
                }
    
    def _check_chemeleon_installation(self, install_missing: bool, verbose: bool):
        """Check Chemeleon installation and install if missing."""
        try:
            from crystalyse_ai.tools.chemeleon_installer import (
                is_chemeleon_installed,
                ensure_chemeleon_available,
                get_chemeleon_install_dir
            )
            
            install_dir = get_chemeleon_install_dir()
            
            if is_chemeleon_installed():
                self.results["chemeleon"] = {
                    "status": "available",
                    "details": {
                        "install_directory": str(install_dir),
                        "installed": True
                    }
                }
            else:
                if install_missing:
                    self.console.print("[yellow]Installing Chemeleon (first-time setup)...[/yellow]")
                    
                    with Status("[bold cyan]Installing Chemeleon from GitHub...", console=self.console):
                        try:
                            ensure_chemeleon_available()
                            self.results["chemeleon"] = {
                                "status": "installed",
                                "details": {
                                    "install_directory": str(install_dir),
                                    "installed": True,
                                    "action": "newly_installed"
                                }
                            }
                            self.console.print("[green]✅ Chemeleon installed successfully![/green]")
                        except Exception as e:
                            self.results["chemeleon"] = {
                                "status": "failed",
                                "details": {
                                    "error": str(e),
                                    "install_directory": str(install_dir)
                                }
                            }
                            self.console.print(f"[red]❌ Chemeleon installation failed: {e}[/red]")
                else:
                    self.results["chemeleon"] = {
                        "status": "missing",
                        "details": {
                            "install_directory": str(install_dir),
                            "installed": False,
                            "note": "Use --install to automatically install"
                        }
                    }
                    
        except ImportError as e:
            self.results["chemeleon"] = {
                "status": "error",
                "details": {
                    "error": f"Chemeleon installer not available: {e}"
                }
            }
    
    def _check_checkpoints(self, install_missing: bool, verbose: bool):
        """Check if Chemeleon checkpoints are available."""
        try:
            from crystalyse_ai.tools.chemeleon_installer import (
                is_chemeleon_installed,
                get_chemeleon_install_dir
            )
            
            if not is_chemeleon_installed():
                self.results["checkpoints"] = {
                    "status": "unavailable",
                    "details": {
                        "reason": "Chemeleon not installed"
                    }
                }
                return
            
            # Try to trigger checkpoint download
            if install_missing:
                self.console.print("[yellow]Checking/downloading model checkpoints...[/yellow]")
                
                self.console.print("[yellow]Downloading checkpoints (this may take a while)...[/yellow]")
                try:
                    # Import and use Chemeleon to trigger checkpoint download
                    from crystalyse_ai.tools.chemeleon import _load_model, _ensure_checkpoints_in_correct_location
                    
                    # Ensure checkpoints are downloaded to correct location
                    _ensure_checkpoints_in_correct_location()
                    
                    # This will download checkpoints if they don't exist
                    model = _load_model(task="csp", prefer_gpu=False)
                    
                    self.results["checkpoints"] = {
                        "status": "available",
                        "details": {
                            "downloaded": True,
                            "action": "verified_and_downloaded"
                        }
                    }
                    self.console.print("[green]✅ Model checkpoints ready![/green]")
                    
                except Exception as e:
                    self.results["checkpoints"] = {
                        "status": "failed",
                        "details": {
                            "error": str(e),
                            "note": "Checkpoint download failed"
                        }
                    }
                    self.console.print(f"[red]❌ Checkpoint download failed: {e}[/red]")
            else:
                # Just check if checkpoints exist without downloading
                try:
                    from crystalyse_ai.tools.chemeleon import get_checkpoint_path
                    # Use user-portable checkpoint directory
                    checkpoint_dir = Path.home() / ".crystalyse" / "checkpoints"
                    default_paths = {
                        "csp": str(checkpoint_dir / "chemeleon_csp_alex_mp_20_v0.0.2.ckpt"),
                        "dng": str(checkpoint_dir / "chemeleon_dng_alex_mp_20_v0.0.2.ckpt"),
                        "guide": "."
                    }
                    checkpoint_path = get_checkpoint_path(task="csp", default_paths=default_paths)
                    
                    if Path(checkpoint_path).exists():
                        self.results["checkpoints"] = {
                            "status": "available",
                            "details": {
                                "checkpoint_path": checkpoint_path,
                                "downloaded": True
                            }
                        }
                    else:
                        self.results["checkpoints"] = {
                            "status": "missing",
                            "details": {
                                "checkpoint_path": checkpoint_path,
                                "downloaded": False,
                                "note": "Use --install to download checkpoints"
                            }
                        }
                except Exception as e:
                    self.results["checkpoints"] = {
                        "status": "unknown",
                        "details": {
                            "error": str(e)
                        }
                    }
                    
        except ImportError as e:
            self.results["checkpoints"] = {
                "status": "error",
                "details": {
                    "error": f"Cannot check checkpoints: {e}"
                }
            }
    
    def _check_mcp_servers(self):
        """Check if MCP servers are available."""
        servers = ["creative", "unified", "visualization"]
        server_status = {}
        
        for server in servers:
            try:
                # Try to import the server module
                module_name = f"crystalyse_ai.mcp_servers.{server}.server"
                server_module = importlib.import_module(module_name)
                
                # Check if main function exists
                if hasattr(server_module, "main"):
                    server_status[server] = {
                        "status": "available",
                        "module": module_name
                    }
                else:
                    server_status[server] = {
                        "status": "error",
                        "error": "No main function found"
                    }
                    
            except ImportError as e:
                server_status[server] = {
                    "status": "missing",
                    "error": str(e)
                }
        
        # Determine overall MCP server status
        all_available = all(s["status"] == "available" for s in server_status.values())
        if all_available:
            self.results["mcp_servers"] = {
                "status": "available",
                "details": server_status
            }
        else:
            self.results["mcp_servers"] = {
                "status": "issues",
                "details": server_status
            }
    
    def _determine_overall_status(self):
        """Determine overall system status and collect issues."""
        issues = []
        
        # Check Python packages
        missing_packages = [
            pkg for pkg, info in self.results["python_packages"].items() 
            if info["status"] == "missing"
        ]
        if missing_packages:
            issues.append(f"Missing Python packages: {', '.join(missing_packages)}")
        
        # Check Chemeleon
        if self.results["chemeleon"]["status"] in ["missing", "failed", "error"]:
            issues.append("Chemeleon not properly installed")
        
        # Check checkpoints
        if self.results["checkpoints"]["status"] in ["missing", "failed", "unavailable"]:
            issues.append("Model checkpoints not available")
        
        # Check MCP servers
        if self.results["mcp_servers"]["status"] != "available":
            issues.append("MCP servers have issues")
        
        self.results["overall"] = {
            "status": "ready" if not issues else "issues",
            "issues": issues
        }
    
    def display_results(self, show_details: bool = False):
        """Display dependency check results in a formatted way."""
        
        # Overall status panel
        overall_status = self.results["overall"]["status"]
        if overall_status == "ready":
            status_text = Text("✅ All dependencies ready!", style="bold green")
        else:
            status_text = Text("⚠️ Issues found", style="bold yellow")
        
        self.console.print(Panel(
            status_text,
            title="[bold]CrystaLyse.AI Dependency Status[/bold]",
            border_style="green" if overall_status == "ready" else "yellow"
        ))
        
        # Issues summary
        if self.results["overall"]["issues"]:
            issues_text = "\n".join(f"• {issue}" for issue in self.results["overall"]["issues"])
            self.console.print(Panel(
                issues_text,
                title="[bold red]Issues Found[/bold red]",
                border_style="red"
            ))
        
        # Detailed results
        if show_details:
            self._display_detailed_results()
    
    def _display_detailed_results(self):
        """Display detailed dependency information."""
        
        # Python packages table
        package_table = Table(title="Python Packages")
        package_table.add_column("Package", style="cyan")
        package_table.add_column("Status", style="bold")
        package_table.add_column("Version/Error", style="dim")
        
        for package, info in self.results["python_packages"].items():
            status = info["status"]
            if status == "available":
                status_text = "✅ Available"
                version_text = info.get("version", "unknown")
            else:
                status_text = "❌ Missing"
                version_text = info.get("error", "")[:50] + "..."
            
            package_table.add_row(package, status_text, version_text)
        
        self.console.print(package_table)
        
        # Chemistry tools status
        tools_table = Table(title="Chemistry Tools")
        tools_table.add_column("Component", style="cyan")
        tools_table.add_column("Status", style="bold")
        tools_table.add_column("Details", style="dim")
        
        # Chemeleon status
        chemeleon_status = self.results["chemeleon"]["status"]
        if chemeleon_status == "available":
            tools_table.add_row("Chemeleon", "✅ Available", "Installed and ready")
        elif chemeleon_status == "installed":
            tools_table.add_row("Chemeleon", "✅ Installed", "Newly installed")
        elif chemeleon_status == "missing":
            tools_table.add_row("Chemeleon", "❌ Missing", "Not installed")
        else:
            tools_table.add_row("Chemeleon", "❌ Error", "Installation failed")
        
        # Checkpoints status
        checkpoint_status = self.results["checkpoints"]["status"]
        if checkpoint_status == "available":
            tools_table.add_row("Model Checkpoints", "✅ Available", "Downloaded and ready")
        elif checkpoint_status == "missing":
            tools_table.add_row("Model Checkpoints", "❌ Missing", "Not downloaded")
        else:
            tools_table.add_row("Model Checkpoints", "⚠️ Unknown", "Status unclear")
        
        # MCP servers status
        mcp_status = self.results["mcp_servers"]["status"]
        if mcp_status == "available":
            tools_table.add_row("MCP Servers", "✅ Available", "All servers ready")
        else:
            tools_table.add_row("MCP Servers", "⚠️ Issues", "Some servers missing")
        
        self.console.print(tools_table)


def check_dependencies(install_missing: bool = False, verbose: bool = False, show_details: bool = False) -> Dict[str, Any]:
    """
    Check all CrystaLyse.AI dependencies and optionally install missing components.
    
    Args:
        install_missing: If True, attempt to install missing components
        verbose: Enable verbose output
        show_details: Show detailed dependency information
    
    Returns:
        Dictionary containing dependency check results
    """
    console = Console()
    
    # Enhanced header
    console.print(Panel(
        Text.assemble(
            ("🔍 CrystaLyse.AI Dependency Checker\n\n", "bold cyan"),
            ("Verifying installation and downloading required components...", "dim")
        ),
        border_style="cyan"
    ))
    
    checker = DependencyChecker(console)
    results = checker.check_all_dependencies(install_missing, verbose)
    
    # Display results
    checker.display_results(show_details)
    
    # Summary message
    if results["overall"]["status"] == "ready":
        console.print("\n[bold green]🎉 CrystaLyse.AI is ready to use![/bold green]")
        console.print("[dim]You can now run 'crystalyse chat' or 'crystalyse analyse' commands.[/dim]")
    else:
        console.print("\n[bold yellow]⚠️ Some issues were found.[/bold yellow]")
        if not install_missing:
            console.print("[dim]Run 'crystalyse check --install' to automatically fix issues.[/dim]")
    
    return results


if __name__ == "__main__":
    # Allow direct execution for testing
    check_dependencies(install_missing=True, verbose=True, show_details=True)