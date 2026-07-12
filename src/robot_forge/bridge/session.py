"""Session: wires a level to the bridge, drives the sim loop, broadcasts state."""

from __future__ import annotations

import logging
import threading
import time

from robot_forge.bridge.server import BridgeServer
from robot_forge.core.profile import ProfileStore
from robot_forge.core.types import SimState
from robot_forge.levels.level_1_1 import DT, ShaftLevel

logger = logging.getLogger(__name__)

# Action names the UI can send.
ACTION_SET_TORQUE = "set_torque"
ACTION_RESET = "reset"
ACTION_PING = "ping"


class LevelSession:
    """Owns one level instance, runs the sim in a thread, syncs to bridge."""

    def __init__(
        self,
        level_id: str,
        profile: ProfileStore | None = None,
        host: str = "127.0.0.1",
        port: int = 9999,
        sim_hz: float = 100.0,
    ) -> None:
        self.level_id = level_id
        self.profile = profile
        self.level: ShaftLevel = self._build_level(level_id)
        self.bridge = BridgeServer(host=host, port=port, on_action=self._on_action)
        self._sim_period = 1.0 / sim_hz
        self._running = False
        self._thread: threading.Thread | None = None

    def _build_level(self, level_id: str) -> ShaftLevel:
        # Registry will grow; for now 1.1 is the only level.
        if level_id == "1.1":
            return ShaftLevel()
        raise ValueError(f"Unknown level: {level_id}")

    def _on_action(self, action) -> None:
        name = action.name
        payload = action.payload
        if name == ACTION_SET_TORQUE:
            self.level.set_torque(float(payload.get("value", 0.0)))
        elif name == ACTION_RESET:
            self.level = self._build_level(self.level_id)
        elif name == ACTION_PING:
            pass  # liveness
        else:
            logger.warning("unknown action: %s", name)

    def start(self) -> None:
        self.bridge.start()
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        logger.info("Session started for level %s", self.level_id)

    def stop(self) -> None:
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)
        self.bridge.stop()
        # Persist last attempt for cross-session continuity.
        if self.profile is not None:
            p = self.profile.load()
            diag = self.level.last_diagnostic
            p.record_attempt(self.level_id, diagnostic=diag.message if diag else "")
            if self.level.won:
                p.record_completion(self.level_id)
            self.profile.save()

    def _loop(self) -> None:
        last = time.perf_counter()
        while self._running:
            now = time.perf_counter()
            if now - last < self._sim_period:
                time.sleep(self._sim_period - (now - last))
            last = time.perf_counter()
            self.level.step(DT)
            self.bridge.broadcast(
                SimState(
                    timestamp=self.level.state.t,
                    joints=[{"id": 0, "rpm": self.level.rpm, "angle": self.level.state.angle_rad}],
                    extras={
                        "level": self.level_id,
                        "target_rpm": self.level.target_rpm,
                        "torque": self.level.applied_torque,
                        "won": self.level.won,
                        "diagnostic": self.level.last_diagnostic.to_dict()
                        if self.level.last_diagnostic
                        else None,
                    },
                )
            )


def main() -> None:
    import argparse

    p = argparse.ArgumentParser()
    p.add_argument("--level", default="1.1")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=9999)
    p.add_argument("--no-profile", action="store_true")
    args = p.parse_args()

    logging.basicConfig(level=logging.INFO)
    profile = None if args.no_profile else ProfileStore()
    sess = LevelSession(args.level, profile=profile, host=args.host, port=args.port)
    sess.start()
    try:
        while True:
            time.sleep(1.0)
    except KeyboardInterrupt:
        sess.stop()


if __name__ == "__main__":
    main()
