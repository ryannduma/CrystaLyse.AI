# SMACT MCP Server

Model Context Protocol (MCP) server that exposes SMACT (Semiconducting Materials from Analogy and Chemical Theory) functionality to LLMs for materials discovery.

## Features

- **smact_validity**: Check if a composition is valid according to SMACT rules
- **neutral_ratios**: Calculate charge-neutral stoichiometric ratios  
- **parse_formula**: Parse chemical formulas into element counts
- **element_info**: Get detailed element properties
- **pauling_test**: Check electronegativity ordering between cations and anions

## Installation

```bash
# Install uv if you haven't already
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install the server
cd smact-mcp-server
uv venv
source .venv/bin/activate
uv pip install -e .
```

## Usage

### As MCP Server
```bash
# Run the server
uv run smact-mcp
```

### With Claude Desktop

Add to your `claude_desktop_config.json`:

```json
{
    "mcpServers": {
        "smact": {
            "command": "uv",
            "args": [
                "run",
                "--directory",
                "/path/to/smact-mcp-server",
                "smact-mcp"
            ]
        }
    }
}
```

## Development

```bash
# Install with dev dependencies
uv pip install -e ".[dev]"

# Run tests
pytest

# Format code
ruff format .

# Check code
ruff check .
```