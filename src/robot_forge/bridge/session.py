"""Session: wires a level to the bridge, drives the sim loop, broadcasts state."""

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

logger = logging.getLogger(__name__)

# Action names the UI can send.
ACTION_SET_TORQUE = "set_torque"
ACTION_SET_VOLTAGE = "set_voltage"
ACTION_SET_GEARS = "set_gears"
ACTION_RESET = "reset"
ACTION_PING = "ping"


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
        self.level = self._build_level(level_id)
        self.bridge = BridgeServer(host=host, port=port, on_action=self._on_action)
        self._sim_period = 1.0 / sim_hz
        self._running = False
        self._thread: threading.Thread | None = None

    def _build_level(self, level_id: str):
        if level_id == "1.1":
            return ShaftLevel()
        if level_id == "1.2":
            return TwoGearLevel()
        raise ValueError(f"Unknown level: {level_id}")

    def _on_action(self, action) -> None:
        name = action.name
        payload = action.payload
        if name == ACTION_SET_TORQUE and hasattr(self.level, "set_torque"):
            self.level.set_torque(float(payload.get("value", 0.0)))
        elif name == ACTION_SET_VOLTAGE and hasattr(self.level, "set_voltage"):
            self.level.set_voltage(float(payload.get("value", 0.0)))
        elif name == ACTION_SET_GEARS and hasattr(self.level, "set_gears"):
            d = int(payload.get("driver", 0))
            dn = int(payload.get("driven", 0))
            if d > 0 and dn > 0:
                self.level.set_gears(driver_teeth=d, driven_teeth=dn)
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
            dt = DT_1_2 if self.level_id == "1.2" else DT_1_1
            self.level.step(dt)
            extras = (
                _summary_1_2(self.level) if self.level_id == "1.2" else _summary_1_1(self.level)
            )
            joints = self._joints_for(self.level_id, self.level)
            self.bridge.broadcast(
                SimState(timestamp=extras.get("t", 0.0), joints=joints, extras=extras)
            )

    def _joints_for(self, level_id: str, level) -> list[dict]:
        if level_id == "1.2":
            return [
                {"id": 0, "rpm": level.driver_rpm, "angle": level.state.driver_angle},
                {"id": 1, "rpm": level.driven_rpm, "angle": level.state.driven_angle},
            ]
        # Default: 1.1 — single shaft.
        return [{"id": 0, "rpm": level.rpm, "angle": level.state.angle_rad}]


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
