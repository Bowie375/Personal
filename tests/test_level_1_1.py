"""Act 1.1 level tests: physics, win condition, diagnostic feedback."""

from __future__ import annotations

import math

from robot_forge.levels.diagnostics import DiagKind
from robot_forge.levels.level_1_1 import (
    DEFAULT_DAMPING,
    DT,
    ShaftLevel,
    solve_steady_state_torque,
)


def test_steady_state_matches_damping_times_omega() -> None:
    tau = solve_steady_state_torque()
    expected = DEFAULT_DAMPING * 60.0 * 2.0 * math.pi / 60.0
    assert math.isclose(tau, expected, rel_tol=1e-9)


def test_zero_torque_does_not_win() -> None:
    lvl = ShaftLevel()
    lvl.set_torque(0.0)
    for _ in range(int(5.0 / DT)):
        lvl.step()
    assert not lvl.won
    assert lvl.last_diagnostic is not None
    assert lvl.last_diagnostic.kind == DiagKind.TOO_SLOW


def test_correct_torque_wins() -> None:
    lvl = ShaftLevel()
    lvl.set_torque(solve_steady_state_torque() * 1.0001)  # tiny headroom
    for _ in range(int(15.0 / DT)):
        lvl.step()
    assert lvl.won
    assert lvl.last_diagnostic is None


def test_torque_clamped_to_limit() -> None:
    lvl = ShaftLevel()
    lvl.set_torque(100.0)
    assert lvl.applied_torque == lvl.torque_limit


def test_too_high_torque_overshoots_then_diagnoses_too_fast() -> None:
    lvl = ShaftLevel()
    lvl.set_torque(lvl.torque_limit)
    for _ in range(int(10.0 / DT)):
        lvl.step()
    # At max torque the shaft will overshoot target.
    assert not lvl.won
    assert lvl.last_diagnostic is not None
    # It will be flagged TOO_FAST at steady state.
    assert lvl.rpm > lvl.target_rpm + lvl.tolerance_rpm


def test_summary_includes_diagnostic() -> None:
    lvl = ShaftLevel()
    lvl.set_torque(0.0)
    for _ in range(int(2.0 / DT)):
        lvl.step()
    s = lvl.summary()
    assert s["level"] == "1.1"
    assert s["diagnostic"] is not None
    assert s["diagnostic"]["kind"] == DiagKind.TOO_SLOW.value
