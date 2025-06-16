#!/usr/bin/env python3
"""
CrystaLyse.AI Python Bridge
Interface between TypeScript CLI and Python analysis engine
"""

import sys
import json
import os
import asyncio
import traceback
from pathlib import Path


def send_message(msg_type: str, payload=None, message=None):
    """Send a JSON message to the TypeScript client"""
    msg = {'type': msg_type}
    if payload is not None:
        msg['payload'] = payload
    if message is not None:
        msg['message'] = message
    
    print(json.dumps(msg), flush=True)


def send_progress(message: str, percent: int = None):
    """Send progress update"""
    payload = {'message': message}
    if percent is not None:
        payload['percent'] = percent
    send_message('data', payload)


def send_status(message: str):
    """Send status update"""
    send_message('data', {'type': 'status', 'message': message})


# Add CrystaLyse.AI to path - now correctly points to parent since we're inside the project
crystalyse_dir = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
sys.path.insert(0, crystalyse_dir)

# Flag to indicate if we have the full CrystaLyse system
has_crystalyse = False
agent = None

try:
    # Import CrystaLyse components
    from crystalyse.agents.enhanced_agent import EnhancedCrystaLyseAgent
    from crystalyse.config import CrystaLyseConfig
    from smact import Element
    
    # Initialize the agent
    config = CrystaLyseConfig()
    agent = EnhancedCrystaLyseAgent(config)
    has_crystalyse = True
    
except ImportError as e:
    # Fall back to demo mode if CrystaLyse modules are not available
    send_message('data', {'type': 'warning', 'message': f'CrystaLyse modules not found, using demo mode: {str(e)}'})
    has_crystalyse = False


async def analyze_query(query: str, mode: str = 'rigorous'):
    """Analyze a materials query using CrystaLyse"""
    try:
        send_progress("🔬 Initializing analysis...")
        
        if has_crystalyse and agent:
            # Set agent mode
            agent.set_mode(mode)
            
            send_progress("⚡ Processing query...")
            
            # Use the agent's analyze method
            result = await agent.analyze_async(query)
            
            # Structure the result for the CLI
            structured_result = {
                'query': query,
                'mode': mode,
                'composition': result.get('composition'),
                'properties': result.get('properties', {}),
                'structure': result.get('structure'),
                'analysis': result.get('analysis'),
                'confidence': result.get('confidence', 0.0),
                'recommendations': result.get('recommendations', []),
                'timestamp': result.get('timestamp')
            }
        else:
            # Demo mode - return sample data
            send_progress("🧪 Running in demo mode...")
            send_progress("⚡ Generating sample result...")
            
            import time
            
            # Sample structure based on query
            sample_structure = """data_LiFePO4
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
"""
            
            structured_result = {
                'query': query,
                'mode': mode,
                'composition': 'LiFePO4',
                'properties': {
                    'voltage': 3.45,
                    'capacity': 170,
                    'energy_density': 586.5,
                    'band_gap': 2.1,
                    'formation_energy': -2.85
                },
                'structure': sample_structure,
                'analysis': f'Demo analysis for query: "{query}". LiFePO4 is an excellent cathode material for lithium-ion batteries with high safety and good cycle life.',
                'confidence': 0.85,
                'recommendations': [
                    'Consider doping with Mn or Co for higher voltage',
                    'Carbon coating can improve conductivity',
                    'Nano-sizing reduces diffusion path length'
                ],
                'timestamp': time.time(),
                'demo_mode': True
            }
        
        send_message('complete', structured_result)
        
    except Exception as e:
        send_message('error', message=f"Analysis failed: {str(e)}")
        traceback.print_exc()


