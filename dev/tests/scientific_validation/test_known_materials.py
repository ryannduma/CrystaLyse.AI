"""Known materials: does the toolchain get the chemistry and the physics right?

Scheduled nightly by directory (``tests/scientific_validation/``), so no
``run_on`` marker is needed here.

Every reference number in this file carries its source inline.  Three kinds of
claim live here and they deserve very different tolerances:

* **Discrete facts** -- a space group, a coordination number, a validity
  verdict.  Exact; a tolerance would only hide a wrong answer.
* **Geometry** -- bond lengths, tight (0.01 A), because they follow from the
  lattice parameter the test itself supplies.
* **Energies from a machine-learned potential** -- deliberately loose.
  MACE-MP-0's reported stability MAE is ~57 meV/atom, so a test demanding
  agreement with DFT at meV precision would assert something the model never
  claimed and would flake forever on correct code.  The bands below are sized
  to catch what actually goes wrong -- a lost reference frame, a per-cell /
  per-atom mix-up, a unit slip -- all of which are off by an eV or more.

Nothing here reads a data file that a person could change, except the Materials
Project snapshot the hull tool itself ships; the three energies quoted from it
are re-derived from that snapshot in
``test_cited_mp_energies_are_the_snapshot_ground_states`` so they cannot rot
silently.
"""

from __future__ import annotations

from typing import Any

import pytest
from smact import Element

from crystalyse.tools.pymatgen import PhaseDiagramAnalyzer, PyMatgenAnalyzer
from crystalyse.tools.smact import SMACTScreener, SMACTValidator
from tests.fakes import make_structure

# ---------------------------------------------------------------------------
# Reference data
# ---------------------------------------------------------------------------

#: Rock-salt NaCl (structure type B1): space group Fm-3m (#225), a = 5.6402 A
#: at 298 K, Na on the 4a site and Cl on 4b, so each ion is coordinated by six
#: of the other at a/2 = 2.820 A and by twelve of its own kind at a/sqrt(2) =
#: 3.988 A.  Source: Wyckoff, *Crystal Structures* Vol. 1 (2nd ed., 1963), NaCl
#: B1 entry.  ``tests.fakes.NACL_STRUCTURE`` is that cell with a rounded to
#: 5.64 A, which is why the geometry assertions derive the expected bond length
#: from the cell the test passes in rather than hard-coding 2.8201.
ROCKSALT_SPACE_GROUP_SYMBOL = "Fm-3m"
ROCKSALT_SPACE_GROUP_NUMBER = 225

#: Body-centred cubic Na (Im-3m, #229), a = 4.2906 A at 293 K.  Source: Wyckoff
#: Vol. 1.  This is sodium's elemental standard state -- the reference phase
#: whose formation energy is zero *by definition*.
BCC_NA_LATTICE_A = 4.2906

#: Materials Project ground-state energies per atom, uncorrected GGA/GGA+U,
#: read from the snapshot this repo feeds to the hull tool
#: (``~/.cache/crystalyse/ppd-mp_all_entries_uncorrected_250409.pkl.gz``).
#: "Uncorrected" matters: MP's published NaCl energy carries an anion
#: correction of about -0.31 eV/atom that MACE was never trained to reproduce,
#: so the uncorrected value is the like-for-like comparison.
#:
#: Together they give the formation energy of NaCl in this frame:
#: -3.388148 - (-1.322525 - 1.848537)/2 = -1.803 eV/atom.  MP's corrected value
#: is about -2.11 eV/atom, and the experimental one is -2.13 eV/atom
#: (Df H = -411.2 kJ/mol over two atoms, CRC Handbook 97th ed.).  Which of those
#: frames the MACE tool actually reports is the subject of the xfail below.
MP_NACL_EV_PER_ATOM = -3.388148  # rock-salt NaCl
MP_CL2_EV_PER_ATOM = -1.848537  # solid Cl2
#: The elemental Na ground state in the snapshot is a 29-atom cell, not the
#: 2-atom one; MP's small-cell Na polymorphs sit at about -1.312 eV/atom, so the
#: whole polymorph spread is ~10 meV/atom -- 4% of the MACE band below, which is
#: why comparing a bcc calculation against this number is safe.
MP_NA_EV_PER_ATOM = -1.322525

