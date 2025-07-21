"""Chemeleon installation utility for CrystaLyse.AI"""

import os
import subprocess
import sys
import logging
from pathlib import Path
import tempfile
import shutil

logger = logging.getLogger(__name__)

def get_chemeleon_install_dir():
    """Get the directory where Chemeleon should be installed."""
    # Install in user's home directory under .crystalyse
    install_dir = Path.home() / ".crystalyse" / "chemeleon-dng"
    return install_dir

def is_chemeleon_installed():
    """Check if Chemeleon is already installed."""
    install_dir = get_chemeleon_install_dir()
    
    # Check if the installation directory exists and has the expected structure
    if not install_dir.exists():
        return False
    
    # Check if we can import chemeleon_dng
    try:
        # Add to Python path temporarily
        sys.path.insert(0, str(install_dir))
        import chemeleon_dng
        return True
    except ImportError:
        return False
    finally:
        # Remove from path
        if str(install_dir) in sys.path:
            sys.path.remove(str(install_dir))

def install_chemeleon():
    """Install Chemeleon from GitHub if not already installed."""
    if is_chemeleon_installed():
        logger.info("Chemeleon is already installed")
        return True
    
    logger.info("Installing Chemeleon (first-time setup)...")
    
    try:
        install_dir = get_chemeleon_install_dir()
        install_dir.parent.mkdir(parents=True, exist_ok=True)
        
        # Clone the repository
        repo_url = "https://github.com/hspark1212/chemeleon-dng.git"
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_clone_dir = Path(temp_dir) / "chemeleon-dng"
            
            logger.info(f"Cloning Chemeleon from {repo_url}...")
            result = subprocess.run([
                "git", "clone", repo_url, str(temp_clone_dir)
            ], capture_output=True, text=True)
            
            if result.returncode != 0:
                logger.error(f"Failed to clone Chemeleon: {result.stderr}")
                return False
            
            # Move to final location
            if install_dir.exists():
                shutil.rmtree(install_dir)
            shutil.move(str(temp_clone_dir), str(install_dir))
            
            # Install the package in development mode
            logger.info("Installing Chemeleon package...")
            result = subprocess.run([
                sys.executable, "-m", "pip", "install", "-e", str(install_dir)
            ], capture_output=True, text=True)
            
            if result.returncode != 0:
                logger.error(f"Failed to install Chemeleon: {result.stderr}")
                return False
            
            logger.info("Chemeleon installed successfully!")
            return True
            
    except Exception as e:
        logger.error(f"Error installing Chemeleon: {e}")
        return False

def ensure_chemeleon_available():
    """Ensure Chemeleon is available, installing if necessary."""
    if not is_chemeleon_installed():
        success = install_chemeleon()
        if not success:
            raise ImportError(
                "Chemeleon is required but could not be installed automatically. "
                "Please install manually:\n"
                "git clone https://github.com/hspark1212/chemeleon-dng.git\n"
                "cd chemeleon-dng\n"
                "pip install -e ."
            )
    
    # Add to Python path if not already there
    install_dir = get_chemeleon_install_dir()
    if str(install_dir) not in sys.path:
        sys.path.insert(0, str(install_dir))

def import_chemeleon():
    """Import Chemeleon, installing if necessary."""
    ensure_chemeleon_available()
    
    try:
        from chemeleon_dng.diffusion.diffusion_module import DiffusionModule
        from chemeleon_dng.script_util import create_diffusion_module
        from chemeleon_dng.download_util import get_checkpoint_path
        
        return DiffusionModule, create_diffusion_module, get_checkpoint_path
    except ImportError as e:
        raise ImportError(f"Failed to import Chemeleon after installation: {e}")