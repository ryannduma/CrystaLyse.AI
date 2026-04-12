"""Tests for crystalyse.plan.heuristic — Feature 2.6 acceptance criteria.

Acceptance criteria from spec §5 Feature 2.6:
  - Unit test per signal
  - Unit test for override precedence
  - "What is the formation energy of NaCl" → False
  - Paper queries → True
"""

from __future__ import annotations

from crystalyse.config.settings import CrystalyseSettings
from crystalyse.plan.heuristic import _run_heuristic, should_auto_enter_plan_mode

# ---------------------------------------------------------------------------
# Per-signal unit tests
# ---------------------------------------------------------------------------


class TestSignalWordCount:
    """Signal 1: query > 20 words."""

    def test_short_query_false(self):
        assert not _run_heuristic("Find stable perovskites")

    def test_21_word_query_true(self):
        q = " ".join(["word"] * 21)
        assert _run_heuristic(q)

    def test_20_word_query_false(self):
        q = " ".join(["word"] * 20)
        assert not _run_heuristic(q)


class TestSignalMultiCandidate:
    """Signal 2: multi-candidate phrases."""

    def test_multiple(self):
        assert _run_heuristic("Find multiple stable oxides")

    def test_several(self):
        assert _run_heuristic("Predict several new perovskites")

    def test_five(self):
        assert _run_heuristic("Predict five new quaternary compositions")

    def test_list(self):
        assert _run_heuristic("List all stable halide perovskites")

    def test_candidates(self):
        assert _run_heuristic("Find candidates for tandem solar cells")

    def test_set_of(self):
        assert _run_heuristic("Design a set of cathode materials")

    def test_family_of(self):
        assert _run_heuristic("Explore the family of double perovskites")


class TestSignalRigour:
    """Signal 3: rigour / publication keywords."""

    def test_stability(self):
        assert _run_heuristic("Check stability of Cs2AgBiBr6")

    def test_validate(self):
        assert _run_heuristic("Validate the phase stability")

    def test_verify(self):
        assert _run_heuristic("Verify these formation energies")

    def test_rigorous(self):
        assert _run_heuristic("Do a rigorous analysis")

    def test_publication(self):
        assert _run_heuristic("Prepare results for publication")


class TestSignalThresholds:
    """Signal 4: threshold patterns."""

    def test_greater_than(self):
        assert _run_heuristic("Find materials with bandgap > 1.5")

    def test_less_than(self):
        assert _run_heuristic("E_hull < 50 meV/atom")

    def test_mev_per_atom(self):
        assert _run_heuristic("Stability threshold of 100 meV/atom")

    def test_gpa(self):
        assert _run_heuristic("Bulk modulus above 200 GPa")

    def test_ev(self):
        assert _run_heuristic("Bandgap around 1.5 eV")

    def test_mah_per_g(self):
        assert _run_heuristic("Capacity exceeding 200 mAh/g")


# ---------------------------------------------------------------------------
# Override precedence
# ---------------------------------------------------------------------------


class TestOverridePrecedence:
    """Override order: CLI flag > settings > heuristic."""

    def test_cli_plan_overrides_settings_off(self):
        settings = CrystalyseSettings(plan_mode="off")
        assert should_auto_enter_plan_mode("short query", settings, cli_plan_flag=True)

    def test_cli_no_plan_overrides_settings_on(self):
        settings = CrystalyseSettings(plan_mode="on")
        assert not should_auto_enter_plan_mode("anything", settings, cli_plan_flag=False)

    def test_cli_no_plan_overrides_heuristic_true(self):
        # This query would trigger the heuristic
        q = "Predict five new stable quaternary compositions"
        assert not should_auto_enter_plan_mode(q, cli_plan_flag=False)

    def test_settings_on_ignores_heuristic(self):
        settings = CrystalyseSettings(plan_mode="on")
        assert should_auto_enter_plan_mode("NaCl", settings)

    def test_settings_off_ignores_heuristic(self):
        settings = CrystalyseSettings(plan_mode="off")
        q = "Predict five new stable quaternary compositions"
        assert not should_auto_enter_plan_mode(q, settings)

    def test_settings_auto_defers_to_heuristic(self):
        settings = CrystalyseSettings(plan_mode="auto")
        assert not should_auto_enter_plan_mode("What is NaCl", settings)
        assert should_auto_enter_plan_mode("Find multiple stable oxides", settings)

    def test_no_settings_defaults_to_auto(self):
        assert not should_auto_enter_plan_mode("What is NaCl")


# ---------------------------------------------------------------------------
# Spec acceptance criteria: specific queries
# ---------------------------------------------------------------------------


class TestSpecQueries:
    """Specific queries from spec §5 Feature 2.6 acceptance criteria."""

    def test_nacl_formation_energy_false(self):
        """'What is the formation energy of NaCl' → False."""
        assert not should_auto_enter_plan_mode("What is the formation energy of NaCl")

    def test_quaternary_oxide_paper_query_true(self):
        """Paper query: 'Predict five new stable quaternary compositions...' → True."""
        q = "Predict five new stable quaternary compositions formed of K, Y, Zr and O"
        assert should_auto_enter_plan_mode(q)

    def test_sodium_ion_cathode_paper_query_true(self):
        """Paper query: 'Design a sodium-ion cathode with capacity > 200 mAh/g' → True."""
        assert should_auto_enter_plan_mode("Design a sodium-ion cathode with capacity > 200 mAh/g")

    def test_lead_free_photovoltaic_paper_query_true(self):
        """Paper query: 'Find me a lead-free photovoltaic with bandgap ~1.5 eV' → True."""
        assert should_auto_enter_plan_mode("Find me a lead-free photovoltaic with bandgap ~1.5 eV")
