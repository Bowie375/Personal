# Robot Forge

A game that takes you from a single gear to a full Franka Panda robot doing manipulation tasks — with real physics, on a guided progression that opens into a sandbox.

## Run the backend (Act 1.1)

```bash
uv run python -m robot_forge.bridge.session --level 1.1
```

The session listens on `udp://127.0.0.1:9999`. It broadcasts sim-state ticks and accepts actions:

- `{"action": "set_torque", "payload": {"value": <float>}}` — apply torque to the shaft
- `{"action": "reset", "payload": {}}` — restart the level
- `{"action": "ping", "payload": {}}` — liveness check

Player profile (unlocked levels, attempts, last diagnostic) is saved to `~/.local/share/robot-forge/profile.json`. Override with `ROBOT_FORGE_DATA_DIR`.

## Test, lint, format

```bash
uv run pytest
uv run ruff check .
uv run ruff format .
```

## Layout

- `src/robot_forge/` — Python (core types, sim, levels, bridge)
- `godot/` — Godot 4 client (UI, 3D, input)
- `data/` — URDFs, MJCFs, level configs
- `tests/` — pytest
- `CLAUDE.md` — architecture & conventions
- `CHANGELOG.md` — version history & progression draft
