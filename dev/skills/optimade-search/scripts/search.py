#!/usr/bin/env python
"""OPTIMADE search script.

Usage:
    echo '{"filter": "elements HAS ALL \\"Li\\",\\"O\\"", "provider": "mp"}' | python search.py

Input (JSON via stdin):
    - filter: OPTIMADE filter string
    - provider: Database provider (mp, aflow, cod, oqmd, nomad)
    - page_limit: Number of results (default: 10)

Output (JSON to stdout):
    - success: True/False
    - provider: Provider name
    - count: Number of results
    - structures: List of structure data
"""

import json
import sys

def main():
    # Read input from stdin
    try:
        input_data = json.loads(sys.stdin.read())
    except json.JSONDecodeError as e:
        print(json.dumps({"success": False, "error": f"Invalid JSON input: {e}"}))
        return

    filter_query = input_data.get("filter", "")
    provider = input_data.get("provider", "mp")
    page_limit = input_data.get("page_limit", 10)

    if not filter_query:
        print(json.dumps({"success": False, "error": "No filter query provided"}))
        return

    # Try to import the OPTIMADE tool
    try:
        from crystalyse.tools.optimade import query_optimade
        result = query_optimade(
            filter_query=filter_query,
            provider=provider,
            page_limit=page_limit,
        )
        print(json.dumps(result, indent=2, default=str))
    except ImportError:
        # Fallback: direct implementation
        import urllib.request
        import urllib.parse

        PROVIDERS = {
            "mp": "https://optimade.materialsproject.org/v1",
            "aflow": "https://aflow.org/API/optimade/v1",
            "cod": "https://www.crystallography.net/cod/optimade/v1",
            "oqmd": "http://oqmd.org/optimade/v1",
            "nomad": "https://nomad-lab.eu/prod/v1/api/optimade/v1",
        }

        if provider not in PROVIDERS:
            print(json.dumps({
                "success": False,
                "error": f"Unknown provider: {provider}"
            }))
            return

        base_url = PROVIDERS[provider]
        encoded_filter = urllib.parse.quote(filter_query)
        url = f"{base_url}/structures?filter={encoded_filter}&page_limit={page_limit}"

        try:
            headers = {"Accept": "application/vnd.api+json"}
            request = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(request, timeout=30) as response:
                data = json.loads(response.read().decode("utf-8"))

            structures = []
            for entry in data.get("data", []):
                attrs = entry.get("attributes", {})
                structures.append({
                    "id": entry.get("id"),
                    "formula": attrs.get("chemical_formula_reduced"),
                    "elements": attrs.get("elements", []),
                    "nsites": attrs.get("nsites"),
                })

            print(json.dumps({
                "success": True,
                "provider": provider,
                "count": len(structures),
                "structures": structures,
            }, indent=2))

        except Exception as e:
            print(json.dumps({
                "success": False,
                "error": str(e)
            }))


if __name__ == "__main__":
    main()
