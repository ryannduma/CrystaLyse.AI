#!/usr/bin/env python3
"""
Test o3 model with tool usage scoring using the updated system
"""

import asyncio
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from crystalyse.agents.unified_agent import CrystaLyse, AgentConfig

def score_tool_usage(result, expected_tools):
    """Score how well the agent used the expected tools"""
    tools_used = extract_tools_used(result)
    
    if not expected_tools:
        return {"score": 1.0, "tools_used": tools_used, "expected_tools": expected_tools}
    
    # Calculate intersection and union
    used_set = set(tools_used)
    expected_set = set(expected_tools)
    
    intersection = used_set.intersection(expected_set)
    union = used_set.union(expected_set)
    
    # Jaccard similarity score
    if not union:
        score = 1.0
    else:
        score = len(intersection) / len(union)
    
    # Bonus for using all expected tools
    if expected_set.issubset(used_set):
        score = min(1.0, score + 0.2)
    
    return {
        "score": score,
        "tools_used": tools_used,
        "expected_tools": expected_tools,
        "intersection": list(intersection),
        "missing_tools": list(expected_set - used_set),
        "extra_tools": list(used_set - expected_set)
    }

def extract_tools_used(result):
    """Extract which tools were actually used from the result"""
    tools_used = set()
    
    # Check new_items for tool calls
    for item in result.get('new_items', []):
        item_str = str(item).lower()
        if 'smact' in item_str:
            tools_used.add('smact')
        if 'chemeleon' in item_str:
            tools_used.add('chemeleon')
        if 'mace' in item_str:
            tools_used.add('mace')
    
    # Also check the discovery result
    discovery_result = str(result.get('discovery_result', '')).lower()
    if 'smact' in discovery_result:
        tools_used.add('smact')
    if 'chemeleon' in discovery_result:
        tools_used.add('chemeleon')
    if 'mace' in discovery_result:
        tools_used.add('mace')
    
    return list(tools_used)

async def test_o3_tool_usage():
    """Test o3 model with tool usage assessment"""
    print("🧪 Testing o3 Model Tool Usage with MDG API Key")
    print("=" * 60)
    
    # Test cases that explicitly require tool usage
    test_cases = [
        {
            "name": "SMACT Validation Test",
            "query": "Use SMACT tools to validate whether the composition NaFePO4 is chemically reasonable for a battery cathode. Show the validation results.",
            "expected_tools": ["smact"],
            "timeout": 60
        },
        {
            "name": "Chemeleon Structure Test", 
            "query": "Use Chemeleon CSP tools to predict the crystal structure of LiCoO2. Generate the structure data.",
            "expected_tools": ["chemeleon"],
            "timeout": 60
        },
        {
            "name": "MACE Energy Test",
            "query": "Use MACE force field calculations to compute the formation energy of CaTiO3 perovskite structure.",
            "expected_tools": ["mace"],
            "timeout": 60
        },
        {
            "name": "Full Workflow Test",
            "query": "Find a stable composition for a sodium-ion battery cathode: 1) Use SMACT to validate Na-containing compositions, 2) Use Chemeleon to predict structures, 3) Use MACE to calculate formation energies. Execute all three steps.",
            "expected_tools": ["smact", "chemeleon", "mace"],
            "timeout": 120
        }
    ]
    
    results = []
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n🔬 Test {i}: {test_case['name']}")
        print(f"📝 Query: {test_case['query']}")
        print(f"🎯 Expected tools: {test_case['expected_tools']}")
        
        try:
            # Create rigorous mode agent (uses o3)
            rigorous_config = AgentConfig(mode="rigorous")
            agent = CrystaLyse(rigorous_config)
            
            print(f"🤖 Using model: {rigorous_config.model}")
            
            start_time = time.time()
            
            # Run the test
            result = await agent.discover_materials(test_case['query'])
            
            elapsed_time = time.time() - start_time
            
            # Score tool usage
            tool_score = score_tool_usage(result, test_case['expected_tools'])
            
            test_result = {
                "name": test_case['name'],
                "tool_score": tool_score,
                "elapsed_time": elapsed_time,
                "success": tool_score['score'] > 0.5,  # 50% threshold
                "status": result.get('status', 'unknown'),
                "response_preview": str(result.get('discovery_result', ''))[:300] + "..."
            }
            
            results.append(test_result)
            
            print(f"⏱️  Completion time: {elapsed_time:.2f}s")
            print(f"🎯 Tool Usage Score: {tool_score['score']:.2f}")
            print(f"🔧 Tools Used: {tool_score['tools_used']}")
            print(f"❌ Missing Tools: {tool_score['missing_tools']}")
            print(f"{'✅ PASS' if tool_score['score'] > 0.5 else '❌ FAIL'}")
            
        except Exception as e:
            print(f"❌ Test failed: {e}")
            test_result = {
                "name": test_case['name'],
                "tool_score": {"score": 0.0, "tools_used": [], "expected_tools": test_case['expected_tools']},
                "elapsed_time": 0,
                "success": False,
                "status": "error",
                "error": str(e)
            }
            results.append(test_result)
    
    # Generate final report
    print(f"\n{'='*60}")
    print("🏆 FINAL o3 TOOL USAGE ASSESSMENT")
    print(f"{'='*60}")
    
    total_tests = len(results)
    passed_tests = sum(1 for r in results if r['success'])
    avg_score = sum(r['tool_score']['score'] for r in results) / total_tests if total_tests > 0 else 0
    avg_time = sum(r['elapsed_time'] for r in results) / total_tests if total_tests > 0 else 0
    
    print(f"📊 Tests Passed: {passed_tests}/{total_tests} ({(passed_tests/total_tests)*100:.1f}%)")
    print(f"🎯 Average Tool Usage Score: {avg_score:.2f}")
    print(f"⏱️  Average Response Time: {avg_time:.2f}s")
    
    # Detailed results
    print(f"\n📋 Detailed Results:")
    for result in results:
        status_icon = "✅" if result['success'] else "❌"
        print(f"{status_icon} {result['name']}: {result['tool_score']['score']:.2f} ({result['elapsed_time']:.1f}s)")
        print(f"   Tools used: {result['tool_score']['tools_used']}")
        print(f"   Expected: {result['tool_score']['expected_tools']}")
    
    # Assessment
    if avg_score >= 0.75:
        print(f"\n🎉 EXCELLENT: o3 model shows excellent tool usage (avg score: {avg_score:.2f})")
        assessment = "excellent"
    elif avg_score >= 0.5:
        print(f"\n✅ GOOD: o3 model shows good tool usage (avg score: {avg_score:.2f})")
        assessment = "good"
    else:
        print(f"\n❌ POOR: o3 model shows poor tool usage (avg score: {avg_score:.2f})")
        assessment = "poor"
    
    # Save detailed report
    save_tool_usage_report(results, avg_score, assessment)
    
    return assessment in ["excellent", "good"]

