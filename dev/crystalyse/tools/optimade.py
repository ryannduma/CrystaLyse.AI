"""OPTIMADE database query tool for Crystalyse.

Provides access to OPTIMADE-compatible materials databases including:
- Materials Project (mp)
- AFLOW (aflow)
- Crystallography Open Database (cod)
- Open Quantum Materials Database (oqmd)
- NOMAD (nomad)
"""

import logging
from typing import Any

try:
    from agents import function_tool

    AGENTS_AVAILABLE = True
except ImportError:
    AGENTS_AVAILABLE = False

    def function_tool(func):
        return func


logger = logging.getLogger(__name__)

# OPTIMADE provider endpoints
PROVIDERS = {
    "mp": {
        "name": "Materials Project",
        "base_url": "https://optimade.materialsproject.org/v1",
        "description": "High-quality DFT calculations from Materials Project",
    },
    "aflow": {
        "name": "AFLOW",
        "base_url": "https://aflow.org/API/optimade/v1",
        "description": "Automatic FLOW for Materials Discovery database",
    },
    "cod": {
        "name": "Crystallography Open Database",
        "base_url": "https://www.crystallography.net/cod/optimade/v1",
        "description": "Experimental crystal structures from X-ray/neutron diffraction",
    },
    "oqmd": {
        "name": "Open Quantum Materials Database",
        "base_url": "http://oqmd.org/optimade/v1",
        "description": "DFT calculations for thermodynamic stability",
    },
    "nomad": {
        "name": "NOMAD",
        "base_url": "https://nomad-lab.eu/prod/v1/api/optimade/v1",
        "description": "Novel Materials Discovery FAIR data sharing",
    },
}

# Common OPTIMADE response fields
DEFAULT_RESPONSE_FIELDS = [
    "id",
    "chemical_formula_reduced",
    "chemical_formula_anonymous",
    "nelements",
    "elements",
    "nsites",
    "dimension_types",
    "lattice_vectors",
]


def _build_optimade_url(
    provider: str,
    filter_query: str,
    response_fields: list[str] | None = None,
    page_limit: int = 10,
    page_offset: int = 0,
) -> str:
    """Build an OPTIMADE query URL.

    Args:
        provider: Provider key (mp, aflow, cod, etc.)
        filter_query: OPTIMADE filter string
        response_fields: Fields to include in response
        page_limit: Number of results per page
        page_offset: Starting offset for pagination

    Returns:
        Complete OPTIMADE query URL
    """
    if provider not in PROVIDERS:
        raise ValueError(f"Unknown provider: {provider}. Available: {list(PROVIDERS.keys())}")

    base_url = PROVIDERS[provider]["base_url"]
    url = f"{base_url}/structures"

    params = []
    if filter_query:
        # URL encode the filter
        import urllib.parse

        encoded_filter = urllib.parse.quote(filter_query)
        params.append(f"filter={encoded_filter}")

    if response_fields:
        fields_str = ",".join(response_fields)
        params.append(f"response_fields={fields_str}")

    params.append(f"page_limit={page_limit}")
    if page_offset > 0:
        params.append(f"page_offset={page_offset}")

    if params:
        url += "?" + "&".join(params)

    return url


def _parse_optimade_response(response_data: dict) -> list[dict[str, Any]]:
    """Parse OPTIMADE response into simplified structure list.

    Args:
        response_data: Raw OPTIMADE response

    Returns:
        List of structure dictionaries
    """
    structures = []

    data = response_data.get("data", [])
    for entry in data:
        attrs = entry.get("attributes", {})

        structure = {
            "id": entry.get("id"),
            "formula": attrs.get("chemical_formula_reduced"),
            "anonymous_formula": attrs.get("chemical_formula_anonymous"),
            "elements": attrs.get("elements", []),
            "nelements": attrs.get("nelements"),
            "nsites": attrs.get("nsites"),
        }

        # Add lattice vectors if present
        if "lattice_vectors" in attrs:
            structure["lattice_vectors"] = attrs["lattice_vectors"]

        # Add additional properties if present
        for key in ["spacegroup_symbol", "spacegroup_number", "volume"]:
            if key in attrs:
                structure[key] = attrs[key]

        structures.append(structure)

    return structures


