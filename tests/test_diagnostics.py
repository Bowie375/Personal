"""Diagnostic engine tests."""

from __future__ import annotations

from robot_forge.levels.diagnostics import (
    DiagKind,
    diagnose_direction,
    diagnose_ratio,
    diagnose_rpm,
    diagnose_rpm_shaft,
    settle_diagnostic,
    slip_diagnostic,
)


def test_rpm_within_tolerance_returns_none() -> None:
    assert diagnose_rpm(measured=100.0, target=100.0, tol=5.0) is None
    assert diagnose_rpm(measured=102.0, target=100.0, tol=5.0) is None


def test_rpm_too_slow() -> None:
    d = diagnose_rpm(measured=80.0, target=100.0, tol=5.0)
    assert d is not None
    assert d.kind == DiagKind.TOO_SLOW
    assert "80.0" in d.message


def test_rpm_too_fast() -> None:
    d = diagnose_rpm(measured=120.0, target=100.0, tol=5.0)
    assert d is not None
    assert d.kind == DiagKind.TOO_FAST


def test_ratio_diagnostic_suggests_correct_teeth() -> None:
    d = diagnose_ratio(
        measured_ratio=2.0,
        target_ratio=3.0,
        tol=0.05,
        driver_teeth=20,
        driven_teeth=40,
    )
    assert d is not None
    assert d.kind == DiagKind.WRONG_RATIO
    assert "60" in d.hint  # expected_teeth = round(3.0 * 20) = 60


def test_ratio_within_tolerance_returns_none() -> None:
    d = diagnose_ratio(
        measured_ratio=3.05,
        target_ratio=3.0,
        tol=0.05,
        driver_teeth=20,
        driven_teeth=60,
    )
    assert d is None


def test_direction_correct_returns_none() -> None:
    assert diagnose_direction(measured=10.0, expected_sign=1) is None
    assert diagnose_direction(measured=-10.0, expected_sign=-1) is None


def test_direction_wrong() -> None:
    d = diagnose_direction(measured=10.0, expected_sign=-1)
    assert d is not None
    assert d.kind == DiagKind.WRONG_DIRECTION


def test_settle_overshoot() -> None:
    d = settle_diagnostic(settle_error=1.0, tol=0.05)
    assert d is not None
    assert d.kind == DiagKind.OVERSHOOT
    assert "Kd" in d.hint


def test_settle_undershoot() -> None:
    d = settle_diagnostic(settle_error=0.1, tol=0.05)
    assert d is not None
    assert d.kind == DiagKind.UNDERSHOOT
    assert "Kp" in d.hint


def test_settle_within_tolerance() -> None:
    assert settle_diagnostic(settle_error=0.01, tol=0.05) is None


def test_slip_diagnostic() -> None:
    assert slip_diagnostic(slip_detected=False) is None
    d = slip_diagnostic(slip_detected=True)
    assert d is not None
    assert d.kind == DiagKind.SLIPPED


def test_shaft_hint_has_no_gear_vocabulary() -> None:
    """1.1 must not leak gear-level hints ('driven gear', 'teeth')."""
    d = diagnose_rpm_shaft(measured=120.0, target=60.0, tol=3.0)
    assert d is not None
    assert d.kind == DiagKind.TOO_FAST
    assert "gear" not in d.hint.lower()
    assert "teeth" not in d.hint.lower()
    assert "shaft" in d.message.lower()


def test_shaft_too_slow_hint() -> None:
    d = diagnose_rpm_shaft(measured=20.0, target=60.0, tol=3.0)
    assert d is not None
    assert d.kind == DiagKind.TOO_SLOW
    assert "torque" in d.hint.lower()
