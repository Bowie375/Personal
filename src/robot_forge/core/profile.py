"""Player profile: persistent state across sessions. JSON file, atomic writes."""

from __future__ import annotations

import json
import os
import tempfile
import threading
from dataclasses import asdict, dataclass, field
from pathlib import Path

PROFILE_VERSION = 1


def default_profile_path() -> Path:
    """XDG-style: ~/.local/share/robot-forge/profile.json, overridable by env."""
    base = os.environ.get("ROBOT_FORGE_DATA_DIR")
    if base:
        return Path(base) / "profile.json"
    return Path.home() / ".local" / "share" / "robot-forge" / "profile.json"


@dataclass
class LevelRecord:
    """Per-level state: completed? how many attempts? last attempt result."""

    completed: bool = False
    attempts: int = 0
    last_diagnostic: str = ""


@dataclass
class Profile:
    """Player profile. Schema-versioned for safe future migrations."""

    version: int = PROFILE_VERSION
    unlocked: list[str] = field(default_factory=lambda: ["1.1"])
    completed: list[str] = field(default_factory=list)
    last_level: str = "1.1"
    level_records: dict[str, LevelRecord] = field(default_factory=dict)
    settings: dict = field(default_factory=dict)

    def record_completion(self, level_id: str) -> None:
        if level_id not in self.completed:
            self.completed.append(level_id)
        rec = self.level_records.setdefault(level_id, LevelRecord())
        rec.completed = True
        self._unlock_next(level_id)
        self.last_level = level_id

    def record_attempt(self, level_id: str, diagnostic: str = "") -> None:
        rec = self.level_records.setdefault(level_id, LevelRecord())
        rec.attempts += 1
        if diagnostic:
            rec.last_diagnostic = diagnostic

    def is_unlocked(self, level_id: str) -> bool:
        return level_id in self.unlocked

    def can_attempt(self, level_id: str) -> bool:
        return self.is_unlocked(level_id)

    def _unlock_next(self, level_id: str) -> None:
        """Linear unlock: a completed level unlocks the next in the table."""
        order = [
            "1.1",
            "1.2",
            "1.3",
            "1.4",
            "2.1",
            "2.2",
            "2.3",
            "2.4",
            "3.1",
            "3.2",
            "3.3",
            "3.4",
            "3.5",
            "4.1",
            "4.2",
            "4.3",
            "4.4",
            "5.1",
            "5.2",
            "5.3",
            "5.4",
        ]
        if level_id in order:
            idx = order.index(level_id)
            if idx + 1 < len(order) and order[idx + 1] not in self.unlocked:
                self.unlocked.append(order[idx + 1])


class ProfileStore:
    """Thread-safe load/save of the player profile."""

    def __init__(self, path: Path | None = None) -> None:
        self.path = path or default_profile_path()
        self._lock = threading.Lock()
        self._profile: Profile | None = None

    def load(self) -> Profile:
        with self._lock:
            if self._profile is not None:
                return self._profile
            if self.path.exists():
                try:
                    data = json.loads(self.path.read_text("utf-8"))
                    self._profile = self._migrate(data)
                except (json.JSONDecodeError, OSError, KeyError):
                    # Corrupt or unreadable: start fresh, don't lose the file yet.
                    self._profile = Profile()
            else:
                self._profile = Profile()
            return self._profile

    def save(self) -> None:
        with self._lock:
            if self._profile is None:
                return
            self.path.parent.mkdir(parents=True, exist_ok=True)
            payload = json.dumps(asdict(self._profile), indent=2)
            # Atomic write: temp file in same dir, then rename.
            fd, tmp = tempfile.mkstemp(dir=self.path.parent, prefix=".profile.", suffix=".tmp")
            try:
                os.write(fd, payload.encode("utf-8"))
                os.close(fd)
                fd = -1
                os.replace(tmp, self.path)
            except OSError:
                if fd >= 0:
                    os.close(fd)
                if os.path.exists(tmp):
                    os.unlink(tmp)
                raise

    def _migrate(self, data: dict) -> Profile:
        """Apply any future schema migrations. v1 is the starting version."""
        v = data.get("version", 1)
        if v == 1:
            return Profile(
                version=1,
                unlocked=data.get("unlocked", ["1.1"]),
                completed=data.get("completed", []),
                last_level=data.get("last_level", "1.1"),
                level_records={
                    k: LevelRecord(**v_) for k, v_ in data.get("level_records", {}).items()
                },
                settings=data.get("settings", {}),
            )
        # Future: elif v == 2: ...
        return Profile()


def smoke_test() -> None:
    import tempfile

    with tempfile.TemporaryDirectory() as d:
        path = Path(d) / "profile.json"
        store = ProfileStore(path)
        p = store.load()
        assert p.last_level == "1.1"
        p.record_attempt("1.1", diagnostic="spin up torque")
        p.record_completion("1.1")
        assert p.is_unlocked("1.2")
        store.save()
        # Reopen.
        store2 = ProfileStore(path)
        p2 = store2.load()
        assert "1.1" in p2.completed
        assert p2.is_unlocked("1.2")
        assert p2.level_records["1.1"].attempts == 1
        print("profile smoke ok")


if __name__ == "__main__":
    smoke_test()
