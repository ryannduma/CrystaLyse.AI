# Coordinate Array Shape Fix

## Problem

MACE energy calculations failed for BaMnO3 and YMnO3 with the error:
```
"Invalid structure: Position array shape (15,) doesn't match 5 atoms"
```

This occurred because coordinate arrays were being flattened during JSON serialisation/deserialisation in the MCP communication pipeline, converting 2D coordinate arrays `(5, 3)` to 1D arrays `(15,)`.

## Root Cause

The issue occurs in the data pipeline between Chemeleon structure generation and MACE energy calculations:

1. **Chemeleon** generates structures with correct `positions.shape = (n_atoms, 3)`
2. **JSON serialisation** during MCP transport can flatten 2D arrays to 1D
3. **MACE validation** expects `(n_atoms, 3)` but receives `(15,)` for 5-atom structures

## Solution

Added coordinate array shape validation and automatic reshaping at three critical points:

### 1. Structure Generation Processing
**Location**: `chemistry-unified-server/src/chemistry_unified/server.py:395-408`

Validates and reshapes coordinate arrays immediately after structure generation:
```python
# Fix coordinate array shape if flattened during JSON serialisation
n_atoms = len(structure_dict["numbers"])
if len(positions_array.shape) == 1:
    # Coordinates were flattened - reshape to (n_atoms, 3)
    if len(positions_array) == n_atoms * 3:
        positions_array = positions_array.reshape(n_atoms, 3)
        structure_dict["positions"] = positions_array.tolist()
        logger.info(f"Fixed flattened coordinates for structure {i}")
```

### 2. MACE Validation
**Location**: `chemistry-unified-server/src/chemistry_unified/server.py:641-652`

Provides a second layer of protection before MACE energy calculations:
```python
# Fix coordinate array shape if flattened (second layer of protection)
if len(positions_array.shape) == 1:
    if len(positions_array) == n_atoms * 3:
        positions_array = positions_array.reshape(n_atoms, 3)
        mace_structure["positions"] = positions_array.tolist()
        logger.info(f"MACE validation: Fixed flattened coordinates for structure {structure_id}")
```

### 3. CIF Generation
**Location**: `chemistry-unified-server/src/chemistry_unified/server.py:115-127`

Ensures CIF files can be generated even if coordinates were flattened:
```python
# Fix coordinate array shape if flattened (CIF generation protection)
if len(positions_array.shape) == 1:
    if len(positions_array) == n_atoms * 3:
        positions_array = positions_array.reshape(n_atoms, 3)
        positions = positions_array.tolist()
        logger.info(f"CIF generation: Fixed flattened coordinates")
```

## Key Features

1. **Automatic Detection**: Automatically detects when coordinate arrays are flattened `(15,)` instead of 2D `(5,3)`
2. **Validation**: Ensures the flattened array has the correct number of elements (`n_atoms * 3`)
3. **Error Handling**: Provides clear error messages for mismatched coordinate arrays
4. **Logging**: Logs coordinate fixes for debugging and monitoring
5. **Multi-layer Protection**: Fixes coordinates at multiple points in the pipeline
6. **Backward Compatibility**: Preserves existing behaviour for correctly shaped arrays

## Impact

- **BaMnO3 and YMnO3**: Should now successfully complete MACE energy calculations
- **All Compositions**: More robust coordinate handling prevents similar failures
- **CIF Generation**: Ensures CIF files are always generated when structures exist
- **Debugging**: Better logging helps identify coordinate shape issues

## Testing

The fix handles the specific error case:
- **Input**: Flattened coordinate array `(15,)` for 5-atom structure
- **Output**: Correctly shaped array `(5, 3)` for MACE compatibility
- **Validation**: Ensures array contains exactly `n_atoms * 3` elements before reshaping

This fix ensures that coordinate arrays maintain their proper 2D shape throughout the MCP communication pipeline, preventing MACE failures due to coordinate formatting issues.