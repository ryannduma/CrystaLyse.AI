#!/usr/bin/env python3
"""Debug script to test Chemeleon MCP server startup and basic functionality."""

import sys
import os
from pathlib import Path

# Add paths
sys.path.insert(0, str(Path(__file__).parent / "chemeleon-mcp-server" / "src"))
sys.path.insert(0, str(Path(__file__).parent / "chemeleon-dng"))

def test_imports():
    """Test that all required imports work."""
    print("Testing imports...")
    
    try:
        import torch
        print(f"✓ PyTorch {torch.__version__}")
        print(f"  - CUDA available: {torch.cuda.is_available()}")
        if torch.cuda.is_available():
            print(f"  - CUDA device: {torch.cuda.get_device_name(0)}")
    except ImportError as e:
        print(f"✗ PyTorch import failed: {e}")
        return False
    
    try:
        import ase
        print(f"✓ ASE {ase.__version__}")
    except ImportError as e:
        print(f"✗ ASE import failed: {e}")
        return False
    
    try:
        import pymatgen
        print(f"✓ Pymatgen {pymatgen.__version__}")
    except ImportError as e:
        print(f"✗ Pymatgen import failed: {e}")
        return False
    
    try:
        import mcp
        print(f"✓ MCP")
    except ImportError as e:
        print(f"✗ MCP import failed: {e}")
        return False
    
    try:
        from chemeleon_dng.diffusion.diffusion_module import DiffusionModule
        print("✓ Chemeleon DiffusionModule")
    except ImportError as e:
        print(f"✗ Chemeleon import failed: {e}")
        return False
    
    try:
        from chemeleon_mcp.server import mcp, SERVER_NAME, SERVER_VERSION
        print(f"✓ Chemeleon MCP Server: {SERVER_NAME} v{SERVER_VERSION}")
    except ImportError as e:
        print(f"✗ Chemeleon MCP Server import failed: {e}")
        return False
    
    return True

def test_tool_registration():
    """Test that tools are properly registered."""
    print("\nTesting tool registration...")
    
    try:
        from chemeleon_mcp.server import mcp
        import chemeleon_mcp.tools  # This registers the tools
        
        # Get registered tools
        tools = []
        if hasattr(mcp, '_tools'):
            tools = list(mcp._tools.keys())
        elif hasattr(mcp, 'list_tools'):
            tools = mcp.list_tools()
        
        expected_tools = [
            'generate_crystal_csp',
            'analyse_structure',
            'get_model_info',
            'clear_model_cache'
        ]
        
        print(f"Registered tools: {tools}")
        
        for tool in expected_tools:
            if tool in tools:
                print(f"✓ {tool}")
            else:
                print(f"✗ {tool} not found")
        
        return len(tools) >= len(expected_tools)
        
    except Exception as e:
        print(f"✗ Tool registration test failed: {e}")
        return False

def test_model_loading():
    """Test basic model loading functionality."""
    print("\nTesting model loading (this may download models)...")
    
    try:
        from chemeleon_mcp.tools import _get_device, get_model_info
        import json
        
        device = _get_device(prefer_gpu=False)
        print(f"Device (CPU default): {device}")
        
        # Test that CPU is default
        if device != "cpu":
            print("⚠️  Warning: Expected CPU as default device")
        
        # Also test GPU preference
        gpu_device = _get_device(prefer_gpu=True)
        print(f"Device (GPU preferred): {gpu_device}")
        
        # Get model info
        info_str = get_model_info()
        info = json.loads(info_str)
        
        print(f"Available tasks: {info.get('available_tasks', [])}")
        print(f"Cached models: {info.get('cached_models', [])}")
        
        return True
        
    except Exception as e:
        print(f"✗ Model loading test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all tests."""
    print("=== Chemeleon MCP Server Debug ===\n")
    
    # Check conda environment
    conda_env = os.environ.get('CONDA_DEFAULT_ENV', 'Not set')
    print(f"Conda environment: {conda_env}")
    if conda_env != 'perry':
        print("⚠️  Warning: Not in 'perry' environment")
    
    print(f"Python: {sys.version}")
    print(f"Python executable: {sys.executable}\n")
    
    # Run tests
    tests = [
        ("Imports", test_imports),
        ("Tool Registration", test_tool_registration),
        ("Model Loading", test_model_loading),
    ]
    
    results = []
    for name, test_func in tests:
        print(f"\n{'='*50}")
        success = test_func()
        results.append((name, success))
    
    # Summary
    print(f"\n{'='*50}")
    print("Summary:")
    for name, success in results:
        status = "✓ PASS" if success else "✗ FAIL"
        print(f"  {name}: {status}")
    
    all_passed = all(success for _, success in results)
    
    if all_passed:
        print("\n✅ All tests passed! The server should be ready to use.")
        print("\nTo run the server:")
        print("  python -m chemeleon_mcp")
    else:
        print("\n❌ Some tests failed. Please check the errors above.")
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())