#: How far a MACE-MP-0 energy may sit from the DFT number it was fitted to.
#: MACE-MP-0's reported stability MAE is ~57 meV/atom, so 0.25 eV/atom is about
#: four times the model's own error: wide enough that correct code never trips
#: it, and wide enough to absorb evaluating the *experimental* lattice constant
#: instead of the PBE-relaxed one.  Still narrow enough to catch a per-cell /
#: per-atom mix-up (a factor of 8 for the cells used here), a Ry/eV slip
#: (13.6x), or a dropped reference (>1 eV/atom).  Do not tighten this into a
#: DFT-agreement claim -- MACE makes no such claim.
MACE_VS_DFT_TOLERANCE_EV_PER_ATOM = 0.25


# ---------------------------------------------------------------------------
# Structures and helpers
# ---------------------------------------------------------------------------


def bcc_sodium() -> dict[str, Any]:
    """Elemental sodium in its standard state, built through the fakes builder."""
    a = BCC_NA_LATTICE_A
    return make_structure(
        numbers=[11, 11],
        positions=[[0.0, 0.0, 0.0], [a / 2, a / 2, a / 2]],
        cell=[[a, 0.0, 0.0], [0.0, a, 0.0], [0.0, 0.0, a]],
    )


def mace_energy(structure: dict[str, Any]) -> Any:
    """Run the production MACE path on *structure*, pinned to CPU.

    The import is deferred because ``crystalyse.tools.mace.energy`` pulls in
    torch and mace at module scope: importing it at the top of this file would
    turn "no MACE model available" into a collection error instead of the skip
    that ``requires("mace_model")`` is supposed to give.

    CPU is pinned so the reference comparisons mean the same thing on a laptop
    and on a GPU runner; the tolerances are far wider than the device
    difference, but a reference test should not move with the hardware.
    """
    from crystalyse.tools.mace.energy import MACECalculator

    result = MACECalculator(device="cpu").calculate_formation_energy_sync(structure)
    assert result.success, f"MACE calculation failed: {result.error}"
    return result


@pytest.fixture(scope="module")
def hull() -> PhaseDiagramAnalyzer:
    """The Materials Project hull, loaded once for the module (~45 s, ~2 GB).

    Every test that asks for this is marked ``requires("phase_diagram")``, so
    the 178 MB snapshot is never downloaded on demand from here.
    """
    analyzer = PhaseDiagramAnalyzer()
    if not analyzer.is_loaded():
        pytest.fail(
            "the phase-diagram snapshot is present but did not load, so the hull "
            "tool is silently returning inf for every composition"
        )
    return analyzer


# ---------------------------------------------------------------------------
# 1. SMACT: is this composition chemically possible at all?
# ---------------------------------------------------------------------------
#
# Charge balance for each of these, using the ICSD24 oxidation-state table that
# smact ships (``Element(sym).oxidation_states_icsd24``):
#
#   NaCl        Na(+1)  Cl(-1)
#   LiFePO4     Li(+1)  Fe(+2)  P(+5)   O(-2)
#   Fe2O3       Fe(+3)  O(-2)
#   BaTiO3      Ba(+2)  Ti(+4)  O(-2)
#   NaClO4      Na(+1)  Cl(+7)  O(-2)          -- sodium perchlorate, a control
#   YBa2Cu3O7   needs Cu(+3) (with Y(+1)) or Y(+4) (with Cu(+2)); the real
#               material is mixed-valence Cu(2+)/Cu(3+) with Y3+, Ba2+, O2-,
#               which smact's one-state-per-element balance cannot express
#   MoS2        Mo(+4)  S(-2)
#   KMnO4       K(+1)   Mn(+7)  O(-2)
#
# The last three are regression guards.  smact 4 honours its ICSD24 commonality
# filter only when ``oxidation_states_set is None``, and that filter drops
# Cu(+3), Y(+4), Mo(+4) and Mn(+7) -- so a port that routes the default call
# through the filtered path turns three real, well-characterised materials into
# "invalid chemistry".  (``tests/unit/tools/test_smact_screening.py`` pins the
# same verdicts as a port regression; this file states the chemistry that makes
# those verdicts right.)

