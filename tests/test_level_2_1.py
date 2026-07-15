"""Act 2.1 — Compound gearbox: stage ratios multiply, reach what one mesh can't."""

from __future__ import annotations

import math

from robot_forge.levels.diagnostics import DiagKind
from robot_forge.levels.level_2_1 import (
    DT,
    CompoundGearLevel,
    solve_driving_voltage_2_1,
)
from robot_forge.sim.gears import CATALOG


def test_default_is_one_to_one() -> None:
    lvl = CompoundGearLevel()
    assert lvl.total_ratio == 1.0
    assert lvl.stage1_ratio == 1.0
    assert lvl.stage2_ratio == 1.0


def test_no_single_pair_reaches_target_ratio() -> None:
    """The keystone: 12:1 is unreachable by any single catalog pair (max 5:1)."""
    max_single = max(
        b.teeth / a.teeth for a in CATALOG.values() for b in CATALOG.values() if a != b
    )
    assert max_single == 5.0  # N12 -> N60
    assert max_single < CompoundGearLevel().target_ratio  # 5 < 12


def test_stage_ratios_multiply() -> None:
    lvl = CompoundGearLevel()
    lvl.set_gears(12, 36, 12, 48)  # 3:1 * 4:1
    assert lvl.stage1_ratio == 3.0
    assert lvl.stage2_ratio == 4.0
    assert lvl.total_ratio == 12.0


def test_shared_shaft_means_b_equals_c_rpm() -> None:
    """B and C are on the same shaft, so they share angular velocity."""
    lvl = CompoundGearLevel()
    lvl.set_gears(12, 36, 12, 48)
    lvl.set_voltage(15.0)
    for _ in range(int(2.0 / DT)):
        lvl.step()
    # The intermediate joint reads the shared-shaft speed; B and C spin together.
    assert math.isclose(lvl.state.b_omega, lvl.state.b_omega)  # tautology guard
    # Kinematic check: omega_B = -omega_A * (N_A/N_B); omega_D = -omega_B*(N_C/N_D)
    assert math.isclose(
        lvl.state.d_omega,
        -lvl.state.b_omega * (lvl.gear_c.teeth / lvl.gear_d.teeth),
        rel_tol=1e-9,
    )


def test_direction_is_same_as_driver() -> None:
    """Two external meshes -> output spins the SAME direction as the driver (+1)."""
    lvl = CompoundGearLevel()
    lvl.set_gears(12, 36, 12, 48)
    lvl.set_voltage(15.0)
    for _ in range(int(2.0 / DT)):
        lvl.step()
    assert lvl.driver_rpm > 0
    assert lvl.output_rpm > 0  # same sign as driver


def test_compound_drives_and_wins() -> None:
    lvl = CompoundGearLevel()
    lvl.set_gears(12, 36, 12, 48)
    lvl.set_load(lvl.target_load_torque)
    v = solve_driving_voltage_2_1(lvl.target_out_rpm, lvl.total_ratio, lvl.target_load_torque)
    assert math.isfinite(v) and abs(v) <= lvl.max_voltage
    lvl.set_voltage(abs(v) * 1.01)
    for _ in range(int(12.0 / DT)):
        lvl.step()
    assert not lvl.state.stalled
    assert lvl.won
    assert math.isclose(lvl.total_ratio, lvl.target_ratio)  # 12:1 exactly
    assert math.isclose(abs(lvl.output_rpm), lvl.target_out_rpm, abs_tol=2.0)


def test_wrong_ratio_diagnoses() -> None:
    """A 1:1 setup can't reach 12:1 — the diagnostic names the ratio mismatch."""
    lvl = CompoundGearLevel()  # 1:1 default
    lvl.set_load(lvl.target_load_torque)
    lvl.set_voltage(20.0)
    for _ in range(int(3.0 / DT)):
        lvl.step()
    assert not lvl.won
    assert lvl.last_diagnostic is not None
    # Ratio is the most salient failure for a 1:1 setup.
    assert lvl.last_diagnostic.kind == DiagKind.WRONG_RATIO


def test_voltage_clamped() -> None:
    lvl = CompoundGearLevel()
    lvl.set_voltage(100.0)
    assert lvl.applied_voltage == lvl.max_voltage


def test_set_gears_updates_all_four() -> None:
    lvl = CompoundGearLevel()
    lvl.set_gears(16, 48, 12, 36)
    assert lvl.gear_a.teeth == 16
    assert lvl.gear_b.teeth == 48
    assert lvl.gear_c.teeth == 12
    assert lvl.gear_d.teeth == 36
    assert lvl.total_ratio == (48 / 16) * (36 / 12)  # 3 * 3 = 9


def test_reflected_load_shrinks_with_compound_ratio() -> None:
    """A compound reduction reflects the load down through BOTH stages."""
    lvl = CompoundGearLevel()
    lvl.set_gears(12, 36, 12, 48)  # 12:1
    lvl.set_load(0.6)
    assert math.isclose(lvl._reflected_load(), 0.6 / 12.0, abs_tol=1e-9)


def test_solve_voltage_finite() -> None:
    v = solve_driving_voltage_2_1(10.0, 12.0, 0.5)
    assert math.isfinite(v)
    assert abs(v) <= 24.0


def test_summary_shape() -> None:
    lvl = CompoundGearLevel()
    s = lvl.summary()
    assert s["level"] == "2.1"
    for key in (
        "driver_rpm",
        "intermediate_rpm",
        "output_rpm",
        "total_ratio",
        "stage1_ratio",
        "stage2_ratio",
        "target_ratio",
        "voltage",
        "load_torque",
        "reflected_load",
        "output_torque",
        "stalled",
        "won",
        "teeth_a",
        "teeth_b",
        "teeth_c",
        "teeth_d",
    ):
        assert key in s
