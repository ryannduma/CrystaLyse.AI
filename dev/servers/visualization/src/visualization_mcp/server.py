"""Visualization MCP Server for CrystaLyse.AI"""

from mcp.server.fastmcp import FastMCP
from .tools import (
    create_3dmol_visualization,
    create_pymatviz_analysis_suite,
    create_creative_visualization,
    create_rigorous_visualization,
    create_mode_aligned_visualization
)

mcp = FastMCP("visualization")

# Register tools
mcp.tool()(create_3dmol_visualization)
mcp.tool()(create_pymatviz_analysis_suite)
mcp.tool()(create_creative_visualization)
mcp.tool()(create_rigorous_visualization)
mcp.tool()(create_mode_aligned_visualization)

if __name__ == "__main__":
    mcp.run()