KNOWN_VALID_CHEMISTRY = [
    "NaCl",
    "LiFePO4",
    "Fe2O3",
    "BaTiO3",
    "NaClO4",
    "YBa2Cu3O7",
    "MoS2",
    "KMnO4",
]


@pytest.mark.parametrize("formula", KNOWN_VALID_CHEMISTRY)
def test_screener_accepts_known_materials(formula: str) -> None:
    """Every formula above is a real, synthesised, charge-balanced compound."""
    result = SMACTScreener.validate_composition(composition=formula)
    assert result.success, result.error_message
    assert result.is_valid is True, (
        f"{formula} is a real material; calling it invalid chemistry would have a "
        f"screening run discard it before any structure is ever generated"
    )


@pytest.mark.parametrize("formula", KNOWN_VALID_CHEMISTRY)
def test_validator_accepts_known_materials(formula: str) -> None:
    """The other public entry point must reach the same chemical verdict.

    ``SMACTValidator`` takes a different route into smact from
    ``SMACTScreener`` (a pymatgen ``Composition``, and no filter argument at
    all).  Two APIs in one package disagreeing about whether a material is
    chemically possible is a defect on its own, whichever one is right.
    """
    result = SMACTValidator.validate_composition(formula)
    assert not result.errors, result.errors
    assert result.valid is True


def test_charge_impossible_composition_is_rejected() -> None:
    """NaClO7 cannot be charge balanced with any tabulated oxidation states.

    Na is only ever +1 and Cl runs to +7 at most, so with seven O(-2) the
    cation charge would have to reach +14 (Cl at +13), and with seven O(-1)
    it would have to reach +7 with one Na and one Cl, i.e. Cl at +6 -- which is
    not a tabulated chlorine state either.  Contrast NaClO4 above, which
    balances at Cl(+7) and must stay valid: without that control this test
    would also pass if the tool simply disliked long formulas.
    """
    result = SMACTScreener.validate_composition(composition="NaClO7")
    assert result.success, result.error_message
    assert result.is_valid is False


def test_icsd24_table_still_lists_the_states_the_guard_materials_need() -> None:
    """The premise the three regression guards rest on.

    If a future smact drops these states upstream, the guards above will fail
    and this test says immediately that the cause is the oxidation-state table,
    not this repo's filter handling.
    """
    assert 3 in Element("Cu").oxidation_states_icsd24, "Cu(+3), as in YBa2Cu3O7"
    assert 4 in Element("Mo").oxidation_states_icsd24, "Mo(+4), as in MoS2"
    assert 7 in Element("Mn").oxidation_states_icsd24, "Mn(+7), as in KMnO4"


@pytest.mark.parametrize(
    ("formula", "survives_strict_filter"),
    [
        ("YBa2Cu3O7", False),
        ("MoS2", False),
        ("KMnO4", False),
        ("NaCl", True),
        ("Fe2O3", True),
    ],
    ids=["YBa2Cu3O7", "MoS2", "KMnO4", "NaCl", "Fe2O3"],
)
def test_commonality_filter_only_rejects_materials_needing_uncommon_states(
    formula: str, survives_strict_filter: bool
) -> None:
    """The mechanism behind the regression guards, stated as chemistry.

    Asking for ``commonality="main"`` restricts each element to its most common
    ICSD oxidation states -- Cu to [+1, +2], Mo to [+5, +6], Mn to [+2, +3, +4]
    -- so exactly the materials that need a less common state lose their only
    charge-balanced assignment, while materials built from common states are
    untouched.  That asymmetry is why the default call must not filter.
    """
    default = SMACTScreener.validate_composition(composition=formula)
    strict = SMACTScreener.validate_composition(composition=formula, commonality="main")

    assert default.success and strict.success
    assert default.is_valid is True
    assert strict.is_valid is survives_strict_filter


