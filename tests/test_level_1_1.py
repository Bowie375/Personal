"""Act 1.1 level tests: voltage-driven motor, tunable params, win condition.

1.1 is the motor primer: the player applies a voltage and directly tunes the
motor + mechanical parameters (Kt, Kb, R, I, b) to hit a fixed target RPM.
"""

from __future__ import annotations

import math

from robot_forge.levels.diagnostics import DiagKind
from robot_forge.levels.level_1_1 import (
    DEFAULT_DAMPING,
    DT,
    KB,
    KT,
    RESISTANCE,
    ShaftLevel,
    solve_steady_state_voltage,
)

# Steps to run a level well past steady state (~3*tau = 3s; use 15s).
STEPS = int(15.0 / DT)


def _run_to_steady(lvl: ShaftLevel, steps: int = STEPS) -> None:
    for _ in range(steps):
        lvl.step()
        if lvl.won:
            break


def test_zero_voltage_does_not_win() -> None:
    lvl = ShaftLevel()
    lvl.set_voltage(0.0)
    _run_to_steady(lvl)
    assert not lvl.won
    assert lvl.last_diagnostic is not None
    assert lvl.last_diagnostic.kind == DiagKind.TOO_SLOW


def test_correct_voltage_wins() -> None:
    lvl = ShaftLevel()
    v = solve_steady_state_voltage(lvl.target_rpm, lvl.kt, lvl.kb, lvl.resistance, lvl.damping)
    lvl.set_voltage(v * 1.02)  # small headroom so it settles above target, then lands
    _run_to_steady(lvl)
    assert lvl.won
    assert lvl.last_diagnostic is None


def test_voltage_clamped_to_limit() -> None:
    lvl = ShaftLevel()
    lvl.set_voltage(1000.0)
    assert lvl.applied_voltage == lvl.max_voltage
    lvl.set_voltage(-1000.0)
    assert lvl.applied_voltage == -lvl.max_voltage


def test_too_high_voltage_overshoots_then_diagnoses_too_fast() -> None:
    lvl = ShaftLevel()
    lvl.set_voltage(lvl.max_voltage)  # 24V >> steady-state ~6.6V
    _run_to_steady(lvl)
    assert not lvl.won
    assert lvl.last_diagnostic is not None
    assert lvl.rpm > lvl.target_rpm + lvl.tolerance_rpm


def test_summary_includes_voltage_and_params() -> None:
    lvl = ShaftLevel()
    lvl.set_voltage(0.0)
    lvl.step()
    s = lvl.summary()
    assert s["level"] == "1.1"
    assert "voltage" in s
    assert "kt" in s
    assert "kb" in s
    assert "resistance" in s
    assert "inertia" in s
    assert "damping" in s


def test_steady_state_voltage_formula() -> None:
    """V = omega * (R*b/Kt + Kb) at steady state."""
    omega = 60.0 * 2.0 * math.pi / 60.0
    expected = omega * (RESISTANCE * DEFAULT_DAMPING / KT + KB)
    assert math.isclose(solve_steady_state_voltage(), expected, rel_tol=1e-9)


def test_set_params_changes_steady_state_rpm() -> None:
    """Raising Kt → more torque per amp → higher steady-state RPM at same V."""
    lvl_low = ShaftLevel()
    lvl_low.set_voltage(6.0)
    _run_to_steady(lvl_low)
    rpm_low = lvl_low.rpm

    lvl_high = ShaftLevel()
    lvl_high.set_params(kt=KT * 2.0)  # double Kt
    lvl_high.set_voltage(6.0)
    _run_to_steady(lvl_high)
    rpm_high = lvl_high.rpm

    assert rpm_high > rpm_low


def test_inertia_does_not_change_steady_state_rpm() -> None:
    """The key lesson: I changes spin-up time, NOT steady-state RPM.

    Set the target far above any voltage the win-check would trigger on, so
    the sim keeps integrating to a true steady state (alpha ~ 0) instead of
    freezing when it crosses the (irrelevant) target band.
    """
    # Target way out of reach so won=True never freezes the sim.
    lvl_small_i = ShaftLevel(target_rpm=10000.0, inertia=0.01)
    v_test = 12.0  # arbitrary; steady state is the same regardless of I
    lvl_small_i.set_voltage(v_test)
    for _ in range(int(30.0 / DT)):
        lvl_small_i.step()

    lvl_big_i = ShaftLevel(target_rpm=10000.0, inertia=0.5)  # 50x inertia
    lvl_big_i.set_voltage(v_test)
    for _ in range(int(300.0 / DT)):  # big I needs long to settle
        lvl_big_i.step()

    # Both reach the same steady-state RPM (set by V, Kt, Kb, R, b — not I).
    assert math.isclose(abs(lvl_small_i.rpm), abs(lvl_big_i.rpm), rel_tol=0.02)


def test_damping_lowers_steady_state_rpm() -> None:
    """More bearing drag → lower terminal speed at the same voltage."""
    lvl_low_b = ShaftLevel(damping=DEFAULT_DAMPING)
    lvl_low_b.set_voltage(6.0)
    _run_to_steady(lvl_low_b)

    lvl_high_b = ShaftLevel(damping=DEFAULT_DAMPING * 4.0)
    lvl_high_b.set_voltage(6.0)
    _run_to_steady(lvl_high_b)

    assert lvl_high_b.rpm < lvl_low_b.rpm


def test_back_emf_limits_speed() -> None:
    """Higher Kb → motor self-limits at a lower RPM at the same voltage."""
    lvl_low_kb = ShaftLevel()
    lvl_low_kb.set_voltage(12.0)
    _run_to_steady(lvl_low_kb)

    lvl_high_kb = ShaftLevel()
    lvl_high_kb.set_params(kb=KB * 10.0)  # 10x back-EMF
    lvl_high_kb.set_voltage(12.0)
    _run_to_steady(lvl_high_kb)

    assert lvl_high_kb.rpm < lvl_low_kb.rpm


def test_diagnostic_hint_has_no_gear_vocabulary() -> None:
    """Regression guard: 1.1 must not leak gear words ('driven gear', 'teeth')."""
    lvl = ShaftLevel()
    lvl.set_voltage(lvl.max_voltage)
    lvl.step()
    assert lvl.last_diagnostic is not None
    assert "gear" not in lvl.last_diagnostic.hint.lower()
    assert "teeth" not in lvl.last_diagnostic.hint.lower()
