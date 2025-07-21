"""SMACT MCP Server using low-level MCP protocol."""

import sys
import os
import json
import asyncio
import logging
from pathlib import Path
from typing import List, Optional, Dict, Any

import anyio
import click
import mcp.types as types
from mcp.server.lowlevel import Server

# Add the SMACT library to the path
SMACT_PATH = Path(__file__).parent.parent.parent.parent / "CrystaLyse.AI" / "smact"
sys.path.insert(0, str(SMACT_PATH))

# Import SMACT modules
import smact
from smact import Element, neutral_ratios
from smact.screening import smact_validity, pauling_test
from smact.utils.composition import parse_formula
try:
    from smact.metallicity import metallicity_score
    METALLICITY_AVAILABLE = True
except ImportError:
    METALLICITY_AVAILABLE = False

# Configure logging
logging.basicConfig(level=logging.INFO, stream=sys.stderr)
logger = logging.getLogger(__name__)


@click.command()
@click.option("--port", default=8000, help="Port to listen on for SSE")
@click.option(
    "--transport",
    type=click.Choice(["stdio", "sse"]),
    default="stdio",
    help="Transport type",
)
def main(port: int, transport: str) -> int:
    """Main SMACT MCP server."""
    app = Server("smact-materials")
    
    @app.list_tools()
    async def list_tools() -> list[types.Tool]:
        """List all available SMACT tools."""
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
                        },
                        "use_pauling_test": {
                            "type": "boolean",
                            "description": "Whether to apply Pauling electronegativity test",
                            "default": True
                        },
                        "include_alloys": {
                            "type": "boolean", 
                            "description": "Consider pure metals valid automatically",
                            "default": True
                        },
                        "oxidation_states_set": {
                            "type": "string",
                            "description": "Which oxidation states to use",
                            "enum": ["icsd24", "icsd16", "smact14", "pymatgen_sp", "wiki"],
                            "default": "icsd24"
                        },
                        "check_metallicity": {
                            "type": "boolean",
                            "description": "If True, consider high metallicity compositions valid",
                            "default": False
                        },
                        "metallicity_threshold": {
                            "type": "number",
                            "description": "Score threshold for metallicity validity (0-1)",
                            "default": 0.7
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
                            "description": "Chemical formula (e.g., 'Ca(OH)2', 'Fe2O3', 'LiFePO4')"
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
                        },
                        "include_oxidation_states": {
                            "type": "boolean",
                            "description": "Whether to include oxidation state data",
                            "default": True
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
            ),
            types.Tool(
                name="test_pauling_rule",
                description="Test if oxidation states satisfy Pauling's electronegativity rule",
                inputSchema={
                    "type": "object",
                    "required": ["elements", "oxidation_states"],
                    "properties": {
                        "elements": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of element symbols (e.g., ['Li', 'Fe', 'O'])"
                        },
                        "oxidation_states": {
                            "type": "array",
                            "items": {"type": "integer"},
                            "description": "Corresponding oxidation states (e.g., [1, 3, -2])"
                        },
                        "threshold": {
                            "type": "number",
                            "description": "Tolerance for electronegativity differences",
                            "default": 0.0
                        }
                    }
                }
            )
        ]
    
    @app.call_tool()
    async def call_tool(
        name: str, arguments: dict
    ) -> list[types.TextContent]:
        """Handle tool calls."""
        
        try:
            if name == "check_smact_validity":
                result = await check_smact_validity(**arguments)
            elif name == "parse_chemical_formula":
                result = await parse_chemical_formula(**arguments)
            elif name == "get_element_info":
                result = await get_element_info(**arguments)
            elif name == "calculate_neutral_ratios":
                result = await calculate_neutral_ratios(**arguments)
            elif name == "test_pauling_rule":
                result = await test_pauling_rule(**arguments)
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

    # Run the server
    if transport == "sse":
        from mcp.server.sse import SseServerTransport
        from starlette.applications import Starlette
        from starlette.responses import Response
        from starlette.routing import Mount, Route

        sse = SseServerTransport("/messages/")

        async def handle_sse(request):
            async with sse.connect_sse(
                request.scope, request.receive, request._send
            ) as streams:
                await app.run(
                    streams[0], streams[1], app.create_initialization_options()
                )
            return Response()

        starlette_app = Starlette(
            debug=True,
            routes=[
                Route("/sse", endpoint=handle_sse, methods=["GET"]),
                Mount("/messages/", app=sse.handle_post_message),
            ],
        )

        import uvicorn
        uvicorn.run(starlette_app, host="127.0.0.1", port=port)
    else:
        from mcp.server.stdio import stdio_server

        async def arun():
            logger.info("Starting SMACT MCP server with stdio transport")
            async with stdio_server() as streams:
                await app.run(
                    streams[0], streams[1], app.create_initialization_options()
                )

        anyio.run(arun)

    return 0


