"""Act 1.1 — Spinning shaft.

A single rigid shaft on bearings, with an applied torque. The player adjusts the
torque magnitude (and observes inertia + damping) until the shaft reaches a
target RPM.

This module is a headless physics-state simulator — it's structured to match
what the real PyBullet sim will provide, so the level logic and diagnostics are
testable without a graphics client. PyBullet integration will replace
`step()` in a follow-up.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from robot_forge.levels.diagnostics import Diagnostic, diagnose_rpm

# Real-world defaults (sim units, m-kg-s):
# Time constant tau = I/b. Pick so the player sees a clear spin-up but reaches
# steady state in a few seconds.
DEFAULT_INERTIA = 0.05  # kg*m^2 — small rotor
DEFAULT_DAMPING = 0.05  # N*m*s/rad — bearing drag
# Time constant = 1.0 s, so steady state in ~3*tau = 3s.
DEFAULT_TORQUE_LIMIT = 2.0  # N*m — max torque the motor can deliver

TARGET_RPM = 60.0
RPM_TOLERANCE = 3.0  # ±3 RPM
SETTLE_TIME_S = 1.0  # must hold target RPM for this long
DT = 0.01  # sim timestep (s)


@dataclass
class ShaftState:
    angle_rad: float = 0.0
    omega_rad_s: float = 0.0
    t: float = 0.0
    settled_time: float = 0.0


class ShaftLevel:
    """The level itself: state, step function, win-check, and diagnostic."""

    def __init__(
        self,
        inertia: float = DEFAULT_INERTIA,
        damping: float = DEFAULT_DAMPING,
        target_rpm: float = TARGET_RPM,
        tolerance_rpm: float = RPM_TOLERANCE,
        settle_time_s: float = SETTLE_TIME_S,
        torque_limit: float = DEFAULT_TORQUE_LIMIT,
    ) -> None:
        self.inertia = inertia
        self.damping = damping
        self.target_rpm = target_rpm
        self.tolerance_rpm = tolerance_rpm
        self.settle_time_s = settle_time_s
        self.torque_limit = torque_limit
        self.state = ShaftState()
        self.applied_torque: float = 0.0
        self.won: bool = False
        self.last_diagnostic: Diagnostic | None = None

    @property
    def rpm(self) -> float:
        return self.state.omega_rad_s * 60.0 / (2.0 * math.pi)

    def set_torque(self, torque: float) -> None:
        """Player action: set the applied torque (clamped to motor limit)."""
        self.applied_torque = max(-self.torque_limit, min(self.torque_limit, torque))

    def step(self, dt: float = DT) -> None:
        """Advance the physics by `dt` seconds. Euler integration is fine
        at this timestep for a first-order rotational system.
        """
        if self.won:
            return
        s = self.state
        # alpha = (tau - b*omega) / I
        alpha = (self.applied_torque - self.damping * s.omega_rad_s) / self.inertia
        s.omega_rad_s += alpha * dt
        s.angle_rad += s.omega_rad_s * dt
        s.t += dt
        self._check_win()

    def _check_win(self) -> None:
        d = diagnose_rpm(self.rpm, self.target_rpm, self.tolerance_rpm)
        if d is None:
            self.state.settled_time += DT
            if self.state.settled_time >= self.settle_time_s:
                self.won = True
                self.last_diagnostic = None
        else:
            self.state.settled_time = 0.0
            self.last_diagnostic = d

    def summary(self) -> dict:
        """Snapshot for the bridge / UI."""
        return {
            "level": "1.1",
            "t": self.state.t,
            "rpm": self.rpm,
            "target_rpm": self.target_rpm,
            "torque": self.applied_torque,
            "won": self.won,
            "diagnostic": self.last_diagnostic.to_dict() if self.last_diagnostic else None,
        }


def solve_steady_state_torque(
    target_rpm: float = TARGET_RPM,
    damping: float = DEFAULT_DAMPING,
) -> float:
    """At steady state, alpha = 0, so tau = b*omega. Useful as a hint
    (but not the answer — the player still has to learn inertia/damping)."""
    omega = target_rpm * 2.0 * math.pi / 60.0
    return damping * omega


def find_min_torque_for_rpm(
    target_rpm: float,
    damping: float = DEFAULT_DAMPING,
    torque_limit: float = DEFAULT_TORQUE_LIMIT,
    settle_time_s: float = SETTLE_TIME_S,
    inertia: float = DEFAULT_INERTIA,
) -> float:
    """At steady state, the smallest torque that holds target RPM.
    Must also reach the target within settle_time_s. Search by binary bisection.
    """
    omega = target_rpm * 2.0 * math.pi / 60.0
    steady = damping * omega
    if steady > torque_limit:
        return float("inf")
    return steady


if __name__ == "__main__":
    print(f"steady-state torque for {TARGET_RPM} RPM: {solve_steady_state_torque():.4f} N*m")
    lvl = ShaftLevel()
    lvl.set_torque(0.01)
    for _ in range(int(2.0 / DT)):
        lvl.step()
    print(f"after 2s: rpm={lvl.rpm:.2f}, won={lvl.won}, diag={lvl.last_diagnostic}")
