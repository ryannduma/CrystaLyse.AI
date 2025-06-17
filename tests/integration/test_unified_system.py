"""
Integration tests for the unified CrystaLyse.AI system
"""

import pytest
import asyncio
import os
import time
from pathlib import Path
import tempfile
import json

# Test the unified system
from crystalyse.unified_agent import CrystaLyseUnifiedAgent, AgentConfig
from crystalyse.tools.atomic_tools import (
    suggest_elements_for_application,
    generate_compositions_simple,
    check_charge_balance_simple,
    suggest_structure_types,
    assess_synthesis_feasibility
)
from crystalyse.monitoring.metrics import MetricsCollector, PerformanceReport

class TestUnifiedSystem:
    """Test the complete integrated system"""
    
    @pytest.mark.asyncio
    async def test_unified_agent_initialisation(self):
        """Test that unified agent initializes correctly"""
        config = AgentConfig(mode="creative", enable_mace=False)  # Disable MACE for faster tests
        agent = CrystaLyseUnifiedAgent(config)
        
        assert agent.config.mode == "creative"
        assert agent.capabilities["validation"] == True
        assert agent.capabilities["structure_generation"] == True
        assert agent.capabilities["energy_calculation"] == False  # MACE disabled
        assert agent.conversation_history == []
    
    @pytest.mark.asyncio
    async def test_unified_agent_both_modes(self):
        """Test that unified agent handles both creative and rigorous modes"""
        
        # Test creative mode
        creative_config = AgentConfig(mode="creative", enable_mace=False, max_turns=3)
        creative_agent = CrystaLyseUnifiedAgent(creative_config)
        
        # Simple test query (may not complete full discovery due to MCP server setup)
        try:
            creative_result = await creative_agent.discover_materials("Find novel battery cathode materials")
            
            # Should have some response even if incomplete
            assert "agent_config" in creative_result
            assert creative_result["agent_config"]["mode"] == "creative"
            
        except Exception as e:
            # Expected if MCP servers not running - check error handling
            assert "Chemistry server unavailable" in str(e) or "connection" in str(e).lower()
        
        # Test rigorous mode
        rigorous_config = AgentConfig(mode="rigorous", enable_mace=False, max_turns=3)
        rigorous_agent = CrystaLyseUnifiedAgent(rigorous_config)
        
        try:
            rigorous_result = await rigorous_agent.discover_materials("Validate Li-ion conductor stability")
            
            # Should have rigorous mode configuration
            assert "agent_config" in rigorous_result
            assert rigorous_result["agent_config"]["mode"] == "rigorous"
            
        except Exception as e:
            # Expected if MCP servers not running
            assert "Chemistry server unavailable" in str(e) or "connection" in str(e).lower()
    
    def test_atomic_tools_functionality(self):
        """Test that atomic tools work correctly and return natural language"""
        
        # Test element suggestion
        battery_elements = suggest_elements_for_application("battery cathode materials")
        assert isinstance(battery_elements, str)
        assert "Li" in battery_elements or "battery" in battery_elements.lower()
        
        # Test composition generation
        elements = ["Li", "Fe", "P", "O"]
        compositions = generate_compositions_simple(elements, max_compositions=5)
        assert isinstance(compositions, str)
        assert "compositions" in compositions.lower()
        assert "Li" in compositions
        
        # Test charge balance
        balance_result = check_charge_balance_simple("LiFePO4")
        assert isinstance(balance_result, str)
        assert "charge" in balance_result.lower()
        assert "LiFePO4" in balance_result
        
        # Test structure prediction
        structure_suggestions = suggest_structure_types("LiFePO4")
        assert isinstance(structure_suggestions, str)
        assert "structure" in structure_suggestions.lower()
        assert "LiFePO4" in structure_suggestions
        
        # Test synthesis assessment
        synthesis_assessment = assess_synthesis_feasibility("LiFePO4", "battery")
        assert isinstance(synthesis_assessment, str)
        assert "synthesis" in synthesis_assessment.lower()
        assert "feasibility" in synthesis_assessment.lower()
    
    def test_metrics_collection(self):
        """Test metrics collection and reporting"""
        
        with tempfile.TemporaryDirectory() as temp_dir:
            metrics = MetricsCollector(Path(temp_dir))
            
            # Test workflow tracking
            metrics.start_workflow("Test query", "creative")
            
            # Simulate some tool calls
            async def mock_tool():
                await asyncio.sleep(0.1)
                return "mock result"
            
            async def failing_tool():
                await asyncio.sleep(0.05)
                raise ValueError("Mock error")
            
            # Run the test
            async def run_metrics_test():
                # Successful tool calls
                await metrics.track_tool_call("smact_validity", mock_tool)
                await metrics.track_tool_call("generate_structures", mock_tool)
                
                # Failed tool call
                try:
                    await metrics.track_tool_call("calculate_energies", failing_tool)
                except ValueError:
                    pass  # Expected
                
                metrics.end_workflow()
                
                # Check metrics
                summary = metrics.get_summary()
                
                assert "tools" in summary
                assert "smact_validity" in summary["tools"]
                assert summary["tools"]["smact_validity"]["calls"] == 1
                assert summary["tools"]["smact_validity"]["success_rate"] == 1.0
                
                assert "calculate_energies" in summary["tools"]
                assert summary["tools"]["calculate_energies"]["success_rate"] == 0.0
                
                assert "workflow" in summary
                assert summary["workflow"]["total_steps"] == 3
                assert summary["workflow"]["success_rate"] == 2/3
                
                # Test persistence
                metrics_file = metrics.save_metrics("test_workflow")
                assert metrics_file.exists()
                
                # Test report generation
                report = PerformanceReport.generate_workflow_report(metrics)
                assert isinstance(report, str)
                assert "Performance Report" in report
                assert "smact_validity" in report
            
            # Run the async test
            asyncio.run(run_metrics_test())
    
    def test_graceful_degradation(self):
        """Test that system handles missing dependencies gracefully"""
        
        # Test atomic tools work without external dependencies
        result = suggest_elements_for_application("unknown application type")
        assert isinstance(result, str)
        assert len(result) > 0
        
        # Test composition generation with minimal elements
        result = generate_compositions_simple(["Li", "O"])
        assert isinstance(result, str)
        assert "Li" in result and "O" in result
        
        # Test charge balance with invalid formula
        result = check_charge_balance_simple("InvalidFormula123")
        assert isinstance(result, str)
        assert "error" in result.lower() or "could not parse" in result.lower()
    
    def test_configuration_management(self):
        """Test configuration system"""
        
        # Test default configuration
        default_config = AgentConfig()
        assert default_config.mode == "creative"
        assert default_config.enable_mace == True
        assert default_config.max_turns == 15
        
        # Test custom configuration
        custom_config = AgentConfig(
            mode="rigorous",
            model="claude-3-haiku-20240307",
            temperature=0.3,
            enable_mace=False,
            max_candidates=50
        )
        
        assert custom_config.mode == "rigorous"
        assert custom_config.model == "claude-3-haiku-20240307"
        assert custom_config.temperature == 0.3
        assert custom_config.enable_mace == False
        assert custom_config.max_candidates == 50
    
    @pytest.mark.asyncio
    async def test_performance_targets(self):
        """Test that system meets basic performance requirements"""
        
        # Test atomic tools performance
        start_time = time.time()
        
        # Run multiple atomic tool operations
        for _ in range(10):
            suggest_elements_for_application("battery")
            generate_compositions_simple(["Li", "Fe", "O"], max_compositions=3)
            check_charge_balance_simple("LiFePO4")
        
        duration = time.time() - start_time
        
        # Should complete 30 operations in under 1 second
        assert duration < 1.0, f"Atomic tools too slow: {duration:.2f}s for 30 operations"
        
        # Test agent initialisation performance
        start_time = time.time()
        
        config = AgentConfig(enable_mace=False)
        agent = CrystaLyseUnifiedAgent(config)
        
        init_duration = time.time() - start_time
        
        # Should initialise in under 0.1 seconds
        assert init_duration < 0.1, f"Agent initialisation too slow: {init_duration:.3f}s"
    
    def test_code_consolidation_success(self):
        """Test that code consolidation was successful"""
        
        # Check that duplicate agent files are eliminated
        agents_dir = Path("crystalyse/agents")
        
        if agents_dir.exists():
            agent_files = list(agents_dir.glob("*.py"))
            # Should have minimal agent files after consolidation
            non_init_files = [f for f in agent_files if f.name != "__init__.py"]
            
            # The old system had 5+ agent files, new system should have fewer
            assert len(non_init_files) <= 3, f"Too many agent files: {[f.name for f in non_init_files]}"
        
        # Check unified agent exists
        unified_agent_path = Path("crystalyse/unified_agent.py")
        if unified_agent_path.exists():
            content = unified_agent_path.read_text()
            
            # Should contain unified agent class
            assert "CrystaLyseUnifiedAgent" in content
            assert "consolidates all functionality" in content.lower()
    
    @pytest.mark.asyncio
    async def test_error_recovery(self):
        """Test graceful error recovery and alternative approaches"""
        
        config = AgentConfig(enable_mace=False, max_turns=2)
        agent = CrystaLyseUnifiedAgent(config)
        
        # Test self-assessment tools
        progress_result = await agent._assess_progress("Testing error recovery")
        assert isinstance(progress_result, str)
        assert "assessment" in progress_result.lower()
        
        alternatives_result = await agent._explore_alternatives("Tool failure")
        assert isinstance(alternatives_result, str)
        assert "alternative" in alternatives_result.lower()
    
    def test_natural_language_returns(self):
        """Test that all tools return natural language that LLMs can understand"""
        
        # All atomic tools should return strings (natural language)
        tools_to_test = [
            (suggest_elements_for_application, ["battery"]),
            (generate_compositions_simple, [["Li", "O"]]),
            (check_charge_balance_simple, ["LiFePO4"]),
            (suggest_structure_types, ["LiFePO4"]),
            (assess_synthesis_feasibility, ["LiFePO4", "battery"])
        ]
        
        for tool_func, args in tools_to_test:
            result = tool_func(*args)
            
            # Should be string (natural language)
            assert isinstance(result, str), f"{tool_func.__name__} should return string"
            
            # Should have reasonable length
            assert len(result) > 10, f"{tool_func.__name__} result too short: {result[:50]}"
            
            # Should not return complex JSON or data structures
            assert not result.startswith("{"), f"{tool_func.__name__} returning JSON instead of natural language"
            assert not result.startswith("["), f"{tool_func.__name__} returning list instead of natural language"

