"""Act 2.2 — Planetary gearbox: same gears, three ratios depending on the grounded member."""

from __future__ import annotations

import math

from robot_forge.levels.diagnostics import DiagKind
from robot_forge.levels.level_2_2 import (
    DT,
    PlanetaryGearLevel,
    solve_driving_voltage_2_2,
)


def test_ring_fixed_reduction_formula() -> None:
    """Ring pinned, sun drives, carrier out: ratio = 1 + N_ring/N_sun."""
    lvl = PlanetaryGearLevel()
    lvl.set_gears(12, 60)  # 1 + 60/12 = 6.0
    lvl.set_mode("ring_fixed")
    assert math.isclose(lvl.reduction_ratio, 6.0, abs_tol=1e-9)
    assert lvl.reduction_ratio > 0  # same direction as the sun


def test_carrier_fixed_reverses() -> None:
    """Carrier pinned, sun drives, ring out: ring spins OPPOSITE the sun."""
    lvl = PlanetaryGearLevel()
    lvl.set_gears(12, 60)
    lvl.set_mode("carrier_fixed")
    # ratio = -N_ring/N_sun = -60/12 = -5.0 (reversing)
    assert math.isclose(lvl.reduction_ratio, -5.0, abs_tol=1e-9)
    lvl.set_voltage(10.0)
    for _ in range(int(2.0 / DT)):
        lvl.step()
    # Sun +, ring - (reversed by the carrier-fixed mode).
    assert lvl.state.sun_omega > 0
    assert lvl.state.ring_omega < 0


def test_sun_fixed_pins_train() -> None:
    """Sun grounded => motor (on the sun) can't drive; train is pinned."""
    lvl = PlanetaryGearLevel()
    lvl.set_gears(12, 60)
    lvl.set_mode("sun_fixed")
    lvl.set_voltage(24.0)  # full voltage, but the sun is locked
    for _ in range(int(1.0 / DT)):
        lvl.step()
    assert lvl.state.sun_omega == 0.0
    assert lvl.state.carrier_omega == 0.0
    assert lvl.state.ring_omega == 0.0
    assert lvl.state.stalled


def test_assemblability_rule() -> None:
    """The planet is DERIVED from sun+ring: N_planet = (N_ring - N_sun)/2, and
    must be a catalog gear; then 3 planets must coexist (slotting)."""
    lvl = PlanetaryGearLevel()
    # sun N12, ring N60 -> planet (60-12)/2 = N24, in catalog, 48%3==0 -> OK.
    lvl.set_gears(12, 60)
    assert lvl.assemblable
    assert lvl.derived_planet_teeth == 24
    # sun N24, ring N48 -> planet N12, in catalog, 24%3==0 -> OK.
    lvl.set_gears(24, 48)
    assert lvl.assemblable
    assert lvl.derived_planet_teeth == 12
    # ring not bigger than sun -> not assemblable.
    lvl.set_gears(40, 30)
    assert not lvl.assemblable


def test_assemblability_rejects_non_catalog_planet() -> None:
    """The OLD (wrong) rule falsely passed sun N12 / ring N48 (diff 36, %3==0).
    The planet would be (48-12)/2 = N18 — NOT in the catalog -> rejected now."""
    lvl = PlanetaryGearLevel()
    lvl.set_gears(12, 48)
    assert lvl.derived_planet_teeth == 18
    assert not lvl.assemblable  # N18 isn't a catalog gear


def test_assemblability_rejects_odd_difference() -> None:
    """(N_ring - N_sun) must be even: a planet needs an integer tooth count."""
    lvl = PlanetaryGearLevel()
    lvl.set_gears(12, 30)  # diff 18, even, planet (30-12)/2 = N9 (not catalog)
    assert lvl.derived_planet_teeth == 9
    assert not lvl.assemblable


def test_assemblability_rejects_slotting_failure() -> None:
    """sun N16 / ring N48 -> planet N16 (in catalog) passes geometry, but
    (48-16)=32 doesn't divide by 3 -> 3 planets collide -> NOT assemblable."""
    lvl = PlanetaryGearLevel()
    lvl.set_gears(16, 48)
    assert lvl.derived_planet_teeth == 16  # fits one planet
    assert not lvl.assemblable  # but 3 won't coexist


def test_compound_drives_and_wins() -> None:
    """The keystone: sun N12 / planet N24 / ring N60, ring-fixed 6:1, wins."""
    lvl = PlanetaryGearLevel()
    lvl.set_gears(12, 60)
    lvl.set_mode("ring_fixed")
    lvl.set_load(lvl.target_load_torque)
    v = solve_driving_voltage_2_2(
        lvl.target_out_rpm, abs(lvl.reduction_ratio), lvl.target_load_torque
    )
    assert math.isfinite(v) and abs(v) <= lvl.max_voltage
    lvl.set_voltage(abs(v) * 1.01)
    for _ in range(int(12.0 / DT)):
        lvl.step()
    assert lvl.assemblable
    assert not lvl.state.stalled
    assert lvl.won
    assert math.isclose(abs(lvl.reduction_ratio), lvl.target_ratio)
    assert math.isclose(abs(lvl.output_rpm), lvl.target_out_rpm, abs_tol=2.0)
    # Carrier (output) is 6x slower than the sun; ring is pinned.
    assert math.isclose(lvl.carrier_rpm, lvl.sun_rpm / 6.0, rel_tol=0.05)
    assert abs(lvl.ring_rpm) < 0.5


