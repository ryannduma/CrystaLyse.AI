#!/usr/bin/env python3
"""
Comprehensive test for rigor mode functionality of the consolidated CrystaLyseAgent.

This test validates the full multi-tool rigorous workflow including:
- SMACT composition validation
- Crystal structure generation via Chemeleon
- MACE energy calculations and uncertainty quantification
- Multi-fidelity routing decisions
- Lead-free ferroelectric materials design
"""

import asyncio
import sys
import os
import json
import time
from pathlib import Path
from datetime import datetime

# Add the CrystaLyse.AI directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent / "CrystaLyse.AI"))

from crystalyse.agents.main_agent import CrystaLyseAgent

class RigorModeTestSuite:
    """Comprehensive test suite for rigor mode functionality."""
    
    def __init__(self):
        self.results = {}
        self.start_time = None
        self.agent = None
        
    async def setup_agent(self):
        """Set up the agent in full rigor mode."""
        print("🔧 Setting up CrystaLyse Agent in Full Rigor Mode...")
        
        self.agent = CrystaLyseAgent(
            use_chem_tools=True,      # Enable SMACT validation
            enable_mace=True,         # Enable MACE energy calculations
            energy_focus=False,       # Use full workflow
            temperature=0.3,          # Lower temperature for precision
            uncertainty_threshold=0.1 # DFT routing threshold
        )
        
        config = self.agent.get_agent_configuration()
        print(f"✓ Agent configured: {config['integration_mode']}")
        
        # Verify all required capabilities are enabled
        capabilities = config['capabilities']
        required_capabilities = [
            'composition_validation',
            'energy_analysis', 
            'crystal_structure_generation',
            'multi_fidelity_routing'
        ]
        
        for capability in required_capabilities:
            if not capabilities.get(capability, False):
                raise ValueError(f"Required capability '{capability}' not enabled")
        
        print("✓ All required capabilities verified")
        return config
    
    async def test_ferroelectric_materials_design(self):
        """Test the primary use case: lead-free ferroelectric materials design."""
        print("\\n🎯 Testing Lead-Free Ferroelectric Materials Design...")
        
        query = '''Design lead-free ferroelectric materials for memory devices using multi-fidelity approach.
        
Requirements:
- High spontaneous polarization (> 50 μC/cm²)
- Curie temperature > 300°C  
- Formation energy analysis with uncertainty quantification
- Intelligent routing: Accept high-confidence MACE predictions, route uncertain cases for DFT validation

Provide 3-5 candidate compositions with energy analysis and synthesis recommendations.

Focus on:
1. SMACT validation for all proposed compositions
2. Crystal structure generation using Chemeleon
3. MACE energy calculations with uncertainty assessment
4. Multi-fidelity routing recommendations based on confidence
5. Detailed synthesis recommendations
'''
        
        test_start = time.time()
        
        try:
            print("🚀 Running comprehensive analysis...")
            result = await self.agent.analyze(query)
            
            duration = time.time() - test_start
            
            # Validate result quality
            assert isinstance(result, str), "Result must be a string"
            assert len(result) > 500, "Result too short for comprehensive analysis"
            
            # Check for key components in the result
            expected_components = [
                "composition",
                "SMACT",
                "crystal structure", 
                "formation energy",
                "uncertainty",
                "synthesis"
            ]
            
            found_components = []
            for component in expected_components:
                if component.lower() in result.lower():
                    found_components.append(component)
            
            self.results['ferroelectric_design'] = {
                'status': 'success',
                'duration': duration,
                'result_length': len(result),
                'components_found': found_components,
                'completeness': len(found_components) / len(expected_components),
                'result_preview': result[:300] + "..." if len(result) > 300 else result
            }
            
            print(f"✅ Test completed in {duration:.1f}s")
            print(f"📊 Result length: {len(result)} characters")
            print(f"🔍 Components found: {len(found_components)}/{len(expected_components)}")
            print(f"📈 Completeness: {self.results['ferroelectric_design']['completeness']:.1%}")
            
            return True
            
        except Exception as e:
            self.results['ferroelectric_design'] = {
                'status': 'failed',
                'error': str(e),
                'duration': time.time() - test_start
            }
            print(f"❌ Test failed: {e}")
            return False
    
    async def test_composition_validation(self):
        """Test the consolidated composition validation functionality."""
        print("\\n🧪 Testing Composition Validation...")
        
        test_compositions = [
            "BaTiO3",           # Classic ferroelectric - should pass
            "KNbO3",            # Lead-free alternative - should pass  
            "PbTiO3",           # Contains lead - should flag
            "BiFeO3",           # Multiferroic - should pass
            "Na0.5Bi0.5TiO3",   # Complex composition - challenging
            "Li2O",             # Simple oxide - different properties
            "InvalidFormula"     # Invalid - should fail
        ]
        
        context = {
            'application': 'ferroelectric memory devices',
            'requirements': ['lead_free', 'high_polarization', 'thermal_stability']
        }
        
        test_start = time.time()
        
        try:
            result = await self.agent.validate_compositions(test_compositions, context)
            duration = time.time() - test_start
            
            # Validate result
            assert isinstance(result, str), "Validation result must be a string"
            assert len(result) > 100, "Validation result too brief"
            
            # Check for validation keywords
            validation_keywords = ['valid', 'invalid', 'SMACT', 'composition', 'analysis']
            found_keywords = sum(1 for keyword in validation_keywords if keyword.lower() in result.lower())
            
            self.results['composition_validation'] = {
                'status': 'success',
                'duration': duration,
                'compositions_tested': len(test_compositions),
                'result_length': len(result),
                'keywords_found': found_keywords,
                'result_preview': result[:200] + "..." if len(result) > 200 else result
            }
            
            print(f"✅ Validation test completed in {duration:.1f}s")
            print(f"📊 Tested {len(test_compositions)} compositions")
            print(f"🔍 Validation keywords found: {found_keywords}")
            
            return True
            
        except Exception as e:
            self.results['composition_validation'] = {
                'status': 'failed',
                'error': str(e),
                'duration': time.time() - test_start
            }
            print(f"❌ Validation test failed: {e}")
            return False
    
    async def test_structure_prediction(self):
        """Test the integrated structure prediction capabilities."""
        print("\\n🏗️ Testing Structure Prediction...")
        
        test_composition = "KNbO3"  # Well-known ferroelectric
        application = "ferroelectric memory devices"
        
        test_start = time.time()
        
        try:
            result = await self.agent.predict_structures(test_composition, application)
            duration = time.time() - test_start
            
            # Validate result
            assert isinstance(result, str), "Structure prediction result must be a string"
            assert len(result) > 100, "Structure prediction result too brief"
            
            # Check for structure-related keywords
            structure_keywords = ['structure', 'crystal', 'lattice', 'symmetry', 'space group']
            found_keywords = sum(1 for keyword in structure_keywords if keyword.lower() in result.lower())
            
            self.results['structure_prediction'] = {
                'status': 'success',
                'duration': duration,
                'composition': test_composition,
                'result_length': len(result),
                'keywords_found': found_keywords,
                'result_preview': result[:200] + "..." if len(result) > 200 else result
            }
            
            print(f"✅ Structure prediction completed in {duration:.1f}s")
            print(f"📊 Composition: {test_composition}")
            print(f"🔍 Structure keywords found: {found_keywords}")
            
            return True
            
        except Exception as e:
            self.results['structure_prediction'] = {
                'status': 'failed',
                'error': str(e),
                'duration': time.time() - test_start
            }
            print(f"❌ Structure prediction failed: {e}")
            return False
    
    async def test_energy_analysis(self):
        """Test the MACE energy analysis capabilities."""
        print("\\n⚡ Testing Energy Analysis...")
        
        # Mock structures for testing
        test_structures = [
            {
                "composition": "BaTiO3",
                "space_group": "Pm-3m",
                "lattice_parameters": {"a": 4.0, "b": 4.0, "c": 4.0}
            },
            {
                "composition": "KNbO3", 
                "space_group": "Pm-3m",
                "lattice_parameters": {"a": 4.1, "b": 4.1, "c": 4.1}
            }
        ]
        
        test_start = time.time()
        
        try:
            result = await self.agent.energy_analysis(test_structures, "comprehensive")
            duration = time.time() - test_start
            
            # Validate result
            assert isinstance(result, dict), "Energy analysis result must be a dictionary"
            assert 'analysis_result' in result, "Missing analysis_result key"
            assert 'num_structures' in result, "Missing num_structures key"
            
            analysis_text = result['analysis_result']
            assert isinstance(analysis_text, str), "Analysis result must be a string"
            assert len(analysis_text) > 100, "Energy analysis too brief"
            
            # Check for energy-related keywords
            energy_keywords = ['energy', 'formation', 'stability', 'MACE', 'uncertainty']
            found_keywords = sum(1 for keyword in energy_keywords if keyword.lower() in analysis_text.lower())
            
            self.results['energy_analysis'] = {
                'status': 'success',
                'duration': duration,
                'structures_analyzed': result['num_structures'],
                'result_length': len(analysis_text),
                'keywords_found': found_keywords,
                'result_preview': analysis_text[:200] + "..." if len(analysis_text) > 200 else analysis_text
            }
            
            print(f"✅ Energy analysis completed in {duration:.1f}s")
            print(f"📊 Structures analyzed: {result['num_structures']}")
            print(f"🔍 Energy keywords found: {found_keywords}")
            
            return True
            
        except Exception as e:
            self.results['energy_analysis'] = {
                'status': 'failed',
                'error': str(e),
                'duration': time.time() - test_start
            }
            print(f"❌ Energy analysis failed: {e}")
            return False
    
    async def test_batch_screening(self):
        """Test the batch screening capabilities."""
        print("\\n📊 Testing Batch Screening...")
        
        test_compositions = ["BaTiO3", "KNbO3", "BiFeO3"]
        structures_per_comp = 2
        
        test_start = time.time()
        
        try:
            result = await self.agent.batch_screening(test_compositions, structures_per_comp)
            duration = time.time() - test_start
            
            # Validate result
            assert isinstance(result, dict), "Batch screening result must be a dictionary"
            assert 'screening_result' in result, "Missing screening_result key"
            assert 'compositions_screened' in result, "Missing compositions_screened key"
            
            screening_text = result['screening_result']
            assert isinstance(screening_text, str), "Screening result must be a string"
            assert len(screening_text) > 100, "Batch screening result too brief"
            
            self.results['batch_screening'] = {
                'status': 'success',
                'duration': duration,
                'compositions_screened': len(result['compositions_screened']),
                'total_structures': result['total_structures'],
                'result_length': len(screening_text),
                'result_preview': screening_text[:200] + "..." if len(screening_text) > 200 else screening_text
            }
            
            print(f"✅ Batch screening completed in {duration:.1f}s")
            print(f"📊 Compositions screened: {len(result['compositions_screened'])}")
            print(f"🏗️ Total structures: {result['total_structures']}")
            
            return True
            
        except Exception as e:
            self.results['batch_screening'] = {
                'status': 'failed',
                'error': str(e),
                'duration': time.time() - test_start
            }
            print(f"❌ Batch screening failed: {e}")
            return False
    
    def generate_report(self):
        """Generate a comprehensive test report."""
        total_duration = time.time() - self.start_time if self.start_time else 0
        
        print("\\n" + "="*60)
        print("🏁 RIGOR MODE FUNCTIONALITY TEST REPORT")
        print("="*60)
        
        # Summary statistics
        total_tests = len(self.results)
        passed_tests = sum(1 for result in self.results.values() if result['status'] == 'success')
        
        print(f"📈 Overall Results: {passed_tests}/{total_tests} tests passed")
        print(f"⏱️ Total test duration: {total_duration:.1f} seconds")
        print(f"🕒 Test completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Detailed results
        print("\\n📋 Detailed Test Results:")
        for test_name, result in self.results.items():
            status_emoji = "✅" if result['status'] == 'success' else "❌"
            print(f"\\n{status_emoji} {test_name.replace('_', ' ').title()}:")
            print(f"   Status: {result['status']}")
            print(f"   Duration: {result.get('duration', 0):.1f}s")
            
            if result['status'] == 'success':
                if 'result_length' in result:
                    print(f"   Result Length: {result['result_length']} characters")
                if 'keywords_found' in result:
                    print(f"   Keywords Found: {result['keywords_found']}")
                if 'completeness' in result:
                    print(f"   Completeness: {result['completeness']:.1%}")
            else:
                print(f"   Error: {result.get('error', 'Unknown error')}")
        
        # Recommendations
        print("\\n💡 Recommendations:")
        if passed_tests == total_tests:
            print("🎉 All tests passed! The rigor mode functionality is working correctly.")
            print("🚀 Ready for production use with MCP servers.")
        else:
            print("⚠️ Some tests failed. This is expected if MCP servers are not running.")
            print("🔧 Ensure SMACT, Chemeleon, and MACE MCP servers are properly configured.")
            print("🌐 Check network connectivity and server health.")
        
        # Save report to file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = f"rigor_mode_test_report_{timestamp}.json"
        
        report_data = {
            'test_summary': {
                'total_tests': total_tests,
                'passed_tests': passed_tests,
                'total_duration': total_duration,
                'timestamp': datetime.now().isoformat()
            },
            'detailed_results': self.results
        }
        
        with open(report_file, 'w') as f:
            json.dump(report_data, f, indent=2)
        
        print(f"\\n💾 Detailed report saved to: {report_file}")
        
        return passed_tests == total_tests

async def main():
    """Run the comprehensive rigor mode test suite."""
    print("🧪 CrystaLyse.AI Rigor Mode Functionality Test Suite")
    print("="*60)
    
    test_suite = RigorModeTestSuite()
    test_suite.start_time = time.time()
    
    try:
        # Setup
        await test_suite.setup_agent()
        
        # Core functionality tests
        tests = [
            test_suite.test_ferroelectric_materials_design,
            test_suite.test_composition_validation,
            test_suite.test_structure_prediction,
            test_suite.test_energy_analysis,
            test_suite.test_batch_screening
        ]
        
        # Run tests
        print("\\n🚀 Running test suite...")
        for test_func in tests:
            await test_func()
        
        # Generate report
        success = test_suite.generate_report()
        
        return success
        
    except Exception as e:
        print(f"\\n💥 Test suite failed with critical error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)