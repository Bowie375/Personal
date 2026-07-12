"""Act 1.2 — Two gears.

A motor drives a "driver" gear; a second "driven" gear meshes with it. The
player picks both gears from the catalog and applies a motor voltage, and
must reach a target RPM on the driven gear — in a specific direction.

Mechanics (sim units, m-kg-s):
- Driver and driven gears share a fixed center distance (frame is pre-built).
- Compatible gear pair: their center_distance == frame_center_distance (tol).
- Motor model: tau_motor = Kt * (V - Kb*omega) / R, clamped to torque_limit.
- Gear constraint: omega_driven = -omega_driver * (N_driver / N_driven)
  when meshed; otherwise driven is free (just bearing drag).
- Bearings: each shaft has damping b on its own omega.
- Target sign: +1 means "same direction as driver", -1 means "opposite".
  For an external mesh, sign is always -1, so target_sign = -1 always wins
  with the right pair. We allow the level to specify it explicitly so 1.3
  (idler) and beyond can re-use the same engine.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from robot_forge.levels.diagnostics import DiagKind, Diagnostic
from robot_forge.sim.gears import SpurGear, center_distance, gear_ratio

# Physical constants for the motor — small DC motor, Kt and Kb in SI-ish units.
KT = 0.05  # N*m/A
KB = 0.05  # V*s/rad
RESISTANCE = 1.0  # ohm
TORQUE_LIMIT = 2.0  # N*m
MAX_VOLTAGE = 24.0  # V

# Default targets — override via constructor.
# Default pair is 1:1 (N30 + N30) so the player can see that one meshing
# reverses direction without changing speed. They'll swap to different
# ratios to see how the driven speed responds.
DEFAULT_TARGET_DRIVEN_RPM = 60.0
DEFAULT_DRIVER_TEETH = 30
DEFAULT_DRIVEN_TEETH = 30
DEFAULT_FRAME_CENTER_DISTANCE = 30.0  # pitch radii 15 + 15 = 30
DEFAULT_INERTIA_PER_GEAR = 0.01
DEFAULT_DAMPING = 0.05
RPM_TOLERANCE = 1.0
SETTLE_TIME_S = 1.0
DT = 0.01

# Direction expected at the driven gear, expressed as the sign of its omega.
# For an external mesh driven by positive voltage on the driver, the driven
# gear spins in the opposite direction. With our convention that positive
# voltage → positive driver_omega → negative driven_omega, the natural
# target sign is -1.
DEFAULT_TARGET_SIGN = -1


@dataclass
class TwoGearState:
    driver_omega: float = 0.0
    driver_angle: float = 0.0
    driven_omega: float = 0.0
    driven_angle: float = 0.0
    t: float = 0.0
    settled_time: float = 0.0


class TwoGearLevel:
    """The level. Pick gears, set voltage, hit the target on the driven gear."""

    def __init__(
        self,
        driver_teeth: int = DEFAULT_DRIVER_TEETH,
        driven_teeth: int = DEFAULT_DRIVEN_TEETH,
        target_driven_rpm: float = DEFAULT_TARGET_DRIVEN_RPM,
        target_sign: int = DEFAULT_TARGET_SIGN,
        frame_center_distance: float = DEFAULT_FRAME_CENTER_DISTANCE,
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
        self.driven = SpurGear(driven_teeth)
        self.target_driven_rpm = target_driven_rpm
        self.target_sign = target_sign
        self.frame_center_distance = frame_center_distance
        self.inertia = inertia
        self.damping = damping
        self.tolerance_rpm = tolerance_rpm
        self.settle_time_s = settle_time_s
        self.torque_limit = torque_limit
        self.kt = kt
        self.kb = kb
        self.resistance = resistance
        self.max_voltage = max_voltage
        self.state = TwoGearState()
        self.applied_voltage: float = 0.0
        self.won: bool = False
        self.last_diagnostic: Diagnostic | None = None

    @property
    def driver_rpm(self) -> float:
        return self.state.driver_omega * 60.0 / (2.0 * math.pi)

    @property
    def driven_rpm(self) -> float:
        return self.state.driven_omega * 60.0 / (2.0 * math.pi)

    @property
    def meshed(self) -> bool:
        """True if the chosen gears physically mesh at the frame's center distance."""
        d = center_distance(self.driver, self.driven)
        return abs(d - self.frame_center_distance) < 1e-6

    @property
    def expected_driven_rpm(self) -> float:
        """If the motor is strong enough and we have a perfect pair: the
        steady-state driven RPM is determined by the motor curve and the
        ratio. We just expose the gear ratio (driver rpm / driven rpm)."""
        return gear_ratio(self.driver, self.driven)

    def set_voltage(self, voltage: float) -> None:
        self.applied_voltage = max(-self.max_voltage, min(self.max_voltage, voltage))

    def set_gears(self, driver_teeth: int, driven_teeth: int) -> None:
        self.driver = SpurGear(driver_teeth)
        self.driven = SpurGear(driven_teeth)

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
        if self.meshed:
            # omega_driven = -omega_driver * (N_driver / N_driven)
            s.driven_omega = -s.driver_omega * (self.driver.teeth / self.driven.teeth)
        else:
            # Free driven shaft — only bearing drag.
            s.driven_omega += (-self.damping * s.driven_omega) / self.inertia * dt
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
                    "Two meshing gears reverse direction. Flip the motor voltage to reverse the driver, "
                    "or add an idler to flip once more."
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
            "level": "1.2",
            "t": self.state.t,
            "driver_rpm": self.driver_rpm,
            "driven_rpm": self.driven_rpm,
            "target_driven_rpm": self.target_driven_rpm,
            "target_sign": self.target_sign,
            "voltage": self.applied_voltage,
            "meshed": self.meshed,
            "won": self.won,
            "driver_teeth": self.driver.teeth,
            "driven_teeth": self.driven.teeth,
            "diagnostic": self.last_diagnostic.to_dict() if self.last_diagnostic else None,
        }


def solve_driving_voltage(
    target_driven_rpm: float,
    driver: SpurGear,
    driven: SpurGear,
    damping: float = DEFAULT_DAMPING,
    kt: float = KT,
    kb: float = KB,
    resistance: float = RESISTANCE,
) -> float:
    """Voltage needed to hold the driven gear at target_driven_rpm steady-state.

    At steady state: alpha=0, so motor_torque = b*omega_driver.
    tau = kt*(V - kb*omega_driver)/R  ->  V = R*tau/kt + kb*omega_driver
                                   = R*b*omega_driver/kt + kb*omega_driver
    And omega_driver = -omega_driven * (N_driver / N_driven).
    """
    if not (kt > 0):
        return float("inf")
    omega_driven = target_driven_rpm * 2.0 * math.pi / 60.0
    omega_driver = -omega_driven * (driven.teeth / driver.teeth)
    tau = damping * omega_driver
    v = resistance * tau / kt + kb * omega_driver
    return v


if __name__ == "__main__":
    lvl = TwoGearLevel()
    v = solve_driving_voltage(lvl.target_driven_rpm, lvl.driver, lvl.driven)
    # For the level's target_sign=-1 we need positive voltage.
    lvl.set_voltage(abs(v) * 1.01)
    for _ in range(int(8.0 / DT)):
        lvl.step()
    print(
        f"target: {lvl.target_driven_rpm:.1f} RPM, sign {lvl.target_sign}; "
        f"V={lvl.applied_voltage:.2f}V, "
        f"driver={lvl.driver_rpm:.1f} RPM, driven={lvl.driven_rpm:.2f} RPM, "
        f"won={lvl.won}, diag={lvl.last_diagnostic}"
    )
