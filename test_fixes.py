#!/usr/bin/env python3
"""
Test script to verify the circular import and coordinate array fixes work correctly.
"""

import sys
import os
from pathlib import Path

# Add the CrystaLyse.AI directory to the Python path
crystalyse_dir = Path(__file__).parent
sys.path.insert(0, str(crystalyse_dir))

def test_circular_import_fix():
    """Test that the circular import issue is resolved."""
    print("Testing circular import fix...")
    
    try:
        # This should work without circular import issues
        from crystalyse.agents.crystalyse_agent import CrystaLyse, AgentConfig
        print("✅ Circular import fix successful - CrystaLyse imports without errors")
        
        # Test that we can create an agent config
        config = AgentConfig(mode="creative")
        print(f"✅ AgentConfig created successfully: mode={config.mode}, model={config.model}")
        
        return True
        
    except ImportError as e:
        print(f"❌ Circular import still present: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def test_coordinate_array_fix():
    """Test that the coordinate array reshape fix works."""
    print("\nTesting coordinate array fix...")
    
    try:
        import numpy as np
        from crystalyse.converters import convert_cif_to_mace_input
        
        # Create a simple test CIF string
        test_cif = """
data_test
_cell_length_a 5.0
_cell_length_b 5.0
_cell_length_c 5.0
_cell_angle_alpha 90.0
_cell_angle_beta 90.0
_cell_angle_gamma 90.0
_symmetry_equiv_pos_as_xyz
'x,y,z'
loop_
_atom_site_label
_atom_site_fract_x
_atom_site_fract_y
_atom_site_fract_z
Na1 0.0 0.0 0.0
Cl1 0.5 0.5 0.5
"""
        
        # Test the conversion
        result = convert_cif_to_mace_input(test_cif)
        
        if result.get("success", False):
            mace_input = result["mace_input"]
            positions = np.array(mace_input["positions"])
            
            # Check that positions have the right shape
            if len(positions.shape) == 2 and positions.shape[1] == 3:
                print(f"✅ Coordinate array fix successful - positions shape: {positions.shape}")
                print(f"✅ Structure: {result['formula']} with {result['num_atoms']} atoms")
                return True
            else:
                print(f"❌ Coordinate array has wrong shape: {positions.shape}")
                return False
        else:
            print(f"❌ CIF conversion failed: {result.get('error', 'Unknown error')}")
            return False
            
    except Exception as e:
        print(f"❌ Error testing coordinate array fix: {e}")
        return False

def test_environment_setup():
    """Test that environment variables are set correctly."""
    print("\nTesting environment variables...")
    
    env_vars = {
        "TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD": "1",
        "KALEIDO_CHROMIUM_ARGS": "--disable-gpu --disable-software-rasterizer --no-sandbox --disable-dev-shm-usage",
        "DISPLAY": ":99"
    }
    
    all_good = True
    for var, expected in env_vars.items():
        actual = os.environ.get(var)
        if actual:
            print(f"✅ {var} = {actual}")
        else:
            print(f"⚠️  {var} not set (expected: {expected})")
            all_good = False
    
    return all_good

def main():
    """Run all tests."""
    print("🔬 Testing CrystaLyse.AI fixes...")
    print("=" * 50)
    
    results = []
    
    # Test circular import fix
    results.append(test_circular_import_fix())
    
    # Test coordinate array fix
    results.append(test_coordinate_array_fix())
    
    # Test environment setup
    results.append(test_environment_setup())
    
    print("\n" + "=" * 50)
    print("📊 Test Results:")
    print(f"✅ Passed: {sum(results)}/{len(results)} tests")
    
    if all(results):
        print("🎉 All fixes are working correctly!")
        print("\nYou can now run:")
        print("crystalyse analyse --mode rigorous \"suggest 1 novel photocatalyst for water splitting\"")
        return 0
    else:
        print("❌ Some fixes need attention. Check the output above.")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 