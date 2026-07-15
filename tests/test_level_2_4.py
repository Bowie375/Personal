"""Act 2.4 — Two-link arm: two abstracted joints driving a tip to a region."""

from __future__ import annotations

from robot_forge.levels.diagnostics import DiagKind
from robot_forge.levels.level_2_4 import (
    TwoLinkLevel,
    solve_driving_voltage_2_4,
    solve_target_angles,
)


def _settle(level: TwoLinkLevel, seconds: float = 18.0) -> None:
    for _ in range(int(seconds / 0.01)):
        level.step()


def test_default_arm_hangs_straight_down() -> None:
    """No voltage -> both joints at 0, tip hangs straight below the shoulder."""
    lvl = TwoLinkLevel()
    _settle(lvl)
    assert lvl.joint_angle_1_deg == 0.0
    assert lvl.joint_angle_2_deg == 0.0
    # Tip straight down: x=0, y = -2*link_length (both links stacked).
    assert abs(lvl.tip_x) < 1e-6
    assert lvl.tip_y == -1.0  # 2 * 0.5 (link_length) below pivot
    assert not lvl.won


def test_solver_voltages_land_tip_in_region_and_win() -> None:
    """The equilibrium voltages bring the tip into the target region -> won."""
    lvl = TwoLinkLevel()
    qa1, qa2 = solve_target_angles(lvl.target_x, lvl.target_y, lvl.link_length)
    v1, v2 = solve_driving_voltage_2_4(qa1, qa2, lvl.ratio_1, lvl.ratio_2)
    lvl.set_joint_voltage(0, v1)
    lvl.set_joint_voltage(1, v2)
    _settle(lvl)
    assert lvl.tip_in_region
    assert lvl.won


def test_undershoot_diagnoses_when_tip_misses() -> None:
    """Too little voltage -> tip short of the region -> UNDERSHOOT, not won."""
    lvl = TwoLinkLevel()
    qa1, qa2 = solve_target_angles(lvl.target_x, lvl.target_y, lvl.link_length)
    v1, v2 = solve_driving_voltage_2_4(qa1, qa2, lvl.ratio_1, lvl.ratio_2)
    # Halve both voltages -> settles short of the target region.
    lvl.set_joint_voltage(0, v1 * 0.5)
    lvl.set_joint_voltage(1, v2 * 0.5)
    _settle(lvl)
    assert not lvl.won
    assert lvl.last_diagnostic is not None
    assert lvl.last_diagnostic.kind == DiagKind.UNDERSHOOT


def test_neither_joint_flips_past_horizontal() -> None:
    """Max voltage on both joints at 6:1: neither angle exceeds the ~90° cap."""
    lvl = TwoLinkLevel()
    lvl.set_joint_voltage(0, 24.0)
    lvl.set_joint_voltage(1, 24.0)
    max1 = max2 = 0.0
    for _ in range(int(18.0 / 0.01)):
        lvl.step()
        max1 = max(max1, abs(lvl.joint_angle_1_deg))
        max2 = max(max2, abs(lvl.joint_angle_2_deg))
    assert max1 < 90.1  # never past horizontal
    assert max2 < 90.1


def test_voltage_clamped() -> None:
    lvl = TwoLinkLevel()
    lvl.set_joint_voltage(0, 1e6)
    assert lvl.voltage_1 == 24.0
    lvl.set_joint_voltage(0, -1e6)
    assert lvl.voltage_1 == -24.0
    lvl.set_joint_voltage(1, 1e6)
    assert lvl.voltage_2 == 24.0


def test_set_joint_ratio_snaps_to_catalog() -> None:
    """Ratios snap to the catalog choices (1..6); the chosen joint updates."""
    lvl = TwoLinkLevel()
    lvl.set_joint_ratio(0, 2.9)  # snaps to 3
    assert lvl.ratio_1 == 3.0
    lvl.set_joint_ratio(1, 5.6)  # snaps to 6
    assert lvl.ratio_2 == 6.0
    # The other joint is untouched.
    assert lvl.ratio_1 == 3.0


def test_coupling_shoulder_load_depends_on_elbow_angle() -> None:
    """Joint 1's gravity torque changes with joint 2's angle (the coupling).

    This is the one new idea over 2.3: the shoulder carries the elbow, so
    moving the elbow shifts the shoulder's equilibrium. The solver's V1
    therefore depends on q2.
    """
    lvl = TwoLinkLevel()
    g1_elbow_down = lvl._gravity_torque_1(0.6, 0.0)
    g1_elbow_bent = lvl._gravity_torque_1(0.6, 0.4)
    assert g1_elbow_bent != g1_elbow_down
    # Solver voltage for joint 1 must therefore differ when q2 differs.
    v1a, _ = solve_driving_voltage_2_4(34.4, 0.0)  # ~0.6 rad, q2=0
    v1b, _ = solve_driving_voltage_2_4(34.4, 22.9)  # ~0.6 rad, q2=0.4
    assert v1a != v1b


def test_fk_tip_round_trips_through_solver() -> None:
    """solve_target_angles recovers joint angles whose FK hits the target tip."""
    lvl = TwoLinkLevel()
    qa1, qa2 = solve_target_angles(lvl.target_x, lvl.target_y, lvl.link_length)
    # Drive the FK at those angles and confirm the tip is at the target.
    import math

    q1 = math.radians(qa1)
    q2 = math.radians(qa2)
    tx = lvl.link_length * (math.sin(q1) + math.sin(q1 + q2))
    ty = -(lvl.link_length * (math.cos(q1) + math.cos(q1 + q2)))
    assert abs(tx - lvl.target_x) < 1e-3
    assert abs(ty - lvl.target_y) < 1e-3


def test_summary_shape() -> None:
    lvl = TwoLinkLevel()
    s = lvl.summary()
    for key in (
        "joint_angle_1",
        "joint_angle_2",
        "joint_angle_1_deg",
        "joint_angle_2_deg",
        "tip_x",
        "tip_y",
        "target_x",
        "target_y",
        "target_radius",
        "tip_in_region",
        "ratio_1",
        "ratio_2",
        "voltage_1",
        "voltage_2",
        "won",
    ):
        assert key in s
    assert s["ratio_1"] == 6.0
    assert s["ratio_2"] == 6.0
    assert s["tip_in_region"] is False  # hangs straight down at start
