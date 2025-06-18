#!/usr/bin/env python3
"""Test that the system prompt is loading correctly"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from crystalyse.agents.unified_agent import CrystaLyse, AgentConfig

# Test prompt loading
for mode in ["rigorous", "creative"]:
    print(f"\n{'='*50}")
    print(f"Testing {mode.upper()} mode prompt loading")
    print(f"{'='*50}")
    
    config = AgentConfig(mode=mode)
    agent = CrystaLyse(agent_config=config)
    
    print(f"\nMode: {agent.mode}")
    print(f"Model: {agent.model_name}")
    print(f"Instructions length: {len(agent.instructions)} characters")
    print(f"\nFirst 200 characters of instructions:")
    print(agent.instructions[:200] + "...")
    print(f"\nLast 200 characters of instructions:")
    print("..." + agent.instructions[-200:])
    
    # Check if mode-specific addition is present
    if mode == "rigorous" and "Rigorous Mode" in agent.instructions:
        print("\n✓ Rigorous mode addition found")
    elif mode == "creative" and "Creative Mode" in agent.instructions:
        print("\n✓ Creative mode addition found")
    else:
        print("\n✗ Mode-specific addition NOT found")

print("\n" + "="*50)
print("Prompt loading test complete!")