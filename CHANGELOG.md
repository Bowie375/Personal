# Changelog

All notable changes to this project are documented here.
Format: [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added
- Project scaffold: uv, ruff, pytest, .gitignore
- Tech stack decision: Godot 4 + Python bridge; PyBullet (Acts 1–2) + MuJoCo (Acts 3–5)
- Game progression: hybrid assembly (schematic → physics test), guided → sandbox
- `src/robot_forge/` Python package layout
- `godot/` Godot 4 project root (scenes/, scripts/, assets/)

### Pending
- Bridge protocol implementation (UDP/JSON)
- Game progression schedule (draft in progress)
- Act 1: Gear basics level

## Progression — Draft for review

### Act 1 — Mechanical Foundations (PyBullet)

| # | Level | Mechanic | Win condition |
|---|-------|----------|---------------|
| 1.1 | Spinning shaft | Apply torque, see angular velocity. | Reach target RPM in 5s. |
| 1.2 | Two gears | Mount driver + driven; observe gear ratio. | Driven gear rotates correct direction & speed. |
| 1.3 | Idler gear | Add a middle gear; reverse direction twice. | Output speed matches expectation. |
| 1.4 | Gear ratios | Choose gear sizes for a target ratio. | Output RPM = target ±5%. |

### Act 2 — Gearboxes & Motors (PyBullet)

| # | Level | Mechanic | Win condition |
|---|-------|----------|---------------|
| 2.1 | DC motor | Apply voltage → torque curve. | Match speed under load. |
| 2.2 | Single-stage gearbox | Combine motor + gear pair. | Hit speed/torque target. |
| 2.3 | Multi-stage | Planetary or compound train. | Compact design that meets both axes. |
| 2.4 | First joint | Mount gearbox to a rotating link. | Link sweeps target angle ±2°. |

### Act 3 — Robotic Arm (MuJoCo)

| # | Level | Mechanic | Win condition |
|---|-------|----------|---------------|
| 3.1 | 1-DOF link | Forward kinematics visualization. | Reach 3 waypoints. |
| 3.2 | 2-DOF planar | Two links; manual joint control. | Trace a line in workspace. |
| 3.3 | 3-DOF | Introduce base rotation. | Draw a triangle. |
| 3.4 | IK intro | Numerical inverse kinematics solver. | Click a target → joints solve. |
| 3.5 | 6-DOF arm | Full manipulator assembly. | Reach points in 3D. |

### Act 4 — Control (MuJoCo)

| # | Level | Mechanic | Win condition |
|---|-------|----------|---------------|
| 4.1 | PD controller | Tune Kp, Kd. | Settle to setpoint, no overshoot. |
| 4.2 | Trajectory | Quintic polynomial between waypoints. | Follow path with bounded error. |
| 4.3 | Gravity comp | Feedforward + feedback. | Hold position under load. |
| 4.4 | Impedance | Stiffness/damping shaping. | Contact task without bounce. |

### Act 5 — Manipulation (MuJoCo)

| # | Level | Mechanic | Win condition |
|---|-------|----------|---------------|
| 5.1 | Pick static | Grasp a cube at rest. | Lift without slip. |
| 5.2 | Pick moving | Grasp a moving object on conveyor. | Catch within time window. |
| 5.3 | Stack | Place block on top of another. | Stack 3 blocks, no collapse. |
| 5.4 | Insert | Peg-in-hole assembly. | Insert within tolerance. |

### Sandbox (post-campaign)

- Free build: parts catalog, no fixed goal
- Challenge missions: player-authored shareable scenarios
- Leaderboards per mission (precision, speed, energy)

## [0.1.0] — 2026-07-12

### Added
- Initial repository: empty working dir
