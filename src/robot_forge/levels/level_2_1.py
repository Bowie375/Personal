"""Act 2.1 — Compound gearbox (two-stage reduction).

A single mesh tops out at the catalog's max ratio (N60/N12 = 5:1). To reach a
bigger reduction the player stacks a **second stage**: the driver (A) meshes
with gear B, and B shares a shaft with gear C, which meshes with the output D.
Because B and C are on the SAME shaft, the stage ratios MULTIPLY:

    total = (N_B / N_A) * (N_D / N_C)

This is the keystone Act-2 mechanic: real gearboxes are multi-stage because
one mesh can't do it. The level pins a target reduction (12:1) that NO single
pair can reach, so the player is FORCED to compound. The diagnostic teaches
why.

Mechanics (reuses the 1.4 motor + reflected-load engine):
- DC motor: tau_motor = Kt * (V - Kb*omega) / R, clamped to torque_limit.
- Gear train (4 gears, 2 external meshes -> output direction +1, same as driver):
    omega_B = -omega_A * (N_A / N_B)
    omega_C = omega_B                (shared shaft)
    omega_D = -omega_C * (N_C / N_D)
  => omega_D = omega_A * (N_A/N_B) * (N_C/N_D) = omega_A / total_ratio
- Reflected load: an output torque tau_load reflects back to the driver as
    tau_reflected = tau_load / total_ratio
  (a bigger reduction shrinks the load the motor fights — same lesson as 1.4,
  now amplified by the squared factor of two stages).
- No back-driving: if the motor can't sustain motion, the train pins at zero
  (same Coulomb-load logic as 1.4; prevents the zero-crossing flicker).

Win condition: total ratio == target_ratio (exact, integer tooth products),
output RPM at target ±5%, load slider at target load ±2.5%, no stall.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from robot_forge.levels.diagnostics import (
    DiagKind,
    Diagnostic,
    diagnose_load,
    diagnose_rpm,
)
from robot_forge.sim.gears import SpurGear

# Motor constants — same small DC motor as 1.2–1.4.
KT = 0.05  # N*m/A
KB = 0.05  # V*s/rad
RESISTANCE = 1.0  # ohm
TORQUE_LIMIT = 2.0  # N*m
MAX_VOLTAGE = 24.0  # V

# Mechanical defaults.
DEFAULT_INERTIA = 0.01  # kg*m^2 — motor shaft + driver gear A
DEFAULT_DAMPING = 0.05  # N*m*s/rad

# The job. Target reduction 12:1 (unreachable by any single catalog pair, max 5:1).
# Default gears: N30/N30 x N30/N30 = 1:1 (obviously wrong — player must change them).
DEFAULT_TARGET_RATIO = 12.0
DEFAULT_TEETH_A = 30
DEFAULT_TEETH_B = 30
DEFAULT_TEETH_C = 30
DEFAULT_TEETH_D = 30

# A light load: the point of 2.1 is the RATIO, not the load. Keep it modest so
# a correct 12:1 compound drives cleanly. (1.4 already taught load + stall.)
DEFAULT_TARGET_LOAD_TORQUE = 0.5
DEFAULT_LOAD_TORQUE = 0.0
DEFAULT_TARGET_OUT_RPM = 10.0

RPM_TOLERANCE_FRAC = 0.05  # ±5%
LOAD_TOLERANCE_FRAC = 0.025  # ±2.5%
RATIO_TOLERANCE = 1e-9  # exact — tooth counts are integers
SETTLE_TIME_S = 1.0
DT = 0.01

# Two external meshes -> output spins the SAME direction as the driver (+1).
DEFAULT_TARGET_SIGN = 1


@dataclass
class CompoundState:
    driver_omega: float = 0.0  # gear A (motor shaft)
    driver_angle: float = 0.0
    b_omega: float = 0.0  # gear B (shares shaft with C)
    b_angle: float = 0.0
    d_omega: float = 0.0  # gear D (output)
    d_angle: float = 0.0
    t: float = 0.0
    settled_time: float = 0.0
    stalled: bool = False


class CompoundGearLevel:
    """Stack two stages on a shared shaft to reach a ratio no single pair can."""

    def __init__(
        self,
        teeth_a: int = DEFAULT_TEETH_A,
        teeth_b: int = DEFAULT_TEETH_B,
        teeth_c: int = DEFAULT_TEETH_C,
        teeth_d: int = DEFAULT_TEETH_D,
        target_ratio: float = DEFAULT_TARGET_RATIO,
        target_out_rpm: float = DEFAULT_TARGET_OUT_RPM,
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
        ratio_tolerance: float = RATIO_TOLERANCE,
    ) -> None:
        self.gear_a = SpurGear(teeth_a)
        self.gear_b = SpurGear(teeth_b)
        self.gear_c = SpurGear(teeth_c)
        self.gear_d = SpurGear(teeth_d)
        self.target_ratio = target_ratio
        self.target_out_rpm = target_out_rpm
        self.target_load_torque = target_load_torque
        self.load_torque = load_torque
        self.target_sign = target_sign
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
        self.ratio_tolerance = ratio_tolerance
        self.state = CompoundState()
        self.applied_voltage: float = 0.0
        self.applied_torque: float = 0.0
        self.reflected_load: float = 0.0
        self.won: bool = False
        self.last_diagnostic: Diagnostic | None = None

    # --- readouts ---------------------------------------------------------

    @property
    def stage1_ratio(self) -> float:
        """Stage 1: A drives B (reduction = N_B / N_A)."""
        return self.gear_b.teeth / self.gear_a.teeth

    @property
    def stage2_ratio(self) -> float:
        """Stage 2: C drives D (reduction = N_D / N_C). C shares B's shaft."""
        return self.gear_d.teeth / self.gear_c.teeth

    @property
    def total_ratio(self) -> float:
        """Compound reduction (B/A) * (D/C). Motor turns this many times per output."""
        return self.stage1_ratio * self.stage2_ratio

    @property
    def driver_rpm(self) -> float:
        """Gear A (motor shaft)."""
        return self.state.driver_omega * 60.0 / (2.0 * math.pi)

    @property
    def intermediate_rpm(self) -> float:
        """Gear B (= C), the shared-shaft middle stage."""
        return self.state.b_omega * 60.0 / (2.0 * math.pi)

    @property
    def output_rpm(self) -> float:
        """Gear D (final output)."""
        return self.state.d_omega * 60.0 / (2.0 * math.pi)

    @property
    def meshed(self) -> bool:
        """Gears are assumed meshed (catalog shares one module)."""
        return True

    @property
    def output_torque(self) -> float:
        """Torque at the output (D) shaft = the load when running."""
        if self.state.stalled:
            return self._motor_stall_torque() * self.total_ratio
        return self.load_torque

    @property
    def motor_side_load(self) -> float:
        """Load as the motor feels it — reflected through BOTH stages."""
        return self.reflected_load

    @property
    def rpm_tolerance(self) -> float:
        return self.rpm_tolerance_frac * abs(self.target_out_rpm)

    @property
    def load_tolerance(self) -> float:
        return self.load_tolerance_frac * max(abs(self.target_load_torque), 1.0)

    # --- player actions ---------------------------------------------------

    def set_voltage(self, voltage: float) -> None:
        self.applied_voltage = max(-self.max_voltage, min(self.max_voltage, voltage))

    def set_gears(
        self,
        teeth_a: int,
        teeth_b: int,
        teeth_c: int,
        teeth_d: int,
    ) -> None:
        """Pick all four gear tooth counts. B and C share a shaft (compound)."""
        self.gear_a = SpurGear(teeth_a)
        self.gear_b = SpurGear(teeth_b)
        self.gear_c = SpurGear(teeth_c)
        self.gear_d = SpurGear(teeth_d)

    def set_load(self, load_torque: float) -> None:
        self.load_torque = max(0.0, load_torque)

    # --- motor / load math ------------------------------------------------

    def _reflected_load(self) -> float:
        """Output load reflected to the driver through the COMPOUND ratio."""
        return self.load_torque / self.total_ratio

    def _motor_stall_torque(self) -> float:
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
        eps = 1e-6
        if abs(s.driver_omega) < eps:
            if abs(tau) > self.reflected_load:
                load_sign = 1.0 if tau > 0 else -1.0
                tau_load_eff = self.reflected_load * load_sign
                alpha = (tau - self.damping * s.driver_omega - tau_load_eff) / self.inertia
                s.driver_omega += alpha * dt
                s.stalled = False
            else:
                s.driver_omega = 0.0
                s.stalled = True
        else:
            load_sign = 1.0 if s.driver_omega > 0 else -1.0
            tau_load_eff = self.reflected_load * load_sign
            alpha = (tau - self.damping * s.driver_omega - tau_load_eff) / self.inertia
            new_omega = s.driver_omega + alpha * dt
            if (new_omega > 0) != (s.driver_omega > 0):
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
        # Compound kinematics: A->B (external, flips), B=C (shared shaft),
        # C->D (external, flips again -> same sign as A).
        s.b_omega = -s.driver_omega * (self.gear_a.teeth / self.gear_b.teeth)
        s.b_angle += s.b_omega * dt
        d_omega = -s.b_omega * (self.gear_c.teeth / self.gear_d.teeth)
        s.d_omega = d_omega
        s.d_angle += s.d_omega * dt
        s.t += dt
        self._check_win()

    def _check_win(self) -> None:
        # 1) Stall dominates.
        if self.state.stalled:
            self.state.settled_time = 0.0
            self.last_diagnostic = Diagnostic(
                kind=DiagKind.STALLED,
                message=(
                    f"Stalled: load reflects {self.reflected_load:.3f} N·m to the motor, "
                    f"which can muster {self._motor_stall_torque():.3f} N·m to start."
                ),
                hint=(
                    "Raise the motor voltage. (With enough reduction the load is tiny "
                    "at the motor — a 12:1 compound turns a 0.5 N·m load into 0.04 N·m.)"
                ),
            )
            return
        # 2) Ratio must hit the target (exact).
        ratio_diag: Diagnostic | None = None
        if abs(self.total_ratio - self.target_ratio) > self.ratio_tolerance:
            ratio_diag = Diagnostic(
                kind=DiagKind.WRONG_RATIO,
                message=(
                    f"Ratio {self.total_ratio:.3f}:1, target {self.target_ratio:.1f}:1 "
                    f"(stage1 {self.stage1_ratio:.2f} × stage2 {self.stage2_ratio:.2f})."
                ),
                hint=(
                    "A single mesh tops out at 5:1 (N12→N60). For a bigger reduction, "
                    "stack a second stage: B and C on a shared shaft, so the stage "
                    "ratios multiply. total = (N_B/N_A) × (N_D/N_C)."
                ),
            )
        # 3) Load must match the target job.
        load_diag = diagnose_load(self.load_torque, self.target_load_torque, self.load_tolerance)
        # 4) Output speed.
        speed_diag = diagnose_rpm(
            abs(self.output_rpm), abs(self.target_out_rpm), self.rpm_tolerance
        )
        # 5) Direction.
        dir_diag: Diagnostic | None = None
        measured = self.state.d_omega
        if measured != 0 and (1 if measured > 0 else -1) != self.target_sign:
            dir_diag = Diagnostic(
                kind=DiagKind.WRONG_DIRECTION,
                message=(
                    f"Output spins {'CW' if measured < 0 else 'CCW'}, "
                    f"target {'CW' if self.target_sign < 0 else 'CCW'}."
                ),
                hint="Two external meshes should give +1 (same as driver). Flip the motor voltage.",
            )
        if ratio_diag is None and load_diag is None and speed_diag is None and dir_diag is None:
            self.state.settled_time += DT
            if self.state.settled_time >= self.settle_time_s:
                self.won = True
                self.last_diagnostic = None
        else:
            self.state.settled_time = 0.0
            self.last_diagnostic = (
                ratio_diag
                if ratio_diag is not None
                else load_diag
                if load_diag is not None
                else speed_diag
                if speed_diag is not None
                else dir_diag
            )

    def summary(self) -> dict:
        return {
            "level": "2.1",
            "t": self.state.t,
            "driver_rpm": self.driver_rpm,
            "intermediate_rpm": self.intermediate_rpm,
            "driven_rpm": self.output_rpm,
            "output_rpm": self.output_rpm,
            "target_out_rpm": self.target_out_rpm,
            "target_driven_rpm": self.target_out_rpm,  # alias for level_state
            "target_sign": self.target_sign,
            "voltage": self.applied_voltage,
            "torque": self.applied_torque,
            "load_torque": self.load_torque,
            "target_load_torque": self.target_load_torque,
            "reflected_load": self.reflected_load,
            "motor_side_load": self.motor_side_load,
            "output_torque": self.output_torque,
            "total_ratio": self.total_ratio,
            "stage1_ratio": self.stage1_ratio,
            "stage2_ratio": self.stage2_ratio,
            "target_ratio": self.target_ratio,
            "stalled": self.state.stalled,
            "meshed": self.meshed,
            "won": self.won,
            "teeth_a": self.gear_a.teeth,
            "teeth_b": self.gear_b.teeth,
            "teeth_c": self.gear_c.teeth,
            "teeth_d": self.gear_d.teeth,
            "driver_teeth": self.gear_a.teeth,  # alias for level_state
            "driven_teeth": self.gear_d.teeth,  # alias for level_state
            "diagnostic": self.last_diagnostic.to_dict() if self.last_diagnostic else None,
        }


