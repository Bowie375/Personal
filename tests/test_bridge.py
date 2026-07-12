"""Bridge round-trip test: spin up server, send an action, expect it back."""

from __future__ import annotations

import socket
import time

from robot_forge.bridge.server import BridgeServer
from robot_forge.core.types import Action, SimState


def test_action_received() -> None:
    received: list[Action] = []
    server = BridgeServer(on_action=lambda a: received.append(a))
    server.start()
    try:
        time.sleep(0.1)
        # Register as a client by sending a packet from a UDP socket.
        sender = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sender.sendto(b'{"action": "ping", "payload": {"value": 42}}', ("127.0.0.1", 9999))
        sender.close()
        time.sleep(0.2)
        assert len(received) == 1
        assert received[0].name == "ping"
        assert received[0].payload == {"value": 42}
    finally:
        server.stop()


def test_broadcast_reaches_client() -> None:
    server = BridgeServer()
    server.start()
    try:
        time.sleep(0.1)
        # Pretend to be a Godot client: bind a socket, register by sending something.
        client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        client.bind(("127.0.0.1", 0))
        client.settimeout(2.0)
        # Send a dummy action to register.
        client.sendto(b'{"action": "hello"}', ("127.0.0.1", 9999))
        time.sleep(0.1)
        # Now broadcast.
        server.broadcast(SimState(timestamp=1.0, joints=[{"id": 0, "angle": 0.5}]))
        data, _ = client.recvfrom(65535)
        client.close()
        text = data.decode("utf-8")
        assert '"type": "state"' in text
        assert '"timestamp": 1.0' in text
    finally:
        server.stop()
