"""Characterisation tests for ``SMACTScreener.validate_composition``.

These exist because the smact 3.x -> 4.0 port silently changed scientific
verdicts and nothing caught it.  smact 4 honours its ``ICSD24FilterConfig``
only when ``oxidation_states_set is None``, and that filtered path applies an
ICSD commonality cut that removes less-common oxidation states -- Cu(3+),
Mo(4+), Mn(7+), W(4+) among them.  Materials needing one of those stop
charge-balancing and flip from valid to invalid.

The first port mapped ``"icsd24"`` to ``None`` unconditionally, which turned
YBa2Cu3O7, MoS2, KMnO4 and WS2 invalid at *default* parameters.  A
35-composition smoke check missed it because none of those compositions
needed a filtered-out oxidation state -- which is precisely why a fixed,
adversarially-chosen formula list belongs in the test suite instead.

So: pin the verdicts, and pin the fact that the filter parameters still do
something when a caller asks for them.
"""

from __future__ import annotations

import pytest

from crystalyse.tools.smact.screening import SMACT_AVAILABLE, SMACTScreener

pytestmark = pytest.mark.skipif(not SMACT_AVAILABLE, reason="smact not installed")


#: Compositions whose validity must not drift.  The first four are the ones
#: the unconditional-``None`` port broke; each needs an oxidation state that
#: the ICSD commonality cut discards.
EXPECTED_VALIDITY: dict[str, bool] = {
    # Regression guards: these need Cu(3+), Mo(4+), Mn(7+), W(4+).
    "YBa2Cu3O7": True,
    "MoS2": True,
    "KMnO4": True,
    "WS2": True,
    # Ordinary valid chemistry.
    "NaCl": True,
    "LiFePO4": True,
    "Fe2O3": True,
    "TiO2": True,
    "BaTiO3": True,
    "Cs2AgBiBr6": True,
    "LiCoO2": True,
    "CaCO3": True,
    # Charge-imbalanced: must stay invalid, or the test proves nothing.
    "NaClO7": False,
}


@pytest.mark.parametrize(("formula", "expected"), sorted(EXPECTED_VALIDITY.items()))
def test_validity_verdicts_are_stable(formula: str, expected: bool) -> None:
    """Default-parameter verdicts are pinned against silent drift."""
    result = SMACTScreener.validate_composition(composition=formula)
    assert result.success, f"{formula}: {result.error_message}"
    assert result.is_valid is expected, (
        f"{formula} validity changed to {result.is_valid}. If this is intended, "
        f"update EXPECTED_VALIDITY and say so in the PR -- a verdict change is a "
        f"change to screening results, not a refactor."
    )


def test_default_call_does_not_apply_the_icsd_commonality_filter() -> None:
    """With default parameters the unfiltered named set is used.

    This is the specific behaviour that keeps YBa2Cu3O7 and friends valid.
    """
    result = SMACTScreener.validate_composition(composition="YBa2Cu3O7")
    assert result.is_valid is True
    assert result.oxidation_states_set == "icsd24"


def test_filter_parameters_still_change_verdicts_when_asked_for() -> None:
    """consensus/commonality must not be inert.

    Keeping the default path unfiltered is only acceptable if a caller who
    explicitly asks for filtering still gets it -- otherwise the parameters are
    decorative, which is the failure mode this port was meant to avoid.
    """
    loose = SMACTScreener.validate_composition("MnO2", consensus=3, commonality="medium")
    strict = SMACTScreener.validate_composition("MnO2", consensus=50, commonality="main")
    assert loose.success and strict.success
    assert loose.is_valid != strict.is_valid, (
        "consensus/commonality no longer affect the result -- the ICSD24 filter "
        "is being ignored, which is what the smact 4 port had to work around."
    )


def test_result_reports_the_oxidation_set_actually_used() -> None:
    """Provenance must not claim a set that was not passed to smact.

    When filtering is requested the set is switched to None; reporting
    ``"icsd24"`` there would record a screening basis that was never used.
    """
    filtered = SMACTScreener.validate_composition("MnO2", consensus=50, commonality="main")
    assert filtered.oxidation_states_set is None

    unfiltered = SMACTScreener.validate_composition("MnO2")
    assert unfiltered.oxidation_states_set == "icsd24"


def test_invalid_oxidation_set_is_rejected() -> None:
    result = SMACTScreener.validate_composition("NaCl", oxidation_states_set="not-a-set")
    assert result.success is False
    assert "Invalid oxidation set" in (result.error_message or "")


def test_named_non_icsd_set_is_passed_through() -> None:
    """A caller naming a different set gets it, filter or not."""
    result = SMACTScreener.validate_composition("NaCl", oxidation_states_set="smact14")
    assert result.success is True
    assert result.oxidation_states_set == "smact14"
