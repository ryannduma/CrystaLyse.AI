"""
MCP Server Test Fixtures.

Provides stream spy pattern and mock server fixtures for testing MCP servers.
Pattern inspired by the MCP Python SDK testing approach.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

# =============================================================================
# Stream Spy Pattern (from MCP SDK)
# =============================================================================


@dataclass
class MCPMessage:
    """Represents an MCP protocol message."""

    method: str
    params: dict[str, Any] | None = None
    result: Any = None
    error: dict[str, Any] | None = None
    message_id: str | None = None
    is_request: bool = True


@dataclass
class StreamSpyCollection:
    """Intercept and inspect MCP messages for testing.

    This class captures all messages flowing between client and server,
    allowing tests to verify the correct sequence of tool calls and responses.
    """

    client_requests: list[MCPMessage] = field(default_factory=list)
    server_responses: list[MCPMessage] = field(default_factory=list)

    def record_request(
        self, method: str, params: dict[str, Any] | None = None, message_id: str | None = None
    ) -> None:
        """Record a client request.

        Args:
            method: MCP method name (e.g., "tools/call")
            params: Request parameters
            message_id: Optional message ID
        """
        self.client_requests.append(
            MCPMessage(method=method, params=params, message_id=message_id, is_request=True)
        )

    def record_response(
        self,
        method: str,
        result: Any = None,
        error: dict[str, Any] | None = None,
        message_id: str | None = None,
    ) -> None:
        """Record a server response.

        Args:
            method: MCP method name
            result: Response result (if successful)
            error: Error dict (if failed)
            message_id: Optional message ID
        """
        self.server_responses.append(
            MCPMessage(
                method=method, result=result, error=error, message_id=message_id, is_request=False
            )
        )

    def get_client_requests(self, method: str | None = None) -> list[MCPMessage]:
        """Get client requests, optionally filtered by method.

        Args:
            method: Filter to specific method (None for all)

        Returns:
            List of matching MCPMessage objects
        """
        if method is None:
            return self.client_requests
        return [msg for msg in self.client_requests if msg.method == method]

    def get_server_responses(self, method: str | None = None) -> list[MCPMessage]:
        """Get server responses, optionally filtered by method.

        Args:
            method: Filter to specific method (None for all)

        Returns:
            List of matching MCPMessage objects
        """
        if method is None:
            return self.server_responses
        return [msg for msg in self.server_responses if msg.method == method]

    def get_tool_calls(self) -> list[MCPMessage]:
        """Get all tool call requests.

        Returns:
            List of tools/call messages
        """
        return self.get_client_requests("tools/call")

    def get_tool_call_results(self) -> list[MCPMessage]:
        """Get all tool call responses.

        Returns:
            List of tools/call response messages
        """
        return self.get_server_responses("tools/call")

    def clear(self) -> None:
        """Clear all recorded messages."""
        self.client_requests.clear()
        self.server_responses.clear()

    def assert_tool_called(self, tool_name: str) -> MCPMessage:
        """Assert that a specific tool was called.

        Args:
            tool_name: Name of the tool to check

        Returns:
            The matching MCPMessage

        Raises:
            AssertionError: If tool was not called
        """
        tool_calls = self.get_tool_calls()
        for call in tool_calls:
            if call.params and call.params.get("name") == tool_name:
                return call
        raise AssertionError(
            f"Tool '{tool_name}' was not called. Called tools: {[c.params.get('name') for c in tool_calls if c.params]}"
        )

    def assert_tool_not_called(self, tool_name: str) -> None:
        """Assert that a specific tool was NOT called.

        Args:
            tool_name: Name of the tool to check

        Raises:
            AssertionError: If tool was called
        """
        tool_calls = self.get_tool_calls()
        for call in tool_calls:
            if call.params and call.params.get("name") == tool_name:
                raise AssertionError(f"Tool '{tool_name}' was called but should not have been")


@pytest.fixture
def stream_spy() -> StreamSpyCollection:
    """Provide a fresh StreamSpyCollection for testing.

    Returns:
        New StreamSpyCollection instance
    """
    return StreamSpyCollection()


# =============================================================================
# Mock MCP Server Fixtures
# =============================================================================


@pytest.fixture
def mock_chemistry_tool_responses() -> dict[str, Any]:
    """Predefined responses for chemistry tools.

    Returns:
        Dictionary mapping tool names to their mock responses
    """
    return {
        "validate_composition": {
            "valid": True,
            "formula": "CaTiO3",
            "charge_balanced": True,
            "oxidation_states": {"Ca": 2, "Ti": 4, "O": -2},
            "message": "Valid composition",
        },
        "analyze_stability": {
            "formula": "CaTiO3",
            "stable": True,
            "smact_valid": True,
            "electronegativity_difference": 2.1,
            "bonding_character": "ionic",
            "stability_prediction": "stable",
        },
        "predict_structure": {
            "success": True,
            "formula": "CaTiO3",
            "numbers": [20, 22, 8, 8, 8],
            "positions": [
                [0.0, 0.0, 0.0],
                [1.95, 1.95, 1.95],
                [1.95, 0.0, 1.95],
                [0.0, 1.95, 1.95],
                [1.95, 1.95, 0.0],
            ],
            "cell": [[3.9, 0.0, 0.0], [0.0, 3.9, 0.0], [0.0, 0.0, 3.9]],
            "confidence": 0.85,
        },
        "calculate_formation_energy": {
            "success": True,
            "formula": "CaTiO3",
            "energy": -25.5,
            "energy_per_atom": -5.1,
            "formation_energy": -1.2,
        },
        "relax_structure": {
            "success": True,
            "formula": "CaTiO3",
            "relaxed": True,
            "initial_energy": -24.8,
            "final_energy": -25.5,
            "max_force": 0.001,
        },
    }


@pytest.fixture
def mock_visualization_tool_responses() -> dict[str, Any]:
    """Predefined responses for visualization tools.

    Returns:
        Dictionary mapping tool names to their mock responses
    """
    return {
        "visualize_structure": {
            "success": True,
            "html_path": "/tmp/structure_viz.html",
            "png_path": "/tmp/structure_viz.png",
        },
        "generate_cif": {
            "success": True,
            "cif_content": "data_CaTiO3\n_cell_length_a 3.9\n...",
            "file_path": "/tmp/CaTiO3.cif",
        },
    }


def create_mock_tool_handler(responses: dict[str, Any]) -> AsyncMock:
    """Create a mock tool handler that returns predefined responses.

    Args:
        responses: Dictionary mapping tool names to responses

    Returns:
        AsyncMock configured to return appropriate responses
    """

    async def handler(name: str, arguments: dict[str, Any]) -> dict[str, Any]:  # noqa: ARG001
        if name in responses:
            # Return a copy to avoid mutation
            return dict(responses[name])
        return {"error": f"Unknown tool: {name}"}

    return AsyncMock(side_effect=handler)


@pytest.fixture
def mock_mcp_tool_handler(mock_chemistry_tool_responses: dict[str, Any]) -> AsyncMock:
    """Create a mock MCP tool handler.

    Args:
        mock_chemistry_tool_responses: Predefined tool responses

    Returns:
        AsyncMock that simulates MCP tool handling
    """
    return create_mock_tool_handler(mock_chemistry_tool_responses)


# =============================================================================
# MCP Server Simulation Fixtures
# =============================================================================


@dataclass
class MockMCPServer:
    """Simulates an MCP server for testing."""

    name: str
    tools: dict[str, dict[str, Any]]
    _handler: AsyncMock | None = None

    async def handle_tool_call(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Handle a tool call.

        Args:
            tool_name: Name of the tool to call
            arguments: Tool arguments

        Returns:
            Tool result dictionary
        """
        if self._handler:
            return await self._handler(tool_name, arguments)
        if tool_name in self.tools:
            return dict(self.tools[tool_name])
        return {"error": f"Tool {tool_name} not found"}

    def list_tools(self) -> list[dict[str, Any]]:
        """List available tools.

        Returns:
            List of tool definitions
        """
        return [{"name": name, "description": f"Mock {name} tool"} for name in self.tools]


