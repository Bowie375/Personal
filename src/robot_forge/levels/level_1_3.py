"""Act 1.3 — Idler gear.

A motor drives a driver gear, which meshes with an idler gear, which meshes
with a driven gear. The player picks all three gear tooth counts and applies
a motor voltage, and must reach a target RPM on the driven gear in the SAME
direction as the driver (target_sign = +1).

Mechanics (sim units, m-kg-s):
- Three external meshes in series: driver → idler → driven.
- Each mesh flips direction: omega_idler = -omega_driver * N_driver / N_idler,
  then omega_driven = -omega_idler * N_idler / N_driven.
  The idler's tooth count cancels: omega_driven = +omega_driver * N_driver / N_driven.
- Motor torque applied only to the driver. Idler and driven are kinematically
  constrained (no active torque).
- Frame spans the three pitch radii: center_distance = r_driver + 2*r_idler + r_driven.
- All catalog gears share the same module, so any triple meshes.
- Target sign: +1 (same direction as driver) — the idler flips direction twice.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from robot_forge.levels.diagnostics import DiagKind, Diagnostic
from robot_forge.sim.gears import SpurGear, gear_ratio

KT = 0.05  # N*m/A
KB = 0.05  # V*s/rad
RESISTANCE = 1.0  # ohm
TORQUE_LIMIT = 2.0  # N*m
MAX_VOLTAGE = 24.0  # V

# Default targets — all 1:1 (N30 base) so the player can learn the idler's
# role: it reverses direction (back to driver's sign) but doesn't change speed.
DEFAULT_TARGET_DRIVEN_RPM = 60.0
DEFAULT_DRIVER_TEETH = 30
DEFAULT_IDLER_TEETH = 30
DEFAULT_DRIVEN_TEETH = 30
DEFAULT_INERTIA_PER_GEAR = 0.01
DEFAULT_DAMPING = 0.05
RPM_TOLERANCE = 1.0
SETTLE_TIME_S = 1.0
DT = 0.01

# With an idler, driven spins the SAME direction as driver (two external
# meshes → sign +1).
DEFAULT_TARGET_SIGN = 1


@dataclass
class ThreeGearState:
    driver_omega: float = 0.0
    driver_angle: float = 0.0
    idler_omega: float = 0.0
    idler_angle: float = 0.0
    driven_omega: float = 0.0
    driven_angle: float = 0.0
    t: float = 0.0
    settled_time: float = 0.0


class ThreeGearLevel:
    """The level. Pick three gears, set voltage, hit the target on the driven gear."""

    def __init__(
        self,
        driver_teeth: int = DEFAULT_DRIVER_TEETH,
        idler_teeth: int = DEFAULT_IDLER_TEETH,
        driven_teeth: int = DEFAULT_DRIVEN_TEETH,
        target_driven_rpm: float = DEFAULT_TARGET_DRIVEN_RPM,
        target_sign: int = DEFAULT_TARGET_SIGN,
        inertia: float = DEFAULT_INERTIA_PER_GEAR,
        damping: float = DEFAULT_DAMPING,
        tolerance_rpm: float = RPM_TOLERANCE,
        settle_time_s: float = SETTLE_TIME_S,
        torque_limit: float = TORQUE_LIMIT,
        kt: float = KT,
        kb: float = KB,
        resistance: float = RESISTANCE,
        max_voltage: float = MAX_VOLTAGE,
    ) -> None:
        self.driver = SpurGear(driver_teeth)
        self.idler = SpurGear(idler_teeth)
        self.driven = SpurGear(driven_teeth)
        self.target_driven_rpm = target_driven_rpm
        self.target_sign = target_sign
        # Frame spans the entire chain: r_driver + 2*r_idler + r_driven.
        # (Idler meshes with both driver and driven.)
        self.frame_span = (
            self.driver.pitch_radius + 2.0 * self.idler.pitch_radius + self.driven.pitch_radius
        )
        self.inertia = inertia
        self.damping = damping
        self.tolerance_rpm = tolerance_rpm
        self.settle_time_s = settle_time_s
        self.torque_limit = torque_limit
        self.kt = kt
        self.kb = kb
        self.resistance = resistance
        self.max_voltage = max_voltage
        self.state = ThreeGearState()
        self.applied_voltage: float = 0.0
        self.won: bool = False
        self.last_diagnostic: Diagnostic | None = None

    @property
    def driver_rpm(self) -> float:
        return self.state.driver_omega * 60.0 / (2.0 * math.pi)

    @property
    def idler_rpm(self) -> float:
        return self.state.idler_omega * 60.0 / (2.0 * math.pi)

    @property
    def driven_rpm(self) -> float:
        return self.state.driven_omega * 60.0 / (2.0 * math.pi)

    @property
    def meshed(self) -> bool:
        """Always true: all catalog gears share the same module."""
        return True

    @property
    def expected_driven_rpm(self) -> float:
        """Speed ratio is N_driver / N_driven; idler cancels out."""
        return gear_ratio(self.driver, self.driven)

    def set_voltage(self, voltage: float) -> None:
        self.applied_voltage = max(-self.max_voltage, min(self.max_voltage, voltage))

    def set_gears(self, driver_teeth: int, idler_teeth: int, driven_teeth: int) -> None:
        self.driver = SpurGear(driver_teeth)
        self.idler = SpurGear(idler_teeth)
        self.driven = SpurGear(driven_teeth)
        self.frame_span = (
            self.driver.pitch_radius + 2.0 * self.idler.pitch_radius + self.driven.pitch_radius
        )

    def _motor_torque(self, omega_driver: float) -> float:
        v = self.applied_voltage
        i = (v - self.kb * omega_driver) / self.resistance
        tau = self.kt * i
        return max(-self.torque_limit, min(self.torque_limit, tau))

    def step(self, dt: float = DT) -> None:
        if self.won:
            return
        s = self.state
        tau = self._motor_torque(s.driver_omega)
        # Driver: I*alpha = tau - b*omega_driver
        s.driver_omega += (tau - self.damping * s.driver_omega) / self.inertia * dt
        s.driver_angle += s.driver_omega * dt
        # Kinematic constraints: two external meshes.
        # omega_idler = -omega_driver * (N_driver / N_idler)
        s.idler_omega = -s.driver_omega * (self.driver.teeth / self.idler.teeth)
        s.idler_angle += s.idler_omega * dt
        # omega_driven = -omega_idler * (N_idler / N_driven)
        #             = +omega_driver * (N_driver / N_driven)
        s.driven_omega = -s.idler_omega * (self.idler.teeth / self.driven.teeth)
        s.driven_angle += s.driven_omega * dt
        s.t += dt
        self._check_win()

    def _check_win(self) -> None:
        # target_driven_rpm is a magnitude; target_sign is the required sign.
        target_omega = self.target_driven_rpm * 2.0 * math.pi / 60.0
        measured = self.state.driven_omega
        # Speed check: |measured| should be within tol of |target|.
        speed_err = abs(measured) - abs(target_omega)
        speed_diag: Diagnostic | None = None
        if abs(speed_err) * 60.0 / (2.0 * math.pi) > self.tolerance_rpm:
            speed_diag = Diagnostic(
                kind=DiagKind.TOO_SLOW if speed_err < 0 else DiagKind.TOO_FAST,
                message=(
                    f"Driven gear: {abs(measured) * 60.0 / (2.0 * math.pi):.1f} RPM, "
                    f"target {self.target_driven_rpm:.1f} RPM (magnitude)."
                ),
                hint=(
                    "Increase motor voltage to speed up, decrease to slow down. "
                    "If the wrong direction, flip the voltage polarity."
                ),
            )
        # Direction check.
        dir_diag: Diagnostic | None = None
        if measured != 0 and (1 if measured > 0 else -1) != self.target_sign:
            dir_diag = Diagnostic(
                kind=DiagKind.WRONG_DIRECTION,
                message=(
                    f"Driven gear is spinning {'clockwise' if measured < 0 else 'counter-clockwise'}, "
                    f"but target is {'clockwise' if self.target_sign < 0 else 'counter-clockwise'}."
                ),
                hint=(
                    "An idler gear flips direction once more — the driven gear ends up "
                    "spinning the same direction as the driver. Pick any idler tooth count; "
                    "the idler's only job is to reverse the output direction."
                ),
            )
        if speed_diag is None and dir_diag is None:
            self.state.settled_time += DT
            if self.state.settled_time >= self.settle_time_s:
                self.won = True
                self.last_diagnostic = None
        else:
            self.state.settled_time = 0.0
            self.last_diagnostic = speed_diag if speed_diag is not None else dir_diag

    def summary(self) -> dict:
        return {
            "level": "1.3",
            "t": self.state.t,
            "driver_rpm": self.driver_rpm,
            "idler_rpm": self.idler_rpm,
            "driven_rpm": self.driven_rpm,
            "target_driven_rpm": self.target_driven_rpm,
            "target_sign": self.target_sign,
            "voltage": self.applied_voltage,
            "meshed": self.meshed,
            "won": self.won,
            "driver_teeth": self.driver.teeth,
            "idler_teeth": self.idler.teeth,
            "driven_teeth": self.driven.teeth,
            "diagnostic": self.last_diagnostic.to_dict() if self.last_diagnostic else None,
        }


def solve_driving_voltage_1_3(
    target_driven_rpm: float,
    driver: SpurGear,
    driven: SpurGear,
    damping: float = DEFAULT_DAMPING,
    kt: float = KT,
    kb: float = KB,
    resistance: float = RESISTANCE,
) -> float:
    """Voltage needed to hold the driven gear at target_driven_rpm steady-state.

    The idler doesn't appear in the calculation: the speed ratio is just
    N_driver / N_driven, independent of N_idler. (Same as 1.2 two-gear formula.)
    """
    if not (kt > 0):
        return float("inf")
    omega_driven = target_driven_rpm * 2.0 * math.pi / 60.0
    omega_driver = omega_driven * (driven.teeth / driver.teeth)
    tau = damping * omega_driver
    v = resistance * tau / kt + kb * omega_driver
    return v


if __name__ == "__main__":
    lvl = ThreeGearLevel()
    v = solve_driving_voltage_1_3(lvl.target_driven_rpm, lvl.driver, lvl.driven)
    lvl.set_voltage(abs(v) * 1.01)
    for _ in range(int(8.0 / DT)):
        lvl.step()
    print(
        f"target: {lvl.target_driven_rpm:.1f} RPM, sign {lvl.target_sign}; "
        f"V={lvl.applied_voltage:.2f}V, "
        f"driver={lvl.driver_rpm:.1f} RPM, idler={lvl.idler_rpm:.1f} RPM, "
        f"driven={lvl.driven_rpm:.2f} RPM, "
        f"won={lvl.won}, diag={lvl.last_diagnostic}"
    )
