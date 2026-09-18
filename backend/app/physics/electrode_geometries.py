"""Point/sphere-electrode DC corona geometries: needle-plane, sphere-plane,
and sphere-sphere (rod-rod) gaps. All three share the same exact point-charge
field solver (conductors.py); they differ only in how the two conductors and
their radii are set up.

Needle-plane is modeled as a small sphere (radius = needle tip radius) above
a grounded plane. This is a standard engineering approximation for the tip
region of a rod/needle electrode -- it reproduces the strong field
concentration a sharp point produces without requiring a separate
hyperboloid solution, and gives an exact solution of Laplace's equation for
that equivalent shape.

Ion mobility used for the indicative corona-current estimate is a fixed
typical value for air; it is not yet exposed as a UI parameter.
"""
from __future__ import annotations

import math

from . import conductors as cd
from .environment import Environment, peek_onset_gradient_kv_cm

ION_MOBILITY_M2_PER_VS = 1.5e-4  # typical positive-ion mobility in air


def _grid(r_max: float, z_min: float, z_max: float, nr: int = 70, nz: int = 100):
    rs = [r_max * i / (nr - 1) for i in range(nr)]
    zs = [z_min + (z_max - z_min) * i / (nz - 1) for i in range(nz)]
    return rs, zs


def _build_field_map(charges, rs, zs, exclude_regions):
    """exclude_regions: list of callables (r, z) -> True if the point is
    inside a conductor (masked out, returned as None in the grid)."""
    field_grid = []
    potential_grid = []
    for z in zs:
        frow = []
        prow = []
        for r in rs:
            if any(fn(r, z) for fn in exclude_regions):
                frow.append(None)
                prow.append(None)
                continue
            frow.append(cd.field_magnitude(r, z, charges))
            prow.append(cd.potential_at(r, z, charges))
        field_grid.append(frow)
        potential_grid.append(prow)
    return field_grid, potential_grid


def _corona_current_ma(voltage_kv: float, onset_kv: float, gap_m: float, electrode_radius_m: float) -> float:
    """Rough order-of-magnitude DC corona current above onset.

    Uses the classical Townsend/Kaptzov quadratic V(V-V0) scaling (well
    established qualitatively for corona V-I characteristics), with a
    prefactor built from ion mobility, the gap length, and the small
    electrode's radius as the characteristic dimension of the space-charge
    sheath. The absolute magnitude is only indicative -- treat this as
    "roughly this order of magnitude and this qualitative trend", not a
    calibrated prediction; the classical formula it's adapted from was
    derived for wire-cylinder geometry, not a localized point/sphere source.
    """
    if voltage_kv <= onset_kv:
        return 0.0
    v = voltage_kv * 1000.0
    v0 = onset_kv * 1000.0
    k = math.pi * cd.EPS0 * ION_MOBILITY_M2_PER_VS * electrode_radius_m / (gap_m**3)
    i_amps = k * v * (v - v0)
    return i_amps * 1000.0  # mA


def analyze_needle_plane(tip_radius_mm: float, gap_mm: float, voltage_kv: float, env: Environment, gas_strength: float = 1.0):
    r1 = tip_radius_mm / 1000.0
    gap = gap_mm / 1000.0
    center1 = gap + r1

    sphere1 = cd.Sphere(r1, center1)
    plane = cd.Plane(0.0)

    charges1_unit, charges2_unit = cd.solve_two_conductor(sphere1, 1000.0, plane, 0.0)
    all_unit = charges1_unit + charges2_unit
    e_max_unit, theta, r_pt, z_pt = cd.surface_max_field(sphere1, all_unit)
    k_field = e_max_unit  # V/m per kV, since solved at V1 = 1000 V = 1 kV

    onset_kv_cm = peek_onset_gradient_kv_cm(tip_radius_mm / 10.0, env, gas_strength)
    onset_v_per_m = onset_kv_cm * 1e5
    v_inception = onset_v_per_m / k_field

    charges1, charges2 = cd.solve_two_conductor(sphere1, voltage_kv * 1000.0, plane, 0.0)
    all_charges = charges1 + charges2
    e_max, *_ = cd.surface_max_field(sphere1, all_charges)

    r_max = max(2.0 * gap, 6.0 * r1, 1e-4)
    z_max = center1 + r1 + 0.3 * gap
    rs, zs = _grid(r_max, -0.1 * gap, z_max)

    def inside_sphere(r, z):
        return (r**2 + (z - center1) ** 2) < r1**2

    def inside_plane(r, z):
        return z < 0.0

    field_grid, potential_grid = _build_field_map(all_charges, rs, zs, [inside_sphere, inside_plane])

    return {
        "grid": {"r": rs, "z": zs},
        "field_magnitude_v_per_m": field_grid,
        "potential_v": potential_grid,
        "max_field_v_per_m": e_max,
        "max_field_location": {"r": r_pt, "z": z_pt},
        "electrode_geometry": {
            "sphere1": {"radius_m": r1, "center_z_m": center1},
            "plane_z_m": 0.0,
        },
        "inception": {
            "onset_gradient_kv_cm": onset_kv_cm,
            "inception_voltage_kv": v_inception,
            "applied_voltage_kv": voltage_kv,
            "margin_ratio": voltage_kv / v_inception,
            "status": "above_onset" if voltage_kv >= v_inception else "below_onset",
        },
        "corona_current_ma": _corona_current_ma(voltage_kv, v_inception, gap, r1),
    }


