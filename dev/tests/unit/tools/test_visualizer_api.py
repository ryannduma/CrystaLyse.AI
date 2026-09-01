"""``CrystaLyseVisualizer`` -- the keyword names are part of the contract.

Both visualization MCP tools in ``chemistry-unified-server`` forward their
arguments **by keyword**::

    visualizer.save_cif_file(
        cif_content=..., formula=..., output_dir=..., title=title
    )

so renaming ``title``/``color_scheme`` to ``_title``/``_color_scheme`` to
silence a lint rule turned every call into a ``TypeError`` at request time.  The
signature assertions below are therefore assertions about behaviour: the name
*is* the interface.  The rest pins what the two methods leave on disk, all of
it under ``tmp_path``.
"""

from __future__ import annotations

import inspect
from collections.abc import Callable
from pathlib import Path

import pytest

from crystalyse.tools.visualization.visualizer import CrystaLyseVisualizer
from tests.fakes import make_cif


@pytest.mark.parametrize(
    ("method", "keyword"),
    [
        (CrystaLyseVisualizer.save_cif_file, "title"),
        (CrystaLyseVisualizer.create_analysis_suite, "title"),
        (CrystaLyseVisualizer.create_analysis_suite, "color_scheme"),
    ],
    ids=[
        "save_cif_file/title",
        "create_analysis_suite/title",
        "create_analysis_suite/color_scheme",
    ],
)
def test_mcp_tools_can_still_pass_this_keyword(method: Callable, keyword: str) -> None:
    """A leading underscore on any of these breaks the MCP tool that calls it.

    The kind matters as much as the name: ``keyword in parameters`` is also true
    for a positional-only parameter, which the keyword call sites could not
    reach, so the guard would pass while every request raised ``TypeError``.
    """
    parameter = inspect.signature(method).parameters.get(keyword)

    assert parameter is not None, f"{method.__name__} no longer accepts '{keyword}'"
    assert parameter.kind in (
        inspect.Parameter.POSITIONAL_OR_KEYWORD,
        inspect.Parameter.KEYWORD_ONLY,
    ), f"{method.__name__} takes '{keyword}' as {parameter.kind.name}, not by keyword"


def test_save_cif_file_accepts_title_by_keyword(tmp_path: Path) -> None:
    result = CrystaLyseVisualizer.save_cif_file(
        cif_content=make_cif(),
        formula="NaCl",
        output_dir=str(tmp_path),
        title="Rock salt",
    )

    assert result.success is True


def test_save_cif_file_writes_the_cif_named_after_the_formula(tmp_path: Path) -> None:
    cif = make_cif()

    result = CrystaLyseVisualizer.save_cif_file(
        cif_content=cif, formula="NaCl", output_dir=str(tmp_path)
    )

    written = tmp_path / "NaCl.cif"
    assert result.success is True
    assert result.output_path == str(written)
    assert result.cached is False
    assert written.read_text() == cif


def test_save_cif_file_creates_a_missing_output_dir(tmp_path: Path) -> None:
    nested = tmp_path / "runs" / "2026-01-01"

    result = CrystaLyseVisualizer.save_cif_file(
        cif_content=make_cif(), formula="NaCl", output_dir=str(nested)
    )

    assert result.success is True
    assert (nested / "NaCl.cif").is_file()


def test_second_save_of_the_same_formula_is_cached_and_does_not_overwrite(tmp_path: Path) -> None:
    first = make_cif(a=5.64)
    second = make_cif(a=6.10)
    assert first != second, "the two CIFs must differ for the no-overwrite claim to mean anything"

    CrystaLyseVisualizer.save_cif_file(cif_content=first, formula="NaCl", output_dir=str(tmp_path))
    result = CrystaLyseVisualizer.save_cif_file(
        cif_content=second, formula="NaCl", output_dir=str(tmp_path)
    )

    assert result.cached is True
    assert (tmp_path / "NaCl.cif").read_text() == first


def test_save_cif_file_reports_failure_instead_of_raising(tmp_path: Path) -> None:
    """A file where the output directory should be: reported, not propagated."""
    blocked = tmp_path / "not-a-dir"
    blocked.write_text("in the way")

    result = CrystaLyseVisualizer.save_cif_file(
        cif_content=make_cif(), formula="NaCl", output_dir=str(blocked)
    )

    assert result.success is False
    assert result.error


def test_create_analysis_suite_accepts_title_and_color_scheme_by_keyword(tmp_path: Path) -> None:
    result = CrystaLyseVisualizer.create_analysis_suite(
        cif_content=make_cif(),
        formula="NaCl",
        output_dir=str(tmp_path),
        title="Rock salt analysis",
        color_scheme="vesta",
    )

    assert result.success is True


def test_create_analysis_suite_creates_the_directory_it_reports(tmp_path: Path) -> None:
    result = CrystaLyseVisualizer.create_analysis_suite(
        cif_content=make_cif(), formula="NaCl", output_dir=str(tmp_path)
    )

    analysis_dir = tmp_path / "NaCl_analysis"
    assert result.success is True
    assert result.output_path == str(analysis_dir)
    assert analysis_dir.is_dir()


def test_create_analysis_suite_puts_the_cif_inside_that_directory(tmp_path: Path) -> None:
    cif = make_cif()

    CrystaLyseVisualizer.create_analysis_suite(
        cif_content=cif, formula="NaCl", output_dir=str(tmp_path)
    )

    assert (tmp_path / "NaCl_analysis" / "NaCl.cif").read_text() == cif
