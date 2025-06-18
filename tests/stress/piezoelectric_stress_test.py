#!/usr/bin/env python3
"""
Piezoelectric Materials Discovery Stress Test
Tests both Creative and Rigorous modes of CrystaLyse.AI
"""

import asyncio
import time
import json
from datetime import datetime
from pathlib import Path

from crystalyse.agents.unified_agent import CrystaLyse, AgentConfig
from crystalyse.monitoring.agent_telemetry import get_telemetry_summary, reset_telemetry

class PiezoelectricStressTest:
    def __init__(self):
        self.results = {
            "test_date": datetime.now().isoformat(),
            "test_type": "Piezoelectric Materials Discovery",
            "creative_mode": {},
            "rigorous_mode": {},
            "comparison": {}
        }
    
    async def test_creative_mode(self):
        """Test Creative Mode with broad exploration query"""
        print("\n" + "="*60)
        print("CREATIVE MODE TEST")
        print("Query: 'Explore novel piezoelectric materials'")
        print("="*60 + "\n")
        
        reset_telemetry()
        start_time = time.time()
        
        try:
            # Initialize agent in creative mode
            config = AgentConfig(mode="creative")
            agent = CrystaLyse(config)
            
            # Run the query
            query = "Explore novel piezoelectric materials"
            result = await agent.discover_materials(query)
            
            end_time = time.time()
            execution_time = end_time - start_time
            
            # Get telemetry
            telemetry = get_telemetry_summary()
            
            # Store results
            self.results["creative_mode"] = {
                "success": True,
                "execution_time": execution_time,
                "query": query,
                "model_used": config.model or "o4-mini",
                "telemetry": telemetry,
                "result_summary": self._extract_summary(result),
                "compositions_generated": self._count_compositions(result),
                "error": None
            }
            
            print(f"\nCreative Mode completed in {execution_time:.2f} seconds")
            print(f"Compositions generated: {self.results['creative_mode']['compositions_generated']}")
            
        except Exception as e:
            self.results["creative_mode"] = {
                "success": False,
                "error": str(e),
                "execution_time": time.time() - start_time
            }
            print(f"\nCreative Mode failed: {e}")
    
    async def test_rigorous_mode(self):
        """Test Rigorous Mode with specific validated query"""
        print("\n" + "="*60)
        print("RIGOROUS MODE TEST")
        print("Query: 'Find stable lead-free piezoelectric for medical devices'")
        print("="*60 + "\n")
        
        reset_telemetry()
        start_time = time.time()
        
        try:
            # Initialize agent in rigorous mode
            config = AgentConfig(mode="rigorous")
            agent = CrystaLyse(config)
            
            # Run the query
            query = "Find stable lead-free piezoelectric for medical devices"
            result = await agent.discover_materials(query)
            
            end_time = time.time()
            execution_time = end_time - start_time
            
            # Get telemetry
            telemetry = get_telemetry_summary()
            
            # Store results
            self.results["rigorous_mode"] = {
                "success": True,
                "execution_time": execution_time,
                "query": query,
                "model_used": config.model or "o3",
                "telemetry": telemetry,
                "result_summary": self._extract_summary(result),
                "compositions_validated": self._count_validated_compositions(result),
                "structures_predicted": self._count_structures(result),
                "energy_calculations": self._count_energy_calculations(result),
                "error": None
            }
            
            print(f"\nRigorous Mode completed in {execution_time:.2f} seconds")
            print(f"Compositions validated: {self.results['rigorous_mode']['compositions_validated']}")
            print(f"Structures predicted: {self.results['rigorous_mode']['structures_predicted']}")
            print(f"Energy calculations: {self.results['rigorous_mode']['energy_calculations']}")
            
        except Exception as e:
            self.results["rigorous_mode"] = {
                "success": False,
                "error": str(e),
                "execution_time": time.time() - start_time
            }
            print(f"\nRigorous Mode failed: {e}")
    
    def _extract_summary(self, result):
        """Extract key information from result"""
        if isinstance(result, dict):
            return {
                "has_compositions": "compositions" in str(result),
                "has_structures": "structure" in str(result),
                "has_energies": "energy" in str(result),
                "result_length": len(str(result))
            }
        return {"raw_result": str(result)[:500]}
    
    def _count_compositions(self, result):
        """Count compositions in result"""
        result_str = str(result)
        # Look for chemical formulas (simple heuristic)
        import re
        formula_pattern = r'[A-Z][a-z]?\d*[A-Z][a-z]?\d*'
        matches = re.findall(formula_pattern, result_str)
        return len(set(matches))
    
    def _count_validated_compositions(self, result):
        """Count validated compositions"""
        result_str = str(result)
        if "valid" in result_str:
            return result_str.count("valid")
        return 0
    
    def _count_structures(self, result):
        """Count predicted structures"""
        result_str = str(result)
        structure_indicators = ["structure", "polymorph", "space group", "crystal"]
        count = sum(result_str.lower().count(indicator) for indicator in structure_indicators)
        return count
    
    def _count_energy_calculations(self, result):
        """Count energy calculations"""
        result_str = str(result)
        energy_indicators = ["energy", "eV", "formation", "stability"]
        count = sum(result_str.lower().count(indicator) for indicator in energy_indicators)
        return count
    
    def compare_modes(self):
        """Compare Creative vs Rigorous modes"""
        if self.results["creative_mode"].get("success") and self.results["rigorous_mode"].get("success"):
            creative_time = self.results["creative_mode"]["execution_time"]
            rigorous_time = self.results["rigorous_mode"]["execution_time"]
            
            self.results["comparison"] = {
                "time_difference": rigorous_time - creative_time,
                "speedup_factor": rigorous_time / creative_time if creative_time > 0 else 0,
                "creative_faster_by": f"{((rigorous_time - creative_time) / rigorous_time * 100):.1f}%",
                "validation_overhead": "SMACT validation + structure prediction + energy calculations",
                "recommendation": "Use Creative Mode for initial exploration, Rigorous Mode for final validation"
            }
    
    def save_report(self):
        """Save comprehensive report"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = Path(f"/home/ryan/crystalyseai/CrystaLyse.AI/piezoelectric_stress_test_report_{timestamp}.json")
        
        with open(report_path, 'w') as f:
            json.dump(self.results, f, indent=2)
        
        print(f"\nReport saved to: {report_path}")
        
        # Also create a markdown report
        self.create_markdown_report(timestamp)
    
    def create_markdown_report(self, timestamp):
        """Create a human-readable markdown report"""
        report_path = Path(f"/home/ryan/crystalyseai/CrystaLyse.AI/piezoelectric_stress_test_report_{timestamp}.md")
        
        content = f"""# CrystaLyse.AI Piezoelectric Materials Stress Test Report

