"""Act 2.2 — Planetary gearbox.

A *planetary* (epicyclic) gearset has three co-axial members — sun, ring,
carrier — and a set of planet gears that idler between the sun (external
mesh) and the ring (internal mesh). Grounding one member and driving a
second leaves the third as the output, so the SAME gearset yields three
different ratios. That compactness is why planetaries are the standard
gearbox inside real robot joints.

The Willis equation ties the three member speeds once one is held still:

    (w_sun - w_carrier) / (w_ring - w_carrier) = -N_ring / N_sun

The minus sign is the two-mesh geometry: sun->planet is an external mesh
(flips sign), planet->ring is an internal mesh (does not), so *relative to
the carrier* the sun and ring counter-rotate.

Three operating modes (input is always the sun = motor shaft):

- ``ring_fixed`` (default): ring pinned, sun drives, carrier out.
    w_C = w_S * N_S/(N_S+N_R)  =>  reduction = 1 + N_R/N_S  (same direction).
    The classic robot-joint reducer.
- ``sun_fixed``: sun pinned, ring drives, carrier out.
    w_C = w_R * N_R/(N_S+N_R)  =>  reduction (ring->carrier) = 1 + N_S/N_R.
    (The motor drives the sun, so this mode requires driving the ring instead;
    surfaced for diagnostics / teaching.)
- ``carrier_fixed``: carrier pinned, sun drives, ring out — a REVERSING box.
    w_R = -w_S * N_S/N_R  =>  output/input = -N_R/N_S (opposite direction).
    Used in robot wrists to flip direction compactly.

Mechanics (reuses the 1.4/2.1 motor + reflected-load engine, now on the sun):
- DC motor on the sun: tau_motor = Kt * (V - Kb*w_sun)/R, clamped to torque_limit.
- Reflected load: an output torque tau_load reflects back to the sun as
    tau_reflected = tau_load / reduction
  (a bigger reduction shrinks the load the motor fights — same lesson as 1.4/2.1).
- No back-driving: if the motor can't sustain motion the sun pins at zero
  (same Coulomb-load logic as 1.4; prevents the zero-crossing flicker).

Win condition: reduction magnitude == target_ratio (±tol), output RPM at
target ±5%, direction == target_sign for the chosen mode, load at target
±2.5%, no stall, AND the set is physically assemblable. Assemblability is the
GEOMETRIC constraint ``N_ring = N_sun + 2*N_planet`` (the planet is determined
by the sun + ring: ``N_planet = (N_ring - N_sun) / 2``, must be a catalog
gear) followed by the 3-planet slotting rule ``(N_ring - N_sun) % 3 == 0``.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from robot_forge.levels.diagnostics import (
    DiagKind,
    Diagnostic,
    diagnose_assemblable,
    diagnose_load,
    diagnose_rpm,
    diagnose_stall,
)
from robot_forge.sim.gears import SpurGear, planetary_gear_ratio

# Motor constants — same small DC motor as 1.2–2.1.
KT = 0.05  # N*m/A
KB = 0.05  # V*s/rad
RESISTANCE = 1.0  # ohm
TORQUE_LIMIT = 2.0  # N*m
MAX_VOLTAGE = 24.0  # V

# Mechanical defaults.
DEFAULT_INERTIA = 0.01  # kg*m^2 — motor shaft + sun gear
DEFAULT_DAMPING = 0.05  # N*m*s/rad — bearing drag on the sun

# The job. Target reduction 6:1 — the catalog's maximum planetary reduction,
# reachable by exactly one assemblable set in ring-fixed mode: sun N12, planet
# N24 (derived: (60-12)/2), ring N60; ratio 1 + 60/12 = 6.
# Default gears: sun N24 / ring N48 -> planet (48-24)/2 = N12, assemblable
# (diff 24, even, /3) but only 3:1, so the level opens as "wrong ratio" (the
# player must grow the ring and shrink the sun). Starting assemblable gives a
# clean first impression: a spinning 3-planet set, not a "can't assemble" wall.
DEFAULT_TARGET_RATIO = 6.0
DEFAULT_TEETH_SUN = 24
DEFAULT_TEETH_PLANET = 12  # derived from (DEFAULT_TEETH_RING - DEFAULT_TEETH_SUN) / 2
DEFAULT_TEETH_RING = 48
DEFAULT_NUM_PLANETS = 3
DEFAULT_MODE = "ring_fixed"

# A light load: the point of 2.2 is the ratio/mode, not the load. (1.4/2.1
# already taught load + stall.)
DEFAULT_TARGET_LOAD_TORQUE = 0.5
DEFAULT_LOAD_TORQUE = 0.0
DEFAULT_TARGET_OUT_RPM = 10.0

RPM_TOLERANCE_FRAC = 0.05  # ±5%
LOAD_TOLERANCE_FRAC = 0.025  # ±2.5%
RATIO_TOLERANCE = 1e-9  # exact — tooth counts are integers
SETTLE_TIME_S = 1.0
DT = 0.01

# Ring-fixed (default) and sun-fixed output (carrier) spin the SAME direction
# as the sun (+1); carrier-fixed (ring out) reverses (-1). The level pins the
# winning mode as ring-fixed, so the target sign is +1.
DEFAULT_TARGET_SIGN = 1

# The three modes the player can ground. Order matches the HUD selector.
MODES: tuple[str, ...] = ("ring_fixed", "sun_fixed", "carrier_fixed")


@dataclass
class PlanetaryState:
    sun_omega: float = 0.0
    sun_angle: float = 0.0
    carrier_omega: float = 0.0
    carrier_angle: float = 0.0
    ring_omega: float = 0.0
    ring_angle: float = 0.0
    # Planet self-spin (inertial). Planets ride the carrier (orbit at carrier
    # rate) AND spin on their own studs; the spin relative to the carrier is
    # -(w_sun - w_carrier) * N_sun/N_planet (external sun-planet mesh flips).
    # Surfaced as joint id 3 so the Godot planet visuals can self-rotate.
    planet_omega: float = 0.0
    planet_angle: float = 0.0
    t: float = 0.0
    settled_time: float = 0.0
    stalled: bool = False


class PlanetaryGearLevel:
    """Same gears, three ratios: pick the member to ground."""

    def __init__(
        self,
        teeth_sun: int = DEFAULT_TEETH_SUN,
        teeth_planet: int = DEFAULT_TEETH_PLANET,
        teeth_ring: int = DEFAULT_TEETH_RING,
        num_planets: int = DEFAULT_NUM_PLANETS,
        mode: str = DEFAULT_MODE,
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
        self.gear_sun = SpurGear(teeth_sun)
        self.gear_planet = SpurGear(teeth_planet)
        self.gear_ring = SpurGear(teeth_ring)
        self.num_planets = num_planets
        self.mode = mode if mode in MODES else DEFAULT_MODE
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
        self.state = PlanetaryState()
        self.applied_voltage: float = 0.0
        self.applied_torque: float = 0.0
        self.reflected_load: float = 0.0
        self.won: bool = False
        self.last_diagnostic: Diagnostic | None = None

    # --- readouts ---------------------------------------------------------

    @property
    def reduction_ratio(self) -> float:
        """Signed |output|/|input|... actually the signed OUTPUT/INPUT speed
        ratio. Magnitude > 1 is a reduction (output slower than the sun);
        negative means the output reverses the sun's direction.
        """
        return planetary_gear_ratio(self.gear_sun, self.gear_ring, self.mode)

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
        """Planet self-spin (inertial frame) — planets ride the carrier AND
        spin on their own studs. Read by the Godot planet visuals."""
        return self.state.planet_omega * 60.0 / (2.0 * math.pi)

    @property
    def output_rpm(self) -> float:
        """The free member's RPM: carrier in ring/sun-fixed, ring in carrier-fixed."""
        if self.mode == "carrier_fixed":
            return self.ring_rpm
        return self.carrier_rpm

    @property
    def meshed(self) -> bool:
        """Planetary gears are assumed meshed when assemblable."""
        return self.assemblable

    @property
    def assemblable(self) -> bool:
        """True if the set is physically buildable with ``num_planets`` planets.

        Two conditions: (1) the GEOMETRIC constraint ``N_ring = N_sun +
        2*N_planet`` — the planet is determined by the sun and ring
        (``N_planet = (N_ring - N_sun)/2``) and must be a catalog gear; (2) the
        SLOTTING rule ``(N_ring - N_sun) % num_planets == 0`` so the chosen
        planet count coexists without tooth collision. The detailed verdict is
        in ``diagnose_assemblable``; this is the boolean the win check gates on.
        """
        return (
            diagnose_assemblable(
                self.gear_sun.teeth,
                self.gear_ring.teeth,
                self.num_planets,
            )
            is None
        )

    @property
    def derived_planet_teeth(self) -> int:
        """The planet tooth count the sun+ring force: (N_ring - N_sun) / 2.

        Set by ``set_gears`` (the player picks sun + ring; the planet is
        derived, not chosen). May be non-catalog/odd for invalid sets — that's
        what ``assemblable`` catches.
        """
        return (self.gear_ring.teeth - self.gear_sun.teeth) // 2

    @property
    def output_torque(self) -> float:
        """Torque at the output member = the load when running; at stall the
        motor's torque multiplied by the reduction (torque multiplication)."""
        if self.state.stalled:
            return self._motor_stall_torque() * abs(self.reduction_ratio)
        return self.load_torque

    @property
    def motor_side_load(self) -> float:
        """Load as the motor feels it — reflected through the reduction."""
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

    def set_gears(self, teeth_sun: int, teeth_ring: int) -> None:
        """Pick the sun and ring tooth counts; the planet is DERIVED.

        The geometric constraint ``N_ring = N_sun + 2*N_planet`` means the
        planet is determined by the sun and ring: ``N_planet =
        (N_ring - N_sun) / 2``. The player chooses only sun + ring; an invalid
        pair (odd difference, or a derived planet not in the catalog, or a
        slotting failure) is caught by ``assemblable`` and surfaces a
        NOT_ASSEMBLABLE diagnostic. We still build a ``SpurGear`` for the
        derived planet (clamped to a sane value) so the kinematics don't crash
        on a bad pick before the diagnostic lands.
        """
        self.gear_sun = SpurGear(teeth_sun)
        self.gear_ring = SpurGear(teeth_ring)
        diff = teeth_ring - teeth_sun
        planet_teeth = diff // 2 if diff > 0 and diff % 2 == 0 else 12
        # Guard against a derived planet that isn't a positive count; the
        # assemblable/diagnostic path reports the real problem, this just
        # keeps _planet_spin from dividing by zero.
        if planet_teeth <= 0:
            planet_teeth = 12
        self.gear_planet = SpurGear(planet_teeth)

    def set_mode(self, mode: str) -> None:
        """Ground one member: 'ring_fixed', 'sun_fixed', or 'carrier_fixed'."""
        if mode in MODES:
            self.mode = mode

    def set_load(self, load_torque: float) -> None:
        self.load_torque = max(0.0, load_torque)

    # --- motor / load math ------------------------------------------------

    def _reduction_magnitude(self) -> float:
        return abs(self.reduction_ratio)

    def _reflected_load(self) -> float:
        """Output load reflected to the sun through the reduction magnitude.

        Power is conserved across an ideal gearset: tau_out * w_out = tau_in *
        w_in (modulo the gearset), so with reduction R = |w_in/w_out| the load
        reflects as tau_load / R. A bigger reduction shrinks the sun-side load.
        """
        r = self._reduction_magnitude()
        if r <= 0.0:
            return self.load_torque
        return self.load_torque / r

    def _motor_stall_torque(self) -> float:
        if self.kt <= 0.0 or self.resistance <= 0.0:
            return 0.0
        return max(
            -self.torque_limit,
            min(self.torque_limit, self.kt * self.applied_voltage / self.resistance),
        )

    def _motor_torque(self, omega_sun: float) -> float:
        if self.kt <= 0.0 or self.resistance <= 0.0:
            return 0.0
        i = (self.applied_voltage - self.kb * omega_sun) / self.resistance
        tau = self.kt * i
        return max(-self.torque_limit, min(self.torque_limit, tau))

    def _kinematics(self, sun_omega: float) -> tuple[float, float]:
        """Carrier & ring omega from the sun omega via the Willis equation,
        given the grounded member (self.mode). Returns (carrier_omega, ring_omega).
        """
        ns = self.gear_sun.teeth
        nr = self.gear_ring.teeth
        if self.mode == "ring_fixed":
            # w_C = w_S * N_S/(N_S+N_R); w_R = 0.
            carrier = sun_omega * ns / (ns + nr)
            ring = 0.0
        elif self.mode == "sun_fixed":
            # Sun grounded => w_S = 0. The motor would have to drive the ring;
            # here the sun is the input axis, so with sun pinned the carrier
            # and ring are linked by w_R = -w_C*(N_S+N_R... ) — but with w_S=0
            # and one DOF left, driving the ring gives w_C = w_R*N_R/(N_S+N_R).
            # Since the sun is the motor shaft and it's pinned, the train is
            # effectively stationary unless the ring is driven. We report the
            # ring-driven kinematics: carrier = ring*N_R/(N_S+N_R); ring free.
            # The motor (sun) is pinned, so sun_omega must be 0 here.
            carrier = 0.0
            ring = 0.0
        else:  # carrier_fixed
            # w_C = 0; w_R = -w_S * N_S/N_R.
            carrier = 0.0
            ring = -sun_omega * ns / nr
        return carrier, ring

    def _planet_spin(self, sun_omega: float, carrier_omega: float) -> float:
        """Planet self-spin in the inertial frame.

        The planet rides the carrier (it orbits at the carrier rate) and spins
        on its own stud. Relative to the carrier, the sun-planet external mesh
        gives ``w_planet_rel = -(w_sun - w_carrier) * N_sun/N_planet`` (the
        minus is the external-mesh flip). Inertial spin = carrier + that.
        """
        np = self.gear_planet.teeth
        if np == 0:
            return 0.0
        return carrier_omega - (sun_omega - carrier_omega) * self.gear_sun.teeth / np

    def step(self, dt: float = DT) -> None:
        if self.won:
            return
        s = self.state
        self.reflected_load = self._reflected_load()

        # sun_fixed mode: the sun (motor shaft) is grounded, so the motor can't
        # drive the train through the sun. Pin everything and let the
        # diagnostic explain it.
        if self.mode == "sun_fixed":
            s.sun_omega = 0.0
            s.carrier_omega = 0.0
            s.ring_omega = 0.0
            s.stalled = True
            s.t += dt
            self._check_win()
            return

        tau = self._motor_torque(s.sun_omega)
        self.applied_torque = tau
        eps = 1e-6
        # No-back-drive Coulomb load on the sun (mirrors 1.4/2.1).
        if abs(s.sun_omega) < eps:
            if abs(tau) > self.reflected_load:
                load_sign = 1.0 if tau > 0 else -1.0
                tau_load_eff = self.reflected_load * load_sign
                alpha = (tau - self.damping * s.sun_omega - tau_load_eff) / self.inertia
                s.sun_omega += alpha * dt
                s.stalled = False
            else:
                s.sun_omega = 0.0
                s.stalled = True
        else:
            load_sign = 1.0 if s.sun_omega > 0 else -1.0
            tau_load_eff = self.reflected_load * load_sign
            alpha = (tau - self.damping * s.sun_omega - tau_load_eff) / self.inertia
            new_omega = s.sun_omega + alpha * dt
            if (new_omega > 0) != (s.sun_omega > 0):
                tau_at_zero = self._motor_torque(0.0)
                if abs(tau_at_zero) <= self.reflected_load:
                    s.sun_omega = 0.0
                    s.stalled = True
                else:
                    s.sun_omega = new_omega
                    s.stalled = False
            else:
                s.sun_omega = new_omega
                s.stalled = False
        s.sun_angle += s.sun_omega * dt
        # Epicyclic kinematics: carrier & ring follow the sun via Willis.
        carrier, ring = self._kinematics(s.sun_omega)
        s.carrier_omega = carrier
        s.ring_omega = ring
        s.planet_omega = self._planet_spin(s.sun_omega, s.carrier_omega)
        s.carrier_angle += s.carrier_omega * dt
        s.ring_angle += s.ring_omega * dt
        s.planet_angle += s.planet_omega * dt
        s.t += dt
        self._check_win()

    def _check_win(self) -> None:
        # 1) Not assemblable — can't be built at all; name it first.
        asm_diag = diagnose_assemblable(self.gear_sun.teeth, self.gear_ring.teeth, self.num_planets)
        if asm_diag is not None:
            self.state.settled_time = 0.0
            self.last_diagnostic = asm_diag
            return
        # 2) Stall dominates.
        if self.state.stalled:
            self.state.settled_time = 0.0
            self.last_diagnostic = diagnose_stall(self.reflected_load, self._motor_stall_torque())
            return
        # 3) Ratio must hit the target (exact). The magnitude of the reduction
        #    must equal the target; the sign is handled by the direction check.
        ratio_diag: Diagnostic | None = None
        if abs(abs(self.reduction_ratio) - self.target_ratio) > self.ratio_tolerance:
            ratio_diag = Diagnostic(
                kind=DiagKind.WRONG_RATIO,
                message=(
                    f"Ratio {abs(self.reduction_ratio):.3f}:1, target "
                    f"{self.target_ratio:.1f}:1 (mode {self.mode}, "
                    f"sun N{self.gear_sun.teeth} / ring N{self.gear_ring.teeth})."
                ),
                hint=self._ratio_hint(),
            )
        # 4) Load must match the target job.
        load_diag = diagnose_load(self.load_torque, self.target_load_torque, self.load_tolerance)
        # 5) Output speed.
        speed_diag = diagnose_rpm(
            abs(self.output_rpm), abs(self.target_out_rpm), self.rpm_tolerance
        )
        # 6) Direction: ring/sun-fixed output (carrier) follows the sun (+1);
        #    carrier-fixed output (ring) reverses (-1). The target sign is +1
        #    for the winning (ring-fixed) config.
        dir_diag: Diagnostic | None = None
        measured = (
            self.state.carrier_omega if self.mode != "carrier_fixed" else self.state.ring_omega
        )
        if measured != 0 and (1 if measured > 0 else -1) != self.target_sign:
            dir_diag = Diagnostic(
                kind=DiagKind.WRONG_DIRECTION,
                message=(
                    f"Output spins {'CW' if measured < 0 else 'CCW'}, "
                    f"target {'CW' if self.target_sign < 0 else 'CCW'} "
                    f"(mode {self.mode})."
                ),
                hint=(
                    "Carrier-fixed mode reverses the output (ring spins "
                    "opposite the sun). Switch to ring-fixed for same-direction "
                    "output, or flip the motor voltage."
                ),
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

    def _ratio_hint(self) -> str:
        """Teach that the ratio depends on the mode AND the tooth counts."""
        ns = self.gear_sun.teeth
        nr = self.gear_ring.teeth
        if self.mode == "ring_fixed":
            return (
                f"Ring-fixed ratio = 1 + N_ring/N_sun = 1 + {nr}/{ns} = "
                f"{1 + nr / ns:.3f}. For {self.target_ratio:.0f}:1 you need "
                f"N_ring/N_sun = {self.target_ratio - 1:.0f}, e.g. sun N12 / ring N60."
            )
        if self.mode == "sun_fixed":
            return (
                f"Sun-fixed ratio (ring->carrier) = 1 + N_sun/N_ring = "
                f"1 + {ns}/{nr}. The motor drives the SUN, so with the sun "
                "grounded the train can't be driven this way — switch to "
                "ring-fixed or carrier-fixed."
            )
        return (
            f"Carrier-fixed ratio = N_ring/N_sun = {nr}/{ns} = {nr / ns:.3f} "
            f"(reversing). For {self.target_ratio:.0f}:1 here you'd need "
            f"N_ring/N_sun = {self.target_ratio:.0f}."
        )

    def summary(self) -> dict:
        return {
            "level": "2.2",
            "t": self.state.t,
            "driver_rpm": self.sun_rpm,
            "sun_rpm": self.sun_rpm,
            "carrier_rpm": self.carrier_rpm,
            "ring_rpm": self.ring_rpm,
            "planet_rpm": self.planet_rpm,
            "intermediate_rpm": self.carrier_rpm,  # alias: the "middle" member
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
            "reduction_ratio": self.reduction_ratio,
            "total_ratio": abs(self.reduction_ratio),  # alias for level_state
            "target_ratio": self.target_ratio,
            "mode": self.mode,
            "num_planets": self.num_planets,
            "assemblable": self.assemblable,
            "stalled": self.state.stalled,
            "meshed": self.meshed,
            "won": self.won,
            "teeth_sun": self.gear_sun.teeth,
            "teeth_planet": self.gear_planet.teeth,
            "teeth_ring": self.gear_ring.teeth,
            "driver_teeth": self.gear_sun.teeth,  # alias for level_state
            "driven_teeth": self.gear_ring.teeth,  # alias for level_state
            "teeth_a": self.gear_sun.teeth,  # alias so compound HUD paths work
            "teeth_b": self.gear_planet.teeth,
            "teeth_c": self.gear_planet.teeth,
            "teeth_d": self.gear_ring.teeth,
            "diagnostic": self.last_diagnostic.to_dict() if self.last_diagnostic else None,
        }


def solve_driving_voltage_2_2(
    target_out_rpm: float,
    reduction: float,
    load_torque: float,
    damping: float = DEFAULT_DAMPING,
    kt: float = KT,
    kb: float = KB,
    resistance: float = RESISTANCE,
) -> float:
    """Voltage to hold the OUTPUT at target_rpm against the load (ring-fixed).

    Output omega = sun_omega / reduction  =>  sun_omega = omega_out * reduction.
    At steady state: tau_motor(omega_sun) = b*omega_sun + tau_reflected
        kt*(V - kb*omega_sun)/R = b*omega_sun + load/reduction
    =>  V = R*(b*omega_sun + load/reduction)/kt + kb*omega_sun
    """
    if not (kt > 0) or reduction <= 0:
        return float("inf")
    omega_out = target_out_rpm * 2.0 * math.pi / 60.0
    omega_sun = omega_out * reduction
    tau_reflected = load_torque / reduction
    tau_needed = damping * omega_sun + tau_reflected
    return resistance * tau_needed / kt + kb * omega_sun


if __name__ == "__main__":
    lvl = PlanetaryGearLevel()
    print(
        f"target ratio {lvl.target_ratio}:1; current {abs(lvl.reduction_ratio):.3f}:1 "
        f"(1:1 default, mode {lvl.mode})"
    )
    # Winning set: sun N12, ring N60 -> planet N24 (derived), catalog's max planetary.
    lvl.set_gears(12, 60)
    lvl.set_mode("ring_fixed")
    lvl.set_load(lvl.target_load_torque)
    v = solve_driving_voltage_2_2(
        lvl.target_out_rpm, abs(lvl.reduction_ratio), lvl.target_load_torque
    )
    print(f"N12/N24/N60 ring-fixed = {abs(lvl.reduction_ratio):.1f}:1; solver V = {v:.2f}")
    lvl.set_voltage(abs(v) * 1.01)
    for _ in range(int(12.0 / DT)):
        lvl.step()
    print(
        f"after 12s: out={lvl.output_rpm:.2f} RPM (target {lvl.target_out_rpm}), "
        f"sun={lvl.sun_rpm:.1f}, carrier={lvl.carrier_rpm:.1f}, ring={lvl.ring_rpm:.1f}, "
        f"ratio={abs(lvl.reduction_ratio):.1f}:1, assemblable={lvl.assemblable}, "
        f"stalled={lvl.state.stalled}, won={lvl.won}, diag={lvl.last_diagnostic}"
    )