def solve_driving_voltage_2_1(
    target_out_rpm: float,
    total_ratio: float,
    load_torque: float,
    damping: float = DEFAULT_DAMPING,
    kt: float = KT,
    kb: float = KB,
    resistance: float = RESISTANCE,
) -> float:
    """Voltage to hold the OUTPUT at target_rpm against the load.

    Output omega = driver_omega / total_ratio  =>  driver_omega = omega_out * ratio.
    At steady state: tau_motor(omega_drv) = b*omega_drv + tau_reflected
        kt*(V - kb*omega_drv)/R = b*omega_drv + load/total_ratio
    """
    if not (kt > 0) or total_ratio <= 0:
        return float("inf")
    omega_out = target_out_rpm * 2.0 * math.pi / 60.0
    omega_driver = omega_out * total_ratio
    tau_reflected = load_torque / total_ratio
    tau_needed = damping * omega_driver + tau_reflected
    return resistance * tau_needed / kt + kb * omega_driver


if __name__ == "__main__":
    lvl = CompoundGearLevel()
    print(f"target ratio {lvl.target_ratio}:1; current {lvl.total_ratio}:1 (1:1 default)")
    # A working compound: N12->N36 x N12->N48 = 3*4 = 12:1.
    lvl.set_gears(12, 36, 12, 48)
    lvl.set_load(lvl.target_load_torque)
    v = solve_driving_voltage_2_1(lvl.target_out_rpm, lvl.total_ratio, lvl.target_load_torque)
    print(f"N12/N36 x N12/N48 = {lvl.total_ratio}:1; solver V = {v:.2f}")
    lvl.set_voltage(abs(v) * 1.01)
    for _ in range(int(12.0 / DT)):
        lvl.step()
    print(
        f"after 12s: out={lvl.output_rpm:.2f} RPM (target {lvl.target_out_rpm}), "
        f"driver={lvl.driver_rpm:.1f}, ratio={lvl.total_ratio}:1, "
        f"stalled={lvl.state.stalled}, won={lvl.won}, diag={lvl.last_diagnostic}"
    )
