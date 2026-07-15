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
- Act 1.1 Spinning Shaft level: rotational dynamics, target RPM, settle window, win condition; full DC motor model (τ = Kt·(V−Kb·ω)/R) with player-tunable Kt/Kb/R/I/b and motor anatomy (shaft + two bearings + one toothed gear)
- Act 1.2 Two Gears level: DC motor curve (Kt, Kb, R), gear mesh constraint, target magnitude+sign on driven gear
- Act 1.3 Idler gear level: 3-gear chain (driver→idler→driven); idler cancels in the ratio but flips direction twice → output same direction as driver
- Act 1.4 Loaded geartrain level: reflected load (`τ_load·N_driver/N_driven`), stall detection, target RPM + target load, torque×speed tradeoff; no-back-drive Coulomb load (a stalled train pins ω=0 instead of reverse-driving)
- Act 2.1 Compound gearbox level: two-stage reduction (B+C on a shared shaft so stage ratios multiply), target ratio (12:1) unreachable by any single mesh (catalog max 5:1), reuse of 1.4 motor + reflected-load engine
- Act 2.2 Planetary gearbox level: sun + planets + ring, three co-axial members; the Willis equation yields three ratios from the SAME gearset depending on which member is grounded (ring/sun/carrier fixed). Carrier-fixed reverses the output. New `set_mode` action. Assemblability enforces the **geometric** constraint `N_ring = N_sun + 2·N_planet` (the planet is *derived* from sun + ring — the player picks only sun and ring; `N_planet = (N_ring − N_sun)/2` must be a catalog gear) **and** the 3-planet slotting rule `(N_ring − N_sun) % 3 == 0`. Catalog max reduction 6:1: sun N12 / ring N60 (planet N24 derived). Repurposes the old "absorbed into 1.1/1.4" 2.2 slot — the planetary is the genuinely-next mechanic after the compound gearbox.
- Act 2.3 First joint level: a single-stage spur gearbox whose driven shaft carries a **rod** (the link). The first level where a gearbox's output is a *joint* moving a link to an *angle* (not a free-spinning shaft). **Open-loop balance** (no voltage cut-off, no PD — that's Act 4.1): the player sets a voltage and the rod settles at the angle where the motor's reflected torque balances gravity (`τ_out = m·g·(L/2)·sin θ`) — over-damped so it rises *monotonically* to the equilibrium and never swings past it ("always points down, no overshoot"). A hard stop at horizontal + voltage/ratio range caps the torque so the rod can never flip over the top. Win: settled angle within ±2° of the 45° target. The rod is **translucent** so the gears show through it. New `diagnose_angle(...)` (reuses UNDERSHOOT/OVERSHOOT with voltage/ratio hints); `solve_driving_voltage_2_3(...)` inverts the equilibrium.
- Act 2.4 Two-link arm level: two **abstracted joints** (shoulder + elbow) in series driving two links in a vertical plane — the **abstraction boundary** where the gearbox becomes a black-box actuator (a clickable cylinder) whose two knobs are *reduction ratio* + *motor voltage*, the same levers tuned since 1.1 with the gear mesh no longer drawn. Full Lagrangian 2R dynamics with **relative** joint angles (real-robot convention) and a **coupled** gravity term: joint 1's equilibrium load depends on where joint 2 sits (the shoulder carries the elbow), so the two voltages can't be tuned independently — coordination is the one new idea over 2.3. Over-damped (monotonic settle, no swing — an *equilibrium* level, control deferred to 4.1); hard stops at ±90° per joint keep both links from flipping past horizontal. Win: the tip of link 2 comes to rest inside a pre-marked region in the scene. New clickable-joint interaction model (`joint_visual.gd` + `joint_control_panel.gd` that re-binds to whichever joint was clicked); `two_link_assembly.gd` runs forward kinematics. New `diagnose_tip_position(...)` (reuses UNDERSHOOT with a coupling hint); `solve_driving_voltage_2_4(...)` + `solve_target_angles(...)` invert the equilibrium / FK.
- `planetary_gear_ratio(sun, ring, mode)` in `gears.py`: signed output/input ratio for all three modes (replaces the ring-fixed-only `planetary_ratio`, kept as a thin back-compat wrapper); `NOT_ASSEMBLABLE` diagnostic + `diagnose_assemblable(...)` teaching why a sun+ring pair won't fit a catalog planet / won't slot 3 planets
- Ring gear renders as an **annulus with inward teeth** enclosing the sun + planets (`_build_ring_surface_normalized` in `gear_visual.gd`), not an outward-toothed disc
- Session (`src/robot_forge/bridge/session.py`): one backend process serves all levels via a `LEVEL_REGISTRY` + `set_level` action (Godot picks a level → backend rebuilds); supports 1.1–1.4, 2.1, 2.2, 2.3, and 2.4. New per-joint `set_joint_ratio` / `set_joint_voltage` actions for the abstracted 2.4 joints.
- Godot scenes: `main.tscn` (level select), `level_1_1.tscn` (motor anatomy + param sliders), `level_1_2.tscn`/`level_1_3.tscn` (two/three-gear + HUD), `level_1_4.tscn` (load slider + stall banner), `level_2_1.tscn` (4-gear compound + ratio readout), `level_2_2.tscn` (planetary: sun + 3 planets inside an inward-toothed ring + carrier + 3-way mode selector; sun/ring selectors, planet shown derived + not-assemblable banner), `level_2_3.tscn` (two-gear joint + translucent rod + angle readout; reuses the 2.2 three-point lighting), `level_2_4.tscn` (two abstracted clickable joints + translucent 2-link arm + target region + re-binding per-joint control panel)
- 146 pytest cases (bridge, profile, gears, diagnostics, levels 1.1–1.4, 2.1, 2.2, 2.3, 2.4, end-to-end session for all levels)

