"""Session: wires a level to the bridge, drives the sim loop, broadcasts state.

The session hosts a registry of level factories and can switch the active
level at runtime via the ``set_level`` action (sent by Godot when the player
picks a level from the menu). This means a single backend process serves all
levels — the player no longer has to restart the bridge with ``--level X``
to play a different level.

For backward compatibility, ``LevelSession("1.1")`` still boots straight into
1.1, and all the per-level actions (set_torque, set_voltage, set_gears,
reset) behave exactly as before.
"""

from __future__ import annotations

import logging
import threading
import time

from robot_forge.bridge.server import BridgeServer
from robot_forge.core.profile import ProfileStore
from robot_forge.core.types import SimState
from robot_forge.levels.level_1_1 import DT as DT_1_1
from robot_forge.levels.level_1_1 import ShaftLevel
from robot_forge.levels.level_1_2 import DT as DT_1_2
from robot_forge.levels.level_1_2 import TwoGearLevel
from robot_forge.levels.level_1_3 import DT as DT_1_3
from robot_forge.levels.level_1_3 import ThreeGearLevel

logger = logging.getLogger(__name__)

# Action names the UI can send.
ACTION_SET_TORQUE = "set_torque"
ACTION_SET_VOLTAGE = "set_voltage"
ACTION_SET_GEARS = "set_gears"
ACTION_SET_LEVEL = "set_level"
ACTION_RESET = "reset"
ACTION_PING = "ping"

# Registry of level id -> (factory, dt). The factory takes no args and
# returns a fresh level instance. Switching levels rebuilds from here.
LEVEL_REGISTRY: dict[str, tuple] = {
    "1.1": (ShaftLevel, DT_1_1),
    "1.2": (TwoGearLevel, DT_1_2),
    "1.3": (ThreeGearLevel, DT_1_3),
}


def _summary_1_1(level: ShaftLevel) -> dict:
    return {
        "level": "1.1",
        "t": level.state.t,
        "driver_rpm": level.rpm,
        "driven_rpm": level.rpm,
        "target_driven_rpm": level.target_rpm,
        "torque": level.applied_torque,
        "voltage": 0.0,
        "meshed": True,
        "won": level.won,
        "driver_teeth": 0,
        "driven_teeth": 0,
        "target_sign": -1,
        "diagnostic": level.last_diagnostic.to_dict() if level.last_diagnostic else None,
    }


def _summary_1_2(level: TwoGearLevel) -> dict:
    s = level.summary()
    # Ensure target_sign is present for the bridge payload.
    s.setdefault("target_sign", level.target_sign)
    return s


def _summary_1_3(level: ThreeGearLevel) -> dict:
    s = level.summary()
    # Ensure target_sign is present for the bridge payload.
    s.setdefault("target_sign", level.target_sign)
    return s