def analyze_sphere_plane(sphere_radius_mm: float, gap_mm: float, voltage_kv: float, env: Environment, gas_strength: float = 1.0):
    r1 = sphere_radius_mm / 1000.0
    gap = gap_mm / 1000.0
    center1 = gap + r1

    sphere1 = cd.Sphere(r1, center1)
    plane = cd.Plane(0.0)

    charges1_unit, charges2_unit = cd.solve_two_conductor(sphere1, 1000.0, plane, 0.0)
    all_unit = charges1_unit + charges2_unit
    e_max_unit, theta, r_pt, z_pt = cd.surface_max_field(sphere1, all_unit)
    k_field = e_max_unit  # V/m per kV, since solved at V1 = 1000 V = 1 kV

    onset_kv_cm = peek_onset_gradient_kv_cm(sphere_radius_mm / 10.0, env, gas_strength)
    onset_v_per_m = onset_kv_cm * 1e5
    v_inception = onset_v_per_m / k_field

    charges1, charges2 = cd.solve_two_conductor(sphere1, voltage_kv * 1000.0, plane, 0.0)
    all_charges = charges1 + charges2
    e_max, *_ = cd.surface_max_field(sphere1, all_charges)

    r_max = max(2.0 * gap, 4.0 * r1, 1e-4)
    z_max = center1 + r1 + 0.3 * gap
    rs, zs = _grid(r_max, -0.1 * gap, z_max)

    def inside_sphere(r, z):
        return (r**2 + (z - center1) ** 2) < r1**2

    def inside_plane(r, z):
        return z < 0.0

    field_grid, potential_grid = _build_field_map(all_charges, rs, zs, [inside_sphere, inside_plane])

    return {
        "grid": {"r": rs, "z": zs},
        "field_magnitude_v_per_m": field_grid,
        "potential_v": potential_grid,
        "max_field_v_per_m": e_max,
        "max_field_location": {"r": r_pt, "z": z_pt},
        "electrode_geometry": {
            "sphere1": {"radius_m": r1, "center_z_m": center1},
            "plane_z_m": 0.0,
        },
        "inception": {
            "onset_gradient_kv_cm": onset_kv_cm,
            "inception_voltage_kv": v_inception,
            "applied_voltage_kv": voltage_kv,
            "margin_ratio": voltage_kv / v_inception,
            "status": "above_onset" if voltage_kv >= v_inception else "below_onset",
        },
        "corona_current_ma": _corona_current_ma(voltage_kv, v_inception, gap, r1),
    }


def analyze_sphere_sphere(electrode_radius_mm: float, gap_mm: float, voltage_kv: float, env: Environment, gas_strength: float = 1.0):
    r1 = electrode_radius_mm / 1000.0
    gap = gap_mm / 1000.0
    half_span = gap / 2.0 + r1
    center1 = half_span
    center2 = -half_span

    sphere1 = cd.Sphere(r1, center1)
    sphere2 = cd.Sphere(r1, center2)

    charges1_unit, charges2_unit = cd.solve_two_conductor(sphere1, 1000.0, sphere2, 0.0)
    all_unit = charges1_unit + charges2_unit
    e_max_unit, theta, r_pt, z_pt = cd.surface_max_field(sphere1, all_unit)
    k_field = e_max_unit  # V/m per kV, since solved at V1 = 1000 V = 1 kV

    onset_kv_cm = peek_onset_gradient_kv_cm(electrode_radius_mm / 10.0, env, gas_strength)
    onset_v_per_m = onset_kv_cm * 1e5
    v_inception = onset_v_per_m / k_field

    charges1, charges2 = cd.solve_two_conductor(sphere1, voltage_kv * 1000.0, sphere2, 0.0)
    all_charges = charges1 + charges2
    e_max, *_ = cd.surface_max_field(sphere1, all_charges)

    r_max = max(2.0 * gap, 4.0 * r1, 1e-4)
    z_max = center1 + r1 + 0.3 * gap
    z_min = center2 - r1 - 0.3 * gap
    rs, zs = _grid(r_max, z_min, z_max)

    def inside_sphere1(r, z):
        return (r**2 + (z - center1) ** 2) < r1**2

    def inside_sphere2(r, z):
        return (r**2 + (z - center2) ** 2) < r1**2

    field_grid, potential_grid = _build_field_map(all_charges, rs, zs, [inside_sphere1, inside_sphere2])

    return {
        "grid": {"r": rs, "z": zs},
        "field_magnitude_v_per_m": field_grid,
        "potential_v": potential_grid,
        "max_field_v_per_m": e_max,
        "max_field_location": {"r": r_pt, "z": z_pt},
        "electrode_geometry": {
            "sphere1": {"radius_m": r1, "center_z_m": center1},
            "sphere2": {"radius_m": r1, "center_z_m": center2},
        },
        "inception": {
            "onset_gradient_kv_cm": onset_kv_cm,
            "inception_voltage_kv": v_inception,
            "applied_voltage_kv": voltage_kv,
            "margin_ratio": voltage_kv / v_inception,
            "status": "above_onset" if voltage_kv >= v_inception else "below_onset",
        },
        "corona_current_ma": _corona_current_ma(voltage_kv, v_inception, gap, r1),
    }