async def validate_composition(composition: str):
    """Validate a chemical composition using SMACT"""
    try:
        send_progress("🧪 Validating composition...")
        
        if has_crystalyse:
            try:
                # Parse composition and validate
                from smact.screening import smact_validity
                from smact import Element
                
                # Extract elements and their counts
                import re
                
                elements = []
                counts = []
                
                # Simple regex to match element symbols and numbers
                pattern = r'([A-Z][a-z?]?)(\d*)'
                matches = re.findall(pattern, composition)
                
                for element_symbol, count in matches:
                    if count == '':
                        count = 1
                    else:
                        count = int(count)
                    
                    elements.append(element_symbol)
                    counts.append(count)
                
                # Get oxidation states for elements
                oxidation_states = []
                for element_symbol in elements:
                    try:
                        element = Element(element_symbol)
                        oxidation_states.append(element.oxidation_states)
                    except:
                        send_message('error', message=f"Unknown element: {element_symbol}")
                        return
                
                # Check SMACT validity
                valid_combinations = []
                for ox_states in oxidation_states:
                    if ox_states:
                        valid_combinations.append(ox_states)
                    else:
                        valid_combinations.append([0])  # Default if no oxidation states
                
                # Test various oxidation state combinations
                is_valid = False
                valid_ox_states = None
                
                from itertools import product
                for ox_combo in product(*valid_combinations):
                    if smact_validity(elements, counts, ox_combo):
                        is_valid = True
                        valid_ox_states = ox_combo
                        break
                
                result = {
                    'composition': composition,
                    'elements': elements,
                    'counts': counts,
                    'valid': is_valid,
                    'oxidation_states': valid_ox_states,
                    'message': 'Valid composition' if is_valid else 'Invalid composition'
                }
                
            except ImportError:
                # Fallback to demo mode even if has_crystalyse is True
                result = await demo_validate_composition(composition)
        else:
            # Demo mode
            result = await demo_validate_composition(composition)
        
        send_message('complete', result)
        
    except Exception as e:
        send_message('error', message=f"Validation failed: {str(e)}")
        traceback.print_exc()


async def demo_validate_composition(composition: str):
    """Demo composition validation"""
    import re
    
    # Extract elements for demo
    elements = []
    counts = []
    
    pattern = r'([A-Z][a-z]?)(\d*)'
    matches = re.findall(pattern, composition)
    
    for element_symbol, count in matches:
        if count == '':
            count = 1
        else:
            count = int(count)
        
        elements.append(element_symbol)
        counts.append(count)
    
    # Demo logic - common valid compositions
    valid_compositions = {
        'LiFePO4': ([1, 2, 5, -2], True),
        'NaCl': ([1, -1], True),
        'TiO2': ([4, -2], True),
        'CaCO3': ([2, 4, -2], True),
        'Al2O3': ([3, -2], True),
        'SiO2': ([4, -2], True)
    }
    
    is_valid = composition in valid_compositions or len(elements) <= 4
    valid_ox_states = valid_compositions.get(composition, ([1] * len(elements), is_valid))[0] if is_valid else None
    
    return {
        'composition': composition,
        'elements': elements,
        'counts': counts,
        'valid': is_valid,
        'oxidation_states': valid_ox_states,
        'message': f'Demo validation: {"Valid" if is_valid else "Invalid"} composition',
        'demo_mode': True
    }


async def main():
    """Main bridge loop"""
    send_message('ready')
    
    try:
        # Read requests from stdin
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
            
            try:
                request = json.loads(line)
                request_type = request.get('type')
                
                if request_type == 'analyze':
                    query = request.get('query', '')
                    mode = request.get('mode', 'rigorous')
                    await analyze_query(query, mode)
                
                elif request_type == 'validate':
                    composition = request.get('composition', '')
                    await validate_composition(composition)
                
                else:
                    send_message('error', message=f"Unknown request type: {request_type}")
                    
            except json.JSONDecodeError as e:
                send_message('error', message=f"Invalid JSON request: {str(e)}")
            except Exception as e:
                send_message('error', message=f"Request processing error: {str(e)}")
                traceback.print_exc()
                
    except KeyboardInterrupt:
        pass
    except Exception as e:
        send_message('error', message=f"Bridge error: {str(e)}")
        traceback.print_exc()


if __name__ == '__main__':
    asyncio.run(main())