# SMACT tool implementations
async def check_smact_validity(
    composition: str,
    use_pauling_test: bool = True,
    include_alloys: bool = True,
    oxidation_states_set: str = "icsd24",
    check_metallicity: bool = False,
    metallicity_threshold: float = 0.7
) -> str:
    """Check if a composition is valid according to SMACT rules."""
    try:
        # Parse composition using pymatgen
        from pymatgen.core import Composition
        comp = Composition(composition)
        
        # Run validity check
        is_valid = smact_validity(
            comp,
            use_pauling_test=use_pauling_test,
            include_alloys=include_alloys,
            oxidation_states_set=oxidation_states_set,
            check_metallicity=check_metallicity,
            metallicity_threshold=metallicity_threshold
        )
        
        # Get additional details
        elem_symbols = list(comp.as_dict().keys())
        elem_counts = list(comp.as_dict().values())
        
        result = {
            "composition": composition,
            "is_valid": is_valid,
            "elements": elem_symbols,
            "counts": elem_counts,
            "settings": {
                "use_pauling_test": use_pauling_test,
                "include_alloys": include_alloys,
                "oxidation_states_set": oxidation_states_set,
                "check_metallicity": check_metallicity,
                "metallicity_threshold": metallicity_threshold
            }
        }
        
        # Add metallicity score if requested and available
        if check_metallicity and METALLICITY_AVAILABLE:
            try:
                score = metallicity_score(comp)
                result["metallicity_score"] = score
            except Exception as e:
                result["metallicity_error"] = str(e)
        
        return json.dumps(result, indent=2)
        
    except Exception as e:
        return json.dumps({
            "error": str(e),
            "composition": composition,
            "is_valid": False
        }, indent=2)


async def parse_chemical_formula(formula: str) -> str:
    """Parse a chemical formula into its constituent elements and counts."""
    try:
        # Parse formula
        element_counts = parse_formula(formula)
        
        # Calculate total atoms
        total_atoms = sum(element_counts.values())
        
        # Get element info
        elements_info = []
        for elem, count in element_counts.items():
            try:
                smact_elem = Element(elem)
                elements_info.append({
                    "symbol": elem,
                    "count": count,
                    "atomic_number": smact_elem.number,
                    "name": smact_elem.name,
                    "electronegativity": smact_elem.pauling_eneg
                })
            except Exception:
                elements_info.append({
                    "symbol": elem,
                    "count": count,
                    "error": "Element data not found"
                })
        
        result = {
            "formula": formula,
            "element_counts": element_counts,
            "total_atoms": total_atoms,
            "elements": elements_info
        }
        
        return json.dumps(result, indent=2)
        
    except Exception as e:
        return json.dumps({
            "error": str(e),
            "formula": formula
        }, indent=2)