### Pending
- Godot UI smoke-test on user machine (no Godot binary in this dev env)
- PyBullet adapter to replace headless rotational sim

### Fixed
- **2.2 planetary tooth constraint was wrong.** The old assemblability check `(N_ring − N_sun) % num_planets == 0` is only the *slotting* condition, not the geometric one — it gave 11 false passes (sets that "assembled" but couldn't fit a catalog planet). Now enforces the real constraint `N_ring = N_sun + 2·N_planet`: the planet is *derived* from sun + ring (`N_planet = (N_ring − N_sun)/2`) and must be a catalog gear, with slotting as a secondary check. The player picks only sun + ring (the planet is shown as a read-only derived label); `set_gears` takes 2 args.
- **2.2 ring gear now an annulus.** It was a plain outward-toothed disc sitting under the sun/planets. Now `_build_ring_surface_normalized` builds an annulus with **inward** teeth and a solid outer rim that encloses the sun + planets (planets mesh at the ring's inner pitch circle).
- Godot 1.2 gear orientation: cylinder mesh was rotating around its diameter (Z) instead of in place (Y→Z align). `gear_visual.gd` and `shaft_visual.gd` now bake a Y→spin_axis alignment so the disc spins flat regardless of the chosen axis.
- Godot 1.1 / 1.2 HUD was overlaying the 3D scene. Moved the HUD to a fixed right-side panel (420 px wide, full height), shifted the gear assembly and camera so the 3D area is unobstructed. Win and diagnostic panels stay centered as transient overlays.
- 1.1 shaft default `spin_axis` is now (0, 1, 0) so the long thin shaft spins around its own length axis.
- **1.2 mesh logic was wrong.** Gears with the same module always mesh in real gear systems; the old `center_distance == 30` check was an arbitrary constant that only matched the 1:1 case. Now `frame_center_distance` auto-sizes to the chosen pair's pitch-radius sum, and the visual repositioning (`gear_assembly.gd`) tracks it. All catalog pairs mesh.
- **1.2 gear visualization is now a real gear.** Replaced the uniform `CylinderMesh` with a procedurally generated toothed gear (`gear_visual.gd::_build_gear_surface`) — flat disc in the XZ plane, hub hole, trapezoidal teeth. Teeth make rotation unambiguous from any angle. The mesh rebuilds when the player picks new gears (driven by `gear_teeth_changed`).
- Bridge tests use a free UDP port (`_free_port()` helper) so they no longer collide on `127.0.0.1:9999` in CI / repeated runs.
- **1.1 `.tscn` parse error.** Godot's text scene format does not allow `#` comments inside the node tree; removed all comment lines from `level_1_1.tscn`.
- **1.4 load-direction semantics.** The load slider sets the resisting torque on the DRIVEN (output) shaft = the job; `output_torque == load_torque` when running, and a new `motor_side_load` readout shows the reflected load (load / reduction) the motor actually fights. The HUD now reads both from the backend instead of recomputing them wrong.
- **1.4 zero-crossing flicker.** A naive `sign(omega)` Coulomb load reversed the resisting torque at ω≈0, kicking the gear backward into a limit cycle on coast-down / under-drive. Rewrote `step()` with no-back-drive semantics: the train pins ω=0 when the motor can't sustain motion (locked by `test_no_back_drive_on_coastdown`).
- **1.4 / 2.1 HUD panel striding outside the window.** A 4-child row forced the `PanelContainer` wider than its 420 px gutter. Split the target-load label onto its own line and tightened every row's fixed widths so all rows fit.
- **2.1 B/C gear overlap.** With the shared intermediate shaft along the camera axis (Z), B and C stacked in depth and C hid behind B. Reoriented the train so the spin axis is X (1.1 motor-shaft orientation): the shared shaft runs along X, meshing pairs separate along Z, and B/C spread horizontally — both visible. Camera now centers on the cluster (look-at basis at (0,1,0); layout subtracts its centroid).

## Progression — Draft for review

### Act 1 — Mechanical Foundations (PyBullet)

| # | Level | Mechanic | Win condition |
|---|-------|----------|---------------|
| 1.1 | Spinning shaft | Apply torque, see angular velocity. | Reach target RPM in 5s. |
| 1.2 | Two gears | Mount driver + driven; observe gear ratio. | Driven gear rotates correct direction & speed. |
| 1.3 | Idler gear | Add a middle gear; reverse direction twice. | Output speed matches expectation. |
| 1.4 | Loaded geartrain | Gear ratio + voltage to drive a load; reflects load to motor via ratio. | Output RPM = target ±5%, no stall, load = target torque. |

### Act 2 — Gearboxes & Motors (PyBullet)

| # | Level | Mechanic | Win condition |
|---|-------|----------|---------------|
| 2.1 | Compound gearbox | Two-stage reduction (shared intermediate shaft); stage ratios multiply. | Hit a target ratio no single mesh can reach (12:1). |
| 2.2 | Planetary gearbox | Sun + planets + ring; ground one member (ring/sun/carrier) for three ratios from one gearset. | Hit 6:1 (catalog max planetary) in ring-fixed mode; carrier-fixed reverses. |
| 2.3 | First joint | Mount gearbox to a rotating link. | Link sweeps target angle ±2°. |
| 2.4 | Two-link arm | Abstract the gearbox into a clickable joint; two joints, two links. | Tip of link 2 reaches a marked region. |

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
