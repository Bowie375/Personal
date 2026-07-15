"""Gear catalog and ratio math.

Real-world gear geometry is governed by the module m = d / N (pitch_diameter / teeth).
For two meshing gears, the module must match. We use a small standard module so all
gears in the catalog mesh.

Act 2.2 uses planetary gear ratios. A simple planetary has three co-axial
members (sun, ring, carrier) and idler planets between sun (external mesh)
and ring (internal mesh). The Willis equation ties the three member speeds
once one is grounded:

    (w_sun - w_carrier) / (w_ring - w_carrier) = -N_ring / N_sun

Grounding one member and driving a second leaves the third as output — the
SAME gearset gives three different ratios. See ``planetary_gear_ratio``.
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


def planetary_gear_ratio(sun: SpurGear, ring: SpurGear, mode: str = "ring_fixed") -> float:
    """Signed output-speed / input-speed ratio for a simple planetary set.

    The three co-axial members are sun (S), ring (R), carrier (C). Planets
    idler between sun (external mesh — flips sign) and ring (internal mesh —
    no flip), so *relative to the carrier* the sun and ring counter-rotate:

        (w_sun - w_C) / (w_R - w_C) = -N_R / N_S            (Willis)

    Grounding one member and driving a second leaves the third as the output.
    The SAME gearset therefore yields three different ratios — the whole
    reason planetary boxes are the standard robot-joint reducer.

    Returns ``w_output / w_input`` (signed: + same direction as the input,
    - opposite). Input is always the sun (the motor shaft); the output and
    grounded member depend on ``mode``:

    - ``"ring_fixed"``    (default): ring pinned, sun drives, carrier out.
      ``w_C = w_S * N_S/(N_S+N_R)``  ->  ratio = 1 + N_R/N_S  (>1, reduction,
      same direction as the sun). The classic robot-joint reducer.
    - ``"sun_fixed"``     : sun pinned, ring drives, carrier out.
      ``w_C = w_R * N_R/(N_S+N_R)``  ->  ratio = (1 + N_S/N_R) from ring→carrier.
      But the motor drives the SUN; with the sun pinned it can't be the input,
      so this mode is only reachable when the player drives the ring. We still
      return the carrier-vs-sun ratio = 1 + N_S/N_R for diagnostics.
    - ``"carrier_fixed"`` : carrier pinned, sun drives, ring out — a REVERSING
      gearbox. ``w_R = -w_S * N_S/N_R``  ->  ratio = -N_R/N_S (opposite
      direction). Smaller magnitude; used in robot wrists to flip direction
      compactly.

    Magnitudes only depend on the tooth counts; the sign encodes direction.
    """
    ns = sun.teeth
    nr = ring.teeth
    if mode == "ring_fixed":
        # w_C = w_S * N_S/(N_S+N_R)  =>  w_C/w_S = N_S/(N_S+N_R)
        # The "reduction" (input over output) is (N_S+N_R)/N_S = 1 + N_R/N_S.
        return (ns + nr) / ns
    if mode == "sun_fixed":
        # Motor on the ring (sun grounded): w_C = w_R * N_R/(N_S+N_R).
        # Expressed as carrier-vs-sun would-be ratio (sun is the "input" axis):
        #   w_C / w_S (if sun were free and driven) = N_S/(N_S+N_R) for ring fixed.
        # Here sun is fixed, so the sun->carrier ratio becomes 1 + N_S/N_R.
        return (ns + nr) / nr
    if mode == "carrier_fixed":
        # w_R = -w_S * N_S/N_R  ->  output (ring) / input (sun) = -N_R/N_S.
        return -nr / ns
    raise ValueError(f"unknown planetary mode: {mode!r}")


def planetary_ratio(sun: SpurGear, ring: SpurGear) -> float:
    """Back-compat: ring-fixed carrier/sun speed fraction (the output speed
    as a fraction of the sun's, i.e. 1/reduction). New code should use
    ``planetary_gear_ratio`` which returns the signed reduction directly.
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
        "Planetary N12 sun + N60 ring (ring fixed, reduction):",
        planetary_gear_ratio(CATALOG["N12"], CATALOG["N60"], "ring_fixed"),
    )
    print(
        "Planetary N12 sun + N60 ring (carrier fixed, reversing):",
        planetary_gear_ratio(CATALOG["N12"], CATALOG["N60"], "carrier_fixed"),
    )
    print("3:1 target combos:", find_ratio_combo(3.0))