@pytest.fixture
def mock_chemistry_creative_server(mock_chemistry_tool_responses: dict[str, Any]) -> MockMCPServer:
    """Create a mock chemistry creative server.

    Args:
        mock_chemistry_tool_responses: Tool responses

    Returns:
        MockMCPServer configured for chemistry-creative
    """
    # Filter to only creative-mode tools
    creative_tools = {
        "predict_structure": mock_chemistry_tool_responses["predict_structure"],
        "calculate_formation_energy": mock_chemistry_tool_responses["calculate_formation_energy"],
        "relax_structure": mock_chemistry_tool_responses["relax_structure"],
    }
    return MockMCPServer(name="chemistry-creative", tools=creative_tools)


@pytest.fixture
def mock_chemistry_unified_server(mock_chemistry_tool_responses: dict[str, Any]) -> MockMCPServer:
    """Create a mock chemistry unified server.

    Args:
        mock_chemistry_tool_responses: Tool responses

    Returns:
        MockMCPServer configured for chemistry-unified
    """
    return MockMCPServer(name="chemistry-unified", tools=mock_chemistry_tool_responses)


@pytest.fixture
def mock_visualization_server(mock_visualization_tool_responses: dict[str, Any]) -> MockMCPServer:
    """Create a mock visualization server.

    Args:
        mock_visualization_tool_responses: Tool responses

    Returns:
        MockMCPServer configured for visualization
    """
    return MockMCPServer(name="visualization", tools=mock_visualization_tool_responses)


# =============================================================================
# Connection Pool Mocking
# =============================================================================


@pytest.fixture
def mock_mcp_connection_pool():
    """Create a mock MCP connection pool.

    Returns:
        MagicMock simulating MCPConnectionPool
    """
    pool = MagicMock()
    pool.get_connection = AsyncMock()
    pool.release_connection = AsyncMock()
    pool.close_all = AsyncMock()
    return pool


# =============================================================================
# Utility Functions
# =============================================================================


async def simulate_tool_call(
    server: MockMCPServer,
    stream_spy: StreamSpyCollection,
    tool_name: str,
    arguments: dict[str, Any],
) -> dict[str, Any]:
    """Simulate a tool call through a mock server with stream spy.

    Args:
        server: Mock MCP server
        stream_spy: Stream spy to record messages
        tool_name: Name of tool to call
        arguments: Tool arguments

    Returns:
        Tool result dictionary
    """
    # Record the request
    stream_spy.record_request("tools/call", params={"name": tool_name, "arguments": arguments})

    # Execute the tool
    try:
        result = await server.handle_tool_call(tool_name, arguments)
        stream_spy.record_response("tools/call", result=result)
        return result
    except Exception as e:
        error = {"code": -1, "message": str(e)}
        stream_spy.record_response("tools/call", error=error)
        raise
