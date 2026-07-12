"""UDP bridge server. Listens for Godot actions, broadcasts sim state."""

from __future__ import annotations

import json
import logging
import socket
import threading
from collections.abc import Callable

from robot_forge.core.types import DEFAULT_HOST, DEFAULT_PORT, Action, SimState

logger = logging.getLogger(__name__)


class BridgeServer:
    """Non-blocking UDP server. Push sim state, receive actions."""

    def __init__(
        self,
        host: str = DEFAULT_HOST,
        port: int = DEFAULT_PORT,
        on_action: Callable[[Action], None] | None = None,
    ) -> None:
        self.host = host
        self.port = port
        self.on_action = on_action
        self._sock: socket.socket | None = None
        self._clients: set[tuple[str, int]] = set()
        self._running = False
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        """Bind socket and spawn the receive thread."""
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._sock.bind((self.host, self.port))
        self._sock.settimeout(0.1)
        self._running = True
        self._thread = threading.Thread(target=self._receive_loop, daemon=True)
        self._thread.start()
        logger.info("Bridge listening on udp://%s:%d", self.host, self.port)

    def stop(self) -> None:
        self._running = False
        if self._thread:
            self._thread.join(timeout=1.0)
        if self._sock:
            self._sock.close()

    def _receive_loop(self) -> None:
        assert self._sock is not None
        while self._running:
            try:
                data, addr = self._sock.recvfrom(65535)
            except TimeoutError:
                continue
            except OSError:
                break
            self._clients.add(addr)
            try:
                action = Action.from_json(data.decode("utf-8"))
                if self.on_action:
                    self.on_action(action)
            except (json.JSONDecodeError, KeyError, UnicodeDecodeError) as e:
                logger.warning("bad packet from %s: %s", addr, e)

    def broadcast(self, state: SimState) -> None:
        """Send a sim-state tick to all known clients."""
        if not self._sock or not self._clients:
            return
        payload = state.to_json().encode("utf-8")
        for addr in tuple(self._clients):
            try:
                self._sock.sendto(payload, addr)
            except OSError as e:
                logger.warning("send to %s failed: %s", addr, e)
                self._clients.discard(addr)


def smoke_test() -> None:
    """Local sanity check: start, send a fake state, stop."""
    import time

    actions: list[Action] = []
    server = BridgeServer(on_action=lambda a: actions.append(a))
    server.start()
    time.sleep(0.2)
    server.broadcast(SimState(timestamp=0.0, joints=[{"id": 0, "angle": 0.0}]))
    time.sleep(0.1)
    server.stop()
    print(
        f"smoke ok — received {len(actions)} actions, broadcast to {len(server._clients)} clients"
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    smoke_test()
