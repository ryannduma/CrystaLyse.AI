#!/usr/bin/env python3
"""
Debug agent behaviour to understand why it's asking for clarification too often
"""

import asyncio
import logging
import sys
from pathlib import Path

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

sys.path.insert(0, str(Path(__file__).parent))

from crystalyse.agents.unified_agent import CrystaLyse, AgentConfig

async def debug_query(mode: str, query: str):
    """Debug a single query to see what the agent does"""
    logger.info(f"\n{'='*50}")
    logger.info(f"DEBUGGING: {mode.upper()} mode")
    logger.info(f"Query: '{query}'")
    logger.info(f"{'='*50}")
    
    config = AgentConfig(mode=mode, max_turns=2)  # Just 2 turns to see initial behaviour
    agent = CrystaLyse(agent_config=config)
    
    try:
        result = await agent.discover_materials(query)
        
        logger.info(f"\nStatus: {result['status']}")
        logger.info(f"\nDiscovery Result:")
        logger.info("-" * 30)
        logger.info(result.get('discovery_result', 'No result'))
        logger.info("-" * 30)
        
        if 'new_items' in result and result['new_items']:
            logger.info(f"\nAgent Actions (first 3):")
            for i, item in enumerate(result['new_items'][:3]):
                logger.info(f"\n{i+1}. {item[:200]}...")
                
    except Exception as e:
        logger.error(f"Error: {str(e)}")

async def main():
    """Run debug tests"""
    # Test a specific formula that should trigger immediate validation
    await debug_query("creative", "NaFePO4")
    
    # Test a property calculation request
    await debug_query("creative", "Calculate formation energy of BaTiO3")

if __name__ == "__main__":
    asyncio.run(main())