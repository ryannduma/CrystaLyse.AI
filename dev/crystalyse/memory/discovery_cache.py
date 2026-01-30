"""Cache for expensive computational results.

Uses SQLite for concurrent access and efficient queries. Stores results
keyed by (formula, computation_type, parameters_hash) for caching different
computation variants.
"""

import hashlib
import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path

DEFAULT_DB = Path.home() / ".crystalyse" / "sessions.db"


def _hash_params(params: dict) -> str:
    """Create deterministic hash of parameters."""
    return hashlib.sha256(json.dumps(params, sort_keys=True).encode()).hexdigest()[:16]


@dataclass
class CachedDiscovery:
    """A cached computation result."""

    formula: str
    computation_type: str
    parameters_hash: str
    result: dict
    created_at: str


class DiscoveryCache:
    """Cache expensive MACE/Chemeleon/SMACT computations.

    Uses SQLite stored in the same database as sessions for consistency.
    Supports different computation variants via parameters_hash.
    """

    def __init__(self, db_path: Path = DEFAULT_DB):
        """Initialize discovery cache.

        Args:
            db_path: Path to SQLite database (shared with sessions)
        """
        self._db_path = db_path
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _init_schema(self) -> None:
        """Create discoveries table if it doesn't exist."""
        with sqlite3.connect(self._db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS discoveries (
                    id INTEGER PRIMARY KEY,
                    formula TEXT NOT NULL,
                    computation_type TEXT NOT NULL,
                    parameters_hash TEXT NOT NULL,
                    result_json TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(formula, computation_type, parameters_hash)
                )
            """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_discoveries_formula ON discoveries(formula)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_discoveries_type ON discoveries(computation_type)"
            )

    def get(self, formula: str, computation_type: str, params: dict | None = None) -> dict | None:
        """Get cached result or None.

        Args:
            formula: Chemical formula (e.g., "LiFePO4")
            computation_type: Type of computation (e.g., "mace_energy", "smact_validity")
            params: Computation parameters (used to differentiate variants)

        Returns:
            Cached result dict if found, None otherwise
        """
        params_hash = _hash_params(params or {})
        with sqlite3.connect(self._db_path) as conn:
            row = conn.execute(
                """SELECT result_json FROM discoveries
                   WHERE formula = ? AND computation_type = ? AND parameters_hash = ?""",
                (formula, computation_type, params_hash),
            ).fetchone()
            return json.loads(row[0]) if row else None

    def put(
        self,
        formula: str,
        computation_type: str,
        result: dict,
        params: dict | None = None,
    ) -> None:
        """Cache a computation result.

        Args:
            formula: Chemical formula
            computation_type: Type of computation
            result: Result to cache
            params: Computation parameters
        """
        params_hash = _hash_params(params or {})
        with sqlite3.connect(self._db_path) as conn:
            conn.execute(
                """INSERT OR REPLACE INTO discoveries
                   (formula, computation_type, parameters_hash, result_json)
                   VALUES (?, ?, ?, ?)""",
                (formula, computation_type, params_hash, json.dumps(result)),
            )

    def search(self, query: str, limit: int = 10) -> list[CachedDiscovery]:
        """Search cached discoveries by formula pattern.

        Args:
            query: Search pattern (e.g., "Li" for lithium compounds)
            limit: Maximum results to return

        Returns:
            List of matching CachedDiscovery objects
        """
        with sqlite3.connect(self._db_path) as conn:
            rows = conn.execute(
                """SELECT formula, computation_type, parameters_hash, result_json, created_at
                   FROM discoveries WHERE formula LIKE ?
                   ORDER BY created_at DESC LIMIT ?""",
                (f"%{query}%", limit),
            ).fetchall()
            return [CachedDiscovery(r[0], r[1], r[2], json.loads(r[3]), r[4]) for r in rows]

    def get_all_for_formula(self, formula: str) -> list[CachedDiscovery]:
        """Get all cached computations for a formula.

        Args:
            formula: Exact chemical formula

        Returns:
            List of all cached results for this formula
        """
        with sqlite3.connect(self._db_path) as conn:
            rows = conn.execute(
                """SELECT formula, computation_type, parameters_hash, result_json, created_at
                   FROM discoveries WHERE formula = ? ORDER BY created_at DESC""",
                (formula,),
            ).fetchall()
            return [CachedDiscovery(r[0], r[1], r[2], json.loads(r[3]), r[4]) for r in rows]

    def get_by_type(self, computation_type: str, limit: int = 50) -> list[CachedDiscovery]:
        """Get cached results by computation type.

        Args:
            computation_type: Type of computation (e.g., "mace_energy")
            limit: Maximum results to return

        Returns:
            List of cached results for this computation type
        """
        with sqlite3.connect(self._db_path) as conn:
            rows = conn.execute(
                """SELECT formula, computation_type, parameters_hash, result_json, created_at
                   FROM discoveries WHERE computation_type = ?
                   ORDER BY created_at DESC LIMIT ?""",
                (computation_type, limit),
            ).fetchall()
            return [CachedDiscovery(r[0], r[1], r[2], json.loads(r[3]), r[4]) for r in rows]

    def delete(self, formula: str, computation_type: str, params: dict | None = None) -> bool:
        """Delete a specific cached result.

        Args:
            formula: Chemical formula
            computation_type: Type of computation
            params: Computation parameters

        Returns:
            True if deleted, False if not found
        """
        params_hash = _hash_params(params or {})
        with sqlite3.connect(self._db_path) as conn:
            cursor = conn.execute(
                """DELETE FROM discoveries
                   WHERE formula = ? AND computation_type = ? AND parameters_hash = ?""",
                (formula, computation_type, params_hash),
            )
            return cursor.rowcount > 0

    def clear(self) -> int:
        """Clear all cached discoveries.

        Returns:
            Number of entries deleted
        """
        with sqlite3.connect(self._db_path) as conn:
            cursor = conn.execute("DELETE FROM discoveries")
            return cursor.rowcount

    def stats(self) -> dict:
        """Get cache statistics.

        Returns:
            Dictionary with total count and counts by type
        """
        with sqlite3.connect(self._db_path) as conn:
            total = conn.execute("SELECT COUNT(*) FROM discoveries").fetchone()[0]
            by_type = conn.execute(
                """SELECT computation_type, COUNT(*) FROM discoveries
                   GROUP BY computation_type ORDER BY COUNT(*) DESC"""
            ).fetchall()
            return {
                "total": total,
                "by_type": {row[0]: row[1] for row in by_type},
            }
