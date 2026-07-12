"""Diagnostic engine: turn a failed attempt into a teaching message.

Each diagnostic is a small structured record with a category, a short human message,
and (optionally) a hint. Levels call `diagnose(...)` and surface the result to the UI.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class DiagKind(str, Enum):  # noqa: UP042  — kept for Py<3.11 readers if needed
    TOO_SLOW = "too_slow"
    TOO_FAST = "too_fast"
    WRONG_DIRECTION = "wrong_direction"
    UNDERSHOOT = "undershoot"
    OVERSHOOT = "overshoot"
    SETTLE_FAILED = "settle_failed"
    WRONG_RATIO = "wrong_ratio"
    SLIPPED = "slipped"
    TIMEOUT = "timeout"
    INSTRUCTION = "instruction"


@dataclass(frozen=True)
class Diagnostic:
    kind: DiagKind
    message: str
    hint: str = ""

    def to_dict(self) -> dict:
        return {"kind": self.kind.value, "message": self.message, "hint": self.hint}


def diagnose_rpm(measured: float, target: float, tol: float) -> Diagnostic | None:
    """Return a diagnostic if measured RPM is outside tolerance of target."""
    err = measured - target
    if abs(err) <= tol:
        return None
    if err < 0:
        return Diagnostic(
            kind=DiagKind.TOO_SLOW,
            message=f"Measured {measured:.1f} RPM, target {target:.1f} RPM ({err:+.1f}).",
            hint="Increase motor torque or check for excessive load on the shaft.",
        )
    return Diagnostic(
        kind=DiagKind.TOO_FAST,
        message=f"Measured {measured:.1f} RPM, target {target:.1f} RPM ({err:+.1f}).",
        hint="Reduce motor torque, or add a larger driven gear to step the speed down.",
    )


def diagnose_ratio(
    measured_ratio: float,
    target_ratio: float,
    tol: float,
    driver_teeth: int,
    driven_teeth: int,
) -> Diagnostic | None:
    err = measured_ratio - target_ratio
    if abs(err) <= tol * abs(target_ratio):
        return None
    expected_teeth = round(target_ratio * driver_teeth)
    return Diagnostic(
        kind=DiagKind.WRONG_RATIO,
        message=(
            f"Your ratio is {measured_ratio:.2f}:1 "
            f"(N{driver_teeth} -> N{driven_teeth}). Target is {target_ratio:.2f}:1."
        ),
        hint=(
            f"For {target_ratio:.2f}:1 with a {driver_teeth}-tooth driver, "
            f"you need roughly a {expected_teeth}-tooth driven gear "
            f"(ratio = N_driven / N_driver)."
        ),
    )


def diagnose_direction(measured: float, expected_sign: int) -> Diagnostic | None:
    """Expected sign is +1 or -1. If measured sign disagrees, return a diagnostic."""
    if measured == 0:
        return None
    measured_sign = 1 if measured > 0 else -1
    if measured_sign == expected_sign:
        return None
    return Diagnostic(
        kind=DiagKind.WRONG_DIRECTION,
        message="Output shaft spins the wrong way.",
        hint=(
            "Two meshing gears reverse direction. Add an idler (3-gear chain) to "
            "flip it back, or swap driver and driven."
        ),
    )


def settle_diagnostic(settle_error: float, tol: float) -> Diagnostic | None:
    if settle_error <= tol:
        return None
    if settle_error > 0.5:
        return Diagnostic(
            kind=DiagKind.OVERSHOOT,
            message=f"Final position is {settle_error:.2f} rad from setpoint.",
            hint="Your controller is oscillating. Increase Kd (derivative gain).",
        )
    return Diagnostic(
        kind=DiagKind.UNDERSHOOT,
        message=f"Final position is {settle_error:.2f} rad from setpoint.",
        hint="Increase Kp (proportional gain) to drive harder to the setpoint.",
    )


def slip_diagnostic(slip_detected: bool) -> Diagnostic | None:
    if not slip_detected:
        return None
    return Diagnostic(
        kind=DiagKind.SLIPPED,
        message="The gripper slipped on the object.",
        hint="Slow the approach or use a softer grip. Lower acceleration = less inertial pull.",
    )
