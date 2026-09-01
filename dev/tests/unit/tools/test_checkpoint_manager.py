"""Unit tests for the Chemeleon checkpoint manager.

``ensure_checkpoints_downloaded`` accepts ``download=`` and ``extract=``, so
everything here runs against a synthetic 200-byte tar.gz built in-process and a
``tmp_path`` cache directory.  No network, no 523 MB Figshare round-trip and no
patching: the dependencies are arguments, so the test supplies them.

The extraction test is a regression guard for a bug that shipped (fixed in
``4d7fec0``): the archive nests the checkpoints in a top-level ``ckpts/``
directory, and the old code extracted to ``cache_dir.parent`` while verifying
inside ``cache_dir``.  Every successful download therefore ended in
"This may indicate a corrupted download".
"""

from __future__ import annotations

from pathlib import Path

import pytest

from crystalyse.tools.chemeleon.checkpoint_manager import (
    CHECKPOINT_FILENAMES,
    FIGSHARE_URL,
    ensure_checkpoints_downloaded,
    get_checkpoint_path,
)
from tests.fakes import (
    FailingDownloader,
    FakeDownloader,
    PartialDownloader,
    checkpoint_payload,
    make_checkpoint_archive,
)
from tests.fakes import (
    real_extractor as extract,
)

CSP = CHECKPOINT_FILENAMES["csp"]
DNG = CHECKPOINT_FILENAMES["dng"]


def _archive(nest_in: str | None = "ckpts") -> bytes:
    """A complete archive: both checkpoints, nested the way Figshare nests them."""
    return make_checkpoint_archive([CSP, DNG], nest_in=nest_in)


# =============================================================================
# Extraction: the checkpoints must land where verification looks for them
# =============================================================================


@pytest.mark.parametrize("nest_in", ["ckpts", None], ids=["nested-in-ckpts-dir", "flat-archive"])
def test_extraction_puts_checkpoints_directly_in_the_cache_dir(
    tmp_path: Path, nest_in: str | None
) -> None:
    downloader = FakeDownloader(_archive(nest_in))

    paths = ensure_checkpoints_downloaded(tmp_path, download=downloader, extract=extract)

    assert paths == {"csp": tmp_path / CSP, "dng": tmp_path / DNG}
    assert paths["csp"].read_bytes() == checkpoint_payload(CSP)
    assert paths["dng"].read_bytes() == checkpoint_payload(DNG)


def test_extraction_writes_nothing_outside_the_cache_dir(tmp_path: Path) -> None:
    """The shipped bug extracted into ``cache_dir.parent``; nothing may go there."""
    cache_dir = tmp_path / "chemeleon_checkpoints"

    ensure_checkpoints_downloaded(cache_dir, download=FakeDownloader(_archive()), extract=extract)

    assert [p.name for p in tmp_path.iterdir()] == ["chemeleon_checkpoints"]


def test_staging_dir_does_not_survive_a_successful_run(tmp_path: Path) -> None:
    ensure_checkpoints_downloaded(tmp_path, download=FakeDownloader(_archive()), extract=extract)

    assert not (tmp_path / "_extract").exists()


def test_archive_is_deleted_after_a_successful_run(tmp_path: Path) -> None:
    ensure_checkpoints_downloaded(tmp_path, download=FakeDownloader(_archive()), extract=extract)

    assert sorted(p.name for p in tmp_path.iterdir()) == sorted([CSP, DNG])


def test_stale_staging_dir_from_an_interrupted_run_is_not_reused(tmp_path: Path) -> None:
    """A leftover ``_extract/`` must not leak its checkpoints into the cache dir.

    The stale file is named for an *older* archive version, which is the case
    the staging dir has to be cleared for: a same-named leftover is overwritten
    by extraction anyway, so it proves nothing.
    """
    stale = tmp_path / "_extract" / "ckpts"
    stale.mkdir(parents=True)
    (stale / "chemeleon_csp_alex_mp_20_v0.0.1.ckpt").write_bytes(b"leftover from a dead run")

    paths = ensure_checkpoints_downloaded(
        tmp_path, download=FakeDownloader(_archive()), extract=extract
    )

    assert paths["csp"].read_bytes() == checkpoint_payload(CSP)
    assert sorted(p.name for p in tmp_path.iterdir()) == sorted([CSP, DNG])


