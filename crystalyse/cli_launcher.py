#!/usr/bin/env python3
"""
CrystaLyse.AI CLI Launcher
This module launches the new TypeScript/Node.js based interactive CLI
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path


def find_node():
    """Find node executable in the system."""
    node = shutil.which('node')
    if not node:
        print("Error: Node.js is not installed or not in PATH")
        print("Please install Node.js 16+ from https://nodejs.org/")
        sys.exit(1)
    return node


def find_cli_directory():
    """Find the crystalyse-cli directory."""
    # Try multiple locations
    possible_paths = [
        # Relative to this file
        Path(__file__).parent.parent / 'crystalyse-cli',
        # Development path
        Path.cwd() / 'crystalyse-cli',
        # Installed path
        Path(__file__).parent.parent / 'crystalyse-cli',
    ]
    
    for path in possible_paths:
        if path.exists() and (path / 'dist' / 'index.js').exists():
            return path
    
    # If not found, check if we need to build
    for path in possible_paths:
        if path.exists() and (path / 'src' / 'index.ts').exists():
            print(f"CLI found at {path} but not built. Building...")
            build_cli(path)
            if (path / 'dist' / 'index.js').exists():
                return path
    
    print("Error: crystalyse-cli not found!")
    print("Make sure the CLI is properly installed.")
    sys.exit(1)


def build_cli(cli_path):
    """Build the TypeScript CLI if needed."""
    try:
        # Install dependencies if needed
        if not (cli_path / 'node_modules').exists():
            print("Installing CLI dependencies...")
            subprocess.run(['npm', 'install'], cwd=cli_path, check=True)
        
        # Build the CLI
        print("Building CLI...")
        subprocess.run(['npm', 'run', 'build'], cwd=cli_path, check=True)
        print("CLI built successfully!")
    except subprocess.CalledProcessError as e:
        print(f"Error building CLI: {e}")
        sys.exit(1)


def main():
    """Main entry point for CrystaLyse CLI."""
    # Find node and CLI directory
    node = find_node()
    cli_dir = find_cli_directory()
    cli_script = cli_dir / 'dist' / 'index.js'
    
    # Pass all arguments to the Node.js CLI
    args = [node, str(cli_script)] + sys.argv[1:]
    
    # Set environment variables
    env = os.environ.copy()
    env['NODE_ENV'] = env.get('NODE_ENV', 'production')
    
    # Launch the CLI
    try:
        result = subprocess.run(args, env=env)
        sys.exit(result.returncode)
    except KeyboardInterrupt:
        sys.exit(0)
    except Exception as e:
        print(f"Error launching CrystaLyse CLI: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()