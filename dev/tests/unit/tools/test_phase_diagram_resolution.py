"""
Regression tests for the phase-diagram file resolution logic.

These tests exist to prevent a specific regression: a prior version of
``crystalyse.tools.pymatgen.phase_diagram._load_phase_diagram`` contained
hardcoded, user-specific absolute paths (e.g. ``/home/ryan/updatecrystalyse/…``)
in its search list. Those paths silently masked the canonical cache
(``~/.cache/crystalyse/``) whenever a developer had data in one of the
hardcoded locations — meaning code running from checkout A would load a pickle
from checkout B without warning.

The tests here cover two things:

1. **Static check**: the module source contains no hardcoded user-specific
   paths. This catches someone re-adding them during a merge.
2. **Behavioural check**: the resolution order is
   ``CRYSTALYSE_PPD_PATH`` → canonical cache → repo-local sibling → download.
"""

from __future__ import annotations

import gzip
import pickle
from pathlib import Path
from unittest.mock import patch

import pytest

from crystalyse.tools.pymatgen import phase_diagram as pd_module

# =============================================================================
# Helpers
# =============================================================================


@pytest.fixture(autouse=True)
def _reset_module_globals() -> None:
    """Reset the cached phase diagram between tests so ordering is independent."""
    pd_module._PPD_DATA = None
    pd_module._PPD_PATH = None
    yield
    pd_module._PPD_DATA = None
    pd_module._PPD_PATH = None


class _FakePD:
    """Stand-in for a real ``pymatgen.PhaseDiagram`` object.

    ``_load_phase_diagram`` calls ``len(_PPD_DATA.all_entries)`` on success.
    This class exposes that attribute so the loader can log without needing a
    real 170 MB Materials Project pickle. Kept at module scope so it is
    picklable (local classes are not).
    """

    all_entries: list = []


