"""Act 1.4 — Loaded geartrain.

A motor drives a "driver" gear, which meshes with a "driven" gear — just like
1.2. The difference: the driven shaft now carries a real **load** (a resisting
torque). The player picks the **gear ratio** and the motor **voltage**, and
must both overcome the load without stalling AND hit a target output RPM.

The teaching goal: gears trade speed for torque. A reduction (small driver →
big driven) *multiplies* the motor's torque at the output (can drive a heavy
load) but *cuts* the output speed; a small reduction gives speed but stalls
under load. This is the torque×speed tradeoff that motivates all of Act 2.

Mechanics (sim units, m-kg-s):
- All catalog gears share the same module, so any pair meshes.
- Motor model: tau_motor = Kt * (V - Kb*omega) / R, clamped to torque_limit.
- Reflected load (ideal-gear power conservation): the load torque at the
  driven shaft is reflected back to the driver as
      tau_reflected = tau_load * (N_driver / N_driven)
  A reduction (N_driver < N_driven) SHRINKS the load the motor sees — that is
  exactly why reductions help drive loads.
- Driver dynamics: I*alpha = tau_motor - b*omega - tau_reflected*sign(omega).
- Driven shaft stays kinematic (as in 1.2):
  omega_driven = -omega_driver * (N_driver / N_driven).
- Stall: at omega ~= 0, the motor's starting torque is Kt*V/R (clamped to
  torque_limit). If that's <= tau_reflected, the train can't start — we pin
  omega = 0 and emit a STALLED diagnostic.

Win condition: hold |driven_rpm| at target_driven_rpm ±5% for 1 s, with the
load slider at target_load_torque ±2.5%, and no stall. (The load is set by the
player; the target is marked on the slider. You're driving THIS job.)
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from robot_forge.levels.diagnostics import (
    DiagKind,
    Diagnostic,
    diagnose_load,
    diagnose_rpm,
    diagnose_stall,
)
from robot_forge.sim.gears import SpurGear, center_distance

# Motor constants — same small DC motor as 1.2/1.3, so the player's motor
# model carries over.
KT = 0.05  # N*m/A
KB = 0.05  # V*s/rad
RESISTANCE = 1.0  # ohm
TORQUE_LIMIT = 2.0  # N*m
MAX_VOLTAGE = 24.0  # V

# Mechanical defaults.
DEFAULT_INERTIA = 0.01  # kg*m^2 — small rotor + driver gear
DEFAULT_DAMPING = 0.05  # N*m*s/rad — bearing drag on the driver

# The job. Target 30 RPM driven; target load 1.5 N·m at the output shaft.
# With load=1.5, the motor's max stall torque (Kt*V_max/R = 1.2 N·m, below
# the 2.0 clamp) is LESS than the load — so a 1:1 pair stalls at every
# voltage. The player must gear down: N20/N40 reflects 0.75 N·m back to the
# motor, well within its torque, and ~21.6 V holds 30 RPM. The lesson lands
# cleanly.
DEFAULT_TARGET_DRIVEN_RPM = 30.0
DEFAULT_TARGET_LOAD_TORQUE = 1.5
DEFAULT_DRIVER_TEETH = 30
DEFAULT_DRIVEN_TEETH = 30
DEFAULT_LOAD_TORQUE = 0.0  # slider starts at 0; player drags up to the target

RPM_TOLERANCE_FRAC = 0.05  # ±5%
LOAD_TOLERANCE_FRAC = 0.025  # ±2.5%
SETTLE_TIME_S = 1.0
DT = 0.01

# External mesh reverses direction. With positive voltage → positive driver
# omega → negative driven omega, the natural target sign is -1.
DEFAULT_TARGET_SIGN = -1


@dataclass
class LoadedGearState:
    driver_omega: float = 0.0
    driver_angle: float = 0.0
    driven_omega: float = 0.0
    driven_angle: float = 0.0
    t: float = 0.0
    settled_time: float = 0.0
    stalled: bool = False


class LoadedGearLevel:
    """Pick a ratio + voltage, drive the load at the target speed."""

    def __init__(
        self,
        driver_teeth: int = DEFAULT_DRIVER_TEETH,
        driven_teeth: int = DEFAULT_DRIVEN_TEETH,
        target_driven_rpm: float = DEFAULT_TARGET_DRIVEN_RPM,
        target_load_torque: float = DEFAULT_TARGET_LOAD_TORQUE,
        load_torque: float = DEFAULT_LOAD_TORQUE,
        target_sign: int = DEFAULT_TARGET_SIGN,
        inertia: float = DEFAULT_INERTIA,
        damping: float = DEFAULT_DAMPING,
        torque_limit: float = TORQUE_LIMIT,
        kt: float = KT,
        kb: float = KB,
        resistance: float = RESISTANCE,
        max_voltage: float = MAX_VOLTAGE,
        settle_time_s: float = SETTLE_TIME_S,
        rpm_tolerance_frac: float = RPM_TOLERANCE_FRAC,
        load_tolerance_frac: float = LOAD_TOLERANCE_FRAC,
    ) -> None:
        self.driver = SpurGear(driver_teeth)
        self.driven = SpurGear(driven_teeth)
        self.target_driven_rpm = target_driven_rpm
        self.target_load_torque = target_load_torque
        self.load_torque = load_torque
        self.target_sign = target_sign
        self.frame_center_distance = center_distance(self.driver, self.driven)
        self.inertia = inertia
        self.damping = damping
        self.torque_limit = torque_limit
        self.kt = kt
        self.kb = kb
        self.resistance = resistance
        self.max_voltage = max_voltage
        self.settle_time_s = settle_time_s
        self.rpm_tolerance_frac = rpm_tolerance_frac
        self.load_tolerance_frac = load_tolerance_frac
        self.state = LoadedGearState()
        self.applied_voltage: float = 0.0
        self.applied_torque: float = 0.0  # motor torque, surfaced for HUD
        self.reflected_load: float = 0.0  # tau_load * N_driver/N_driven (for HUD)
        self.won: bool = False
        self.last_diagnostic: Diagnostic | None = None

    # --- readouts ---------------------------------------------------------

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
    def reduction_ratio(self) -> float:
        """Driven/driver teeth (>=1 is a reduction; multiplies output torque)."""
        return self.driven.teeth / self.driver.teeth

    @property
    def output_torque(self) -> float:
        """Torque at the DRIVEN (output) shaft.

        The load slider sets the resisting torque on the driven shaft, so at
        steady state (running, not stalled) the train delivers exactly that
        load to the output: ``output_torque == load_torque``. At stall the
        motor can't sustain the full load, so the output is whatever torque
        the motor can muster, multiplied by the ratio (torque multiplication
        in the motor's favor): ``motor_stall_torque * reduction_ratio``.
        """
        if self.state.stalled:
            return self._motor_stall_torque() * self.reduction_ratio
        return self.load_torque

    @property
    def motor_side_load(self) -> float:
        """The load AS THE MOTOR FEELS IT — reflected through the ratio.

        ``tau_reflected = load_torque * (N_driver / N_driven) = load / ratio``.
        A reduction (ratio > 1) shrinks this number — that is why gear
        reductions help a small motor drive a heavy load.
        """
        return self.reflected_load

    @property
    def rpm_tolerance(self) -> float:
        return self.rpm_tolerance_frac * abs(self.target_driven_rpm)

    @property
    def load_tolerance(self) -> float:
        return self.load_tolerance_frac * max(abs(self.target_load_torque), 1.0)

    # --- player actions ---------------------------------------------------

    def set_voltage(self, voltage: float) -> None:
        self.applied_voltage = max(-self.max_voltage, min(self.max_voltage, voltage))

    def set_gears(self, driver_teeth: int, driven_teeth: int) -> None:
        self.driver = SpurGear(driver_teeth)
        self.driven = SpurGear(driven_teeth)
        self.frame_center_distance = center_distance(self.driver, self.driven)

    def set_load(self, load_torque: float) -> None:
        """Player drags the load slider. Non-negative — a load resists motion."""
        self.load_torque = max(0.0, load_torque)

    # --- motor / load math ------------------------------------------------

    def _reflected_load(self) -> float:
        """Load torque reflected to the driver through the gear ratio."""
        return self.load_torque * (self.driver.teeth / self.driven.teeth)

    def _motor_stall_torque(self) -> float:
        """Motor torque at omega=0 (the starting torque), clamped to limit."""
        if self.kt <= 0.0 or self.resistance <= 0.0:
            return 0.0
        return max(
            -self.torque_limit,
            min(self.torque_limit, self.kt * self.applied_voltage / self.resistance),
        )

    def _motor_torque(self, omega_driver: float) -> float:
        if self.kt <= 0.0 or self.resistance <= 0.0:
            return 0.0
        i = (self.applied_voltage - self.kb * omega_driver) / self.resistance
        tau = self.kt * i
        return max(-self.torque_limit, min(self.torque_limit, tau))

    def step(self, dt: float = DT) -> None:
        if self.won:
            return
        s = self.state
        self.reflected_load = self._reflected_load()
        tau = self._motor_torque(s.driver_omega)
        self.applied_torque = tau
        # The load is Coulomb (constant magnitude, opposes motion). A stalled
        # train cannot be back-driven: once the motor can't sustain motion the
        # load pins omega at zero rather than reversing the gear. This kills the
        # flicker that a naive sign(omega) load produces around zero.
        eps = 1e-6
        if abs(s.driver_omega) < eps:
            # At rest. Can the motor start the load?
            if abs(tau) > self.reflected_load:
                load_sign = 1.0 if tau > 0 else -1.0
                tau_load_eff = self.reflected_load * load_sign
                alpha = (tau - self.damping * s.driver_omega - tau_load_eff) / self.inertia
                s.driver_omega += alpha * dt
                s.stalled = False
            else:
                # True stall — the motor can't overcome the reflected load.
                # No back-driving; the train stays pinned at zero.
                s.driver_omega = 0.0
                s.stalled = True
        else:
            # Moving: the load opposes the current direction of motion.
            load_sign = 1.0 if s.driver_omega > 0 else -1.0
            tau_load_eff = self.reflected_load * load_sign
            alpha = (tau - self.damping * s.driver_omega - tau_load_eff) / self.inertia
            new_omega = s.driver_omega + alpha * dt
            # Anti-back-drive: if this step would cross zero, the motor must be
            # strong enough to sustain motion in the NEW direction. Otherwise
            # the load pins the train at rest (stall) — no kicking it backward.
            if (new_omega > 0) != (s.driver_omega > 0):  # sign would flip
                tau_at_zero = self._motor_torque(0.0)
                if abs(tau_at_zero) <= self.reflected_load:
                    s.driver_omega = 0.0
                    s.stalled = True
                else:
                    s.driver_omega = new_omega
                    s.stalled = False
            else:
                s.driver_omega = new_omega
                s.stalled = False
        s.driver_angle += s.driver_omega * dt
        if self.meshed:
            s.driven_omega = -s.driver_omega * (self.driver.teeth / self.driven.teeth)
        else:
            s.driven_omega += (-self.damping * s.driven_omega) / self.inertia * dt
        s.driven_angle += s.driven_omega * dt
        s.t += dt
        self._check_win()

    def _check_win(self) -> None:
        # 1) Stall dominates — no win, surface the stall diagnostic.
        if self.state.stalled:
            self.state.settled_time = 0.0
            self.last_diagnostic = diagnose_stall(self.reflected_load, self._motor_stall_torque())
            return
        # 2) Load must match the target (you're driving THIS job).
        load_diag = diagnose_load(self.load_torque, self.target_load_torque, self.load_tolerance)
        # 3) Speed must hit the target magnitude.
        speed_diag = diagnose_rpm(
            abs(self.driven_rpm), abs(self.target_driven_rpm), self.rpm_tolerance
        )
        # 4) Direction.
        dir_diag: Diagnostic | None = None
        measured = self.state.driven_omega
        if measured != 0 and (1 if measured > 0 else -1) != self.target_sign:
            dir_diag = Diagnostic(
                kind=DiagKind.WRONG_DIRECTION,
                message=(
                    f"Driven gear spins {'CW' if measured < 0 else 'CCW'}, "
                    f"target {'CW' if self.target_sign < 0 else 'CCW'}."
                ),
                hint="Flip the motor voltage to reverse the driver.",
            )
        if load_diag is None and speed_diag is None and dir_diag is None:
            self.state.settled_time += DT
            if self.state.settled_time >= self.settle_time_s:
                self.won = True
                self.last_diagnostic = None
        else:
            self.state.settled_time = 0.0
            # Surface the most informative diagnostic: stall already handled;
            # prefer load mismatch (the new mechanic) then speed then direction.
            self.last_diagnostic = (
                load_diag
                if load_diag is not None
                else speed_diag
                if speed_diag is not None
                else dir_diag
            )

    def summary(self) -> dict:
        return {
            "level": "1.4",
            "t": self.state.t,
            "driver_rpm": self.driver_rpm,
            "driven_rpm": self.driven_rpm,
            "target_driven_rpm": self.target_driven_rpm,
            "target_sign": self.target_sign,
            "voltage": self.applied_voltage,
            "torque": self.applied_torque,
            "load_torque": self.load_torque,
            "target_load_torque": self.target_load_torque,
            "reflected_load": self.reflected_load,
            "motor_side_load": self.motor_side_load,
            "output_torque": self.output_torque,
            "reduction_ratio": self.reduction_ratio,
            "stalled": self.state.stalled,
            "meshed": self.meshed,
            "won": self.won,
            "driver_teeth": self.driver.teeth,
            "driven_teeth": self.driven.teeth,
            "center_distance": self.frame_center_distance,
            "diagnostic": self.last_diagnostic.to_dict() if self.last_diagnostic else None,
        }


def solve_driving_voltage_1_4(
    target_driven_rpm: float,
    driver: SpurGear,
    driven: SpurGear,
    load_torque: float,
    damping: float = DEFAULT_DAMPING,
    kt: float = KT,
    kb: float = KB,
    resistance: float = RESISTANCE,
) -> float:
    """Voltage that holds the driven gear at target_rpm against the load.

    At steady state: alpha=0, so
        tau_motor(omega_driver) = b*omega_driver + tau_reflected
        kt*(V - kb*omega_driver)/R = b*omega_driver + tau_load*N_driver/N_driven
    =>  V = R*(b*omega_driver + tau_reflected)/kt + kb*omega_driver
    And omega_driver = -omega_driven * (N_driven/N_driver) (sign handled by caller).
    """
    if not (kt > 0):
        return float("inf")
    omega_driven = target_driven_rpm * 2.0 * math.pi / 60.0
    omega_driver = omega_driven * (driven.teeth / driver.teeth)
    tau_reflected = load_torque * (driver.teeth / driven.teeth)
    tau_needed = damping * omega_driver + tau_reflected
    return resistance * tau_needed / kt + kb * omega_driver


if __name__ == "__main__":
    lvl = LoadedGearLevel()
    lvl.set_load(lvl.target_load_torque)  # set the slider to the target job
    v = solve_driving_voltage_1_4(
        lvl.target_driven_rpm, lvl.driver, lvl.driven, lvl.target_load_torque
    )
    print(f"1:1 pair, load {lvl.target_load_torque} N·m: solver V = {v:.2f} (stalls)")
    # Try the solution pair N20/N40.
    lvl.set_gears(20, 40)
    lvl.set_load(lvl.target_load_torque)
    v = solve_driving_voltage_1_4(
        lvl.target_driven_rpm, lvl.driver, lvl.driven, lvl.target_load_torque
    )
    print(f"N20/N40 pair, load {lvl.target_load_torque} N·m: solver V = {v:.2f}")
    lvl.set_voltage(abs(v) * 1.01)
    for _ in range(int(12.0 / DT)):
        lvl.step()
    print(
        f"after 12s: driven={lvl.driven_rpm:.2f} RPM (target {lvl.target_driven_rpm}), "
        f"stalled={lvl.state.stalled}, won={lvl.won}, diag={lvl.last_diagnostic}"
    )
