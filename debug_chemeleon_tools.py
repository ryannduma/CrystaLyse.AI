#!/usr/bin/env python3
"""Debug script to test Chemeleon MCP tools directly."""

import sys
import json
import asyncio
from pathlib import Path

# Add paths
sys.path.insert(0, str(Path(__file__).parent / "chemeleon-mcp-server" / "src"))
sys.path.insert(0, str(Path(__file__).parent / "chemeleon-dng"))

async def test_generate_csp():
    """Test CSP generation."""
    print("\n=== Testing generate_crystal_csp ===")
    
    try:
        from chemeleon_mcp.tools import generate_crystal_csp
        
        # Test single formula
        print("\nGenerating structure for NaCl...")
        result_str = generate_crystal_csp(
            formulas="NaCl",
            num_samples=1,
            output_format="dict"
        )
        result = json.loads(result_str)
        
        if result.get("success"):
            print("✓ CSP generation successful")
            print(f"  Generated {result['num_structures']} structure(s)")
            
            if result['structures']:
                struct = result['structures'][0]
                print(f"  Formula: {struct['structure']['formula']}")
                print(f"  Symbols: {struct['structure']['symbols']}")
                print(f"  Volume: {struct['structure']['volume']:.2f} Ų")
        else:
            print(f"✗ CSP generation failed: {result.get('error')}")
            return False
            
        # Test multiple formulas
        print("\nGenerating structures for multiple formulas...")
        result_str = generate_crystal_csp(
            formulas=["MgO", "SiO2"],
            num_samples=1,
            output_format="both"
        )
        result = json.loads(result_str)
        
        if result.get("success"):
            print(f"✓ Generated {result['num_structures']} structures")
            for struct in result['structures']:
                print(f"  - {struct['formula']}: {len(struct.get('cif', '').splitlines())} CIF lines")
        
        return True
        
    except Exception as e:
        print(f"✗ CSP test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_analyse_structure():
    """Test structure analysis."""
    print("\n=== Testing analyse_structure ===")
    
    try:
        from chemeleon_mcp.tools import generate_crystal_csp, analyse_structure
        
        # First generate a structure
        print("\nGenerating test structure...")
        result_str = generate_crystal_csp(
            formulas="TiO2",
            num_samples=1,
            output_format="dict"
        )
        result = json.loads(result_str)
        
        if not result.get("success") or not result['structures']:
            print("✗ Failed to generate test structure")
            return False
        
        # Analyse the structure
        print("Analysing structure...")
        struct_dict = result['structures'][0]['structure']
        
        analysis_str = analyse_structure(
            structure_dict=struct_dict,
            calculate_symmetry=True,
            tolerance=0.1
        )
        analysis = json.loads(analysis_str)
        
        if 'error' not in analysis:
            print("✓ Structure analysis successful")
            print(f"  Formula: {analysis['formula']}")
            print(f"  Density: {analysis['density']:.2f} g/cm³")
            print(f"  Lattice: a={analysis['lattice']['a']:.2f}, b={analysis['lattice']['b']:.2f}, c={analysis['lattice']['c']:.2f}")
            
            if 'symmetry' in analysis:
                print(f"  Space group: {analysis['symmetry']['space_group']}")
                print(f"  Crystal system: {analysis['symmetry']['crystal_system']}")
        else:
            print(f"✗ Analysis failed: {analysis['error']}")
            return False
        
        return True
        
    except Exception as e:
        print(f"✗ Structure analysis test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_model_info():
    """Test model info retrieval."""
    print("\n=== Testing get_model_info ===")
    
    try:
        from chemeleon_mcp.tools import get_model_info
        
        info_str = get_model_info()
        info = json.loads(info_str)
        
        print("✓ Model info retrieved")
        print(f"  Available tasks: {info['available_tasks']}")
        print(f"  Device: {info['device']}")
        print(f"  Cached models: {info['cached_models']}")
        print(f"  Benchmarks: {list(info['benchmarks'].keys())}")
        
        return True
        
    except Exception as e:
        print(f"✗ Model info test failed: {e}")
        return False

async def main():
    """Run all tool tests."""
    print("=== Chemeleon MCP Tools Debug ===\n")
    
    # Note about model downloads
    print("⚠️  Note: First run may download the CSP model file (~1GB)")
    print("   This is normal and only happens once.\n")
    
    # Run tests
    tests = [
        ("Model Info", test_model_info),
        ("CSP Generation", test_generate_csp),
        ("Structure Analysis", test_analyse_structure),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            success = await test_func()
            results.append((name, success))
        except Exception as e:
            print(f"\n✗ {name} crashed: {e}")
            results.append((name, False))
    
    # Summary
    print(f"\n{'='*50}")
    print("Summary:")
    for name, success in results:
        status = "✓ PASS" if success else "✗ FAIL"
        print(f"  {name}: {status}")
    
    all_passed = all(success for _, success in results)
    
    if all_passed:
        print("\n✅ All tool tests passed!")
    else:
        print("\n❌ Some tool tests failed.")
    
    # Test cache clearing
    print("\n=== Testing clear_model_cache ===")
    try:
        from chemeleon_mcp.tools import clear_model_cache
        result_str = clear_model_cache()
        result = json.loads(result_str)
        print(f"✓ Cache cleared: {result['models_cleared']} models removed")
    except Exception as e:
        print(f"✗ Cache clear failed: {e}")
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))