# ---------------------------------------------------------------------------
# 2. Rock-salt geometry, from the structure alone (no checkpoints, no model)
# ---------------------------------------------------------------------------


def test_rocksalt_nacl_has_space_group_fm3m() -> None:
    """The B1 structure is face-centred cubic, Fm-3m (#225)."""
    result = PyMatgenAnalyzer.analyze_space_group(make_structure())

    assert result.success, result.error
    assert result.space_group_symbol == ROCKSALT_SPACE_GROUP_SYMBOL
    assert result.space_group_number == ROCKSALT_SPACE_GROUP_NUMBER
    assert result.crystal_system == "cubic"


def test_rocksalt_primitive_cell_holds_one_formula_unit() -> None:
    """Fm-3m has an FCC lattice, so the 8-atom conventional cell reduces to 2.

    Getting 8 back would mean the symmetry search found only P1 and every
    downstream "primitive cell" claim is four times too large.
    """
    result = PyMatgenAnalyzer.analyze_space_group(make_structure())

    assert result.success, result.error
    assert result.original_num_atoms == 8
    assert result.primitive_num_atoms == 2
    assert result.primitive_formula == "NaCl"


def test_rocksalt_sodium_is_six_coordinate_octahedral() -> None:
    """Na sits in an octahedral hole of the Cl FCC sublattice: CN 6."""
    result = PyMatgenAnalyzer.analyze_coordination(make_structure())

    assert result.success, result.error
    sodium = [site for site in result.coordination_data if site["element"] == "Na"]
    assert len(sodium) == 4, "the conventional cell contains four Na sites"
    assert {site["coordination_number"] for site in sodium} == {6}
    assert {site["geometry"] for site in sodium} == {"octahedral"}


def test_rocksalt_first_shell_is_six_equal_na_cl_bonds_at_half_the_cell_edge() -> None:
    """Nearest neighbours are Cl at a/2, not Na at a/sqrt(2).

    In B1 the six nearest neighbours of Na are all Cl at a/2 = 2.820 A, and the
    twelve Na second neighbours sit further out at 3.988 A.  A coordination
    routine that reached into the second shell would report Na among the
    coordinating elements and a mean bond length near 3.6 A.
    """
    structure = make_structure()
    expected_bond_length = structure["cell"][0][0] / 2

    result = PyMatgenAnalyzer.analyze_coordination(structure)
    assert result.success, result.error

    sodium = [s for s in result.coordination_data if s["element"] == "Na"]
    assert sodium, "no Na site was returned, so the per-site assertions below never ran"

    for site in sodium:
        assert site["coordinating_elements"] == ["Cl"]
        lengths = site["bond_lengths"]
        assert lengths["mean"] == pytest.approx(expected_bond_length, abs=0.01)
        # A regular octahedron: all six bonds the same length.
        assert lengths["max"] - lengths["min"] == pytest.approx(0.0, abs=0.01)


# ---------------------------------------------------------------------------
# 3. MACE energies on known materials
# ---------------------------------------------------------------------------


@pytest.mark.requires("mace_model")
@pytest.mark.parametrize(
    ("structure_builder", "mp_energy_per_atom"),
    [
        (make_structure, MP_NACL_EV_PER_ATOM),
        (bcc_sodium, MP_NA_EV_PER_ATOM),
    ],
    ids=["NaCl-rocksalt", "Na-bcc"],
)
def test_mace_total_energy_reproduces_the_mp_gga_energy(
    structure_builder: Any, mp_energy_per_atom: float
) -> None:
    """MACE-MP-0 was fitted to MPTrj, so it must land near the MP energy.

    This is the only MACE number with an unambiguous definition (the total
    energy of the cell in the model's own frame), which makes it the right
    place to check the model is loaded and wired up correctly.  See
    ``MACE_VS_DFT_TOLERANCE_EV_PER_ATOM`` for why the band is 0.25 eV/atom and
    must not be tightened; the ~10 meV/atom spread between MP's Na polymorphs
    disappears inside it, so the bcc-versus-ground-state mismatch on the sodium
    case cannot decide the outcome either way.
    """
    structure = structure_builder()
    result = mace_energy(structure)

    energy_per_atom = result.total_energy / len(structure["numbers"])
    assert energy_per_atom == pytest.approx(
        mp_energy_per_atom, abs=MACE_VS_DFT_TOLERANCE_EV_PER_ATOM
    )


