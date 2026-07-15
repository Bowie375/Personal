"""Act 2.4 — Two-link arm (two abstracted joints in series).

Act 2.3 made a gearbox's *output* a joint that moves one link. Here we
**abstract the gearbox away**: the joint is a black-box *actuator* — a
clickable housing whose two knobs are **reduction ratio** and **motor
voltage**, the same two levers the player has tuned since 1.1, now without
the gear mesh to watch. From here on, Act 3+ works with joints, not gears.

Two such joints in series make a planar 2R arm in the **vertical** plane
(joint axes along Z, gravity along −Y). At V=0 both links hang straight
down. The player picks a ratio and a voltage per joint; the arm settles
under gravity + heavy damping at the **coupled equilibrium**. The win is the
tip of link 2 coming to rest inside a pre-marked region in the scene.

The one new idea over 2.3 is **joint coupling**: joint 1's equilibrium load
depends on where joint 2 sits (the shoulder carries the elbow+link-2
weight), so the two voltages can't be tuned independently — they must be
coordinated. The full Lagrangian dynamics are integrated honestly (no
quasi-static cheat), in the over-damped regime so the arm settles
monotonically rather than swinging (an *equilibrium* level — control is
Act 4.1, deferred per design).

Physics (planar 2R arm, RELATIVE joint angles q1 = link 1 from straight
down, q2 = link 2 *relative to* link 1; thin rods mass m, length L,
I = m·L²/12; motor reflected inertia I_mot·r² on each joint diagonal):

    τ_motor_i = Kt·(V_i − Kb·ω_i)/R, clamped to TORQUE_LIMIT    (per joint)
    τ_joint_i = τ_motor_i · r_i                                  (ratio knob)
    M(q2)·q̈ + C(q, q̇)·q̇ + G(q) = τ_joint − B·q̇                (Lagrangian)

At equilibrium ω→0, so back-EMF vanishes and the motor torque is its stall
value: τ_joint_i = Kt·V_i·r_i/R. Equilibrium balances the coupled gravity:
τ_joint_i = G_i(q1, q2), so V_i = G_i(q1,q2)·R/(Kt·r_i). Because G_1 depends
on q2 (shoulder carries the elbow) the voltages couple — moving joint 2
shifts joint 1's hold torque. Hard stops at ±(π/2 − ε) per joint keep both
links from flipping past horizontal (the "always points down" guarantee).
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from robot_forge.levels.diagnostics import (
    Diagnostic,
    diagnose_tip_position,
)

# Motor constants — same small DC motor as 1.2–2.3.
KT = 0.05  # N*m/A
KB = 0.05  # V*s/rad
RESISTANCE = 1.0  # ohm
TORQUE_LIMIT = 2.0  # N*m
MAX_VOLTAGE = 24.0  # V

# Motor shaft + sun gear inertia, reflected through the ratio (I_sun * r²).
DEFAULT_INERTIA_MOTOR = 0.01  # kg*m²

# The two links (thin rods). Same modest mass/length as the 2.3 rod so the
# gravity torques sit in a reachable band for the catalog reductions + motor.
LINK_MASS = 0.5  # kg
LINK_LENGTH = 0.5  # m
GRAVITY = 9.81  # m/s²

# Joint damping (over-damped regime — settle monotonically, no swing).
# Affects ONLY the transient, not the equilibrium: at steady state ω=0 so
# damping torque vanishes. The 2-link arm has a larger coupled inertia than
# the 2.3 single rod; 4.0 keeps the rise monotonic while converging fast
# enough to win inside ~16s at the default target (tuned by sweep).
JOINT_DAMPING = 4.0  # N*m*s/rad

# Hard stop: a joint can't rotate past horizontal (±90°). Gravity always
# restores toward straight-down, so the links can never flip over the top —
# the open-loop no-overshoot-past-horizontal guarantee from 2.3, per joint.
CAP_ANGLE = math.pi / 2.0 - 1e-3  # rad

# Default reductions (one per joint): catalog planetary max is 6:1. Both
# joints default to 6:1 so the solver voltages land comfortably inside 24 V.
DEFAULT_RATIO_1 = 6.0
DEFAULT_RATIO_2 = 6.0
RATIO_CHOICES: tuple[float, ...] = (1.0, 2.0, 3.0, 4.0, 5.0, 6.0)

# The job: bring the tip of link 2 to rest inside a target region. The
# region is a disc in the swing plane; the win needs the tip inside it AND
# both joints settled.
DEFAULT_TARGET_X = 0.775  # world X of region center (link lengths give ~0.775 at 40°/25°)
DEFAULT_TARGET_Y = -0.594  # world Y (below the shoulder pivot)
TARGET_RADIUS = 0.12  # disc radius — generous, this is a coordination level
SETTLE_TIME_S = 1.0
SETTLED_OMEGA = 5e-3  # rad/s — both joints effectively at rest
DT = 0.01


@dataclass
class TwoLinkState:
    # Relative joint angles (rad). q1 = link 1 from straight down; q2 = link 2
    # relative to link 1. Both 0 => arm hangs straight down.
    q1: float = 0.0
    q2: float = 0.0
    # Joint angular velocities (rad/s).
    w1: float = 0.0
    w2: float = 0.0
    t: float = 0.0
    settled_time: float = 0.0
    pinned1: bool = False  # joint 1 hit a hard stop this step
    pinned2: bool = False  # joint 2 hit a hard stop this step


class TwoLinkLevel:
    """Two abstracted joints driving a 2-link arm; bring the tip to a region."""

    def __init__(
        self,
        ratio_1: float = DEFAULT_RATIO_1,
        ratio_2: float = DEFAULT_RATIO_2,
        target_x: float = DEFAULT_TARGET_X,
        target_y: float = DEFAULT_TARGET_Y,
        target_radius: float = TARGET_RADIUS,
        link_mass: float = LINK_MASS,
        link_length: float = LINK_LENGTH,
        damping: float = JOINT_DAMPING,
        gravity: float = GRAVITY,
        inertia_motor: float = DEFAULT_INERTIA_MOTOR,
        torque_limit: float = TORQUE_LIMIT,
        kt: float = KT,
        kb: float = KB,
        resistance: float = RESISTANCE,
        max_voltage: float = MAX_VOLTAGE,
        settle_time_s: float = SETTLE_TIME_S,
        settled_omega: float = SETTLED_OMEGA,
    ) -> None:
        self.ratio_1 = float(ratio_1)
        self.ratio_2 = float(ratio_2)
        self.target_x = float(target_x)
        self.target_y = float(target_y)
        self.target_radius = float(target_radius)
        self.link_mass = link_mass
        self.link_length = link_length
        self.damping = damping
        self.gravity = gravity
        self.inertia_motor = inertia_motor
        self.torque_limit = torque_limit
        self.kt = kt
        self.kb = kb
        self.resistance = resistance
        self.max_voltage = max_voltage
        self.settle_time_s = settle_time_s
        self.settled_omega = settled_omega
        self.state = TwoLinkState()
        self.voltage_1: float = 0.0
        self.voltage_2: float = 0.0
        self.applied_torque_1: float = 0.0  # motor-side (pre-reduction)
        self.applied_torque_2: float = 0.0
        self.won: bool = False
        self.last_diagnostic: Diagnostic | None = None

    # --- readouts ---------------------------------------------------------

    @property
    def joint_angle_1(self) -> float:
        return self.state.q1

    @property
    def joint_angle_2(self) -> float:
        return self.state.q2

    @property
    def joint_angle_1_deg(self) -> float:
        return math.degrees(self.state.q1)

    @property
    def joint_angle_2_deg(self) -> float:
        return math.degrees(self.state.q2)

    @property
    def omega_1(self) -> float:
        return self.state.w1

    @property
    def omega_2(self) -> float:
        return self.state.w2

    @property
    def tip_x(self) -> float:
        """Forward kinematics: tip X (world), relative to the shoulder pivot."""
        a = self.state.q1
        b = self.state.q1 + self.state.q2
        return self.link_length * (math.sin(a) + math.sin(b))

    @property
    def tip_y(self) -> float:
        """Tip Y (world). Down is -Y, so hanging straight down -> negative Y."""
        a = self.state.q1
        b = self.state.q1 + self.state.q2
        return -(self.link_length * (math.cos(a) + math.cos(b)))

    @property
    def tip_in_region(self) -> bool:
        dx = self.tip_x - self.target_x
        dy = self.tip_y - self.target_y
        return dx * dx + dy * dy <= self.target_radius * self.target_radius

    @property
    def settled(self) -> bool:
        return abs(self.state.w1) <= self.settled_omega and abs(self.state.w2) <= self.settled_omega

    @property
    def stalled(self) -> bool:
        return False

    # --- player actions ---------------------------------------------------

    def set_joint_ratio(self, joint_id: int, ratio: float) -> None:
        """Pick a reduction for joint 0 (shoulder) or joint 1 (elbow)."""
        r = self._snap_ratio(ratio)
        if joint_id == 0:
            self.ratio_1 = r
        elif joint_id == 1:
            self.ratio_2 = r

    def set_joint_voltage(self, joint_id: int, voltage: float) -> None:
        """Set the motor voltage for joint 0 or 1 (clamped to ±max)."""
        v = max(-self.max_voltage, min(self.max_voltage, voltage))
        if joint_id == 0:
            self.voltage_1 = v
        elif joint_id == 1:
            self.voltage_2 = v

    # Back-compat shims so the bridge's generic set_voltage/set_gears paths
    # don't crash on this level (they're a no-op here; 2.4 uses its own
    # set_joint_voltage / set_joint_ratio actions).
    def set_voltage(self, _voltage: float) -> None:  # pragma: no cover
        pass

    def set_gears(self, *_args, **_kwargs) -> None:  # pragma: no cover
        pass

    # --- motor / dynamics math --------------------------------------------

    def _snap_ratio(self, ratio: float) -> float:
        """Snap to the nearest catalog reduction (1..6)."""
        best = RATIO_CHOICES[0]
        for r in RATIO_CHOICES:
            if abs(r - ratio) < abs(best - ratio):
                best = r
        return best

    def _motor_torque(self, voltage: float, omega: float) -> float:
        if self.kt <= 0.0 or self.resistance <= 0.0:
            return 0.0
        i = (voltage - self.kb * omega) / self.resistance
        tau = self.kt * i
        return max(-self.torque_limit, min(self.torque_limit, tau))

    def _motor_stall_torque(self, voltage: float) -> float:
        if self.kt <= 0.0 or self.resistance <= 0.0:
            return 0.0
        return max(
            -self.torque_limit,
            min(self.torque_limit, self.kt * voltage / self.resistance),
        )

    def _mass_matrix(self, q2: float) -> tuple[float, float, float]:
        """Planar 2R mass matrix M(q2) = [[M11, M12], [M12, M22]].

        Thin-rod links with motor reflected inertia on the diagonal.
        """
        m = self.link_mass
        L = self.link_length
        I_rod = m * L * L / 12.0
        cos2 = math.cos(q2)
        # Coupling term (off-diagonal).
        M12 = m * ((L / 2.0) ** 2 + (L * L / 2.0) * cos2) + I_rod
        M11 = (
            m * (L / 2.0) ** 2
            + I_rod  # link 1 about shoulder
            + m * (L * L + (L / 2.0) ** 2 + L * (L / 2.0) * cos2)
            + I_rod  # link 2
            + self.inertia_motor * self.ratio_1 * self.ratio_1  # motor 1 reflected
        )
        M22 = m * (L / 2.0) ** 2 + I_rod + self.inertia_motor * self.ratio_2 * self.ratio_2
        return M11, M12, M22

    def _coriolis_coeff(self, q2: float) -> float:
        """d(q2) = m·L1·L2/2 · sin(q2) — the Coriolis coupling coefficient."""
        m = self.link_mass
        L = self.link_length
        return m * (L * L / 2.0) * math.sin(q2)

    def _gravity_torque_1(self, q1: float, q2: float) -> float:
        """G1(q1,q2): gravity torque on joint 1 (shoulder). COUPLED — depends on q2."""
        m = self.link_mass
        L = self.link_length
        return self.gravity * ((m / 2.0 + m) * L * math.sin(q1) + m * (L / 2.0) * math.sin(q1 + q2))

    def _gravity_torque_2(self, q1: float, q2: float) -> float:
        """G2(q1,q2): gravity torque on joint 2 (elbow). COUPLED — depends on q1."""
        m = self.link_mass
        L = self.link_length
        return self.gravity * (m * (L / 2.0) * math.sin(q1 + q2))

    def step(self, dt: float = DT) -> None:
        if self.won:
            return
        s = self.state

        # Motor torque per joint (back-EMF on each joint's own speed).
        tau_m1 = self._motor_torque(self.voltage_1, s.w1)
        tau_m2 = self._motor_torque(self.voltage_2, s.w2)
        self.applied_torque_1 = tau_m1
        self.applied_torque_2 = tau_m2
        # Reflect through the ratio knob (positive ratio lifts the joint).
        tau_j1 = tau_m1 * self.ratio_1
        tau_j2 = tau_m2 * self.ratio_2

        # Coupled dynamics: M·q̈ = R, where R absorbs Coriolis + gravity + input.
        M11, M12, M22 = self._mass_matrix(s.q2)
        d = self._coriolis_coeff(s.q2)
        G1 = self._gravity_torque_1(s.q1, s.q2)
        G2 = self._gravity_torque_2(s.q1, s.q2)

        # RHS of M·q̈ = R. Coriolis terms use the standard 2R form with the
        # Christoffel symbols for the thin-rod linkage (verified by energy
        # decay — energy strictly decreases under damping with no input).
        R1 = -G1 + d * (s.w1 * s.w2 + s.w2 * s.w2) + tau_j1 - self.damping * s.w1
        R2 = -G2 - 0.5 * d * s.w1 * s.w1 + tau_j2 - self.damping * s.w2

        det = M11 * M22 - M12 * M12
        if abs(det) < 1e-12:
            # Degenerate config (links collinear) — skip this step.
            s.t += dt
            return
        a1 = (M22 * R1 - M12 * R2) / det
        a2 = (M11 * R2 - M12 * R1) / det

        # Semi-implicit Euler (update velocity first, then position by the
        # new velocity) — stable for the stiff over-damped regime.
        new_w1 = s.w1 + a1 * dt
        new_w2 = s.w2 + a2 * dt
        new_q1 = s.q1 + new_w1 * dt
        new_q2 = s.q2 + new_w2 * dt

        # Hard stops at ±cap: clamp the angle and kill the velocity into the
        # stop (no energy carried past horizontal — the no-flip guarantee).
        s.pinned1 = False
        s.pinned2 = False
        if new_q1 > CAP_ANGLE:
            new_q1 = CAP_ANGLE
            if new_w1 > 0.0:
                new_w1 = 0.0
            s.pinned1 = True
        elif new_q1 < -CAP_ANGLE:
            new_q1 = -CAP_ANGLE
            if new_w1 < 0.0:
                new_w1 = 0.0
            s.pinned1 = True
        if new_q2 > CAP_ANGLE:
            new_q2 = CAP_ANGLE
            if new_w2 > 0.0:
                new_w2 = 0.0
            s.pinned2 = True
        elif new_q2 < -CAP_ANGLE:
            new_q2 = -CAP_ANGLE
            if new_w2 < 0.0:
                new_w2 = 0.0
            s.pinned2 = True

        s.q1 = new_q1
        s.q2 = new_q2
        s.w1 = new_w1
        s.w2 = new_w2
        s.t += dt
        self._check_win()

    def _check_win(self) -> None:
        s = self.state
        # Must be settled (both joints at rest) before judging the tip.
        if not self.settled:
            s.settled_time = 0.0
            self.last_diagnostic = None
            return
        # Settled: judge the tip against the target region.
        diag = diagnose_tip_position(
            self.tip_x,
            self.tip_y,
            self.target_x,
            self.target_y,
            self.target_radius,
            self.joint_angle_1_deg,
            self.joint_angle_2_deg,
        )
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
            "level": "2.4",
            "t": self.state.t,
            # Joint angles (the arm's state the UI renders).
            "joint_angle_1": self.joint_angle_1,
            "joint_angle_2": self.joint_angle_2,
            "joint_angle_1_deg": self.joint_angle_1_deg,
            "joint_angle_2_deg": self.joint_angle_2_deg,
            "omega_1": self.omega_1,
            "omega_2": self.omega_2,
            # Tip (forward kinematics) + target region.
            "tip_x": self.tip_x,
            "tip_y": self.tip_y,
            "target_x": self.target_x,
            "target_y": self.target_y,
            "target_radius": self.target_radius,
            "tip_in_region": self.tip_in_region,
            # Per-joint actuator knobs.
            "ratio_1": self.ratio_1,
            "ratio_2": self.ratio_2,
            "voltage_1": self.voltage_1,
            "voltage_2": self.voltage_2,
            "torque_1": self.applied_torque_1,
            "torque_2": self.applied_torque_2,
            # Legacy aliases so level_state.gd's generic parser stays happy.
            "voltage": self.voltage_1,
            "torque": self.applied_torque_1,
            "reduction_ratio": self.ratio_1,
            "total_ratio": self.ratio_1,
            "link_angle": self.joint_angle_1,
            "link_angle_deg": self.joint_angle_1_deg,
            "target_angle": 0.0,
            "target_angle_deg": 0.0,
            "settled": self.settled,
            "stalled": self.stalled,
            "pinned1": self.state.pinned1,
            "pinned2": self.state.pinned2,
            "won": self.won,
            "diagnostic": self.last_diagnostic.to_dict() if self.last_diagnostic else None,
        }


def solve_driving_voltage_2_4(
    target_q1_deg: float,
    target_q2_deg: float,
    ratio_1: float = DEFAULT_RATIO_1,
    ratio_2: float = DEFAULT_RATIO_2,
    link_mass: float = LINK_MASS,
    link_length: float = LINK_LENGTH,
    gravity: float = GRAVITY,
    kt: float = KT,
    resistance: float = RESISTANCE,
) -> tuple[float, float]:
    """Open-loop equilibrium voltages to hold the arm at (q1, q2).

    At settle, back-EMF vanishes and the motor torque is its stall value, so
    the *reflected* joint torque ``Kt·V·r/R`` balances the coupled gravity::

        Kt * V_i * r_i / R = G_i(q1, q2)
        =>  V_i = G_i(q1, q2) * R / (Kt * r_i)

    G1 depends on q2 (the shoulder carries the elbow), so the two voltages
    couple — this is the coordination the level teaches. Returns (V1, V2).
    """
    q1 = math.radians(target_q1_deg)
    q2 = math.radians(target_q2_deg)
    g1 = gravity * (
        (link_mass / 2.0 + link_mass) * link_length * math.sin(q1)
        + link_mass * (link_length / 2.0) * math.sin(q1 + q2)
    )
    g2 = gravity * (link_mass * (link_length / 2.0) * math.sin(q1 + q2))
    v1 = resistance * g1 / (kt * ratio_1) if kt > 0 and ratio_1 > 0 else float("inf")
    v2 = resistance * g2 / (kt * ratio_2) if kt > 0 and ratio_2 > 0 else float("inf")
    return v1, v2


def solve_target_angles(
    target_x: float,
    target_y: float,
    link_length: float = LINK_LENGTH,
    guess_deg: tuple[float, float] = (40.0, 25.0),
) -> tuple[float, float]:
    """Invert the 2R forward kinematics to get joint angles for a target tip.

    Uses damped Newton on the 2D position residual (the tip map is periodic,
    so an unconstrained Newton blows up — a step cap keeps it in range).
    Returns (q1_deg, q2_deg). Used by the solver/tests, not the player.
    """
    q1 = math.radians(guess_deg[0])
    q2 = math.radians(guess_deg[1])

    def fk(a: float, b: float) -> tuple[float, float]:
        x = link_length * (math.sin(a) + math.sin(a + b))
        y = -(link_length * (math.cos(a) + math.cos(a + b)))
        return x, y

    def resid(a: float, b: float) -> tuple[float, float]:
        x, y = fk(a, b)
        return x - target_x, y - target_y

    eps = 1e-6
    for _ in range(200):
        rx, ry = resid(q1, q2)
        if abs(rx) < 1e-7 and abs(ry) < 1e-7:
            break
        jxx = (resid(q1 + eps, q2)[0] - resid(q1 - eps, q2)[0]) / (2 * eps)
        jxy = (resid(q1, q2 + eps)[0] - resid(q1, q2 - eps)[0]) / (2 * eps)
        jyx = (resid(q1 + eps, q2)[1] - resid(q1 - eps, q2)[1]) / (2 * eps)
        jyy = (resid(q1, q2 + eps)[1] - resid(q1, q2 - eps)[1]) / (2 * eps)
        det = jxx * jyy - jxy * jyx
        if abs(det) < 1e-12:
            break
        dq1 = (jyy * rx - jxy * ry) / det
        dq2 = (-jyx * rx + jxx * ry) / det
        step = max(abs(dq1), abs(dq2))
        if step > 0.2:
            dq1 *= 0.2 / step
            dq2 *= 0.2 / step
        q1 -= dq1
        q2 -= dq2
    return math.degrees(q1), math.degrees(q2)


if __name__ == "__main__":
    lvl = TwoLinkLevel()
    print(
        f"two-link arm: ratios {lvl.ratio_1:.0f}:{lvl.ratio_2:.0f}, "
        f"target region ({lvl.target_x:.3f},{lvl.target_y:.3f}) r={lvl.target_radius}"
    )
    qa1, qa2 = solve_target_angles(lvl.target_x, lvl.target_y, lvl.link_length)
    v1, v2 = solve_driving_voltage_2_4(qa1, qa2, lvl.ratio_1, lvl.ratio_2)
    print(
        f"target angles q1={qa1:.1f}° q2={qa2:.1f}° -> solver V1={v1:.3f} V2={v2:.3f} "
        f"(max {lvl.max_voltage:.0f})"
    )
    lvl.set_joint_voltage(0, v1)
    lvl.set_joint_voltage(1, v2)
    for _ in range(int(16.0 / DT)):
        lvl.step()
    print(
        f"after 16s: tip=({lvl.tip_x:.3f},{lvl.tip_y:.3f}) "
        f"in_region={lvl.tip_in_region} settled={lvl.settled} "
        f"won={lvl.won} diag={lvl.last_diagnostic}"
    )
