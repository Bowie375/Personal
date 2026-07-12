"""Act 1.2 — Two gears: ratio, direction, win, diagnostic, motor curve."""

from __future__ import annotations

import math

from robot_forge.levels.diagnostics import DiagKind
from robot_forge.levels.level_1_2 import (
    DT,
    TwoGearLevel,
    solve_driving_voltage,
)


def test_default_pair_is_meshed() -> None:
    lvl = TwoGearLevel()  # default N30 + N30
    assert lvl.meshed
    assert lvl.frame_center_distance == 30.0  # 15 + 15


def test_any_pair_is_always_meshed() -> None:
    # All catalog gears share the same module, so the frame auto-sizes.
    for d in (12, 20, 30, 48, 60):
        for n in (12, 20, 30, 48, 60):
            lvl = TwoGearLevel(driver_teeth=d, driven_teeth=n)
            assert lvl.meshed, f"N{d} + N{n} should mesh"
            assert lvl.frame_center_distance == (d + n) * 0.5


def test_1_to_1_pair_wins_with_correct_voltage() -> None:
    lvl = TwoGearLevel()
    v = solve_driving_voltage(lvl.target_driven_rpm, lvl.driver, lvl.driven)
    lvl.set_voltage(abs(v) * 1.01)
    for _ in range(int(8.0 / DT)):
        lvl.step()
    assert lvl.won
    assert lvl.last_diagnostic is None
    # Driven should match target magnitude, opposite sign.
    assert math.isclose(abs(lvl.driven_rpm), lvl.target_driven_rpm, abs_tol=2.0)
    assert lvl.driven_rpm < 0  # target_sign=-1


def test_direction_is_opposite_for_external_mesh() -> None:
    lvl = TwoGearLevel()
    lvl.set_voltage(6.0)  # positive driver
    for _ in range(int(5.0 / DT)):
        lvl.step()
    assert lvl.driver_rpm > 0
    assert lvl.driven_rpm < 0  # mesh flips sign


def test_too_low_voltage_diagnoses_too_slow() -> None:
    lvl = TwoGearLevel()
    lvl.set_voltage(0.5)
    for _ in range(int(3.0 / DT)):
        lvl.step()
    assert not lvl.won
    assert lvl.last_diagnostic is not None
    assert lvl.last_diagnostic.kind in (DiagKind.TOO_SLOW, DiagKind.WRONG_DIRECTION)


def test_wrong_direction_diagnoses_direction() -> None:
    # With target_sign=+1, the player must apply negative voltage.
    # Positive voltage spins driver +, which makes driven -. Wrong direction.
    # Use a low voltage so the speed is in-tolerance (sign-only failure).
    lvl = TwoGearLevel(target_sign=1)
    lvl.set_voltage(0.1)  # tiny positive V: driver barely moves, driven barely moves (wrong sign)
    for _ in range(int(3.0 / DT)):
        lvl.step()
    assert not lvl.won
    assert lvl.last_diagnostic is not None
    # Either speed or direction diagnostic is acceptable; the level surfaces
    # the speed one first if both fail. Use a higher V to get clean direction failure.
    lvl.set_voltage(6.0)
    for _ in range(int(8.0 / DT)):
        lvl.step()
    # At V=6 the 1:1 ratio gives ~54 RPM driven, just under target 60.
    # So speed diagnostic will still fire. Force a win-shape by changing
    # target magnitude to 50 (so 54 is within tol) and keep sign +1.
    lvl2 = TwoGearLevel(target_sign=1, target_driven_rpm=50.0, tolerance_rpm=10.0)
    lvl2.set_voltage(6.0)
    for _ in range(int(8.0 / DT)):
        lvl2.step()
    assert not lvl2.won  # wrong direction
    assert lvl2.last_diagnostic is not None
    assert lvl2.last_diagnostic.kind == DiagKind.WRONG_DIRECTION


def test_voltage_clamped_to_max() -> None:
    lvl = TwoGearLevel()
    lvl.set_voltage(100.0)
    assert lvl.applied_voltage == lvl.max_voltage
    lvl.set_voltage(-100.0)
    assert lvl.applied_voltage == -lvl.max_voltage


def test_set_gears_resets_pair_and_recomputes_frame() -> None:
    lvl = TwoGearLevel()
    assert lvl.frame_center_distance == 30.0  # 1:1 default
    lvl.set_gears(driver_teeth=20, driven_teeth=60)
    assert lvl.driver.teeth == 20
    assert lvl.driven.teeth == 60
    # Frame auto-sizes to the new pair's pitch radii sum.
    assert lvl.frame_center_distance == 40.0  # 10 + 30
    assert lvl.meshed


def test_summary_includes_state() -> None:
    lvl = TwoGearLevel()
    s = lvl.summary()
    assert s["level"] == "1.2"
    assert "driver_rpm" in s
    assert "driven_rpm" in s
    assert "voltage" in s
    assert "meshed" in s


def test_solve_voltage_is_finite() -> None:
    lvl = TwoGearLevel()
    v = solve_driving_voltage(lvl.target_driven_rpm, lvl.driver, lvl.driven)
    assert math.isfinite(v)


def test_3_to_1_pair_wins_with_lower_voltage() -> None:
    # N20 + N60: ratio 3:1, so driven is 1/3 of driver. To get 60 RPM
    # driven, the driver needs 180 RPM — higher voltage than the 1:1 case.
    lvl = TwoGearLevel(
        driver_teeth=20,
        driven_teeth=60,
    )
    assert lvl.meshed
    v = solve_driving_voltage(lvl.target_driven_rpm, lvl.driver, lvl.driven)
    assert math.isfinite(v) and abs(v) > 6.0  # needs more V than 1:1
    lvl.set_voltage(abs(v) * 1.01)
    for _ in range(int(10.0 / DT)):
        lvl.step()
    assert lvl.won
    assert math.isclose(abs(lvl.driven_rpm), lvl.target_driven_rpm, abs_tol=2.0)


def test_summary_includes_center_distance() -> None:
    lvl = TwoGearLevel()
    s = lvl.summary()
    assert "center_distance" in s
    assert s["center_distance"] == 30.0
