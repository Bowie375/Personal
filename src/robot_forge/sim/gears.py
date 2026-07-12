"""Gear catalog and ratio math.

Real-world gear geometry is governed by the module m = d / N (pitch_diameter / teeth).
For two meshing gears, the module must match. We use a small standard module so all
gears in the catalog mesh.

Act 2.3 will use planetary gear ratios: (1 + N_ring / N_sun) for a simple planetary,
or the Willis formula for compound planets.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

# Standard module (mm-ish, sim units): all catalog gears share this so they mesh.
STANDARD_MODULE = 1.0

# Pressure angle — typical for spur gears.
PRESSURE_ANGLE_DEG = 20.0


@dataclass(frozen=True)
class SpurGear:
    """A simple involute spur gear. All dimensions in sim units (m-like)."""

    teeth: int
    module: float = STANDARD_MODULE

    @property
    def pitch_radius(self) -> float:
        return self.module * self.teeth / 2.0

    @property
    def pitch_diameter(self) -> float:
        return self.module * self.teeth

    @property
    def addendum(self) -> float:
        return self.module

    @property
    def dedendum(self) -> float:
        return 1.25 * self.module

    @property
    def outer_radius(self) -> float:
        return self.pitch_radius + self.addendum

    @property
    def root_radius(self) -> float:
        return self.pitch_radius - self.dedendum

    @property
    def thickness(self) -> float:
        return 6.0 * self.module

    @property
    def mass(self) -> float:
        # Approximate as a solid cylinder of steel-ish density for sim inertia.
        rho = 7850.0
        return rho * math.pi * self.pitch_radius**2 * self.thickness


# Catalog: standard tooth counts so any two mesh, and ratios come out clean.
CATALOG: dict[str, SpurGear] = {f"N{n}": SpurGear(n) for n in (12, 16, 20, 24, 30, 36, 40, 48, 60)}


def center_distance(a: SpurGear, b: SpurGear) -> float:
    """Two gears mesh when their pitch circles are tangent. Distance = r_a + r_b."""
    return a.pitch_radius + b.pitch_radius


def gear_ratio(driver: SpurGear, driven: SpurGear) -> float:
    """Speed ratio (driver angular speed / driven angular speed). Magnitude only;
    sign is determined by mesh geometry (idler flips sign)."""
    return driven.teeth / driver.teeth


def ratio_from_names(driver: str, driven: str) -> float:
    return gear_ratio(CATALOG[driver], CATALOG[driven])


def mesh_sign(num_external_meshes: int) -> int:
    """Sign of (driver speed) -> (output speed) for a chain of external meshes.
    Each external mesh flips sign.
    Returns +1 or -1.

    A 3-gear chain (driver -> idler -> output) has 2 external meshes -> sign +1.
    A 2-gear chain (driver -> output) has 1 external mesh -> sign -1.
    """
    return -1 if num_external_meshes % 2 == 1 else 1


def planetary_ratio(sun: SpurGear, ring: SpurGear) -> float:
    """Simple planetary: carrier fixed, sun drives, ring driven, or vice versa.
    With carrier fixed: w_sun * N_sun + w_ring * N_ring = 0  =>  ratio = -N_ring / N_sun.
    With ring fixed (sun drives, carrier driven):
        w_carrier = w_sun * N_sun / (N_sun + N_ring).
    Returns the carrier/output ratio when ring is fixed (the most common case).
    """
    return sun.teeth / (sun.teeth + ring.teeth)


def find_ratio_combo(target: float, tolerance: float = 0.02) -> list[tuple[str, str, float]]:
    """Return (driver, driven, ratio) tuples whose ratio is within tolerance of target.
    Used by Act 1.4 to validate the player's gear choice.
    """
    matches: list[tuple[str, str, float]] = []
    for d_name, d in CATALOG.items():
        for n_name, n in CATALOG.items():
            if d_name == n_name:
                continue
            r = gear_ratio(d, n)
            if abs(r - target) <= tolerance * abs(target):
                matches.append((d_name, n_name, r))
    return matches


if __name__ == "__main__":
    print("Standard module:", STANDARD_MODULE)
    print("Catalog pitches:", [(k, v.pitch_radius) for k, v in CATALOG.items()])
    print("N20 drives N40 -> ratio", gear_ratio(CATALOG["N20"], CATALOG["N40"]))
    print(
        "Planetary N20 sun + N60 ring (ring fixed):",
        planetary_ratio(CATALOG["N20"], CATALOG["N60"]),
    )
    print("3:1 target combos:", find_ratio_combo(3.0))
