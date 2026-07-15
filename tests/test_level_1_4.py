"""Act 1.4 — Loaded geartrain: reflected load, stall, torque×speed tradeoff."""

from __future__ import annotations

import math

from robot_forge.levels.diagnostics import DiagKind
from robot_forge.levels.level_1_4 import (
    DT,
    LoadedGearLevel,
    solve_driving_voltage_1_4,
)


def test_default_pair_meshes() -> None:
    lvl = LoadedGearLevel()
    assert lvl.meshed
    assert lvl.frame_center_distance == 30.0  # N30 + N30


def test_one_to_one_stalls_under_target_load() -> None:
    """The keystone lesson: 1:1 can't drive the target load at any voltage."""
    lvl = LoadedGearLevel()
    lvl.set_load(lvl.target_load_torque)  # 1.5 N·m
    lvl.set_voltage(lvl.max_voltage)  # give it everything
    for _ in range(int(3.0 / DT)):
        lvl.step()
    assert lvl.state.stalled
    assert not lvl.won
    assert lvl.last_diagnostic is not None
    assert lvl.last_diagnostic.kind == DiagKind.STALLED


def test_reduction_drives_and_wins() -> None:
    """N20/N40 reflects the load down enough to start, and hits the target."""
    lvl = LoadedGearLevel(driver_teeth=20, driven_teeth=40)
    lvl.set_load(lvl.target_load_torque)
    v = solve_driving_voltage_1_4(
        lvl.target_driven_rpm, lvl.driver, lvl.driven, lvl.target_load_torque
    )
    assert math.isfinite(v) and abs(v) <= lvl.max_voltage  # fits within the rail
    lvl.set_voltage(abs(v) * 1.01)
    for _ in range(int(12.0 / DT)):
        lvl.step()
    assert not lvl.state.stalled
    assert lvl.won
    assert math.isclose(abs(lvl.driven_rpm), lvl.target_driven_rpm, abs_tol=2.0)
    # External mesh reverses direction.
    assert lvl.driven_rpm < 0  # target_sign = -1


def test_no_load_no_stall_but_load_mismatch() -> None:
    """Slider at 0: no stall, but the load doesn't match the target job."""
    lvl = LoadedGearLevel(driver_teeth=20, driven_teeth=40)
    # load stays at 0 (default)
    v = solve_driving_voltage_1_4(lvl.target_driven_rpm, lvl.driver, lvl.driven, 0.0)
    lvl.set_voltage(abs(v) * 1.01)
    for _ in range(int(10.0 / DT)):
        lvl.step()
    assert not lvl.state.stalled
    assert not lvl.won
    # The load-mismatch diagnostic should fire (we're not driving the job).
    assert lvl.last_diagnostic is not None
    assert lvl.last_diagnostic.kind == DiagKind.LOAD_MISMATCH


def test_reflected_load_shrinks_with_reduction() -> None:
    """The core mechanic: a reduction reflects LESS load to the motor."""
    lvl = LoadedGearLevel()
    lvl.set_load(1.5)
    # 1:1 — full load seen by motor.
    assert math.isclose(lvl._reflected_load(), 1.5, abs_tol=1e-9)
    # N20/N40 (2:1) — load halved at the motor.
    lvl.set_gears(20, 40)
    assert math.isclose(lvl._reflected_load(), 0.75, abs_tol=1e-9)
    # N12/N48 (4:1) — quarter.
    lvl.set_gears(12, 48)
    assert math.isclose(lvl._reflected_load(), 0.375, abs_tol=1e-9)


def test_set_gears_updates_ratio_and_frame() -> None:
    lvl = LoadedGearLevel()
    assert lvl.reduction_ratio == 1.0
    lvl.set_gears(20, 60)
    assert lvl.reduction_ratio == 3.0
    assert lvl.frame_center_distance == 40.0  # 10 + 30
    assert lvl.meshed


def test_voltage_clamped() -> None:
    lvl = LoadedGearLevel()
    lvl.set_voltage(100.0)
    assert lvl.applied_voltage == lvl.max_voltage
    lvl.set_voltage(-100.0)
    assert lvl.applied_voltage == -lvl.max_voltage


