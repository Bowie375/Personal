"""Profile round-trip and unlock chain tests."""

from __future__ import annotations

from pathlib import Path

from robot_forge.core.profile import Profile, ProfileStore


def test_fresh_profile_starts_at_1_1() -> None:
    store = ProfileStore(Path("/tmp/robot_forge_test_a.json"))
    p = store.load()
    assert p.last_level == "1.1"
    assert p.is_unlocked("1.1")
    assert not p.is_unlocked("1.2")


def test_completion_unlocks_next() -> None:
    store = ProfileStore(Path("/tmp/robot_forge_test_b.json"))
    p = store.load()
    p.record_completion("1.1")
    assert p.is_unlocked("1.2")
    assert p.is_unlocked("1.3") is False


def test_save_and_reload() -> None:
    path = Path("/tmp/robot_forge_test_c.json")
    if path.exists():
        path.unlink()
    s1 = ProfileStore(path)
    p1 = s1.load()
    p1.record_attempt("1.1", diagnostic="need more torque")
    p1.record_completion("1.1")
    s1.save()
    s2 = ProfileStore(path)
    p2 = s2.load()
    assert "1.1" in p2.completed
    assert p2.level_records["1.1"].attempts == 1
    assert p2.level_records["1.1"].last_diagnostic == "need more torque"
    path.unlink(missing_ok=True)


def test_corrupt_profile_resets_gracefully() -> None:
    path = Path("/tmp/robot_forge_test_d.json")
    path.write_text("not valid json {{{")
    s = ProfileStore(path)
    p = s.load()
    assert isinstance(p, Profile)
    path.unlink(missing_ok=True)
