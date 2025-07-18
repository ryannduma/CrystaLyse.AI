"""
Output formatting and export functionality for CrystaLyse.AI.

This module provides various output formats for query results including:
- Dual JSON/Markdown output for individual queries
- Structured directory creation for result organisation
- Human-readable report generation
- Machine-readable data export
"""

from .dual_formatter import DualOutputFormatter, create_dual_output

__all__ = ["DualOutputFormatter", "create_dual_output"]