def test_load_clamped_non_negative() -> None:
    lvl = LoadedGearLevel()
    lvl.set_load(-5.0)
    assert lvl.load_torque == 0.0


def test_solve_voltage_finite_and_higher_than_unloaded() -> None:
    """Driving a load needs more voltage than spinning free."""
    lvl = LoadedGearLevel(driver_teeth=20, driven_teeth=40)
    v_load = solve_driving_voltage_1_4(
        lvl.target_driven_rpm, lvl.driver, lvl.driven, lvl.target_load_torque
    )
    v_free = solve_driving_voltage_1_4(lvl.target_driven_rpm, lvl.driver, lvl.driven, 0.0)
    assert math.isfinite(v_load)
    assert abs(v_load) > abs(v_free)  # the load costs voltage


def test_summary_shape() -> None:
    lvl = LoadedGearLevel()
    s = lvl.summary()
    assert s["level"] == "1.4"
    for key in (
        "driver_rpm",
        "driven_rpm",
        "voltage",
        "load_torque",
        "target_load_torque",
        "reflected_load",
        "output_torque",
        "reduction_ratio",
        "stalled",
        "meshed",
        "won",
    ):
        assert key in s


def test_deeper_reduction_also_wins() -> None:
    """N12/N48 (4:1): even less reflected load, still hits the target."""
    lvl = LoadedGearLevel(driver_teeth=12, driven_teeth=48)
    lvl.set_load(lvl.target_load_torque)
    v = solve_driving_voltage_1_4(
        lvl.target_driven_rpm, lvl.driver, lvl.driven, lvl.target_load_torque
    )
    assert math.isfinite(v) and abs(v) <= lvl.max_voltage
    lvl.set_voltage(abs(v) * 1.01)
    for _ in range(int(12.0 / DT)):
        lvl.step()
    assert lvl.won
    assert not lvl.state.stalled


def test_no_back_drive_on_coastdown() -> None:
    """A stalled train cannot be reverse-driven by the load.

    Spin up, then cut voltage. The load + bearing drag decelerate the train
    to rest; once omega crosses zero the load must PIN it there (not kick it
    backward into a flickering limit cycle).
    """
    lvl = LoadedGearLevel(driver_teeth=20, driven_teeth=40)
    lvl.set_load(lvl.target_load_torque)
    lvl.set_voltage(24.0)
    for _ in range(int(3.0 / DT)):
        lvl.step()  # spin up
    assert lvl.driver_rpm > 0
    lvl.set_voltage(0.0)  # cut power — coast down under load
    omegas: list[float] = []
    for _ in range(int(4.0 / DT)):
        lvl.step()
        omegas.append(lvl.state.driver_omega)
    # No sign-flip oscillation (the old flicker bug).
    crossings = sum(1 for k in range(1, len(omegas)) if omegas[k - 1] * omegas[k] < 0)
    assert crossings == 0
    # And it ends pinned at rest, stalled.
    assert lvl.state.stalled
    assert abs(lvl.driver_rpm) < 1e-3


def test_output_torque_equals_load_when_running() -> None:
    """The load slider sets the resisting torque on the DRIVEN (output) shaft.

    So at steady state, output_torque == load_torque, independent of the ratio.
    """
    lvl = LoadedGearLevel(driver_teeth=20, driven_teeth=40)
    lvl.set_load(lvl.target_load_torque)
    v = solve_driving_voltage_1_4(
        lvl.target_driven_rpm, lvl.driver, lvl.driven, lvl.target_load_torque
    )
    lvl.set_voltage(abs(v) * 1.01)
    for _ in range(int(12.0 / DT)):
        lvl.step()
    assert not lvl.state.stalled
    # The motor fights the REFLECTED load (smaller under a reduction);
    # the OUTPUT torque equals the full load on the driven gear.
    assert math.isclose(lvl.motor_side_load, 0.75, abs_tol=1e-9)
    assert math.isclose(lvl.output_torque, lvl.target_load_torque, abs_tol=1e-9)
