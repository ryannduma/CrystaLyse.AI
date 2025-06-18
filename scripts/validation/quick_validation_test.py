#!/usr/bin/env python3
"""
Quick validation test for the new CrystaLyse system prompt.
Tests basic functionality in both modes.
"""

import asyncio
import json
import time
from datetime import datetime
from pathlib import Path
import logging
import sys

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent))

from crystalyse.agents.unified_agent import CrystaLyse, AgentConfig

async def test_single_query(mode: str, query: str):
    """Test a single query in the specified mode"""
    logger.info(f"\n{'='*50}")
    logger.info(f"Testing {mode.upper()} MODE")
    logger.info(f"Query: {query}")
    logger.info(f"{'='*50}")
    
    start_time = time.time()
    config = AgentConfig(mode=mode, max_turns=5)  # Limit turns for faster testing
    agent = CrystaLyse(agent_config=config)
    
    try:
        result = await agent.discover_materials(query)
        elapsed = time.time() - start_time
        
        logger.info(f"\nStatus: {result['status']}")
        logger.info(f"Time: {elapsed:.2f}s")
        logger.info(f"Tool calls: {result.get('metrics', {}).get('tool_calls', 0)}")
        
        if result['status'] == 'completed':
            logger.info(f"\nDiscovery result preview:")
            logger.info(result['discovery_result'][:500] + "..." if len(result['discovery_result']) > 500 else result['discovery_result'])
            
            # Analyse tool usage
            tool_usage = {
                'smact': 0,
                'chemeleon': 0,
                'mace': 0,
                'clarification': 0
            }
            
            for item in result.get('new_items', []):
                item_str = str(item).lower()
                if 'smact' in item_str:
                    tool_usage['smact'] += 1
                if 'chemeleon' in item_str:
                    tool_usage['chemeleon'] += 1
                if 'mace' in item_str:
                    tool_usage['mace'] += 1
                if 'clarifying' in item_str:
                    tool_usage['clarification'] += 1
                    
            logger.info(f"\nTool usage analysis:")
            for tool, count in tool_usage.items():
                if count > 0:
                    logger.info(f"  - {tool}: {count} calls")
                    
            return {
                'success': True,
                'mode': mode,
                'query': query,
                'elapsed': elapsed,
                'tool_usage': tool_usage,
                'metrics': result.get('metrics', {})
            }
        else:
            logger.error(f"Failed: {result.get('error', 'Unknown error')}")
            return {
                'success': False,
                'mode': mode,
                'query': query,
                'elapsed': elapsed,
                'error': result.get('error', 'Unknown error')
            }
            
    except Exception as e:
        elapsed = time.time() - start_time
        logger.error(f"Exception: {str(e)}")
        return {
            'success': False,
            'mode': mode,
            'query': query,
            'elapsed': elapsed,
            'error': str(e)
        }

async def main():
    """Run quick validation tests"""
    logger.info("CrystaLyse System Prompt Quick Validation Test")
    logger.info(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    test_cases = [
        # Test specific formula analysis (should use all tools immediately)
        ("rigorous", "Analyse LiFePO4 for battery applications"),
        
        # Test discovery request (should generate and validate candidates)
        ("creative", "Find novel piezoelectric materials without lead"),
        
        # Test ambiguous query (should ask for clarification)
        ("rigorous", "Find a new battery material"),
        
        # Test property calculation (should use MACE immediately)
        ("creative", "Calculate formation energy of BaTiO3")
    ]
    
    results = []
    
    for mode, query in test_cases:
        result = await test_single_query(mode, query)
        results.append(result)
        
        # Small delay between tests
        await asyncio.sleep(2)
    
    # Summary
    logger.info(f"\n{'='*50}")
    logger.info("TEST SUMMARY")
    logger.info(f"{'='*50}")
    
    successful = sum(1 for r in results if r['success'])
    total = len(results)
    
    logger.info(f"Success rate: {successful}/{total} ({successful/total*100:.1f}%)")
    
    # Tool usage summary
    all_tools = {}
    for result in results:
        if result['success'] and 'tool_usage' in result:
            for tool, count in result['tool_usage'].items():
                all_tools[tool] = all_tools.get(tool, 0) + count
                
    logger.info("\nOverall tool usage:")
    for tool, count in all_tools.items():
        if count > 0:
            logger.info(f"  - {tool}: {count} total calls")
    
    # Assessment
    logger.info("\nASSESSMENT:")
    if successful == total:
        logger.info("✓ All tests passed - System prompt is working correctly!")
    elif successful >= total * 0.75:
        logger.info("✓ Most tests passed - System prompt is mostly working")
    else:
        logger.info("✗ Many tests failed - System prompt needs adjustment")
        
    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = Path(f"test_reports/quick_validation_{timestamp}.json")
    report_path.parent.mkdir(exist_ok=True)
    
    with open(report_path, 'w') as f:
        json.dump({
            'timestamp': timestamp,
            'results': results,
            'summary': {
                'success_rate': f"{successful}/{total}",
                'percentage': successful/total*100,
                'tool_usage': all_tools
            }
        }, f, indent=2)
        
    logger.info(f"\nResults saved to: {report_path}")

if __name__ == "__main__":
    asyncio.run(main())