# =============================================================================
# Caching
# =============================================================================


def test_cached_checkpoints_are_not_downloaded_again(tmp_path: Path) -> None:
    """Not re-downloading 523 MB *is* the behaviour, so the call count is the assertion."""
    (tmp_path / CSP).write_bytes(b"already on disk")
    (tmp_path / DNG).write_bytes(b"already on disk")
    downloader = FakeDownloader(_archive())

    paths = ensure_checkpoints_downloaded(tmp_path, download=downloader, extract=extract)

    assert downloader.calls == []
    assert paths["csp"].read_bytes() == b"already on disk"


def test_zero_byte_checkpoint_does_not_count_as_cached(tmp_path: Path) -> None:
    (tmp_path / CSP).write_bytes(b"")
    (tmp_path / DNG).write_bytes(b"complete")
    downloader = FakeDownloader(_archive())

    paths = ensure_checkpoints_downloaded(tmp_path, download=downloader, extract=extract)

    assert paths["csp"].read_bytes() == checkpoint_payload(CSP)
    assert [url for url, _ in downloader.calls] == [FIGSHARE_URL]


# =============================================================================
# Failure paths
# =============================================================================


def test_download_failure_surfaces_as_runtime_error(tmp_path: Path) -> None:
    downloader = FailingDownloader(OSError("name resolution failed"))

    with pytest.raises(RuntimeError, match="Checkpoint download failed"):
        ensure_checkpoints_downloaded(tmp_path, download=downloader, extract=extract)


def test_interrupted_download_leaves_no_partial_archive(tmp_path: Path) -> None:
    downloader = PartialDownloader()

    with pytest.raises(RuntimeError):
        ensure_checkpoints_downloaded(tmp_path, download=downloader, extract=extract)

    assert list(tmp_path.iterdir()) == []


def test_unreadable_archive_surfaces_as_runtime_error(tmp_path: Path) -> None:
    downloader = FakeDownloader(b"HTML error page, not a gzip stream")

    with pytest.raises(RuntimeError, match="Failed to extract checkpoint archive"):
        ensure_checkpoints_downloaded(tmp_path, download=downloader, extract=extract)


def test_unreadable_archive_leaves_no_archive_behind(tmp_path: Path) -> None:
    downloader = FakeDownloader(b"HTML error page, not a gzip stream")

    with pytest.raises(RuntimeError):
        ensure_checkpoints_downloaded(tmp_path, download=downloader, extract=extract)

    assert list(tmp_path.glob("*.tar.gz")) == []


def test_archive_missing_a_checkpoint_names_the_task(tmp_path: Path) -> None:
    downloader = FakeDownloader(make_checkpoint_archive([CSP]))

    with pytest.raises(RuntimeError, match="Checkpoint dng not found after extraction"):
        ensure_checkpoints_downloaded(tmp_path, download=downloader, extract=extract)


# =============================================================================
# get_checkpoint_path
# =============================================================================


def test_get_checkpoint_path_rejects_an_unknown_task() -> None:
    with pytest.raises(ValueError, match="Invalid task: dgn"):
        get_checkpoint_path("dgn")


def test_get_checkpoint_path_reports_a_missing_file_in_a_custom_dir(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="Checkpoint not found in custom directory"):
        get_checkpoint_path("csp", custom_dir=str(tmp_path))


def test_get_checkpoint_path_uses_a_custom_dir_without_downloading(tmp_path: Path) -> None:
    (tmp_path / CSP).write_bytes(b"checkpoint the user supplied")
    downloader = FakeDownloader(_archive())

    path = get_checkpoint_path(
        "csp", custom_dir=str(tmp_path), download=downloader, extract=extract
    )

    assert path == tmp_path / CSP
    assert downloader.calls == []


def test_get_checkpoint_path_forwards_kwargs_to_the_downloader(tmp_path: Path) -> None:
    downloader = FakeDownloader(_archive())

    path = get_checkpoint_path("dng", cache_dir=tmp_path, download=downloader, extract=extract)

    assert path == tmp_path / DNG
    assert path.read_bytes() == checkpoint_payload(DNG)
