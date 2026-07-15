"""Act 2.3 — First joint (planetary gearbox driving a rod to an angle).

A *joint* is where a gearbox stops being a free-spinning shaft and starts
moving a *link* to an angle. Here a **planetary** gearbox (the standard real
robot-joint reducer) drives a rigid **rod** mounted to the **carrier** — the
output member in ring-fixed mode (motor → sun → planets → carrier → rod).

The player sets a **voltage**; the motor+planetary torque lifts the rod
against **gravity** (fixed rod mass) and **joint damping**. There is no
voltage cut-off and no PD controller — the rod *settles* at the angle where
the motor's reflected torque (through the reduction) balances the gravity
torque. The win is that settled angle landing within ±2° of a target.

The lesson: a robot joint is a *reduction* problem — the planetary's carrier
is the output, and the gearbox must be stiff enough that gravity can't
back-drive it, yet the voltage must push the equilibrium onto the target.

Physics (rod of length L, mass m, angle θ from straight down, on the carrier):

    τ_motor_sun = Kt * (V - Kb*w_sun)/R            # DC motor, clamped
    τ_motor_carrier = τ_motor_sun * reduction       # reflected (ring-fixed)
    τ_gravity = m*g*(L/2)*sin(θ)                     # restoring, pulls to θ=0
    τ_damp   = b * w_carrier                          # transient, zero at settle
    I_carrier * α_carrier = τ_motor_carrier - τ_grav(θ) - τ_damp

At settle:  τ_motor_stall_carrier = τ_gravity(θ_eq)
    =>  θ_eq = asin( τ_motor_stall_carrier / (m*g*L/2) )

No-overshoot invariant: the level enforces the motor can never drive the rod
past horizontal — if the reflected stall torque would exceed m*g*L/2 (the
torque to hold the rod at 90°), the rod pins at the horizontal hard stop with
zero velocity (no energy carried past 90°) and an OVERSHOOT diagnostic fires.
Gravity always restores, so the rod never flips and the player never cuts
voltage. The damping is in the over-damped regime so the rod rises
monotonically to the equilibrium without swinging past it.

Reduction (ring-fixed, the winning mode): 1 + N_ring/N_sun. Default set
sun N12 / ring N60 (planet N24 derived) = 6:1, the catalog max planetary.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from robot_forge.levels.diagnostics import (
    DiagKind,
    Diagnostic,
    diagnose_angle,
    diagnose_assemblable,
)
from robot_forge.sim.gears import SpurGear, planetary_gear_ratio

# Motor constants — same small DC motor as 1.2–2.2.
KT = 0.05  # N*m/A
KB = 0.05  # V*s/rad
RESISTANCE = 1.0  # ohm
TORQUE_LIMIT = 2.0  # N*m
MAX_VOLTAGE = 24.0  # V

# Mechanical defaults.
DEFAULT_INERTIA_SUN = 0.01  # kg*m^2 — motor shaft + sun gear

# The rod (the link / joint arm). A modest mass and length so the gravity
# torque sits in a reachable band for the catalog planetary + small motor.
ROD_MASS = 0.5  # kg
ROD_LENGTH = 0.4  # m
GRAVITY = 9.81  # m/s^2
# Joint damping on the carrier/output shaft. Affects ONLY the transient
# (settle time / overshoot), not the equilibrium: at steady state w_carrier=0
# so the damping torque vanishes. Set in the OVER-DAMPED regime so the rod
# rises MONOTONICALLY to its equilibrium — never swings past the target (the
# "always points down, no overshoot" guarantee). At the default 6:1 reduction
# the reflected inertia is large (I_sun·R²), so the damping is scaled up from
# the 3:1 case to keep the rise monotonic and well-damped.
ROD_DAMPING = 1.0  # N*m*s/rad

# The job: lift the rod to 45° and hold it. sin(45°)=0.707. At 6:1 (the default
# planetary) the solver voltage is ~2.3 V — comfortably inside the 24 V clamp.
# ±2° tolerance per the progression design.
DEFAULT_TARGET_ANGLE_DEG = 45.0
ANGLE_TOLERANCE_DEG = 2.0
SETTLE_TIME_S = 1.0
DT = 0.01

# Default planetary set: sun N12 / ring N60 -> planet N24 (derived), ring-fixed
# ratio 1 + 60/12 = 6:1 (catalog max planetary reduction). At V=0 the rod hangs
# at 0°; the player raises the voltage to climb toward the target. Starting at
# 0 V / 0° gives a clean "wrong" first impression the player must tune.
DEFAULT_TEETH_SUN = 12
DEFAULT_TEETH_RING = 60
DEFAULT_NUM_PLANETS = 3
DEFAULT_MODE = "ring_fixed"

# Output direction: positive motor torque lifts the rod from straight down
# (θ=0) toward horizontal (θ=90°), so the target sign is +1.
DEFAULT_TARGET_SIGN = 1

# Settled-speed threshold: once |w_carrier| is below this for SETTLE_TIME_S the
# rod is at rest and the angle is judged.
SETTLED_OMEGA = 1e-3  # rad/s

MODES: tuple[str, ...] = ("ring_fixed", "sun_fixed", "carrier_fixed")


@dataclass
class JointState:
    sun_omega: float = 0.0  # motor/sun shaft (rad/s)
    sun_angle: float = 0.0
    carrier_omega: float = 0.0  # rod / carrier shaft (rad/s) — the joint
    carrier_angle: float = 0.0  # rod angle from straight down (rad)
    ring_omega: float = 0.0
    ring_angle: float = 0.0
    planet_omega: float = 0.0  # planet self-spin (for visuals)
    planet_angle: float = 0.0
    t: float = 0.0
    settled_time: float = 0.0
    overspeed: bool = False  # over-torque: would lift past 90°, capped


class JointLevel:
    """A planetary gearbox whose carrier carries a rod; balance it at target."""

    def __init__(
        self,
        teeth_sun: int = DEFAULT_TEETH_SUN,
        teeth_ring: int = DEFAULT_TEETH_RING,
        num_planets: int = DEFAULT_NUM_PLANETS,
        mode: str = DEFAULT_MODE,
        target_angle_deg: float = DEFAULT_TARGET_ANGLE_DEG,
        rod_mass: float = ROD_MASS,
        rod_length: float = ROD_LENGTH,
        damping: float = ROD_DAMPING,
        gravity: float = GRAVITY,
        inertia_sun: float = DEFAULT_INERTIA_SUN,
        torque_limit: float = TORQUE_LIMIT,
        kt: float = KT,
        kb: float = KB,
        resistance: float = RESISTANCE,
        max_voltage: float = MAX_VOLTAGE,
        settle_time_s: float = SETTLE_TIME_S,
        angle_tolerance_deg: float = ANGLE_TOLERANCE_DEG,
        target_sign: int = DEFAULT_TARGET_SIGN,
    ) -> None:
        self.gear_sun = SpurGear(teeth_sun)
        self.gear_ring = SpurGear(teeth_ring)
        # Planet is DERIVED from the sun+ring (N_planet = (N_ring-N_sun)/2).
        diff = teeth_ring - teeth_sun
        planet_teeth = diff // 2 if diff > 0 and diff % 2 == 0 else 12
        if planet_teeth <= 0:
            planet_teeth = 12
        self.gear_planet = SpurGear(planet_teeth)
        self.num_planets = num_planets
        self.mode = mode if mode in MODES else DEFAULT_MODE
        self.target_angle = math.radians(target_angle_deg)
        self.rod_mass = rod_mass
        self.rod_length = rod_length
        self.damping = damping
        self.gravity = gravity
        self.inertia_sun = inertia_sun
        self.torque_limit = torque_limit
        self.kt = kt
        self.kb = kb
        self.resistance = resistance
        self.max_voltage = max_voltage
        self.settle_time_s = settle_time_s
        self.angle_tolerance = math.radians(angle_tolerance_deg)
        self.target_sign = target_sign
        self.state = JointState()
        self.applied_voltage: float = 0.0
        self.applied_torque: float = 0.0  # motor-side (sun) torque
        self.won: bool = False
        self.last_diagnostic: Diagnostic | None = None

    # --- readouts ---------------------------------------------------------

    @property
    def reduction_ratio(self) -> float:
        """Signed output/input for the current mode. Ring-fixed = 1+N_R/N_S."""
        return planetary_gear_ratio(self.gear_sun, self.gear_ring, self.mode)

    @property
    def derived_planet_teeth(self) -> int:
        """The planet tooth count the sun+ring force: (N_ring - N_sun) / 2."""
        return (self.gear_ring.teeth - self.gear_sun.teeth) // 2

    @property
    def assemblable(self) -> bool:
        """Geometric N_ring = N_sun + 2*N_planet + slotting (same as 2.2)."""
        return (
            diagnose_assemblable(
                self.gear_sun.teeth,
                self.gear_ring.teeth,
                self.num_planets,
            )
            is None
        )

    @property
    def meshed(self) -> bool:
        return self.assemblable

    @property
    def sun_rpm(self) -> float:
        return self.state.sun_omega * 60.0 / (2.0 * math.pi)

    @property
    def carrier_rpm(self) -> float:
        return self.state.carrier_omega * 60.0 / (2.0 * math.pi)

    @property
    def ring_rpm(self) -> float:
        return self.state.ring_omega * 60.0 / (2.0 * math.pi)

    @property
    def planet_rpm(self) -> float:
        return self.state.planet_omega * 60.0 / (2.0 * math.pi)

    @property
    def driver_rpm(self) -> float:
        return self.sun_rpm

    @property
    def driven_rpm(self) -> float:
        return self.carrier_rpm

    @property
    def output_rpm(self) -> float:
        return self.carrier_rpm

    @property
    def link_angle(self) -> float:
        """Rod angle from straight down, radians (= carrier angle)."""
        return self.state.carrier_angle

    @property
    def link_angle_deg(self) -> float:
        return math.degrees(self.state.carrier_angle)

    @property
    def target_angle_deg(self) -> float:
        return math.degrees(self.target_angle)

    @property
    def gravity_torque_amplitude(self) -> float:
        """Max gravity torque = m*g*L/2 (rod horizontal, sin θ = 1)."""
        return self.rod_mass * self.gravity * (self.rod_length * 0.5)

    def gravity_torque(self, theta: float) -> float:
        """Restoring torque magnitude pulling the rod back to θ=0."""
        return self.gravity_torque_amplitude * math.sin(theta)

    @property
    def motor_stall_torque_sun(self) -> float:
        if self.kt <= 0.0 or self.resistance <= 0.0:
            return 0.0
        return max(
            -self.torque_limit,
            min(self.torque_limit, self.kt * self.applied_voltage / self.resistance),
        )

    @property
    def motor_stall_torque_out(self) -> float:
        """Motor stall torque reflected to the carrier (the rod)."""
        return self.motor_stall_torque_sun * abs(self.reduction_ratio)

    # --- player actions ---------------------------------------------------

    def set_voltage(self, voltage: float) -> None:
        self.applied_voltage = max(-self.max_voltage, min(self.max_voltage, voltage))

    def set_gears(self, teeth_sun: int, teeth_ring: int) -> None:
        """Pick sun + ring; the planet is DERIVED (N_planet = (N_ring-N_sun)/2),
        same 2-arg convention as 2.2. An invalid pair surfaces a
        NOT_ASSEMBLABLE diagnostic on the next step."""
        self.gear_sun = SpurGear(teeth_sun)
        self.gear_ring = SpurGear(teeth_ring)
        diff = teeth_ring - teeth_sun
        planet_teeth = diff // 2 if diff > 0 and diff % 2 == 0 else 12
        if planet_teeth <= 0:
            planet_teeth = 12
        self.gear_planet = SpurGear(planet_teeth)

    def set_mode(self, mode: str) -> None:
        """Ground one member: 'ring_fixed' (default/winning), 'sun_fixed',
        or 'carrier_fixed'. The carrier is the rod output; ring-fixed is the
        classic same-direction reducer."""
        if mode in MODES:
            self.mode = mode

    # --- motor / load math ------------------------------------------------

    def _motor_torque(self, omega_sun: float) -> float:
        if self.kt <= 0.0 or self.resistance <= 0.0:
            return 0.0
        i = (self.applied_voltage - self.kb * omega_sun) / self.resistance
        tau = self.kt * i
        return max(-self.torque_limit, min(self.torque_limit, tau))

    def _reflected_inertia_out(self) -> float:
        """Rod inertia about the pivot (thin rod about end: mL²/3), plus the
        motor+sun reflected through the reduction (I_sun * R²)."""
        rod = self.rod_mass * self.rod_length * self.rod_length / 3.0
        r = abs(self.reduction_ratio)
        return rod + self.inertia_sun * r * r

    def _planet_spin(self, sun_omega: float, carrier_omega: float) -> float:
        """Planet self-spin in the inertial frame (for visuals). Relative to the
        carrier, the sun-planet external mesh gives
        w_planet_rel = -(w_sun - w_carrier) * N_sun/N_planet."""
        np = self.gear_planet.teeth
        if np == 0:
            return 0.0
        return carrier_omega - (sun_omega - carrier_omega) * self.gear_sun.teeth / np

    def step(self, dt: float = DT) -> None:
        if self.won:
            return
        s = self.state

        # Not assemblable: the set can't be built; surface the diagnostic and
        # hold still (same gate as 2.2).
        if not self.assemblable:
            s.t += dt
            self.last_diagnostic = diagnose_assemblable(
                self.gear_sun.teeth, self.gear_ring.teeth, self.num_planets
            )
            return

        tau_sun = self._motor_torque(s.sun_omega)
        self.applied_torque = tau_sun
        # Reflect to the carrier (the rod). Ring-fixed: positive sun torque
        # lifts the rod (positive carrier angle), so sign follows the reduction.
        r = self.reduction_ratio
        tau_out = tau_sun * r

        # Gravity (restoring toward θ=0) + damping (transient). gravity_torque()
        # returns +amplitude*sin(θ); negate for the dynamics.
        tau_grav = -self.gravity_torque(s.carrier_angle)
        tau_damp = -self.damping * s.carrier_omega

        # No-overshoot cap (hard stop at ~horizontal): if the reflected stall
        # torque would hold the rod at/above 90° (equilibrium sin θ >= 1) the
        # rod pins at the hard stop with zero velocity — no energy past 90°.
        cap_angle = math.pi / 2.0 - 1e-3
        s.overspeed = False
        if tau_out > 0.0 and tau_out >= self.gravity_torque_amplitude - 1e-9:
            s.carrier_omega = 0.0
            s.carrier_angle = cap_angle
            s.sun_omega = 0.0
            s.overspeed = True
            s.t += dt
            self._check_win()
            return

        alpha_out = (tau_out + tau_grav + tau_damp) / self._reflected_inertia_out()
        new_out_omega = s.carrier_omega + alpha_out * dt
        new_out_angle = s.carrier_angle + new_out_omega * dt
        # Hard-stop at the cap: clamp this step's angle and kill velocity.
        if new_out_angle >= cap_angle:
            new_out_angle = cap_angle
            new_out_omega = 0.0
            s.overspeed = tau_out > 0.0
        # Lower bound: the rod can't swing below straight-down.
        if new_out_angle < 0.0:
            new_out_angle = 0.0
            if new_out_omega < 0.0:
                new_out_omega = 0.0
        s.carrier_omega = new_out_omega
        s.carrier_angle = new_out_angle
        # Sun speed follows the carrier through the reduction
        # (w_sun = w_carrier * reduction, ring-fixed).
        s.sun_omega = s.carrier_omega * r
        s.sun_angle += s.sun_omega * dt
        # Ring & planet for visuals (ring pinned in ring-fixed mode).
        s.ring_omega = 0.0 if self.mode == "ring_fixed" else 0.0
        s.planet_omega = self._planet_spin(s.sun_omega, s.carrier_omega)
        s.planet_angle += s.planet_omega * dt
        s.t += dt
        self._check_win()

    def _check_win(self) -> None:
        s = self.state
        # Over-torque: the rod pinned at the horizontal cap (an overshoot — the
        # rod went past the target, all the way to ~90°). Lever: voltage/ratio.
        if s.overspeed:
            s.settled_time = 0.0
            self.last_diagnostic = Diagnostic(
                kind=DiagKind.OVERSHOOT,
                message=(
                    f"Rod pinned at ~90° — the motor torque ({self.motor_stall_torque_out:.2f} N·m "
                    f"at the carrier) exceeds what gravity can balance. The rod would flip."
                ),
                hint=(
                    "Too much torque for this rod. Lower the voltage, or reduce "
                    "the reduction (smaller ring / larger sun) so the equilibrium "
                    "lands below horizontal."
                ),
            )
            return
        # Must be settled (at rest) before judging the angle.
        if abs(s.carrier_omega) > SETTLED_OMEGA:
            s.settled_time = 0.0
            self.last_diagnostic = None
            return
        # Settled: judge the angle.
        diag = diagnose_angle(s.carrier_angle, self.target_angle, self.angle_tolerance)
        if diag is None:
            s.settled_time += DT
            if s.settled_time >= self.settle_time_s:
                self.won = True
                self.last_diagnostic = None
        else:
            s.settled_time = 0.0
            self.last_diagnostic = diag

    def summary(self) -> dict:
        return {
            "level": "2.3",
            "t": self.state.t,
            "driver_rpm": self.driver_rpm,
            "driven_rpm": self.driven_rpm,
            "output_rpm": self.output_rpm,
            "sun_rpm": self.sun_rpm,
            "carrier_rpm": self.carrier_rpm,
            "ring_rpm": self.ring_rpm,
            "planet_rpm": self.planet_rpm,
            "intermediate_rpm": self.carrier_rpm,  # alias for level_state
            "link_angle": self.link_angle,
            "link_angle_deg": self.link_angle_deg,
            "target_angle": self.target_angle,
            "target_angle_deg": self.target_angle_deg,
            "target_driven_rpm": 0.0,  # angle target, not rpm
            "target_sign": self.target_sign,
            "voltage": self.applied_voltage,
            "torque": self.applied_torque,
            "load_torque": self.gravity_torque(self.state.carrier_angle),
            "target_load_torque": self.gravity_torque(self.target_angle),
            "reflected_load": self.motor_stall_torque_out,
            "motor_side_load": self.motor_stall_torque_sun,
            "output_torque": self.motor_stall_torque_out,
            "reduction_ratio": self.reduction_ratio,
            "total_ratio": abs(self.reduction_ratio),  # alias for level_state
            "target_ratio": abs(self.reduction_ratio),
            "mode": self.mode,
            "assemblable": self.assemblable,
            "overspeed": self.state.overspeed,
            "stalled": False,
            "meshed": self.meshed,
            "won": self.won,
            "teeth_sun": self.gear_sun.teeth,
            "teeth_planet": self.gear_planet.teeth,
            "teeth_ring": self.gear_ring.teeth,
            "driver_teeth": self.gear_sun.teeth,  # alias for level_state
            "driven_teeth": self.gear_ring.teeth,  # alias for level_state
            "num_planets": self.num_planets,
            "rod_mass": self.rod_mass,
            "rod_length": self.rod_length,
            "diagnostic": self.last_diagnostic.to_dict() if self.last_diagnostic else None,
        }


def solve_driving_voltage_2_3(
    target_angle_deg: float,
    reduction: float,
    rod_mass: float = ROD_MASS,
    rod_length: float = ROD_LENGTH,
    gravity: float = GRAVITY,
    kt: float = KT,
    resistance: float = RESISTANCE,
) -> float:
    """Voltage to hold the rod at target_angle (open-loop equilibrium).

    At settle, motor stall torque reflected to the carrier equals gravity:
        kt * V / R * reduction = m*g*(L/2)*sin(θ)
    =>  V = R * m*g*(L/2)*sin(θ) / (kt * reduction)
    """
    if kt <= 0 or reduction <= 0:
        return float("inf")
    theta = math.radians(target_angle_deg)
    if math.sin(theta) <= 0.0:
        return 0.0
    tau_needed = rod_mass * gravity * (rod_length * 0.5) * math.sin(theta)
    return resistance * tau_needed / (kt * reduction)


if __name__ == "__main__":
    lvl = JointLevel()
    print(
        f"target {lvl.target_angle_deg:.0f}°; reduction {abs(lvl.reduction_ratio):.1f}:1 "
        f"(sun N{lvl.gear_sun.teeth} / ring N{lvl.gear_ring.teeth}, "
        f"planet N{lvl.gear_planet.teeth} derived, mode {lvl.mode})"
    )
    v = solve_driving_voltage_2_3(
        lvl.target_angle_deg, abs(lvl.reduction_ratio), lvl.rod_mass, lvl.rod_length
    )
    print(
        f"solver V = {v:.3f} (gravity hold torque {lvl.gravity_torque(lvl.target_angle):.3f} N·m)"
    )
    lvl.set_voltage(v)
    for _ in range(int(8.0 / DT)):
        lvl.step()
    print(
        f"after 8s: θ={lvl.link_angle_deg:.2f}° (target {lvl.target_angle_deg:.0f}°), "
        f"settled={abs(lvl.state.carrier_omega) < SETTLED_OMEGA}, "
        f"won={lvl.won}, overspeed={lvl.state.overspeed}, diag={lvl.last_diagnostic}"
    )
