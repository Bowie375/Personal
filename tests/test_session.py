"""Session integration: bridge + level + profile, end-to-end."""

from __future__ import annotations

import json
import socket
import time
from pathlib import Path

import pytest

from robot_forge.bridge.session import ACTION_SET_TORQUE, LevelSession
from robot_forge.core.profile import ProfileStore


def _make_client(port: int) -> socket.socket:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.bind(("127.0.0.1", 0))
    s.settimeout(3.0)
    return s


def _send_action(sock: socket.socket, name: str, payload: dict, port: int) -> None:
    msg = json.dumps({"action": name, "payload": payload}).encode("utf-8")
    sock.sendto(msg, ("127.0.0.1", port))


def _recv_states(sock: socket.socket, n: int) -> list[dict]:
    out: list[dict] = []
    for _ in range(n):
        data, _ = sock.recvfrom(65535)
        out.append(json.loads(data.decode("utf-8")))
    return out


def test_session_drives_level_and_saves_profile(tmp_path: Path) -> None:
    profile_path = tmp_path / "profile.json"
    port = 19999
    profile = ProfileStore(profile_path)
    sess = LevelSession("1.1", profile=profile, host="127.0.0.1", port=port, sim_hz=200.0)
    sess.start()
    try:
        client = _make_client(port)
        # Register as a client.
        _send_action(client, "ping", {}, port)
        # Apply the correct torque and let the sim run.
        from robot_forge.levels.level_1_1 import solve_steady_state_torque

        _send_action(client, ACTION_SET_TORQUE, {"value": solve_steady_state_torque() * 1.05}, port)
        # Collect states until we see won=True (max 6s).
        deadline = time.time() + 6.0
        states = []
        while time.time() < deadline:
            try:
                client.settimeout(0.5)
                data, _ = client.recvfrom(65535)
                s = json.loads(data.decode("utf-8"))
                states.append(s)
                if s.get("extras", {}).get("won"):
                    break
            except TimeoutError:
                pass
        client.close()
        assert any(s["extras"]["won"] for s in states), (
            f"never won. last rpm={states[-1]['joints']}"
        )
    finally:
        sess.stop()

    # Profile should record completion + at least one attempt.
    p = ProfileStore(profile_path).load()
    assert "1.1" in p.completed
    assert p.level_records["1.1"].attempts >= 1


def test_session_handles_reset_action(tmp_path: Path) -> None:
    port = 19998
    sess = LevelSession("1.1", profile=None, host="127.0.0.1", port=port, sim_hz=200.0)
    sess.start()
    try:
        client = _make_client(port)
        _send_action(client, "ping", {}, port)
        _send_action(client, ACTION_SET_TORQUE, {"value": 1.0}, port)
        time.sleep(0.2)
        before = sess.level.state.angle_rad
        _send_action(client, "reset", {}, port)
        time.sleep(0.2)
        after = sess.level.state.angle_rad
        client.close()
        # After reset the level is fresh: state should not have accumulated.
        assert sess.level.state.omega_rad_s == 0.0
        assert after <= before + 0.1  # tiny integration window, but reset must clear
    finally:
        sess.stop()


@pytest.mark.timeout(10)
def test_session_clamps_unknown_action(tmp_path: Path) -> None:
    sess = LevelSession("1.1", profile=None, port=19997, sim_hz=200.0)
    sess.start()
    try:
        client = _make_client(19997)
        _send_action(client, "not_a_real_action", {"value": 1.0}, 19997)
        time.sleep(0.1)
        client.close()
        # No crash, level state still pristine.
        assert sess.level.applied_torque == 0.0
    finally:
        sess.stop()
