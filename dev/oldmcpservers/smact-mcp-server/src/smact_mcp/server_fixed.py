"""Fixed SMACT MCP Server using working pattern."""

import sys
import json
from pathlib import Path

import anyio
import mcp.types as types
from mcp.server.lowlevel import Server

# Add the SMACT library to the path
SMACT_PATH = Path(__file__).parent.parent.parent.parent / "CrystaLyse.AI" / "smact"
sys.path.insert(0, str(SMACT_PATH))


def main():
    """Main SMACT MCP server."""
    app = Server("smact-materials")
    
    @app.list_tools()
    async def list_tools() -> list[types.Tool]:
        """List all available SMACT tools."""
        print("DEBUG SMACT list_tools() called!")
        
        return [
            types.Tool(
                name="check_smact_validity",
                description="Check if a composition is valid according to SMACT rules",
                inputSchema={
                    "type": "object",
                    "required": ["composition"],
                    "properties": {
                        "composition": {
                            "type": "string",
                            "description": "Chemical formula (e.g., 'LiFePO4', 'CaTiO3')"
                        }
                    }
                }
            ),
            types.Tool(
                name="parse_chemical_formula",
                description="Parse a chemical formula into element counts",
                inputSchema={
                    "type": "object", 
                    "required": ["formula"],
                    "properties": {
                        "formula": {
                            "type": "string",
                            "description": "Chemical formula (e.g., 'Ca(OH)2', 'Fe2O3')"
                        }
                    }
                }
            ),
            types.Tool(
                name="get_element_info",
                description="Get detailed information about a chemical element",
                inputSchema={
                    "type": "object",
                    "required": ["symbol"],
                    "properties": {
                        "symbol": {
                            "type": "string",
                            "description": "Chemical symbol (e.g., 'Fe', 'O', 'Li')"
                        }
                    }
                }
            ),
            types.Tool(
                name="calculate_neutral_ratios",
                description="Calculate charge-neutral stoichiometric ratios for given oxidation states",
                inputSchema={
                    "type": "object",
                    "required": ["oxidation_states"],
                    "properties": {
                        "oxidation_states": {
                            "type": "array",
                            "items": {"type": "integer"},
                            "description": "List of oxidation states (e.g., [1, -2] for Na+ and O2-)"
                        },
                        "threshold": {
                            "type": "integer",
                            "description": "Maximum stoichiometric coefficient to try",
                            "default": 5
                        }
                    }
                }
            )
        ]
    
    @app.call_tool()
    async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
        """Handle tool calls."""
        print(f"DEBUG SMACT call_tool() called with: {name}, {arguments}")
        
        try:
            if name == "check_smact_validity":
                result = check_smact_validity_sync(arguments["composition"])
            elif name == "parse_chemical_formula":
                result = parse_chemical_formula_sync(arguments["formula"])
            elif name == "get_element_info":
                result = get_element_info_sync(arguments["symbol"])
            elif name == "calculate_neutral_ratios":
                result = calculate_neutral_ratios_sync(
                    arguments["oxidation_states"],
                    arguments.get("threshold", 5)
                )
            else:
                raise ValueError(f"Unknown tool: {name}")
                
            return [types.TextContent(type="text", text=result)]
            
        except Exception as e:
            error_result = json.dumps({
                "error": str(e),
                "tool": name,
                "arguments": arguments
            }, indent=2)
            return [types.TextContent(type="text", text=error_result)]

    # Run with stdio
    from mcp.server.stdio import stdio_server

    async def arun():
        print("Starting SMACT MCP server...")
        async with stdio_server() as streams:
            await app.run(
                streams[0], streams[1], app.create_initialization_options()
            )

    anyio.run(arun)


def check_smact_validity_sync(composition: str) -> str:
    """Synchronous SMACT validity check."""
    try:
        # Import here to avoid startup issues
        import smact
        from smact.screening import smact_validity
        from pymatgen.core import Composition
        
        # Parse and validate composition
        comp = Composition(composition)
        is_valid = smact_validity(comp)
        
        result = {
            "composition": composition,
            "is_valid": is_valid,
            "elements": list(comp.as_dict().keys()),
            "message": f"SMACT validity check: {'VALID' if is_valid else 'INVALID'}"
        }
        
        return json.dumps(result, indent=2)
        
    except Exception as e:
        return json.dumps({
            "error": str(e),
            "composition": composition,
            "is_valid": False
        }, indent=2)


def parse_chemical_formula_sync(formula: str) -> str:
    """Synchronous formula parsing."""
    try:
        # Import here to avoid startup issues
        from smact.utils.composition import parse_formula
        
        # Parse formula
        element_counts = parse_formula(formula)
        total_atoms = sum(element_counts.values())
        
        result = {
            "formula": formula,
            "element_counts": element_counts,
            "total_atoms": total_atoms,
            "message": f"Parsed {len(element_counts)} unique elements"
        }
        
        return json.dumps(result, indent=2)
        
    except Exception as e:
        return json.dumps({
            "error": str(e),
            "formula": formula
        }, indent=2)


def get_element_info_sync(symbol: str) -> str:
    """Synchronous element info lookup."""
    try:
        # Import here to avoid startup issues
        from smact import Element
        
        # Get element
        elem = Element(symbol)
        
        result = {
            "symbol": elem.symbol,
            "name": elem.name,
            "atomic_number": elem.number,
            "atomic_mass": elem.mass,
            "electronegativity": elem.pauling_eneg,
            "covalent_radius": elem.cov_radius,
            "oxidation_states": {
                "icsd24": getattr(elem, 'oxidation_states_icsd24', []),
                "wiki": getattr(elem, 'oxidation_states_wiki', [])
            },
            "message": f"Element data for {elem.name} ({symbol})"
        }
        
        return json.dumps(result, indent=2)
        
    except Exception as e:
        return json.dumps({
            "error": str(e),
            "symbol": symbol
        }, indent=2)


def calculate_neutral_ratios_sync(oxidation_states: list, threshold: int = 5) -> str:
    """Synchronous neutral ratios calculation."""
    try:
        # Import here to avoid startup issues
        from smact import neutral_ratios
        
        # Calculate neutral ratios
        cn_e, cn_r = neutral_ratios(oxidation_states, stoichs=False, threshold=threshold)
        
        result = {
            "oxidation_states": oxidation_states,
            "charge_neutral": cn_e,
            "neutral_ratios": [list(ratio) for ratio in cn_r] if cn_e else [],
            "threshold": threshold,
            "message": f"Found {len(cn_r) if cn_r else 0} charge-neutral combinations"
        }
        
        # Add example formulas if neutral
        if cn_e and cn_r:
            examples = []
            for i, ratio in enumerate(cn_r[:3]):  # Show up to 3 examples
                formula_parts = []
                for j, (ox, count) in enumerate(zip(oxidation_states, ratio)):
                    if count > 1:
                        formula_parts.append(f"X{j+1}_{count}")
                    else:
                        formula_parts.append(f"X{j+1}")
                examples.append({
                    "ratio": list(ratio),
                    "example_formula": "".join(formula_parts),
                    "total_charge": sum(ox * c for ox, c in zip(oxidation_states, ratio))
                })
            result["examples"] = examples
        
        return json.dumps(result, indent=2)
        
    except Exception as e:
        return json.dumps({
            "error": str(e),
            "oxidation_states": oxidation_states,
            "charge_neutral": False
        }, indent=2)


if __name__ == "__main__":
    main()