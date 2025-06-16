#!/usr/bin/env python3
"""
Simple test script to verify CrystaLyse CLI integration
"""

import os
import sys
import json
import time

# Add the current directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../CrystaLyse.AI'))

def test_python_bridge():
    """Test the Python bridge functionality"""
    print("Testing Python bridge...")
    
    # Simulate bridge communication
    request = {
        "type": "analyze",
        "query": "Design a battery cathode material",
        "mode": "rigorous"
    }
    
    print(json.dumps({"type": "ready"}))
    print(json.dumps({"type": "data", "payload": {"message": "Starting analysis...", "percent": 10}}))
    print(json.dumps({"type": "data", "payload": {"message": "Generating structure...", "percent": 50}}))
    print(json.dumps({"type": "data", "payload": {"message": "Calculating properties...", "percent": 80}}))
    
    # Simulate result
    result = {
        "composition": "LiFePO4",
        "properties": {
            "voltage": 3.45,
            "capacity": 170,
            "energy_density": 586.5,
            "band_gap": 2.1
        },
        "structure": """data_LiFePO4
_cell_length_a    10.332
_cell_length_b     6.010
_cell_length_c     4.693
_cell_angle_alpha  90.0
_cell_angle_beta   90.0
_cell_angle_gamma  90.0
_space_group_name_H-M_alt 'P n m a'
loop_
_atom_site_label
_atom_site_fract_x
_atom_site_fract_y
_atom_site_fract_z
Li 0.0000 0.0000 0.0000
Fe 0.2820 0.2500 0.9747
P  0.0954 0.2500 0.4180
O1 0.0974 0.2500 0.7434
O2 0.4557 0.2500 0.2066
O3 0.1649 0.0464 0.2843
""",
        "analysis": "LiFePO4 is an excellent cathode material for lithium-ion batteries with high safety and good cycle life.",
        "confidence": 0.92,
        "timestamp": time.time()
    }
    
    print(json.dumps({"type": "complete", "payload": result}))

def test_validation():
    """Test composition validation"""
    print("Testing validation...")
    
    result = {
        "composition": "LiFePO4",
        "elements": ["Li", "Fe", "P", "O"],
        "counts": [1, 1, 1, 4],
        "valid": True,
        "oxidation_states": [1, 2, 5, -2],
        "message": "Valid composition"
    }
    
    print(json.dumps({"type": "complete", "payload": result}))

if __name__ == "__main__":
    if len(sys.argv) > 1:
        command = sys.argv[1]
        if command == "analyze":
            test_python_bridge()
        elif command == "validate":
            test_validation()
    else:
        test_python_bridge()