class LevelSession:
    """Owns one level instance, runs the sim in a thread, syncs to bridge.

    Hosts the full level registry in one process. Godot sends ``set_level``
    when the player picks a level from the menu; the session rebuilds the
    active level from the registry and continues broadcasting. For backward
    compatibility, constructing with an explicit ``level_id`` boots
    straight into that level.
    """

    def __init__(
        self,
        level_id: str | None = None,
        profile: ProfileStore | None = None,
        host: str = "127.0.0.1",
        port: int = 9999,
        sim_hz: float = 100.0,
    ) -> None:
        self.profile = profile
        self.bridge = BridgeServer(host=host, port=port, on_action=self._on_action)
        self._sim_period = 1.0 / sim_hz
        self._running = False
        self._thread: threading.Thread | None = None
        # _level_lock guards level/level_id swaps against the sim loop read.
        self._level_lock = threading.Lock()
        self.level_id: str | None = level_id
        # If the caller gave an id, boot straight in (backward compat).
        # Otherwise wait for Godot to send `set_level` before running.
        self.level = self._build_level(level_id) if level_id is not None else None

    def _build_level(self, level_id: str):
        if level_id not in LEVEL_REGISTRY:
            raise ValueError(f"Unknown level: {level_id}")
        factory, _dt = LEVEL_REGISTRY[level_id]
        return factory()

    def set_level(self, level_id: str) -> None:
        """Switch the active level at runtime (called from `set_level` action).

        Rebuilds the level from the registry. Safe to call from the bridge
        receive thread while the sim loop runs — the swap is guarded by
        _level_lock and the loop re-reads self.level each tick.
        """
        if level_id not in LEVEL_REGISTRY:
            logger.warning("set_level: unknown level %s", level_id)
            return
        # Persist any completion on the outgoing level before swapping.
        self._maybe_record_outgoing()
        with self._level_lock:
            self.level_id = level_id
            self.level = self._build_level(level_id)
        logger.info("Switched active level to %s", level_id)

    def _maybe_record_outgoing(self) -> None:
        """Record the outgoing level's last attempt/completion to the profile."""
        if self.profile is None or self.level is None:
            return
        try:
            p = self.profile.load()
            diag = self.level.last_diagnostic
            p.record_attempt(self.level_id or "", diagnostic=diag.message if diag else "")
            if getattr(self.level, "won", False):
                p.record_completion(self.level_id or "")
            self.profile.save()
        except Exception:  # noqa: BLE001 — profile write must not crash the swap
            logger.exception("profile write during level switch failed")

    def _on_action(self, action) -> None:
        name = action.name
        payload = action.payload
        # set_level can arrive before any level is active; handle first.
        if name == ACTION_SET_LEVEL:
            new_id = str(payload.get("id", ""))
            self.set_level(new_id)
            return
        # Guard the active level against a concurrent set_level swap.
        with self._level_lock:
            level = self.level
        if level is None:
            # No level active yet — ignore until Godot sends set_level.
            logger.debug("ignoring %s: no active level (send set_level first)", name)
            return
        if name == ACTION_SET_TORQUE and hasattr(level, "set_torque"):
            level.set_torque(float(payload.get("value", 0.0)))
        elif name == ACTION_SET_VOLTAGE and hasattr(level, "set_voltage"):
            level.set_voltage(float(payload.get("value", 0.0)))
        elif name == ACTION_SET_GEARS and hasattr(level, "set_gears"):
            d = int(payload.get("driver", 0))
            dn = int(payload.get("driven", 0))
            idler = int(payload.get("idler", 0))
            if idler > 0:
                # Three-gear level (1.3)
                if d > 0 and dn > 0:
                    level.set_gears(driver_teeth=d, idler_teeth=idler, driven_teeth=dn)
            elif d > 0 and dn > 0:
                # Two-gear level (1.2)
                level.set_gears(driver_teeth=d, driven_teeth=dn)
        elif name == ACTION_RESET:
            with self._level_lock:
                self.level = self._build_level(self.level_id or "")
        elif name == ACTION_PING:
            pass  # liveness
        else:
            logger.warning("unknown action: %s", name)

    def start(self) -> None:
        self.bridge.start()
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        logger.info("Session started (active level: %s)", self.level_id)

    def stop(self) -> None:
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)
        self.bridge.stop()
        # Persist last attempt for cross-session continuity.
        if self.profile is not None and self.level is not None:
            p = self.profile.load()
            diag = self.level.last_diagnostic
            p.record_attempt(self.level_id or "", diagnostic=diag.message if diag else "")
            if getattr(self.level, "won", False):
                p.record_completion(self.level_id or "")
            self.profile.save()

    def _loop(self) -> None:
        last = time.perf_counter()
        while self._running:
            now = time.perf_counter()
            if now - last < self._sim_period:
                time.sleep(self._sim_period - (now - last))
            last = time.perf_counter()
            # Snapshot the active level under the lock so a concurrent
            # set_level swap can't race the step/broadcast.
            with self._level_lock:
                level = self.level
                level_id = self.level_id
            if level is None:
                # No level active yet — idle-spin until Godot picks one.
                continue
            if level_id == "1.2":
                dt = DT_1_2
                extras = _summary_1_2(level)
            elif level_id == "1.3":
                dt = DT_1_3
                extras = _summary_1_3(level)
            else:
                dt = DT_1_1
                extras = _summary_1_1(level)
            level.step(dt)
            joints = self._joints_for(level_id, level)
            self.bridge.broadcast(
                SimState(timestamp=extras.get("t", 0.0), joints=joints, extras=extras)
            )

    def _joints_for(self, level_id: str, level) -> list[dict]:
        if level_id == "1.2":
            return [
                {"id": 0, "rpm": level.driver_rpm, "angle": level.state.driver_angle},
                {"id": 1, "rpm": level.driven_rpm, "angle": level.state.driven_angle},
            ]
        if level_id == "1.3":
            return [
                {"id": 0, "rpm": level.driver_rpm, "angle": level.state.driver_angle},
                {"id": 1, "rpm": level.idler_rpm, "angle": level.state.idler_angle},
                {"id": 2, "rpm": level.driven_rpm, "angle": level.state.driven_angle},
            ]
        # Default: 1.1 — single shaft.
        return [{"id": 0, "rpm": level.rpm, "angle": level.state.angle_rad}]


def main() -> None:
    import argparse

    p = argparse.ArgumentParser(
        description="Robot Forge bridge: one process serving all levels."
    )
    # --level is now optional: omit it to wait for Godot to pick via set_level.
    p.add_argument(
        "--level",
        default=None,
        help="Boot straight into a level (e.g. 1.3). Omit to wait for the "
        "Godot client to send `set_level` (recommended for normal play).",
    )
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=9999)
    p.add_argument("--no-profile", action="store_true")
    args = p.parse_args()

    logging.basicConfig(level=logging.INFO)
    profile = None if args.no_profile else ProfileStore()
    sess = LevelSession(args.level, profile=profile, host=args.host, port=args.port)
    sess.start()
    logger.info(
        "Bridge up on %s:%d. %s",
        args.host,
        args.port,
        f"Booted into level {args.level}."
        if args.level
        else "Waiting for Godot to send set_level.",
    )
    try:
        while True:
            time.sleep(1.0)
    except KeyboardInterrupt:
        sess.stop()


if __name__ == "__main__":
    main()