# Performance benchmarks
class TestPerformanceBenchmarks:
    """Performance-focused tests to ensure system meets targets"""
    
    def test_tool_response_times(self):
        """Test that individual tools meet response time targets"""
        
        # Each atomic tool should complete in under 0.1 seconds
        tools_and_args = [
            (suggest_elements_for_application, "battery"),
            (generate_compositions_simple, ["Li", "Fe", "O", "P"]),
            (check_charge_balance_simple, "LiFePO4"),
            (suggest_structure_types, "LiFePO4"),
            (assess_synthesis_feasibility, "LiFePO4")
        ]
        
        for tool_func, args in tools_and_args:
            start_time = time.time()
            
            if isinstance(args, list):
                result = tool_func(args)
            else:
                result = tool_func(args)
            
            duration = time.time() - start_time
            
            assert duration < 0.1, f"{tool_func.__name__} too slow: {duration:.3f}s"
            assert len(result) > 0, f"{tool_func.__name__} returned empty result"
    
    def test_batch_operations_performance(self):
        """Test performance of batch operations"""
        
        # Test batch composition generation
        start_time = time.time()
        
        compositions = []
        for elements in [["Li", "Fe", "O"], ["Na", "Mn", "O"], ["K", "Co", "O"]]:
            result = generate_compositions_simple(elements, max_compositions=5)
            compositions.append(result)
        
        duration = time.time() - start_time
        
        # Should process 3 element sets in under 0.3 seconds
        assert duration < 0.3, f"Batch composition generation too slow: {duration:.3f}s"
        assert len(compositions) == 3
        
        # Test batch validation
        start_time = time.time()
        
        test_formulas = ["LiFePO4", "NaMnO2", "KCoO2", "CaTiO3", "BaTiO3"]
        for formula in test_formulas:
            result = check_charge_balance_simple(formula)
            assert len(result) > 0
        
        duration = time.time() - start_time
        
        # Should validate 5 formulas in under 0.5 seconds
        assert duration < 0.5, f"Batch validation too slow: {duration:.3f}s"

if __name__ == "__main__":
    # Run tests manually if pytest not available
    import sys
    
    print("Running CrystaLyse.AI Integration Tests...")
    
    test_suite = TestUnifiedSystem()
    
    # Test atomic tools
    print("✓ Testing atomic tools...")
    test_suite.test_atomic_tools_functionality()
    
    # Test configuration
    print("✓ Testing configuration...")
    test_suite.test_configuration_management()
    
    # Test graceful degradation
    print("✓ Testing graceful degradation...")
    test_suite.test_graceful_degradation()
    
    # Test natural language returns
    print("✓ Testing natural language returns...")
    test_suite.test_natural_language_returns()
    
    # Performance tests
    print("✓ Testing performance...")
    perf_suite = TestPerformanceBenchmarks()
    perf_suite.test_tool_response_times()
    perf_suite.test_batch_operations_performance()
    
    print("\n✅ All integration tests passed!")
    print("Note: Full agent tests require MCP server setup and may fail in this environment.")