@pytest.mark.requires("mace_model")
def test_mace_reports_rocksalt_nacl_as_bound() -> None:
    """The reported energy must be negative and of a physical magnitude.

    ``calculate_formation_energy`` returns the total energy minus MACE's own
    fitted atomic reference energies, divided by the atom count.  That is a
    binding energy in the model's reference frame rather than a thermochemical
    formation energy (see the xfail below), so the only claims that survive are
    weak ones: it is negative, because rock-salt NaCl is a bound crystal, and
    its magnitude does not exceed ~4 eV/atom, comfortably above the 3.32
    eV/atom needed to atomise NaCl (Df H = -411.2 kJ/mol, sublimation of Na
    107.5 kJ/mol, half the Cl2 bond enthalpy 121.3 kJ/mol; CRC Handbook 97th
    ed.).  Deliberately wide: it exists to catch a sign error, an eV/Ry slip or
    a per-cell value (8x here), not to pin the reference frame.  The strict
    version of that claim is the xfail below -- do not delete one as a
    duplicate of the other.
    """
    result = mace_energy(make_structure())

    assert result.formation_energy < -0.05, "a bound crystal cannot have E >= 0"
    assert result.formation_energy > -4.0, "more binding than atomisation is unphysical"


@pytest.mark.requires("mace_model")
def test_mace_gives_the_same_energy_for_the_same_structure_twice() -> None:
    """Two evaluations of one structure must agree to 1e-6 eV/atom.

    Inference on the cached float32 model is deterministic, so the observed
    difference is exactly zero; 1e-6 eV/atom leaves room for a different
    reduction order without admitting real drift, which would show at the meV
    scale.  What this catches is state leaking between calls -- a mutated Atoms
    object, or a calculator that keeps results from the previous structure.
    """
    structure = make_structure()
    n_atoms = len(structure["numbers"])
    first = mace_energy(structure)
    second = mace_energy(make_structure())

    assert first.total_energy / n_atoms == pytest.approx(second.total_energy / n_atoms, abs=1e-6)
    assert first.formation_energy == pytest.approx(second.formation_energy, abs=1e-6)


@pytest.mark.requires("mace_model")
@pytest.mark.xfail(
    strict=True,
    reason=(
        "BUG (reported, not fixed): calculate_formation_energy subtracts "
        "MACE-MP-0's fitted atomic reference energies (E0: Na -2.759 eV, "
        "Cl -2.812 eV), not the energies of the elemental ground states, so the "
        "field it calls 'formation_energy' -- surfaced to agents and users as "
        "'formation_energy_per_atom' -- is not a formation energy. For bcc Na it "
        "returns +1.46 eV/atom where the definition requires exactly 0, and the "
        "sign alone would mark the element unstable. For NaCl it returns -0.60 "
        "eV/atom against -1.80 (uncorrected GGA) and -2.13 (experiment). "
        "Remove this marker when the reference frame is fixed."
    ),
)
def test_formation_energy_of_an_element_in_its_standard_state_is_zero() -> None:
    """Df H of an element in its standard state is zero by definition.

    No reference data is needed for this one: bcc Na *is* the reference state,
    so any correct formation-energy implementation returns zero for it.  The
    0.1 eV/atom band is generous -- nearly twice MACE-MP-0's 57 meV/atom
    stability MAE -- so the failure is not a tolerance argument.
    """
    result = mace_energy(bcc_sodium())

    assert result.formation_energy == pytest.approx(0.0, abs=0.1)


# ---------------------------------------------------------------------------
# 4. Convex hull: is this composition thermodynamically stable?
# ---------------------------------------------------------------------------


