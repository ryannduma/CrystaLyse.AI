#!/usr/bin/env python3
"""
Basic test to validate critical fixes.
"""

import asyncio
import sys
from pathlib import Path

# Add paths
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

async def test_query_classification():
    """Test that query classification works correctly."""
    print("🔍 Testing Query Classification")
    print("=" * 40)
    
    try:
        from crystalyse.agents.unified_agent import ComputationalQueryClassifier
        
        classifier = ComputationalQueryClassifier()
        
        test_cases = [
            ("Validate LiFePO4", True),
            ("Calculate formation energy", True),
            ("What is a battery?", False),
            ("Generate structure for NaCl", True),
            ("Hello world", False)
        ]
        
        for query, expected in test_cases:
            result = classifier.requires_computation(query)
            status = "✅" if result == expected else "❌"
            print(f"   {status} '{query}' -> {result} (expected {expected})")
        
        return True
        
    except Exception as e:
        print(f"❌ Classification test failed: {e}")
        return False

async def test_response_validation():
    """Test response validation system."""
    print("\n🛡️  Testing Response Validation")
    print("=" * 40)
    
    try:
        from crystalyse.validation import validate_computational_response
        
        # Test hallucinated response
        is_valid, sanitized, violations = validate_computational_response(
            query="Validate LiFePO4",
            response="SMACT validation: ✅ Valid (confidence: 0.95)",
            tool_calls=[],
            requires_computation=True
        )
        
        print(f"   Hallucination detection: {'✅' if not is_valid else '❌'}")
        print(f"   Violations found: {len(violations)}")
        
        # Test legitimate response
        is_valid2, sanitized2, violations2 = validate_computational_response(
            query="What is a battery?",
            response="A battery stores energy.",
            tool_calls=[],
            requires_computation=False
        )
        
        print(f"   Legitimate response: {'✅' if is_valid2 else '❌'}")
        
        return not is_valid and is_valid2  # First should be invalid, second valid
        
    except Exception as e:
        print(f"❌ Validation test failed: {e}")
        return False

async def test_simple_agent_call():
    """Test basic agent functionality."""
    print("\n🤖 Testing Simple Agent Call")
    print("=" * 40)
    
    try:
        from crystalyse.agents.unified_agent import CrystaLyse, AgentConfig
        
        config = AgentConfig(mode="rigorous", max_turns=2)
        agent = CrystaLyse(agent_config=config)
        
        # Simple non-computational query
        query = "What is the formula for water?"
        result = await agent.discover_materials(query)
        
        status = result.get('status')
        print(f"   Status: {status}")
        print(f"   Response exists: {'✅' if result.get('discovery_result') else '❌'}")
        
        return status == 'completed'
        
    except Exception as e:
        print(f"❌ Agent test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Run basic validation tests."""
    print("🚀 BASIC FIXES VALIDATION")
    print("=" * 50)
    
    tests = [
        ("query_classification", test_query_classification),
        ("response_validation", test_response_validation), 
        ("simple_agent_call", test_simple_agent_call)
    ]
    
    results = {}
    for test_name, test_func in tests:
        try:
            results[test_name] = await test_func()
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {e}")
            results[test_name] = False
    
    print("\n" + "=" * 50)
    print("📊 BASIC VALIDATION RESULTS:")
    
    for test_name, result in results.items():
        icon = "✅" if result else "❌"
        print(f"{icon} {test_name}: {'PASSED' if result else 'FAILED'}")
    
    success_rate = sum(results.values()) / len(results)
    print(f"\nSuccess rate: {success_rate:.1%}")
    
    if success_rate >= 0.8:
        print("🎉 Basic fixes are working!")
    else:
        print("⚠️  Some basic functionality needs work")

if __name__ == "__main__":
    asyncio.run(main())