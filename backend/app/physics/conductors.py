"""Exact electrostatic field solver for axisymmetric point-charge conductors
(sphere-sphere, sphere-plane, rod-rod-as-spheres, needle-as-small-sphere).

Method: successive images (Maxwell/Russell's classical method for two-sphere
gap capacitance, generalized here to sphere-plane by treating the plane as a
conductor whose "image" operation is a mirror reflection). Every conductor's
charge distribution is represented by a converging series of point charges on
the symmetry axis; the field anywhere in space is the exact superposition of
those point charges plus their partner conductor's images.

This is the same physics used to build the IEC 60052 sphere-gap calibration
tables, so accuracy is good as long as the gap is not vanishingly small
compared to the electrode radii (the series still converges, just needs more
terms).
"""
from __future__ import annotations

import math
from dataclasses import dataclass

EPS0 = 8.8541878128e-12  # F/m
K = 1.0 / (4.0 * math.pi * EPS0)


@dataclass
class PointCharge:
    q: float  # coulombs
    z: float  # position on the symmetry axis, meters


class Sphere:
    """A spherical conductor centered on the axis at z=center_z."""

    def __init__(self, radius_m: float, center_z_m: float):
        self.radius = radius_m
        self.center_z = center_z_m

    def self_charge(self, potential_v: float) -> PointCharge:
        return PointCharge(4.0 * math.pi * EPS0 * self.radius * potential_v, self.center_z)

    def image_of(self, charge: PointCharge) -> PointCharge:
        d = charge.z - self.center_z
        dist = abs(d)
        if dist < 1e-12:
            # Degenerate: charge at this sphere's own center contributes no
            # useful image (already perfectly represented).
            return PointCharge(0.0, self.center_z)
        q_img = -charge.q * self.radius / dist
        z_img = self.center_z + math.copysign(self.radius**2 / dist, d)
        return PointCharge(q_img, z_img)


class Plane:
    """A grounded (or fixed-potential) infinite plane perpendicular to the axis."""

    def __init__(self, z_m: float = 0.0):
        self.z = z_m

    def self_charge(self, potential_v: float) -> PointCharge | None:
        # A plane held at a nonzero potential still needs no seed charge in
        # this two-conductor formulation when the *other* conductor is what
        # carries the interesting nonzero potential; for the symmetric
        # rod-rod case both electrodes are modeled as spheres instead.
        return None

    def image_of(self, charge: PointCharge) -> PointCharge:
        return PointCharge(-charge.q, 2.0 * self.z - charge.z)


def solve_two_conductor(cond1, v1: float, cond2, v2: float, max_terms: int = 60, tol: float = 1e-9):
    """Return (charges1, charges2): the point-charge series representing
    cond1 (held at v1) and cond2 (held at v2), accurate to the given
    fractional tolerance on the last added term relative to the first term.
    """
    seed1 = cond1.self_charge(v1) if hasattr(cond1, "self_charge") else None
    seed2 = cond2.self_charge(v2) if hasattr(cond2, "self_charge") else None

    all1 = [seed1] if seed1 else []
    all2 = [seed2] if seed2 else []
    pending1 = list(all1)
    pending2 = list(all2)

    ref_mag = max([abs(c.q) for c in all1 + all2] or [1.0])

    for _ in range(max_terms):
        new2 = [cond2.image_of(c) for c in pending1]
        new1 = [cond1.image_of(c) for c in pending2]
        all1.extend(new1)
        all2.extend(new2)
        pending1, pending2 = new1, new2
        largest_new = max([abs(c.q) for c in new1 + new2], default=0.0)
        if largest_new < tol * ref_mag:
            break

    return all1, all2


def field_at(r: float, z: float, charges: list[PointCharge]) -> tuple[float, float]:
    """Electric field (Er, Ez) at cylindrical point (r, z) due to a set of
    on-axis point charges, V/m.
    """
    er = 0.0
    ez = 0.0
    for c in charges:
        dz = z - c.z
        dist2 = r * r + dz * dz
        if dist2 < 1e-24:
            continue
        dist = math.sqrt(dist2)
        e_mag = K * c.q / dist2
        er += e_mag * (r / dist)
        ez += e_mag * (dz / dist)
    return er, ez


def field_magnitude(r: float, z: float, charges: list[PointCharge]) -> float:
    er, ez = field_at(r, z, charges)
    return math.hypot(er, ez)


def potential_at(r: float, z: float, charges: list[PointCharge]) -> float:
    v = 0.0
    for c in charges:
        dz = z - c.z
        dist = math.hypot(r, dz)
        if dist < 1e-12:
            continue
        v += K * c.q / dist
    return v


def surface_max_field(sphere: Sphere, all_charges: list[PointCharge], n_samples: int = 361):
    """Sample the field magnitude around a sphere's meridian and return the
    (max_field, theta_rad, r, z) of the strongest point. theta=0 points along
    +z from the sphere center.
    """
    best = (0.0, 0.0, 0.0, 0.0)
    for i in range(n_samples):
        theta = math.pi * i / (n_samples - 1)
        r = sphere.radius * math.sin(theta)
        z = sphere.center_z + sphere.radius * math.cos(theta)
        mag = field_magnitude(r, z, all_charges)
        if mag > best[0]:
            best = (mag, theta, r, z)
    return best
