"""Web search tool for Crystalyse.

Provides web search capability for finding materials science information,
literature, and external resources.
"""

import logging
import os
from typing import Any

try:
    from agents import function_tool

    AGENTS_AVAILABLE = True
except ImportError:
    AGENTS_AVAILABLE = False

    def function_tool(func):
        return func


logger = logging.getLogger(__name__)


@function_tool
def web_search(
    query: str,
    num_results: int = 5,
    search_type: str = "general",
) -> dict:
    """Search the web for materials science information.

    Use this tool to find:
    - Research papers and literature
    - Material property databases
    - Synthesis methods and procedures
    - Recent developments in materials science

    Args:
        query: Search query string.
        num_results: Number of results to return (default: 5, max: 20).
        search_type: Type of search:
            - "general": General web search
            - "academic": Focus on academic sources
            - "databases": Focus on materials databases

    Returns:
        Dictionary with:
        - success: True if search succeeded
        - query: Original query
        - results: List of search results
        - error: Error message if search failed

    Note: Requires SERPAPI_KEY or similar search API key in environment.
    """
    num_results = min(num_results, 20)

    # Enhance query based on search type
    enhanced_query = query
    if search_type == "academic":
        enhanced_query = (
            f"{query} site:arxiv.org OR site:nature.com OR site:acs.org OR site:rsc.org"
        )
    elif search_type == "databases":
        enhanced_query = f"{query} site:materialsproject.org OR site:aflow.org OR site:nomad-lab.eu"

    # Try different search backends
    result = _try_serpapi_search(enhanced_query, num_results)
    if result["success"]:
        return result

    result = _try_duckduckgo_search(enhanced_query, num_results)
    if result["success"]:
        return result

    # Fallback: suggest manual search
    return {
        "success": False,
        "query": query,
        "results": [],
        "error": "No search API available. Please search manually or set SERPAPI_KEY.",
        "suggested_urls": _get_suggested_urls(query, search_type),
    }


def _try_serpapi_search(query: str, num_results: int) -> dict[str, Any]:
    """Try to search using SerpAPI."""
    api_key = os.getenv("SERPAPI_KEY")
    if not api_key:
        return {"success": False, "error": "SERPAPI_KEY not set"}

    try:
        import json
        import urllib.parse
        import urllib.request

        params = {
            "q": query,
            "api_key": api_key,
            "num": num_results,
            "engine": "google",
        }

        url = f"https://serpapi.com/search?{urllib.parse.urlencode(params)}"

        with urllib.request.urlopen(url, timeout=15) as response:
            data = json.loads(response.read().decode("utf-8"))

        results = []
        for item in data.get("organic_results", [])[:num_results]:
            results.append(
                {
                    "title": item.get("title"),
                    "url": item.get("link"),
                    "snippet": item.get("snippet"),
                }
            )

        return {
            "success": True,
            "query": query,
            "results": results,
            "error": None,
        }

    except Exception as e:
        logger.warning(f"SerpAPI search failed: {e}")
        return {"success": False, "error": str(e)}


def _try_duckduckgo_search(query: str, num_results: int) -> dict[str, Any]:
    """Try to search using DuckDuckGo instant answers API."""
    try:
        import json
        import urllib.parse
        import urllib.request

        # DuckDuckGo instant answer API (limited but free)
        params = {
            "q": query,
            "format": "json",
            "no_html": "1",
            "skip_disambig": "1",
        }

        url = f"https://api.duckduckgo.com/?{urllib.parse.urlencode(params)}"

        headers = {
            "User-Agent": "CrystaLyse/1.0 Materials Science Agent",
        }

        request = urllib.request.Request(url, headers=headers)

        with urllib.request.urlopen(request, timeout=10) as response:
            data = json.loads(response.read().decode("utf-8"))

        results = []

        # Abstract
        if data.get("AbstractText"):
            results.append(
                {
                    "title": data.get("Heading", "Summary"),
                    "url": data.get("AbstractURL", ""),
                    "snippet": data.get("AbstractText"),
                    "source": data.get("AbstractSource", ""),
                }
            )

        # Related topics
        for topic in data.get("RelatedTopics", [])[:num_results]:
            if isinstance(topic, dict) and "Text" in topic:
                results.append(
                    {
                        "title": topic.get("Text", "")[:100],
                        "url": topic.get("FirstURL", ""),
                        "snippet": topic.get("Text", ""),
                    }
                )

        if results:
            return {
                "success": True,
                "query": query,
                "results": results,
                "error": None,
            }
        else:
            return {"success": False, "error": "No results from DuckDuckGo"}

    except Exception as e:
        logger.warning(f"DuckDuckGo search failed: {e}")
        return {"success": False, "error": str(e)}


def _get_suggested_urls(query: str, search_type: str) -> list[dict[str, str]]:
    """Generate suggested URLs for manual search."""
    import urllib.parse

    encoded_query = urllib.parse.quote(query)

    suggestions = [
        {
            "name": "Google Scholar",
            "url": f"https://scholar.google.com/scholar?q={encoded_query}",
            "description": "Academic papers and citations",
        },
        {
            "name": "Materials Project",
            "url": f"https://materialsproject.org/materials?formula={encoded_query}",
            "description": "Materials database with DFT calculations",
        },
        {
            "name": "arXiv",
            "url": f"https://arxiv.org/search/?query={encoded_query}&searchtype=all",
            "description": "Preprints in physics and materials science",
        },
    ]

    if search_type == "databases":
        suggestions.extend(
            [
                {
                    "name": "AFLOW",
                    "url": f"https://aflow.org/material/?query={encoded_query}",
                    "description": "Automatic FLOW database",
                },
                {
                    "name": "NOMAD",
                    "url": f"https://nomad-lab.eu/prod/v1/gui/search/entries?query={encoded_query}",
                    "description": "NOMAD repository",
                },
            ]
        )

    return suggestions