def _write_fake_ppd_pickle(path: Path) -> None:
    """Write a trivially-picklable stand-in PhaseDiagram at ``path``."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wb") as f:
        pickle.dump(_FakePD(), f)


# =============================================================================
# Static regression check
# =============================================================================


class TestNoHardcodedPaths:
    """Source-level guard against reintroducing user-specific paths."""

    def test_module_source_has_no_user_specific_absolute_paths(self) -> None:
        """Catch anyone re-adding ``/home/<user>/…`` hardcoded paths."""
        source = Path(pd_module.__file__).read_text()

        forbidden_fragments = [
            "/home/ryan/",
            "updatecrystalyse",
            "mycrystalyse",
        ]
        offenders = [frag for frag in forbidden_fragments if frag in source]
        assert not offenders, (
            f"{pd_module.__file__} contains hardcoded user-specific paths: {offenders}. "
            "These silently mask the canonical cache and break reproducibility for "
            "anyone running from a different checkout. Use CRYSTALYSE_PPD_PATH or "
            "the ~/.cache/crystalyse/ cache instead."
        )


# =============================================================================
# Resolution-order behavioural checks
# =============================================================================


class TestResolutionOrder:
    """Verify the documented priority order of ``_load_phase_diagram``."""

    def test_env_var_override_wins_over_cache(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """``CRYSTALYSE_PPD_PATH`` must be checked before the canonical cache."""
        cache_file = tmp_path / "cache" / "ppd-mp_all_entries_uncorrected_250409.pkl.gz"
        env_file = tmp_path / "elsewhere" / "ppd-mp_all_entries_uncorrected_250409.pkl.gz"
        _write_fake_ppd_pickle(cache_file)
        _write_fake_ppd_pickle(env_file)

        monkeypatch.setenv("CRYSTALYSE_PPD_PATH", str(env_file))

        # Patch ``get_phase_diagram_path`` inside the downloader module so the
        # import inside ``_load_phase_diagram`` picks up our tmp cache.
        with patch("crystalyse.tools.downloader.get_phase_diagram_path", return_value=cache_file):
            pd_module._load_phase_diagram()

        assert pd_module._PPD_PATH == str(env_file)

    def test_cache_wins_over_repo_local_fallback(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Canonical cache beats the source-relative <repo-root>/ppd-… fallback."""
        monkeypatch.delenv("CRYSTALYSE_PPD_PATH", raising=False)

        cache_file = tmp_path / "cache" / "ppd-mp_all_entries_uncorrected_250409.pkl.gz"
        _write_fake_ppd_pickle(cache_file)

        # Create a file at the real repo-local location too, to confirm the
        # cache wins even when both exist. The repo_local_path inside the
        # loader is computed from ``Path(__file__).resolve().parents[4]`` on
        # the *module*, so we drop a file there, then clean up afterwards.
        repo_root = Path(pd_module.__file__).resolve().parents[4]
        repo_local = repo_root / "ppd-mp_all_entries_uncorrected_250409.pkl.gz"
        created_repo_local = False
        if not repo_local.exists():
            _write_fake_ppd_pickle(repo_local)
            created_repo_local = True

        try:
            with patch(
                "crystalyse.tools.downloader.get_phase_diagram_path", return_value=cache_file
            ):
                pd_module._load_phase_diagram()
            assert pd_module._PPD_PATH == str(cache_file)
        finally:
            if created_repo_local:
                repo_local.unlink()

    def test_repo_local_used_when_cache_missing(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """If the cache is empty, the <repo-root>/ppd-… fallback is consulted."""
        monkeypatch.delenv("CRYSTALYSE_PPD_PATH", raising=False)

        empty_cache = tmp_path / "cache" / "ppd-mp_all_entries_uncorrected_250409.pkl.gz"
        # NB: intentionally not writing empty_cache — it must not exist.

        repo_root = Path(pd_module.__file__).resolve().parents[4]
        repo_local = repo_root / "ppd-mp_all_entries_uncorrected_250409.pkl.gz"
        created_repo_local = False
        if not repo_local.exists():
            _write_fake_ppd_pickle(repo_local)
            created_repo_local = True

        try:
            with patch(
                "crystalyse.tools.downloader.get_phase_diagram_path", return_value=empty_cache
            ):
                pd_module._load_phase_diagram()
            assert pd_module._PPD_PATH == str(repo_local)
        finally:
            if created_repo_local:
                repo_local.unlink()

    def test_download_attempted_when_nothing_found(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """With no env var, no cache, and no repo-local file, the loader must
        fall back to ``ensure_phase_diagram_data`` rather than silently fail."""
        monkeypatch.delenv("CRYSTALYSE_PPD_PATH", raising=False)

        empty_cache = tmp_path / "cache" / "ppd-mp_all_entries_uncorrected_250409.pkl.gz"

        # Ensure the repo-local location is empty for this test.
        repo_root = Path(pd_module.__file__).resolve().parents[4]
        repo_local = repo_root / "ppd-mp_all_entries_uncorrected_250409.pkl.gz"
        had_repo_local = repo_local.exists()
        backup_bytes = repo_local.read_bytes() if had_repo_local else None
        if had_repo_local:
            repo_local.unlink()

        downloaded = tmp_path / "downloaded" / "ppd-mp_all_entries_uncorrected_250409.pkl.gz"
        _write_fake_ppd_pickle(downloaded)

        try:
            with (
                patch(
                    "crystalyse.tools.downloader.get_phase_diagram_path",
                    return_value=empty_cache,
                ),
                patch(
                    "crystalyse.tools.downloader.ensure_phase_diagram_data",
                    return_value=downloaded,
                ) as mock_download,
            ):
                pd_module._load_phase_diagram()

            mock_download.assert_called_once()
            assert pd_module._PPD_PATH == str(downloaded)
        finally:
            if had_repo_local and backup_bytes is not None:
                repo_local.write_bytes(backup_bytes)


class TestCanonicalCachePath:
    """Canonical cache path must be machine-independent (under ``$HOME``)."""

    def test_cache_path_is_under_home_cache_crystalyse(self) -> None:
        """Regression guard: canonical path must stay ``~/.cache/crystalyse/…``."""
        from crystalyse.tools.downloader import (
            PHASE_DIAGRAM_FILENAME,
            get_phase_diagram_path,
        )

        cache_path = get_phase_diagram_path()
        expected = Path.home() / ".cache" / "crystalyse" / PHASE_DIAGRAM_FILENAME
        assert cache_path == expected