async def get_element_info(
    symbol: str,
    include_oxidation_states: bool = True
) -> str:
    """Get detailed properties of a chemical element from SMACT database."""
    try:
        # Get element
        elem = Element(symbol)
        
        result = {
            "symbol": elem.symbol,
            "name": elem.name,
            "atomic_number": elem.number,
            "atomic_mass": elem.mass,
            "electronegativity": {
                "pauling": elem.pauling_eneg,
            },
            "radii": {
                "covalent": elem.cov_radius,
            }
        }
        
        # Add available properties safely
        if hasattr(elem, 'ionpot') and elem.ionpot is not None:
            result["ionization_potential"] = elem.ionpot
        if hasattr(elem, 'e_affinity') and elem.e_affinity is not None:
            result["electron_affinity"] = elem.e_affinity
        if hasattr(elem, 'eig') and elem.eig is not None:
            result["electronegativity"]["allen"] = elem.eig
        
        # Add oxidation states if requested
        if include_oxidation_states:
            ox_states = {}
            if hasattr(elem, 'oxidation_states_icsd24'):
                ox_states["icsd24"] = elem.oxidation_states_icsd24
            if hasattr(elem, 'oxidation_states_icsd16'):
                ox_states["icsd16"] = elem.oxidation_states_icsd16
            if hasattr(elem, 'oxidation_states_smact14'):
                ox_states["smact14"] = elem.oxidation_states_smact14
            if hasattr(elem, 'oxidation_states_wiki'):
                ox_states["wiki"] = elem.oxidation_states_wiki
            result["oxidation_states"] = ox_states
        
        return json.dumps(result, indent=2)
        
    except Exception as e:
        return json.dumps({
            "error": str(e),
            "symbol": symbol
        }, indent=2)


async def calculate_neutral_ratios(
    oxidation_states: List[int],
    threshold: int = 5
) -> str:
    """Find charge-neutral stoichiometric ratios for given oxidation states."""
    try:
        # Calculate neutral ratios
        cn_e, cn_r = neutral_ratios(
            oxidation_states,
            stoichs=False,
            threshold=threshold
        )
        
        result = {
            "oxidation_states": oxidation_states,
            "charge_neutral": cn_e,
            "neutral_ratios": [list(ratio) for ratio in cn_r] if cn_e else [],
            "threshold": threshold
        }
        
        # Add example formulas if neutral
        if cn_e and cn_r:
            examples = []
            for ratio in cn_r[:5]:  # Show up to 5 examples
                formula_parts = []
                for i, (ox, count) in enumerate(zip(oxidation_states, ratio)):
                    if count > 1:
                        formula_parts.append(f"X{i+1}_{count}")
                    else:
                        formula_parts.append(f"X{i+1}")
                examples.append({
                    "ratio": list(ratio),
                    "example": "".join(formula_parts),
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


async def test_pauling_rule(
    elements: List[str],
    oxidation_states: List[int],
    threshold: float = 0.0
) -> str:
    """Check if a combination of elements and oxidation states satisfies Pauling's rule."""
    try:
        if len(elements) != len(oxidation_states):
            raise ValueError("Elements and oxidation states must have same length")
        
        # Get electronegativities
        electronegativities = []
        element_data = []
        
        for elem_symbol in elements:
            elem = Element(elem_symbol)
            electronegativities.append(elem.pauling_eneg)
            element_data.append({
                "symbol": elem_symbol,
                "electronegativity": elem.pauling_eneg
            })
        
        # Run Pauling test
        passes_test = pauling_test(
            oxidation_states,
            electronegativities,
            symbols=elements,
            threshold=threshold
        )
        
        # Identify cations and anions
        cations = []
        anions = []
        for i, (elem, ox, eneg) in enumerate(zip(elements, oxidation_states, electronegativities)):
            if ox > 0:
                cations.append({
                    "element": elem,
                    "oxidation_state": ox,
                    "electronegativity": eneg
                })
            elif ox < 0:
                anions.append({
                    "element": elem,
                    "oxidation_state": ox,
                    "electronegativity": eneg
                })
        
        result = {
            "passes_test": passes_test,
            "elements": element_data,
            "oxidation_states": oxidation_states,
            "cations": cations,
            "anions": anions,
            "threshold": threshold,
            "rule": "Cations should have lower electronegativity than anions"
        }
        
        return json.dumps(result, indent=2)
        
    except Exception as e:
        return json.dumps({
            "error": str(e),
            "elements": elements,
            "oxidation_states": oxidation_states
        }, indent=2)


if __name__ == "__main__":
    main()