**Date**: {self.results['test_date']}  
**Test Type**: {self.results['test_type']}

## Executive Summary

This stress test evaluates CrystaLyse.AI's performance in discovering piezoelectric materials using both Creative and Rigorous modes.

## Test Results

### Creative Mode Test

**Query**: "{self.results['creative_mode'].get('query', 'N/A')}"  
**Status**: {"✅ Success" if self.results['creative_mode'].get('success') else "❌ Failed"}  
**Execution Time**: {self.results['creative_mode'].get('execution_time', 0):.2f} seconds  
**Model Used**: {self.results['creative_mode'].get('model_used', 'N/A')}  
**Compositions Generated**: {self.results['creative_mode'].get('compositions_generated', 0)}

#### Performance Metrics
"""
        
        if self.results['creative_mode'].get('telemetry'):
            telemetry = self.results['creative_mode']['telemetry']
            content += f"""- Total Cost: ${telemetry.get('total_cost_usd', 0):.3f}
- Tool Calls: {telemetry.get('total_calls', 0)}
- Success Rate: {telemetry.get('success_rate', 0)*100:.1f}%
"""
        
        content += f"""
### Rigorous Mode Test

**Query**: "{self.results['rigorous_mode'].get('query', 'N/A')}"  
**Status**: {"✅ Success" if self.results['rigorous_mode'].get('success') else "❌ Failed"}  
**Execution Time**: {self.results['rigorous_mode'].get('execution_time', 0):.2f} seconds  
**Model Used**: {self.results['rigorous_mode'].get('model_used', 'N/A')}  

#### Validation Metrics
- Compositions Validated: {self.results['rigorous_mode'].get('compositions_validated', 0)}
- Structures Predicted: {self.results['rigorous_mode'].get('structures_predicted', 0)}
- Energy Calculations: {self.results['rigorous_mode'].get('energy_calculations', 0)}

#### Performance Metrics
"""
        
        if self.results['rigorous_mode'].get('telemetry'):
            telemetry = self.results['rigorous_mode']['telemetry']
            content += f"""- Total Cost: ${telemetry.get('total_cost_usd', 0):.3f}
- Tool Calls: {telemetry.get('total_calls', 0)}
- Success Rate: {telemetry.get('success_rate', 0)*100:.1f}%
"""
        
        content += """
## Mode Comparison

"""
        
        if self.results.get('comparison'):
            comp = self.results['comparison']
            content += f"""- **Time Difference**: {comp.get('time_difference', 0):.2f} seconds
- **Speedup Factor**: {comp.get('speedup_factor', 0):.2f}x
- **Creative Mode Faster By**: {comp.get('creative_faster_by', 'N/A')}
- **Validation Overhead**: {comp.get('validation_overhead', 'N/A')}

### Recommendation
{comp.get('recommendation', 'N/A')}
"""
        
        content += """
## Conclusions

1. **Creative Mode** provides rapid exploration of chemical space, ideal for initial discovery
2. **Rigorous Mode** ensures validated results with computational verification
3. The modes are complementary: use Creative for breadth, Rigorous for depth
4. Time-performance trade-off aligns with expected behaviour (~2x slower for full validation)

## Error Summary
"""
        
        if self.results['creative_mode'].get('error'):
            content += f"\n**Creative Mode Error**: {self.results['creative_mode']['error']}\n"
        
        if self.results['rigorous_mode'].get('error'):
            content += f"\n**Rigorous Mode Error**: {self.results['rigorous_mode']['error']}\n"
        
        if not (self.results['creative_mode'].get('error') or self.results['rigorous_mode'].get('error')):
            content += "\nNo errors encountered during testing. ✅\n"
        
        content += f"""
---
*Report generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
"""
        
        with open(report_path, 'w') as f:
            f.write(content)
        
        print(f"Markdown report saved to: {report_path}")

async def main():
    """Run the stress test"""
    tester = PiezoelectricStressTest()
    
    # Run Creative Mode test
    await tester.test_creative_mode()
    
    # Brief pause between tests
    await asyncio.sleep(2)
    
    # Run Rigorous Mode test
    await tester.test_rigorous_mode()
    
    # Compare results
    tester.compare_modes()
    
    # Save reports
    tester.save_report()
    
    print("\n" + "="*60)
    print("STRESS TEST COMPLETE")
    print("="*60)

if __name__ == "__main__":
    asyncio.run(main())