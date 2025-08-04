#!/usr/bin/env python3
"""
Patched Chemistry Unified Server with runtime error fixes.
This version automatically applies all necessary patches for v2.0-alpha stability.
"""

import sys
import os
import logging

# Add path for patches
dev_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, dev_path)

# Apply patches before importing server
try:
    from patch_chemistry_server import apply_all_patches
    apply_all_patches()
    print("🚀 CrystaLyse.AI v2.0-alpha patches applied successfully")
except Exception as e:
    print(f"⚠️ Warning: Could not apply patches: {e}")

# Now import the original server
from chemistry_unified.server import *

# Additional patches for specific issues
def patch_mace_dtype_issues():
    """Apply MACE-specific dtype fixes."""
    try:
        from mace_mcp import tools as mace_tools
        
        # Patch MACE relaxation to handle dtype mismatches
        if hasattr(mace_tools, 'relax_structure'):
            original_relax = mace_tools.relax_structure
            
            def patched_relax_structure(*args, **kwargs):
                try:
                    # Ensure float64 precision for all inputs
                    if args and hasattr(args[0], 'astype'):
                        args = list(args)
                        args[0] = args[0].astype(np.float64)
                        args = tuple(args)
                    
                    return original_relax(*args, **kwargs)
                except Exception as e:
                    if "dtype" in str(e).lower():
                        logging.warning(f"MACE dtype issue: {e}")
                        return {"success": False, "error": f"MACE dtype mismatch: {str(e)}"}
                    raise
            
            mace_tools.relax_structure = patched_relax_structure
            print("✅ Applied MACE dtype patch")
            
    except ImportError:
        print("ℹ️ MACE tools not available for patching")
    except Exception as e:
        print(f"⚠️ Could not patch MACE dtype issues: {e}")

def patch_electronegativity_warnings():
    """Suppress PyMatgen electronegativity warnings for noble gases."""
    try:
        import warnings
        
        # Filter out specific electronegativity warnings
        warnings.filterwarnings("ignore", message=".*Pauling electronegativity.*Setting to NaN.*")
        warnings.filterwarnings("ignore", message=".*No Pauling electronegativity.*")
        
        print("✅ Applied electronegativity warning filters")
        
    except Exception as e:
        print(f"⚠️ Could not filter electronegativity warnings: {e}")

def enhanced_main():
    """Enhanced main function with all patches applied."""
    
    # Apply additional patches
    patch_mace_dtype_issues()
    patch_electronegativity_warnings()
    
    # Configure enhanced logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    logger = logging.getLogger(__name__)
    logger.info("Starting CrystaLyse.AI Chemistry Unified MCP Server (Patched v2.0-alpha)")
    logger.info(f"Available tools: SMACT={SMACT_AVAILABLE}, Chemeleon={CHEMELEON_AVAILABLE}, MACE={MACE_AVAILABLE}, Converter={CONVERTER_AVAILABLE}")
    
    # Add patch information to server
    @mcp.tool()
    def get_server_patch_info() -> str:
        """Get information about applied patches and server version."""
        return json.dumps({
            "server_version": "Chemistry Unified MCP Server",
            "crystalyse_version": "v2.0-alpha-patched",
            "patches_applied": [
                "JSON serialization fixes",
                "MACE dtype compatibility",
                "Structure validation (0-atom filtering)", 
                "Electronegativity warning suppression",
                "Enhanced error handling"
            ],
            "available_tools": {
                "SMACT": SMACT_AVAILABLE,
                "Chemeleon": CHEMELEON_AVAILABLE, 
                "MACE": MACE_AVAILABLE,
                "Converter": CONVERTER_AVAILABLE,
                "PyMatgen": PYMATGEN_AVAILABLE if 'PYMATGEN_AVAILABLE' in globals() else True
            },
            "timestamp": str(pd.Timestamp.now()) if 'pd' in globals() else "unknown"
        }, indent=2)
    
    # Run the server
    mcp.run()

if __name__ == "__main__":
    enhanced_main()