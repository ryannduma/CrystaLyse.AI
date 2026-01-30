"""Tests for tool classification module."""

from crystalyse.agents.tool_classification import (
    PARALLEL_TOOLS,
    SERIAL_TOOLS,
    ToolSpec,
    classify_tool,
    create_tool_spec,
    create_tool_specs,
    get_parallel_tools,
    get_serial_tools,
)


class TestToolClassification:
    """Tests for classify_tool function."""

    def test_parallel_tools_classified_correctly(self):
        """Test that parallel tools are classified as parallel."""
        for tool_name in PARALLEL_TOOLS:
            assert classify_tool(tool_name) is True, f"{tool_name} should be parallel"

    def test_serial_tools_classified_correctly(self):
        """Test that serial tools are classified as serial."""
        for tool_name in SERIAL_TOOLS:
            assert classify_tool(tool_name) is False, f"{tool_name} should be serial"

    def test_unknown_tool_defaults_to_serial(self):
        """Test that unknown tools default to serial (safer)."""
        assert classify_tool("unknown_dangerous_tool") is False

    def test_query_optimade_is_parallel(self):
        """Test specific parallel tool."""
        assert classify_tool("query_optimade") is True

    def test_run_shell_command_is_serial(self):
        """Test specific serial tool."""
        assert classify_tool("run_shell_command") is False


class TestToolSpec:
    """Tests for ToolSpec dataclass."""

    def test_tool_spec_creation(self):
        """Test creating a ToolSpec."""
        spec = ToolSpec(
            name="test_tool",
            handler=lambda: None,
            supports_parallel=True,
            description="A test tool",
        )
        assert spec.name == "test_tool"
        assert spec.supports_parallel is True
        assert spec.description == "A test tool"

    def test_tool_spec_default_values(self):
        """Test ToolSpec default values."""
        spec = ToolSpec(name="test", handler=lambda: None)
        assert spec.supports_parallel is True  # Default
        assert spec.description == ""  # Default


class TestCreateToolSpec:
    """Tests for create_tool_spec function."""

    def test_creates_spec_from_function(self):
        """Test creating spec from a function."""

        def my_tool():
            """My tool description."""
            pass

        spec = create_tool_spec(my_tool)
        assert spec.name == "my_tool"
        assert spec.handler is my_tool
        assert "My tool description" in spec.description

    def test_handles_no_docstring(self):
        """Test handling function without docstring."""

        def nodoc_tool():
            pass

        spec = create_tool_spec(nodoc_tool)
        assert spec.description == ""

    def test_classifies_parallel_tool(self):
        """Test that known parallel tools are classified."""

        def query_optimade():
            """Query OPTIMADE databases."""
            pass

        spec = create_tool_spec(query_optimade)
        assert spec.supports_parallel is True

    def test_classifies_serial_tool(self):
        """Test that known serial tools are classified."""

        def run_shell_command():
            """Run shell command."""
            pass

        spec = create_tool_spec(run_shell_command)
        assert spec.supports_parallel is False


class TestCreateToolSpecs:
    """Tests for create_tool_specs function."""

    def test_creates_multiple_specs(self):
        """Test creating specs for multiple tools."""

        def tool1():
            pass

        def tool2():
            pass

        specs = create_tool_specs([tool1, tool2])
        assert len(specs) == 2
        assert specs[0].name == "tool1"
        assert specs[1].name == "tool2"

    def test_empty_list(self):
        """Test with empty list."""
        specs = create_tool_specs([])
        assert specs == []


class TestGetParallelSerialTools:
    """Tests for filtering functions."""

    def test_get_parallel_tools(self):
        """Test filtering to parallel tools."""
        specs = [
            ToolSpec(name="parallel1", handler=lambda: None, supports_parallel=True),
            ToolSpec(name="serial1", handler=lambda: None, supports_parallel=False),
            ToolSpec(name="parallel2", handler=lambda: None, supports_parallel=True),
        ]
        parallel = get_parallel_tools(specs)
        assert len(parallel) == 2
        assert all(s.supports_parallel for s in parallel)

    def test_get_serial_tools(self):
        """Test filtering to serial tools."""
        specs = [
            ToolSpec(name="parallel1", handler=lambda: None, supports_parallel=True),
            ToolSpec(name="serial1", handler=lambda: None, supports_parallel=False),
            ToolSpec(name="serial2", handler=lambda: None, supports_parallel=False),
        ]
        serial = get_serial_tools(specs)
        assert len(serial) == 2
        assert all(not s.supports_parallel for s in serial)


class TestToolSets:
    """Tests for the tool set constants."""

    def test_parallel_and_serial_are_disjoint(self):
        """Test that no tool appears in both sets."""
        overlap = PARALLEL_TOOLS & SERIAL_TOOLS
        assert len(overlap) == 0, f"Tools in both sets: {overlap}"

    def test_parallel_tools_not_empty(self):
        """Test that parallel tools set is populated."""
        assert len(PARALLEL_TOOLS) > 0

    def test_serial_tools_not_empty(self):
        """Test that serial tools set is populated."""
        assert len(SERIAL_TOOLS) > 0

    def test_sets_are_frozen(self):
        """Test that tool sets are immutable."""
        assert isinstance(PARALLEL_TOOLS, frozenset)
        assert isinstance(SERIAL_TOOLS, frozenset)