@pytest.mark.requires("phase_diagram")
@pytest.mark.parametrize(
    ("composition", "energy_per_atom"),
    [
        ("NaCl", MP_NACL_EV_PER_ATOM),
        ("Na", MP_NA_EV_PER_ATOM),
        ("Cl", MP_CL2_EV_PER_ATOM),
    ],
    ids=["NaCl-rocksalt", "Na-ground-state", "Cl2-solid"],
)
def test_cited_mp_energies_are_the_snapshot_ground_states(
    hull: PhaseDiagramAnalyzer, composition: str, energy_per_atom: float
) -> None:
    """Verify the three MP numbers this file quotes against the snapshot itself.

    A ground-state energy sits *on* the hull, so feeding one back in must give a
    hull distance of zero.  This keeps the constants above honest without
    reaching into the pickle, and states the chemistry too: rock-salt NaCl and
    solid Cl2 are the stable phases at their compositions, as is the elemental
    sodium ground state.  The sign of a 1e-7 residual is meaningless, so the
    assertion is on the magnitude and on the tool not calling a ground state
    unstable.
    """
    result = hull.calculate_energy_above_hull(composition, energy_per_atom)

    assert result.success, result.error
    assert result.energy_above_hull == pytest.approx(0.0, abs=1e-3)
    assert result.is_unstable is False


@pytest.mark.requires("phase_diagram")
def test_rocksalt_nacl_does_not_decompose(hull: PhaseDiagramAnalyzer) -> None:
    """NaCl is a hull vertex: its decomposition is itself, one phase."""
    result = hull.calculate_energy_above_hull("NaCl", MP_NACL_EV_PER_ATOM)

    assert result.success, result.error
    assert [phase["formula"] for phase in result.decomposition_products] == ["NaCl"]


@pytest.mark.requires("phase_diagram")
def test_hypothetical_sodium_trichloride_decomposes_to_rocksalt_and_chlorine(
    hull: PhaseDiagramAnalyzer,
) -> None:
    """Sodium has only the +1 state, so "NaCl3" is a two-phase mixture.

    The hull must report NaCl + Cl2 in equal *atomic* fractions: one NaCl3
    formula unit is one NaCl (2 atoms) plus one Cl2 (2 atoms).  The energy
    passed in is irrelevant to the decomposition, which follows from the
    composition and the hull alone; it is supplied only because the API asks
    for one.
    """
    result = hull.calculate_energy_above_hull("NaCl3", -3.0)

    assert result.success, result.error
    products = {phase["formula"]: phase["fraction"] for phase in result.decomposition_products}
    assert set(products) == {"NaCl", "Cl2"}
    assert products["NaCl"] == pytest.approx(0.5, abs=0.01)
    assert products["Cl2"] == pytest.approx(0.5, abs=0.01)


@pytest.mark.requires("mace_model", "phase_diagram")
def test_mace_energy_places_rocksalt_nacl_on_the_mp_hull(hull: PhaseDiagramAnalyzer) -> None:
    """The end-to-end claim: MACE's energy must not make table salt unstable.

    This is the pipeline an agent actually runs -- MACE energy in, hull distance
    out -- and the one place where an error in either tool shows up as a wrong
    scientific conclusion.  0.1 eV/atom is under two times MACE-MP-0's 57
    meV/atom stability MAE and inside the 0.2 eV/atom window the tool itself
    calls metastable; the measured distance is ~7 meV/atom, so the band is not
    load-bearing, but tightening it towards that value would be asserting an
    accuracy MACE does not have.

    Note the energy is handed over *per atom* together with the reduced formula.
    Passing the cell's total energy with a reduced formula instead would divide
    -27.05 eV by the two atoms of "NaCl" rather than the eight in the cell, and
    place NaCl 10 eV/atom *below* its own hull -- a silent, spectacularly
    over-stable answer rather than an error.
    """
    structure = make_structure()
    mace_result = mace_energy(structure)
    energy_per_atom = mace_result.total_energy / len(structure["numbers"])

    result = hull.calculate_energy_above_hull("NaCl", energy_per_atom, per_atom=True)

    assert result.success, result.error
    assert result.energy_above_hull == pytest.approx(0.0, abs=0.1)
    assert result.is_unstable is False