@function_tool
def query_optimade(
    filter_query: str,
    provider: str = "mp",
    response_fields: str = "",
    page_limit: int = 10,
) -> dict:
    """Query OPTIMADE-compatible materials databases.

    OPTIMADE provides a standardized API for querying materials databases.
    Use this tool to search for structures across multiple databases.

    Example filters:
    - 'elements HAS "Li"' - Structures containing lithium
    - 'elements HAS ALL "Li","O"' - Structures with both Li and O
    - 'nelements=2' - Binary compounds
    - 'chemical_formula_reduced="NaCl"' - Specific formula
    - 'nsites<10' - Small unit cells

    Args:
        filter_query: OPTIMADE filter string (e.g., 'elements HAS "Li"').
        provider: Database provider (mp, aflow, cod, oqmd, nomad). Default: mp.
        response_fields: Fields to include in response. Default: common fields.
        page_limit: Maximum number of results (default: 10, max: 100).

    Returns:
        Dictionary with:
        - success: True if query succeeded
        - provider: Provider name
        - count: Number of structures returned
        - structures: List of structure data
        - error: Error message if query failed

    Available providers:
    - mp: Materials Project (DFT calculations)
    - aflow: AFLOW database
    - cod: Crystallography Open Database (experimental)
    - oqmd: Open Quantum Materials Database
    - nomad: NOMAD repository
    """
    try:
        import json
        import urllib.request

        # Validate provider
        if provider not in PROVIDERS:
            return {
                "success": False,
                "provider": provider,
                "count": 0,
                "structures": [],
                "error": f"Unknown provider: {provider}. Available: {list(PROVIDERS.keys())}",
            }

        # Parse response_fields from comma-separated string
        if response_fields and response_fields.strip():
            fields = [f.strip() for f in response_fields.split(",")]
        else:
            fields = DEFAULT_RESPONSE_FIELDS
        page_limit = min(page_limit, 100)  # Cap at 100

        url = _build_optimade_url(
            provider=provider,
            filter_query=filter_query,
            response_fields=fields,
            page_limit=page_limit,
        )

        logger.info(f"Querying OPTIMADE: {provider} with filter: {filter_query}")

        # Make request
        headers = {
            "Accept": "application/vnd.api+json",
            "User-Agent": "CrystaLyse/1.0",
        }

        request = urllib.request.Request(url, headers=headers)

        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                response_data = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            error_body = e.read().decode("utf-8") if e.fp else ""
            return {
                "success": False,
                "provider": PROVIDERS[provider]["name"],
                "count": 0,
                "structures": [],
                "error": f"HTTP {e.code}: {e.reason}. {error_body[:500]}",
            }
        except urllib.error.URLError as e:
            return {
                "success": False,
                "provider": PROVIDERS[provider]["name"],
                "count": 0,
                "structures": [],
                "error": f"Connection error: {e.reason}",
            }

        # Parse response
        structures = _parse_optimade_response(response_data)

        # Get metadata
        meta = response_data.get("meta", {})
        data_returned = meta.get("data_returned", len(structures))
        data_available = meta.get("data_available")

        return {
            "success": True,
            "provider": PROVIDERS[provider]["name"],
            "count": data_returned,
            "total_available": data_available,
            "structures": structures,
            "error": None,
        }

    except Exception as e:
        logger.error(f"OPTIMADE query failed: {e}")
        return {
            "success": False,
            "provider": provider,
            "count": 0,
            "structures": [],
            "error": str(e),
        }


def list_providers() -> dict[str, dict[str, str]]:
    """List all available OPTIMADE providers.

    Returns:
        Dictionary of provider info.
    """
    return {
        key: {"name": info["name"], "description": info["description"]}
        for key, info in PROVIDERS.items()
    }
