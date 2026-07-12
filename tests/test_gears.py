"""Gear math: ratios, meshing distance, planetary formulas."""

from __future__ import annotations

import math

from robot_forge.sim.gears import (
    CATALOG,
    SpurGear,
    center_distance,
    find_ratio_combo,
    gear_ratio,
    mesh_sign,
    planetary_ratio,
)


def test_meshing_distance_equals_sum_of_pitch_radii() -> None:
    a = CATALOG["N20"]
    b = CATALOG["N40"]
    assert math.isclose(center_distance(a, b), a.pitch_radius + b.pitch_radius)


def test_ratio_inverse_to_teeth() -> None:
    r = gear_ratio(CATALOG["N20"], CATALOG["N40"])
    assert math.isclose(r, 2.0)


def test_mesh_sign_two_gear_chain() -> None:
    assert mesh_sign(num_external_meshes=1) == -1


def test_mesh_sign_three_gear_chain_with_idler() -> None:
    # driver -> idler -> output: 2 external meshes -> sign +1
    assert mesh_sign(num_external_meshes=2) == 1


def test_mesh_sign_four_gear_chain() -> None:
    assert mesh_sign(num_external_meshes=3) == -1


def test_planetary_ring_fixed() -> None:
    r = planetary_ratio(CATALOG["N20"], CATALOG["N60"])
    # N_sun / (N_sun + N_ring) = 20 / 80 = 0.25
    assert math.isclose(r, 0.25)


def test_find_ratio_combo_finds_3_to_1() -> None:
    matches = find_ratio_combo(3.0, tolerance=0.01)
    assert any(dr == "N20" and dn == "N60" and math.isclose(r, 3.0) for dr, dn, r in matches)


def test_gear_mass_positive() -> None:
    assert CATALOG["N20"].mass > 0
    assert CATALOG["N60"].mass > CATALOG["N20"].mass


def test_outer_radius_greater_than_pitch() -> None:
    g = SpurGear(24)
    assert g.outer_radius > g.pitch_radius > g.root_radius
