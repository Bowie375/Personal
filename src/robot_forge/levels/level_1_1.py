"""Act 1.1 — Spinning shaft (motor primer).

A single rigid shaft on bearings, driven by a DC motor. The player applies
a voltage and — uniquely in this level — directly tunes the motor and
mechanical parameters (Kt, Kb, R, I, b) to see how each shapes the final
RPM. Later levels abstract this V→RPM mapping away; 1.1 makes it visible
so the player builds the mental model first.

Mechanics (sim units, m-kg-s):
- Motor model: tau = Kt * (V - Kb*omega) / R, clamped to torque_limit.
- Shaft dynamics: alpha = (tau - b*omega) / I.
- Steady state (alpha=0): omega = (V*Kt/R) / (b + Kt*Kb/R).

The teaching insight: V, Kt, Kb, R, b all change WHERE the shaft settles;
inertia I only changes HOW FAST it gets there (not the steady-state RPM).
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from robot_forge.levels.diagnostics import Diagnostic, diagnose_rpm_shaft

# Motor constants — small DC motor, SI-ish units. Tunable by the player.
KT = 0.05  # N*m/A  (torque constant)
KB = 0.05  # V*s/rad (back-EMF constant)
RESISTANCE = 1.0  # ohm
TORQUE_LIMIT = 2.0  # N*m
MAX_VOLTAGE = 24.0  # V

# Mechanical defaults.
DEFAULT_INERTIA = 0.05  # kg*m^2 — small rotor
DEFAULT_DAMPING = 0.05  # N*m*s/rad — bearing drag
# Time constant tau = I/b = 1.0 s, so steady state in ~3*tau = 3s.

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
    """The level: apply voltage, tune params, hit target RPM."""

    def __init__(
        self,
        target_rpm: float = TARGET_RPM,
        tolerance_rpm: float = RPM_TOLERANCE,
        settle_time_s: float = SETTLE_TIME_S,
        inertia: float = DEFAULT_INERTIA,
        damping: float = DEFAULT_DAMPING,
        torque_limit: float = TORQUE_LIMIT,
        kt: float = KT,
        kb: float = KB,
        resistance: float = RESISTANCE,
        max_voltage: float = MAX_VOLTAGE,
    ) -> None:
        self.target_rpm = target_rpm
        self.tolerance_rpm = tolerance_rpm
        self.settle_time_s = settle_time_s
        self.inertia = inertia
        self.damping = damping
        self.torque_limit = torque_limit
        self.kt = kt
        self.kb = kb
        self.resistance = resistance
        self.max_voltage = max_voltage
        self.state = ShaftState()
        self.applied_voltage: float = 0.0
        self.applied_torque: float = 0.0  # computed each step; surfaced for HUD
        self.won: bool = False
        self.last_diagnostic: Diagnostic | None = None

    @property
    def rpm(self) -> float:
        return self.state.omega_rad_s * 60.0 / (2.0 * math.pi)

    def set_voltage(self, voltage: float) -> None:
        """Player action: set motor voltage (clamped to ±max)."""
        self.applied_voltage = max(-self.max_voltage, min(self.max_voltage, voltage))

    def set_params(
        self,
        kt: float | None = None,
        kb: float | None = None,
        resistance: float | None = None,
        inertia: float | None = None,
        damping: float | None = None,
    ) -> None:
        """Player action: tune motor + mechanical parameters. Only the
        provided (non-None) fields are updated — the HUD sends the full set
        each time, but partial updates are supported for safety."""
        if kt is not None:
            self.kt = kt
        if kb is not None:
            self.kb = kb
        if resistance is not None:
            self.resistance = resistance
        if inertia is not None:
            self.inertia = inertia
        if damping is not None:
            self.damping = damping

    def _motor_torque(self, omega: float) -> float:
        if self.kt <= 0.0 or self.resistance <= 0.0:
            return 0.0
        i = (self.applied_voltage - self.kb * omega) / self.resistance
        tau = self.kt * i
        return max(-self.torque_limit, min(self.torque_limit, tau))

    def step(self, dt: float = DT) -> None:
        """Euler integration; fine at this timestep for first-order rotational."""
        if self.won:
            return
        s = self.state
        tau = self._motor_torque(s.omega_rad_s)
        self.applied_torque = tau  # surface for HUD
        # alpha = (tau - b*omega) / I
        alpha = (tau - self.damping * s.omega_rad_s) / self.inertia
        s.omega_rad_s += alpha * dt
        s.angle_rad += s.omega_rad_s * dt
        s.t += dt
        self._check_win()

    def _check_win(self) -> None:
        d = diagnose_rpm_shaft(self.rpm, self.target_rpm, self.tolerance_rpm)
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
            "voltage": self.applied_voltage,
            "torque": self.applied_torque,
            "kt": self.kt,
            "kb": self.kb,
            "resistance": self.resistance,
            "inertia": self.inertia,
            "damping": self.damping,
            "won": self.won,
            "diagnostic": self.last_diagnostic.to_dict() if self.last_diagnostic else None,
        }


def solve_steady_state_voltage(
    target_rpm: float = TARGET_RPM,
    kt: float = KT,
    kb: float = KB,
    resistance: float = RESISTANCE,
    damping: float = DEFAULT_DAMPING,
) -> float:
    """Voltage that holds target_rpm at steady state.

    At steady state alpha=0, so motor_torque = b*omega.
        kt*(V - kb*omega)/R = b*omega
        V = R*b*omega/kt + kb*omega
          = omega * (R*b/kt + kb)
    """
    if kt <= 0.0:
        return float("inf")
    omega = target_rpm * 2.0 * math.pi / 60.0
    return omega * (resistance * damping / kt + kb)


def solve_steady_state_torque(
    target_rpm: float = TARGET_RPM,
    damping: float = DEFAULT_DAMPING,
) -> float:
    """At steady state, motor_torque = b*omega. Kept for HUD readouts and
    backward compatibility (some tests/hints reference the required torque)."""
    omega = target_rpm * 2.0 * math.pi / 60.0
    return damping * omega


def find_min_torque_for_rpm(
    target_rpm: float,
    damping: float = DEFAULT_DAMPING,
    torque_limit: float = TORQUE_LIMIT,
    settle_time_s: float = SETTLE_TIME_S,
    inertia: float = DEFAULT_INERTIA,
) -> float:
    """Smallest torque that holds target RPM at steady state."""
    omega = target_rpm * 2.0 * math.pi / 60.0
    steady = damping * omega
    if steady > torque_limit:
        return float("inf")
    return steady


if __name__ == "__main__":
    v = solve_steady_state_voltage()
    print(f"steady-state voltage for {TARGET_RPM} RPM: {v:.4f} V")
    lvl = ShaftLevel()
    lvl.set_voltage(v * 1.01)
    for _ in range(int(8.0 / DT)):
        lvl.step()
    print(
        f"after 8s: rpm={lvl.rpm:.2f}, won={lvl.won}, diag={lvl.last_diagnostic}, "
        f"tau={lvl.applied_torque:.4f}"
    )
