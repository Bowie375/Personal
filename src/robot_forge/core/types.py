"""Shared types and constants for the bridge and sim layers."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

# Bridge
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 9999


@dataclass
class SimState:
    """Snapshot of a sim tick, sent to Godot."""

    timestamp: float
    joints: list[dict[str, Any]] = field(default_factory=list)
    links: list[dict[str, Any]] = field(default_factory=list)
    extras: dict[str, Any] = field(default_factory=dict)

    def to_json(self) -> str:
        return json.dumps(
            {
                "type": "state",
                "timestamp": self.timestamp,
                "joints": self.joints,
                "links": self.links,
                "extras": self.extras,
            }
        )


@dataclass
class Action:
    """A player action sent from Godot."""

    name: str
    payload: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_json(cls, raw: str) -> Action:
        data = json.loads(raw)
        return cls(name=data["action"], payload=data.get("payload", {}))

    def to_json(self) -> str:
        return json.dumps({"action": self.name, "payload": self.payload})
