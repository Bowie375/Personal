# Robot Forge

Build a robot from gears up to manipulation tasks. Real-world physics, game-style progression.

## Architecture

```
┌─────────────────┐    JSON/UDP    ┌──────────────────┐
│  Godot 4 client │◄──────────────►│  Python backend  │
│  (3D UI, input) │  port 9999     │  (sim, logic)    │
└─────────────────┘                └──────────────────┘
                                           │
                                    ┌──────┴──────┐
                                    │   PyBullet  │  Acts 1–2 (low-level)
                                    │   MuJoCo    │  Acts 3–5 (control)
                                    └─────────────┘
```

- **Godot 4** — game engine, 3D visualization, UI, input, scene composition
- **Python** — physics simulation, robot logic, progression/level state
- **PyBullet** — Acts 1–2: gear meshing, rigid body collisions, fast iteration
- **MuJoCo** — Acts 3–5: precise contact, motor dynamics, control tasks
- **Bridge** — UDP JSON messages; Godot sends player actions, Python streams sim state

## Project layout

```
robot/
├── pyproject.toml          # uv + ruff config
├── CLAUDE.md               # this file
├── CHANGELOG.md            # version history
├── src/robot_forge/
│   ├── sim/                # PyBullet + MuJoCo wrappers
│   ├── levels/             # per-level state machines
│   ├── bridge/             # UDP server, JSON protocol
│   └── core/               # shared types
├── godot/                  # Godot 4 project root
│   ├── scenes/             # .tscn files
│   ├── scripts/            # .gd files (bridge client, UI)
│   └── assets/             # meshes, textures
├── tests/                  # pytest
└── data/                   # URDFs, MJCFs, level configs
```

## Conventions

- Python 3.13, ruff format+lint, pytest
- Godot 4.x, GDScript (typed, with `@tool` only where needed)
- Branch: `main`. Work in topic branches; merge via squash.
- Commit prefixes: `sim:`, `godot:`, `bridge:`, `level:`, `docs:`, `chore:`

## Sim selection rule

| Act | Sim | Reason |
|-----|-----|--------|
| 1 (gears) | PyBullet | Simple rigid body, fast setup |
| 2 (gearbox/motors) | PyBullet | Joint dynamics, good enough |
| 3 (arm FK/IK) | MuJoCo | Precise joint control |
| 4 (control loops) | MuJoCo | Contact fidelity |
| 5 (manipulation) | MuJoCo | Industry standard |

## Game progression (current draft)

See [CHANGELOG.md §Progression](CHANGELOG.md) — pending your review.

## Bridge protocol (skeleton)

- **Client → Server** (Godot → Python): `{"action": "set_motor", "id": 0, "value": 1.0}`
- **Server → Client** (Python → Godot): `{"type": "state", "joints": [...], "links": [...]}`

## Commands

```bash
uv sync                 # install deps
uv run pytest           # tests
uv run ruff check .     # lint
uv run ruff format .    # format
```
