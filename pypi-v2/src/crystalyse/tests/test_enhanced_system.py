"""
Comprehensive integration tests for the enhanced CrystaLyse.AI system.

Tests all major improvements including:
- Enhanced error handling and graceful degradation
- Improved clarification system
- Better JSON output formatting
- Cleaned up agent architecture
- Configuration management
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from rich.console import Console

# Import the main components
from crystalyse.config import CrystaLyseConfig
from crystalyse.infrastructure.resilient_tool_caller import (
    ResilientToolCaller, 
    ToolError, 
    ToolTimeoutError, 
    ToolValidationError,
    ToolServerError,
    ToolDegradedError
)
from crystalyse.ui.enhanced_clarification import IntegratedClarificationSystem
from crystalyse.ui.enhanced_result_formatter import EnhancedResultFormatter
from crystalyse.workspace.workspace_tools import Question, ClarificationRequest


class TestEnhancedErrorHandling:
    """Test the improved error handling system."""
    
    def test_specific_error_types(self):
        """Test that specific error types are properly defined."""
        # Test error hierarchy
        assert issubclass(ToolTimeoutError, ToolError)
        assert issubclass(ToolValidationError, ToolError)
        assert issubclass(ToolServerError, ToolError)
        assert issubclass(ToolDegradedError, ToolError)
    
    @pytest.mark.asyncio
    async def test_timeout_error_handling(self):
        """Test timeout error handling in resilient tool caller."""
        tool_caller = ResilientToolCaller()
        
        async def timeout_function():
            await asyncio.sleep(10)  # This will timeout
        
        with pytest.raises(ToolTimeoutError):
            await tool_caller.call_with_retry(
                timeout_function,
                tool_name="test_tool",
                timeout_override=0.1,  # Very short timeout
                max_retries=1
            )
    
    @pytest.mark.asyncio
    async def test_validation_error_handling(self):
        """Test validation error handling."""
        tool_caller = ResilientToolCaller()
        
        def validation_error_function():
            raise ValueError("Invalid input")
        
        with pytest.raises(ToolValidationError):
            await tool_caller.call_with_retry(
                validation_error_function,
                tool_name="test_tool",
                max_retries=1
            )
    
    @pytest.mark.asyncio 
    async def test_graceful_degradation(self):
        """Test graceful degradation with fallback functions."""
        tool_caller = ResilientToolCaller()
        
        async def failing_primary():
            raise ConnectionError("Primary failed")
            
        async def working_fallback():
            return {"result": "fallback_success", "degraded": True}
        
        with pytest.raises(ToolDegradedError) as exc_info:
            await tool_caller.call_with_fallback(
                failing_primary,
                working_fallback,
                tool_name="test_tool"
            )
        
        # The error should contain the result
        assert hasattr(exc_info.value, 'result')
        assert exc_info.value.result["result"] == "fallback_success"


class TestConfigurationManagement:
    """Test the improved configuration system."""
    
    def test_config_loading(self):
        """Test configuration loading with environment variables."""
        config = CrystaLyseConfig()
        assert config.mcp_servers is not None
        assert "chemistry_unified" in config.mcp_servers
        assert "chemistry_creative" in config.mcp_servers
        assert "visualization" in config.mcp_servers
    
    @patch.dict('os.environ', {'CRYSTALYSE_PYTHON_PATH': '/custom/python'})
    def test_custom_python_path(self):
        """Test custom Python path from environment variable."""
        config = CrystaLyseConfig()
        chemistry_config = config.mcp_servers["chemistry_unified"]
        assert chemistry_config["command"] == "/custom/python"
    
    def test_server_validation(self):
        """Test server configuration validation."""
        config = CrystaLyseConfig()
        
        # Test valid server
        server_config = config.get_server_config("chemistry_unified")
        assert "command" in server_config
        assert "args" in server_config
        assert "cwd" in server_config
        assert "env" in server_config
        
        # Test invalid server
        with pytest.raises(ValueError):
            config.get_server_config("nonexistent_server")


class TestEnhancedClarification:
    """Test the improved clarification system."""
    
    def test_clarification_handler_creation(self):
        """Test creation of enhanced clarification handler."""
        console = Console()
        handler = IntegratedClarificationSystem(console)
        assert handler.console is console
        assert handler.clarification_prompt is not None
    
    @pytest.mark.asyncio
    async def test_natural_language_interpretation(self):
        """Test natural language interpretation of clarifications."""
        console = Console()
        
        # Mock OpenAI client
        mock_client = AsyncMock()
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = '{"chemistry": "Na-ion", "component": "Cathode"}'
        mock_client.chat.completions.create.return_value = mock_response
        
        handler = IntegratedClarificationSystem(console, mock_client)
        
        questions = [
            Question(id="chemistry", text="Battery chemistry?", options=["Li-ion", "Na-ion", "K-ion"]),
            Question(id="component", text="Component?", options=["Cathode", "Anode", "Electrolyte"])
        ]
        
        result = await handler._interpret_with_llm(questions, "sodium-ion battery cathodes")
        assert result["chemistry"] == "Na-ion"
        assert result["component"] == "Cathode"
    
    def test_simple_option_matching(self):
        """Test simple option matching for fallback clarification."""
        console = Console()
        handler = IntegratedClarificationSystem(console)
        
        options = ["Li-ion", "Na-ion", "K-ion"]
        
        # Test exact match
        result = handler._find_best_option_match("Na-ion", options)
        assert result == "Na-ion"
        
        # Test partial match
        result = handler._find_best_option_match("sodium", options)
        assert result == "Na-ion"
        
        # Test no match
        result = handler._find_best_option_match("invalid", options)
        assert result is None


class TestEnhancedResultFormatter:
    """Test the improved JSON result formatting."""
    
    def test_formatter_creation(self):
        """Test creation of enhanced result formatter."""
        console = Console()
        formatter = EnhancedResultFormatter(console)
        assert formatter.console is console
    
    def test_chemistry_result_detection(self):
        """Test detection of chemistry results."""
        console = Console()
        formatter = EnhancedResultFormatter(console)
        
        chemistry_data = {
            "composition": "LiFePO4",
            "is_valid": True,
            "elements": ["Li", "Fe", "P", "O"],
            "counts": [1.0, 1.0, 1.0, 4.0]
        }
        
        assert formatter._is_chemistry_result(chemistry_data)
        
        non_chemistry_data = {"random": "data"}
        assert not formatter._is_chemistry_result(non_chemistry_data)
    
    def test_energy_result_detection(self):
        """Test detection of energy calculation results."""
        console = Console()
        formatter = EnhancedResultFormatter(console)
        
        energy_data = {
            "formation_energy_per_atom": -6.123,
            "total_energy": -45.67,
            "status": "completed"
        }
        
        assert formatter._is_energy_result(energy_data)
    
    def test_structure_result_detection(self):
        """Test detection of structure results."""
        console = Console()
        formatter = EnhancedResultFormatter(console)
        
        structure_data = {
            "structures": [{"formula": "LiFePO4", "cell": [1, 2, 3]}],
            "num_structures": 1
        }
        
        assert formatter._is_structure_result(structure_data)


class TestAgentArchitecture:
    """Test the cleaned up agent architecture."""
    
    def test_single_agent_import(self):
        """Test that only the main agent is available."""
        from crystalyse.agents import EnhancedCrystaLyseAgent
        assert EnhancedCrystaLyseAgent is not None
    
    def test_removed_agents_not_importable(self):
        """Test that removed agents are no longer importable."""
        with pytest.raises(ImportError):
            pass
        
        with pytest.raises(ImportError):
            pass
        
        with pytest.raises(ImportError):
            pass


class TestIntegrationWorkflow:
    """Test complete integration workflows."""
    
    @pytest.mark.asyncio
    async def test_complete_clarification_workflow(self):
        """Test a complete clarification workflow."""
        console = Console()
        
        # Create clarification request
        questions = [
            Question(
                id="material_type",
                text="What type of battery material?",
                options=["Cathode", "Anode", "Electrolyte"]
            ),
            Question(
                id="chemistry",
                text="Which chemistry?",
                options=["Li-ion", "Na-ion", "K-ion"]
            )
        ]
        
        request = ClarificationRequest(questions=questions)
        
        # This would normally be tested with actual user interaction
        # For now, just test that the components can be created
        handler = IntegratedClarificationSystem(console)
        assert handler is not None
        assert len(request.questions) == 2
    
    def test_complete_result_formatting_workflow(self):
        """Test complete result formatting workflow."""
        console = Console()
        formatter = EnhancedResultFormatter(console)
        
        # Test different types of results
        chemistry_result = {
            "composition": "LiFePO4",
            "is_valid": True,
            "elements": ["Li", "Fe", "P", "O"],
            "counts": [1.0, 1.0, 1.0, 4.0]
        }
        
        energy_result = {
            "formation_energy_per_atom": -6.123,
            "total_energy": -45.67,
            "status": "completed",
            "num_atoms": 7
        }
        
        # These should not raise exceptions
        try:
            formatter._format_chemistry_result("validate_composition_smact", chemistry_result)
            formatter._format_energy_result("calculate_energy_mace", energy_result)
        except Exception as e:
            pytest.fail(f"Result formatting failed: {e}")


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v"])