def save_tool_usage_report(results, avg_score, assessment):
    """Save detailed tool usage report"""
    
    report = f"""# o3 Model Tool Usage Assessment Report

## Executive Summary
- **Overall Assessment**: {assessment.upper()}
- **Average Tool Usage Score**: {avg_score:.2f}
- **Success Rate**: {sum(1 for r in results if r['success'])}/{len(results)} tests passed

## Test Results

| Test | Tool Score | Tools Used | Expected Tools | Status | Time |
|------|------------|------------|----------------|--------|------|
"""
    
    for result in results:
        status = "✅ PASS" if result['success'] else "❌ FAIL"
        tools_used = ', '.join(result['tool_score']['tools_used']) or 'None'
        expected = ', '.join(result['tool_score']['expected_tools'])
        
        report += f"| {result['name']} | {result['tool_score']['score']:.2f} | {tools_used} | {expected} | {status} | {result['elapsed_time']:.1f}s |\n"
    
    report += f"""
## Scoring Methodology

**Tool Usage Score Calculation:**
1. **Jaccard Similarity**: |intersection| / |union| of expected vs used tools
2. **Bonus Points**: +0.2 for using all expected tools  
3. **Pass Threshold**: 0.5 (50% tool usage required)
4. **Success Criteria**: 
   - Excellent: ≥0.75 average score
   - Good: ≥0.5 average score
   - Poor: <0.5 average score

## Key Findings

### Tool Usage Patterns
"""
    
    # Analyze tool usage patterns
    all_tools = ['smact', 'chemeleon', 'mace']
    for tool in all_tools:
        expected_count = sum(1 for r in results if tool in r['tool_score']['expected_tools'])
        used_count = sum(1 for r in results if tool in r['tool_score']['tools_used'])
        usage_rate = (used_count / expected_count * 100) if expected_count > 0 else 0
        
        report += f"- **{tool.upper()}**: Expected {expected_count} times, used {used_count} times ({usage_rate:.1f}% usage rate)\n"
    
    report += f"""
### Performance Analysis
- **Response Time**: Average {sum(r['elapsed_time'] for r in results) / len(results):.2f}s per query
- **Model**: o3 with OPENAI_MDG_API_KEY  
- **Mode**: Rigorous (with SMACT, Chemeleon, MACE servers)

## Recommendations

"""
    
    if assessment == "excellent":
        report += "✅ **o3 model demonstrates excellent tool usage capabilities**\n- Ready for production materials science workflows\n- Consistently leverages computational tools appropriately\n"
    elif assessment == "good":
        report += "✅ **o3 model shows good tool usage with room for improvement**\n- Suitable for most materials science applications\n- May need prompt refinement for consistent tool usage\n"
    else:
        report += "❌ **o3 model requires significant improvement in tool usage**\n- Consider alternative models or prompt engineering\n- Review tool integration and documentation\n"
    
    with open("o3_tool_usage_assessment.md", "w") as f:
        f.write(report)
    
    print(f"\n📄 Detailed report saved to: o3_tool_usage_assessment.md")

if __name__ == "__main__":
    success = asyncio.run(test_o3_tool_usage())
    if success:
        print("\n🎉 o3 model passed tool usage assessment!")
    else:
        print("\n🚨 o3 model failed tool usage assessment")
        sys.exit(1)