def test_wrong_ratio_diagnoses() -> None:
    """An assemblable but too-small set (ratio 3.0) can't reach the 6:1 target."""
    lvl = PlanetaryGearLevel()
    # sun N12 / ring N36 -> diff 24, divisible by 3 -> assemblable, ratio 4.0.
    # (Not 6.0, so it's a ratio mismatch, not an assembly failure.)
    lvl.set_gears(12, 36)
    assert lvl.assemblable
    assert math.isclose(abs(lvl.reduction_ratio), 4.0)
    lvl.set_load(lvl.target_load_torque)
    lvl.set_voltage(20.0)
    for _ in range(int(3.0 / DT)):
        lvl.step()
    assert not lvl.won
    assert lvl.last_diagnostic is not None
    assert lvl.last_diagnostic.kind == DiagKind.WRONG_RATIO


def test_wrong_mode_gives_wrong_ratio_and_direction() -> None:
    """Right gears but wrong mode: carrier-fixed yields -5:1, not +6:1."""
    lvl = PlanetaryGearLevel()
    lvl.set_gears(12, 60)  # the winning gears
    lvl.set_mode("carrier_fixed")  # but wrong mode -> ratio -5.0
    lvl.set_load(lvl.target_load_torque)
    lvl.set_voltage(15.0)
    for _ in range(int(3.0 / DT)):
        lvl.step()
    assert not lvl.won
    assert lvl.last_diagnostic is not None
    # Either the ratio magnitude (5 != 6) or the reversed direction fails.
    assert lvl.last_diagnostic.kind in (DiagKind.WRONG_RATIO, DiagKind.WRONG_DIRECTION)


def test_not_assemblable_blocks_win() -> None:
    """A non-assemblable set is flagged before any ratio/speed check."""
    lvl = PlanetaryGearLevel()
    lvl.set_gears(16, 48)  # diff 32, not divisible by 3
    lvl.set_load(lvl.target_load_torque)
    lvl.set_voltage(20.0)
    for _ in range(int(2.0 / DT)):
        lvl.step()
    assert not lvl.assemblable
    assert not lvl.won
    assert lvl.last_diagnostic is not None
    assert lvl.last_diagnostic.kind == DiagKind.NOT_ASSEMBLABLE


def test_no_back_drive_on_coastdown() -> None:
    """A train under insufficient voltage pins at zero — no flicker / reversal."""
    lvl = PlanetaryGearLevel()
    lvl.set_gears(12, 60)
    lvl.set_load(lvl.target_load_torque)
    lvl.set_voltage(0.5)  # far too small to start a 0.5 N·m / 6 load
    crossings = 0
    prev_sign = 0
    for _ in range(int(3.0 / DT)):
        lvl.step()
        sign = 1 if lvl.state.sun_omega > 1e-4 else (-1 if lvl.state.sun_omega < -1e-4 else 0)
        if sign != 0 and prev_sign != 0 and sign != prev_sign:
            crossings += 1
        if sign != 0:
            prev_sign = sign
    assert crossings == 0  # never reversed
    assert lvl.state.stalled  # and it stayed pinned


def test_reflected_load_shrinks_with_reduction() -> None:
    """A 6:1 planetary reflects the load down to the sun by /6."""
    lvl = PlanetaryGearLevel()
    lvl.set_gears(12, 60)
    lvl.set_mode("ring_fixed")
    lvl.set_load(0.6)
    assert math.isclose(lvl._reflected_load(), 0.6 / 6.0, abs_tol=1e-9)


def test_solve_voltage_finite() -> None:
    v = solve_driving_voltage_2_2(10.0, 6.0, 0.5)
    assert math.isfinite(v)
    assert abs(v) <= 24.0


def test_voltage_clamped() -> None:
    lvl = PlanetaryGearLevel()
    lvl.set_voltage(100.0)
    assert lvl.applied_voltage == lvl.max_voltage


def test_set_gears_derives_planet() -> None:
    """set_gears takes sun + ring; the planet is derived: (40-16)/2 = N12."""
    lvl = PlanetaryGearLevel()
    lvl.set_gears(16, 40)
    assert lvl.gear_sun.teeth == 16
    assert lvl.gear_ring.teeth == 40
    assert lvl.gear_planet.teeth == 12  # derived
    assert lvl.derived_planet_teeth == 12


def test_set_mode_rejects_unknown() -> None:
    lvl = PlanetaryGearLevel()
    lvl.set_mode("nonsense")
    assert lvl.mode == PlanetaryGearLevel().mode  # unchanged (default)


def test_summary_shape() -> None:
    lvl = PlanetaryGearLevel()
    s = lvl.summary()
    assert s["level"] == "2.2"
    for key in (
        "sun_rpm",
        "carrier_rpm",
        "ring_rpm",
        "output_rpm",
        "reduction_ratio",
        "target_ratio",
        "mode",
        "num_planets",
        "assemblable",
        "voltage",
        "load_torque",
        "reflected_load",
        "output_torque",
        "stalled",
        "won",
        "teeth_sun",
        "teeth_planet",
        "teeth_ring",
    ):
        assert key in s


def test_default_mode_is_ring_fixed() -> None:
    """The classic robot-joint reducer is the default (and the win target)."""
    lvl = PlanetaryGearLevel()
    assert lvl.mode == "ring_fixed"
    assert lvl.target_sign == 1
