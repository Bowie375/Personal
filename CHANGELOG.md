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
- Bridge: UDP server (`src/robot_forge/bridge/server.py`), JSON protocol, `BridgeClient` GDScript
- Persistence: `ProfileStore` with atomic writes, schema versioning, XDG path (`~/.local/share/robot-forge/profile.json`)
- Gear catalog (`src/robot_forge/sim/gears.py`): standard module, planetary ratio formulas, ratio solver
- Diagnostic engine (`src/robot_forge/levels/diagnostics.py`): structured teaching on failure
- Act 1.1 Spinning Shaft level: rotational dynamics, target RPM, settle window, win condition
- Act 1.2 Two Gears level: DC motor curve (Kt, Kb, R), gear mesh constraint, target magnitude+sign on driven gear
- Session (`src/robot_forge/bridge/session.py`): wires level + bridge + profile, broadcasts sim-state ticks; supports 1.1 and 1.2
- Godot scenes: `main.tscn` (level select), `level_1_1.tscn` (3D shaft + HUD), `level_1_2.tscn` (two gears + HUD with voltage slider, gear selectors, dual RPM gauges)
- 49 pytest cases (bridge, profile, gears, diagnostics, level 1.1, level 1.2, end-to-end session for both levels)

### Pending
- Godot UI smoke-test on user machine (no Godot binary in this dev env)
- Act 1.3 Idler gear level
- PyBullet adapter to replace headless rotational sim

### Fixed
- Godot 1.2 gear orientation: cylinder mesh was rotating around its diameter (Z) instead of in place (Y→Z align). `gear_visual.gd` and `shaft_visual.gd` now bake a Y→spin_axis alignment so the disc spins flat regardless of the chosen axis.
- Godot 1.1 / 1.2 HUD was overlaying the 3D scene. Moved the HUD to a fixed right-side panel (420 px wide, full height), shifted the gear assembly and camera so the 3D area is unobstructed. Win and diagnostic panels stay centered as transient overlays.
- 1.1 shaft default `spin_axis` is now (0, 1, 0) so the long thin shaft spins around its own length axis.
- **1.2 mesh logic was wrong.** Gears with the same module always mesh in real gear systems; the old `center_distance == 30` check was an arbitrary constant that only matched the 1:1 case. Now `frame_center_distance` auto-sizes to the chosen pair's pitch-radius sum, and the visual repositioning (`gear_assembly.gd`) tracks it. All catalog pairs mesh.
- **1.2 gear visualization is now a real gear.** Replaced the uniform `CylinderMesh` with a procedurally generated toothed gear (`gear_visual.gd::_build_gear_surface`) — flat disc in the XZ plane, hub hole, trapezoidal teeth. Teeth make rotation unambiguous from any angle. The mesh rebuilds when the player picks new gears (driven by `gear_teeth_changed`).
- Bridge tests use a free UDP port (`_free_port()` helper) so they no longer collide on `127.0.0.1:9999` in CI / repeated runs.

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

## Design decisions (locked 2026-07-12)

- **Gearbox style:** planetary (compact, common in real robot joints)
- **Arm:** Franka Emika Panda (7-DOF, torque-sensing, redundant)
- **Failure feedback:** teach — diagnostic engine explains *why* a level failed
- **Persistence:** player profile (unlocked levels, last completed, settings) — no best-time leaderboards

## [0.1.0] — 2026-07-12

### Added
- Initial repository: empty working dir
