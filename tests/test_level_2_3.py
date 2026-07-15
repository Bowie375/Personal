"""Act 2.3 — First joint: a planetary gearbox lifts a rod to a settled angle."""

from __future__ import annotations

from robot_forge.levels.diagnostics import DiagKind
from robot_forge.levels.level_2_3 import (
    DT,
    JointLevel,
    solve_driving_voltage_2_3,
)


def _settle(level: JointLevel, seconds: float = 16.0) -> None:
    for _ in range(int(seconds / DT)):
        level.step()


def test_default_rod_hangs_at_zero() -> None:
    """No voltage -> the rod hangs straight down at angle 0, at rest."""
    lvl = JointLevel()
    _settle(lvl)
    assert lvl.applied_voltage == 0.0
    assert lvl.link_angle == 0.0
    assert abs(lvl.state.carrier_omega) == 0.0
    assert not lvl.won


def test_default_reduction_is_six_to_one() -> None:
    """Default set sun N12 / ring N60 -> planet N24, ring-fixed 6:1."""
    lvl = JointLevel()
    assert lvl.gear_sun.teeth == 12
    assert lvl.gear_ring.teeth == 60
    assert lvl.derived_planet_teeth == 24  # (60-12)/2
    assert abs(lvl.reduction_ratio) == 6.0  # 1 + 60/12


def test_solver_voltage_settles_at_target_and_wins() -> None:
    """The equilibrium voltage lands the rod at the target angle (±2°) -> won."""
    lvl = JointLevel()
    v = solve_driving_voltage_2_3(
        lvl.target_angle_deg, abs(lvl.reduction_ratio), lvl.rod_mass, lvl.rod_length
    )
    lvl.set_voltage(v)
    _settle(lvl)
    assert abs(lvl.link_angle_deg - lvl.target_angle_deg) < 2.0
    assert lvl.won


def test_undershoot_diagnoses() -> None:
    """Too little torque -> settles short of target -> UNDERSHOOT, not won."""
    lvl = JointLevel()
    v = solve_driving_voltage_2_3(
        lvl.target_angle_deg, abs(lvl.reduction_ratio), lvl.rod_mass, lvl.rod_length
    )
    lvl.set_voltage(v * 0.5)
    _settle(lvl)
    assert lvl.link_angle_deg < lvl.target_angle_deg - 2.0
    assert not lvl.won
    assert lvl.last_diagnostic is not None
    assert lvl.last_diagnostic.kind == DiagKind.UNDERSHOOT


def test_overshoot_diagnoses() -> None:
    """Too much torque -> rod pins at ~90° (the over-torque cap) -> OVERSHOOT."""
    lvl = JointLevel()
    lvl.set_voltage(24.0)  # max voltage at 6:1 -> equilibrium past horizontal
    _settle(lvl)
    assert lvl.link_angle_deg > 89.0  # pinned at the cap
    assert not lvl.won
    assert lvl.last_diagnostic is not None
    assert lvl.last_diagnostic.kind == DiagKind.OVERSHOOT


def test_rod_never_overshoots_past_horizontal() -> None:
    """Max voltage at the default 6:1: the rod pins at ~90°, NEVER exceeds 90°.

    The open-loop no-flip guarantee: gravity always restores, so the player
    never needs to cut voltage. Even at full torque the rod rests against the
    horizontal hard stop rather than flipping over the top.
    """
    lvl = JointLevel()
    lvl.set_voltage(24.0)
    max_angle = 0.0
    for _ in range(int(16.0 / DT)):
        lvl.step()
        max_angle = max(max_angle, lvl.link_angle_deg)
    assert max_angle < 90.1  # never past horizontal
    assert lvl.state.overspeed  # flagged as over-torque


def test_voltage_clamped() -> None:
    lvl = JointLevel()
    lvl.set_voltage(1e6)
    assert lvl.applied_voltage == 24.0
    lvl.set_voltage(-1e6)
    assert lvl.applied_voltage == -24.0


def test_set_gears_updates_reduction_and_assemblability() -> None:
    """set_gears(sun, ring) derives the planet; invalid pairs are not assemblable."""
    lvl = JointLevel()
    # A valid 2.5:1 set: sun N12 / ring N18 -> planet N3 (NOT in catalog) -> bad.
    # Use a valid one: sun N12 / ring N48 -> planet N18 (not catalog) -> bad.
    lvl.set_gears(12, 48)
    assert lvl.derived_planet_teeth == 18
    assert not lvl.assemblable  # N18 not in the catalog
    # Valid: sun N12 / ring N60 -> planet N24 -> assemblable, 6:1.
    lvl.set_gears(12, 60)
    assert lvl.derived_planet_teeth == 24
    assert lvl.assemblable
    assert abs(lvl.reduction_ratio) == 6.0


def test_summary_shape() -> None:
    """summary() surfaces the angle + planetary teeth + mode."""
    lvl = JointLevel()
    s = lvl.summary()
    for key in (
        "link_angle",
        "link_angle_deg",
        "target_angle",
        "target_angle_deg",
        "reduction_ratio",
        "teeth_sun",
        "teeth_planet",
        "teeth_ring",
        "mode",
        "voltage",
        "won",
    ):
        assert key in s
    assert s["target_angle_deg"] == 45.0
    assert s["teeth_sun"] == 12
    assert s["teeth_ring"] == 60
    assert s["mode"] == "ring_fixed"
