"""Diagnostic engine: turn a failed attempt into a teaching message.

Each diagnostic is a small structured record with a category, a short human message,
and (optionally) a hint. Levels call `diagnose(...)` and surface the result to the UI.
"""

from __future__ import annotations

import math
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
    STALLED = "stalled"
    LOAD_MISMATCH = "load_mismatch"
    NOT_ASSEMBLABLE = "not_assemblable"


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


def diagnose_rpm_shaft(measured: float, target: float, tol: float) -> Diagnostic | None:
    """Like diagnose_rpm, but with hints tailored to a single spinning shaft
    (Act 1.1) — no gear vocabulary. Used so the gear-level hints in
    diagnose_rpm don't leak into the shaft level. Copy references voltage and
    the tunable motor params (Kt, Kb, R, I, b) since 1.1 exposes them.
    """
    err = measured - target
    if abs(err) <= tol:
        return None
    if err < 0:
        return Diagnostic(
            kind=DiagKind.TOO_SLOW,
            message=f"Shaft: {measured:.1f} RPM, target {target:.1f} RPM ({err:+.1f}).",
            hint="Increase voltage, raise Kt (torque constant), reduce bearing "
            "drag (b), or lower resistance (R). The shaft takes time to spin "
            "up — inertia (I) affects how fast, not where it settles.",
        )
    return Diagnostic(
        kind=DiagKind.TOO_FAST,
        message=f"Shaft: {measured:.1f} RPM, target {target:.1f} RPM ({err:+.1f}).",
        hint="Reduce voltage to slow the motor down. Back-EMF (Kb) also caps "
        "top speed — raise Kb for a lower terminal RPM.",
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


def diagnose_angle(measured: float, target: float, tol: float) -> Diagnostic | None:
    """Act 2.3 — the rod's settled angle missed the target (open-loop balance).

    The rod finds an equilibrium where the motor's torque (through the
    reduction) balances gravity; the player tunes the *voltage* (and the
    gear ratio) to push that equilibrium onto the target angle. This is NOT
    a control problem (no Kp/Kd — that's Act 4.1): the levers are voltage
    and ratio. Undershoot = too little torque for gravity's pull; overshoot
    = too much.
    """
    err = measured - target
    if abs(err) <= tol:
        return None
    if err < 0:
        return Diagnostic(
            kind=DiagKind.UNDERSHOOT,
            message=(
                f"Rod settled at {math.degrees(measured):.1f}°, target "
                f"{math.degrees(target):.1f}° ({err * 180 / math.pi:+.1f}°)."
            ),
            hint=(
                "Not enough torque to lift the rod to the target. Raise the "
                "voltage, or increase the reduction (larger driven / smaller "
                "driver) — the rod settles where motor torque balances gravity."
            ),
        )
    return Diagnostic(
        kind=DiagKind.OVERSHOOT,
        message=(
            f"Rod settled at {math.degrees(measured):.1f}°, target "
            f"{math.degrees(target):.1f}° ({err * 180 / math.pi:+.1f}°)."
        ),
        hint=(
            "Too much torque — the rod climbed past the target. Lower the "
            "voltage, or reduce the reduction (smaller driven / larger driver)."
        ),
    )


def diagnose_tip_position(
    tip_x: float,
    tip_y: float,
    target_x: float,
    target_y: float,
    target_radius: float,
    joint_1_deg: float = 0.0,
    joint_2_deg: float = 0.0,
) -> Diagnostic | None:
    """Act 2.4 — the 2-link arm's settled tip missed the target region.

    This is an open-loop *equilibrium* level (no PD — that's Act 4.1): the
    player tunes a **voltage** (and the **ratio**) per joint, and the arm
    settles where the motor's reflected torque balances the coupled gravity.
    The lever is the same as 2.3, but now there are TWO coordinated joints —
    joint 1's hold torque depends on where joint 2 sits (the shoulder carries
    the elbow), so a single-joint miss usually means retuning *both*.

    Returns a teaching diagnostic if the tip is outside the region, else None.
    The hint names voltage/ratio (not Kp/Kd) and flags the coupling.
    """
    dx = tip_x - target_x
    dy = tip_y - target_y
    dist = math.hypot(dx, dy)
    if dist <= target_radius:
        return None
    # Which side of the region did the tip land? Frame as under/overshoot on
    # the radial direction so the hint points at a concrete lever.
    return Diagnostic(
        kind=DiagKind.UNDERSHOOT,
        message=(
            f"Tip settled at ({tip_x:.2f}, {tip_y:.2f}); target region "
            f"({target_x:.2f}, {target_y:.2f}) r={target_radius:.2f} "
            f"(missed by {dist - target_radius:.2f}). "
            f"Joints: {joint_1_deg:.1f}° / {joint_2_deg:.1f}°."
        ),
        hint=(
            "The arm settles where each joint's motor torque balances gravity. "
            "Raise the voltage on the joint that's short of its mark, or "
            "increase that joint's reduction for more lift at the same voltage. "
            "The shoulder's load depends on where the elbow sits — retune both "
            "joints together, not one at a time."
        ),
    )


def slip_diagnostic(slip_detected: bool) -> Diagnostic | None:
    if not slip_detected:
        return None
    return Diagnostic(
        kind=DiagKind.SLIPPED,
        message="The gripper slipped on the object.",
        hint="Slow the approach or use a softer grip. Lower acceleration = less inertial pull.",
    )


def diagnose_stall(load_torque: float, motor_stall_torque: float) -> Diagnostic | None:
    """Act 1.4 — the motor can't start the load.

    A DC motor's stall (starting) torque is ``Kt * V / R``, clamped to
    ``torque_limit``. If the load reflected back to the driver exceeds that,
    the train never turns. Return a teaching diagnostic; None if the motor is
    strong enough to start.
    """
    if load_torque <= motor_stall_torque:
        return None
    return Diagnostic(
        kind=DiagKind.STALLED,
        message=(
            f"Stalled: load needs {load_torque:.2f} N·m at the motor, "
            f"but it can only muster {motor_stall_torque:.2f} N·m to start."
        ),
        hint=(
            "Gear down (smaller driver / larger driven) to multiply torque at "
            "the output, or raise the motor voltage. A reduction trades speed "
            "for torque — that's why gearboxes exist."
        ),
    )


def diagnose_load(measured_torque: float, target_torque: float, tol: float) -> Diagnostic | None:
    """Act 1.4 — the applied load must match the target (you're driving THIS job)."""
    err = measured_torque - target_torque
    if abs(err) <= tol * max(abs(target_torque), 1.0):
        return None
    return Diagnostic(
        kind=DiagKind.LOAD_MISMATCH,
        message=(f"Output torque: {measured_torque:.2f} N·m, target {target_torque:.2f} N·m."),
        hint="Set the load to the target torque — you're driving this specific job.",
    )


def diagnose_assemblable(
    sun_teeth: int, ring_teeth: int, num_planets: int, catalog: set[int] | None = None
) -> Diagnostic | None:
    """Act 2.2 — a planetary set must be physically assemblable.

    Two conditions, in order of severity:

    1. **Geometric constraint (primary).** A planet of ``N_p`` teeth must
       simultaneously mesh with the sun (external) and the ring (internal),
       which forces ``N_ring = N_sun + 2 * N_planet``. Given the sun and ring
       the planet is *determined*: ``N_planet = (N_ring - N_sun) / 2``. This
       must be a positive even split AND a real gear in the catalog. Sets that
       fail this can't fit a planet at all — no catalogue gear bridges them.

    2. **Slotting (secondary).** For ``num_planets`` planets to coexist
       equally spaced without tooth collision, ``(N_ring - N_sun)`` must
       divide evenly by ``num_planets`` (the standard 3-planet assembly rule).
       A set that passes geometry but fails slotting can fit ONE planet but
       not the chosen count side-by-side.

    Returns a teaching diagnostic if either fails, else None. ``catalog`` is the
    set of available tooth counts (defaults to the project's catalog); the
    derived planet must land in it.
    """
    if catalog is None:
        from robot_forge.sim.gears import CATALOG  # local import: avoid cycle

        catalog = {g.teeth for g in CATALOG.values()}

    if num_planets <= 0 or ring_teeth <= sun_teeth:
        return Diagnostic(
            kind=DiagKind.NOT_ASSEMBLABLE,
            message=(
                f"Sun N{sun_teeth} / ring N{ring_teeth} can't be built: "
                f"the ring must have MORE teeth than the sun."
            ),
            hint="Pick a ring with more teeth than the sun.",
        )

    diff = ring_teeth - sun_teeth
    # 1) Geometric: the planet is determined by sun + ring.
    if diff % 2 != 0:
        return Diagnostic(
            kind=DiagKind.NOT_ASSEMBLABLE,
            message=(
                f"Sun N{sun_teeth} / ring N{ring_teeth} can't fit a planet: "
                f"(N_ring - N_sun) = {diff} is odd, but a planet needs "
                f"N_planet = (N_ring - N_sun) / 2 teeth."
            ),
            hint=(
                "N_ring - N_sun must be even (the planet bridges sun and ring: "
                "N_ring = N_sun + 2*N_planet). Try sun N12 / ring N36 or N60."
            ),
        )
    planet_teeth = diff // 2
    if planet_teeth not in catalog:
        return Diagnostic(
            kind=DiagKind.NOT_ASSEMBLABLE,
            message=(
                f"Sun N{sun_teeth} / ring N{ring_teeth} needs a planet of "
                f"N{planet_teeth} teeth (=(N_ring - N_sun)/2), which isn't in "
                f"the catalog."
            ),
            hint=(
                "The planet is determined by the sun and ring: "
                "N_planet = (N_ring - N_sun) / 2. Pick a sun+ring whose half-"
                "difference is a catalog count (12, 16, 20, 24, 30, 36, 40, "
                "48, or 60). E.g. sun N12 / ring N60 -> planet N24."
            ),
        )
    # 2) Slotting: the chosen planet count must coexist without collision.
    if diff % num_planets != 0:
        return Diagnostic(
            kind=DiagKind.NOT_ASSEMBLABLE,
            message=(
                f"Sun N{sun_teeth} / ring N{ring_teeth} fits a planet (N{planet_teeth}) "
                f"but {num_planets} planets won't coexist: (N_ring - N_sun) = {diff} "
                f"must divide by the planet count ({num_planets})."
            ),
            hint=(
                f"The planet (N{planet_teeth}) fits between sun and ring, but "
                f"{num_planets} of them would collide. Try a sun+ring whose "
                "difference is a multiple of 3 (e.g. sun N12 / ring N60)."
            ),
        )
    return None
