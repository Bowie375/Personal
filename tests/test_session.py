"""Session integration: bridge + level + profile, end-to-end."""

from __future__ import annotations

import json
import socket
import time
from pathlib import Path

import pytest

from robot_forge.bridge.session import (
    ACTION_SET_VOLTAGE,
    LevelSession,
)
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
        # Apply the correct voltage and let the sim run.
        from robot_forge.levels.level_1_1 import solve_steady_state_voltage

        _send_action(
            client,
            ACTION_SET_VOLTAGE,
            {"value": solve_steady_state_voltage() * 1.05},
            port,
        )
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
        _send_action(client, ACTION_SET_VOLTAGE, {"value": 8.0}, port)
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
        assert sess.level.applied_voltage == 0.0
    finally:
        sess.stop()


def test_session_runs_level_1_2_and_wins(tmp_path: Path) -> None:
    """End-to-end for Act 1.2: voltage action drives a 1:1 gear pair to target."""
    profile_path = tmp_path / "profile_12.json"
    port = 19996
    profile = ProfileStore(profile_path)
    sess = LevelSession("1.2", profile=profile, port=port, sim_hz=200.0)
    sess.start()
    try:
        client = _make_client(port)
        _send_action(client, "ping", {}, port)
        from robot_forge.levels.level_1_2 import solve_driving_voltage

        v = solve_driving_voltage(
            sess.level.target_driven_rpm, sess.level.driver, sess.level.driven
        )
        _send_action(client, ACTION_SET_VOLTAGE, {"value": abs(v) * 1.01}, port)
        deadline = time.time() + 12.0
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
            f"1.2 never won after 12s; last extras: {states[-1]['extras'] if states else 'no states'}"
        )
    finally:
        sess.stop()
    p = ProfileStore(profile_path).load()
    assert "1.2" in p.completed


def test_session_set_gears_action_swaps_pair(tmp_path: Path) -> None:
    port = 19995
    sess = LevelSession("1.2", profile=None, port=port, sim_hz=200.0)
    sess.start()
    try:
        client = _make_client(port)
        _send_action(client, "ping", {}, port)
        _send_action(client, "set_gears", {"driver": 20, "driven": 60}, port)
        time.sleep(0.1)
        client.close()
        assert sess.level.driver.teeth == 20
        assert sess.level.driven.teeth == 60
    finally:
        sess.stop()


def test_session_set_level_swaps_active_level_at_runtime(tmp_path: Path) -> None:
    """A single bridge process serves all levels: `set_level` rebuilds the
    active level without restarting the backend."""
    port = 19994
    sess = LevelSession("1.1", profile=None, port=port, sim_hz=200.0)
    sess.start()
    try:
        client = _make_client(port)
        _send_action(client, "ping", {}, port)
        # Start in 1.1 (shaft) — should be a ShaftLevel.
        from robot_forge.levels.level_1_1 import ShaftLevel

        assert isinstance(sess.level, ShaftLevel)
        # Godot sends set_level to switch to 1.3 (three-gear).
        _send_action(client, "set_level", {"id": "1.3"}, port)
        time.sleep(0.15)
        from robot_forge.levels.level_1_3 import ThreeGearLevel

        assert isinstance(sess.level, ThreeGearLevel)
        assert sess.level_id == "1.3"
        # The new level is fresh (not the old 1.1 state).
        assert sess.level.state.driven_omega == 0.0
        client.close()
    finally:
        sess.stop()


def test_session_boots_without_level_and_waits_for_set_level(tmp_path: Path) -> None:
    """Omitting --level starts the bridge idle; it serves nothing until
    Godot sends set_level. This is the normal-play path."""
    port = 19993
    sess = LevelSession(level_id=None, profile=None, port=port, sim_hz=200.0)
    sess.start()
    try:
        client = _make_client(port)
        _send_action(client, "ping", {}, port)
        # No active level: other actions are ignored, not crashing.
        _send_action(client, "set_voltage", {"value": 8.0}, port)
        time.sleep(0.1)
        assert sess.level is None
        # Now Godot picks 1.2.
        _send_action(client, "set_level", {"id": "1.2"}, port)
        time.sleep(0.15)
        from robot_forge.levels.level_1_2 import TwoGearLevel

        assert isinstance(sess.level, TwoGearLevel)
        client.close()
    finally:
        sess.stop()


def test_session_set_level_unknown_is_ignored(tmp_path: Path) -> None:
    """Unknown level id is logged and ignored; the active level is untouched."""
    port = 19992
    sess = LevelSession("1.1", profile=None, port=port, sim_hz=200.0)
    sess.start()
    try:
        client = _make_client(port)
        _send_action(client, "ping", {}, port)
        _send_action(client, "set_level", {"id": "9.9"}, port)
        time.sleep(0.15)
        # Still on 1.1.
        assert sess.level_id == "1.1"
        client.close()
    finally:
        sess.stop()

