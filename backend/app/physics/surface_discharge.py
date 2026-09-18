"""Surface discharge along a solid insulator: an HV electrode edge and a
grounded counter-electrode separated by a creepage (surface) path across a
solid dielectric, exposed to an ambient gas.

Rigorous field modeling at the electrode/insulator/gas triple junction is a
research-grade problem (the field has a geometric singularity there whose
exponent depends on the local wedge angle and the permittivity ratio --
Sommerfeld/Meixner edge conditions). This module uses a documented
engineering approximation instead:

1. The HV electrode edge is modeled as a small sphere (its radius of
   curvature) facing a grounded plane across the creepage distance, reusing
   the exact same image-charge solver as the needle-plane/sphere-plane
   geometries.
2. A classical flat-interface field-refraction factor
   k = 2*eps_r / (eps_r + 1) approximates the local field enhancement a
   dielectric substrate produces on the tangential field just above it.
3. A user-set "surface condition factor" (0-1) derates the clean-gas-gap
   Peek onset gradient to account for real-surface effects (adsorbed
   moisture, contamination, tracking) that make real surfaces flash over
   well below the idealized clean-gap prediction.
4. Transient-vs-steady-state behavior is approximated with the same
   two-layer Maxwell-Wagner analogy used for internal voids, treating the
   substrate thickness and the surface gas path as a series pair. This is a
   simplification: real HVDC surface charge accumulation is governed by
   *surface* conductivity (adsorbed layers), not the substrate's bulk
   conductivity used here -- treat the transient/steady split as
   illustrative, not quantitative, for this geometry.
"""
from __future__ import annotations

from . import conductors as cd
from .dielectric_layers import two_layer_fields
from .electrode_geometries import _ion_transit_time_s, _utilization_factor
from .environment import Environment, peek_onset_gradient_kv_cm


def _refraction_factor(eps_r: float) -> float:
    return 2.0 * eps_r / (eps_r + 1.0)


def analyze_surface_discharge(
    creepage_distance_mm: float,
    electrode_edge_radius_mm: float,
    voltage_kv: float,
    substrate_thickness_mm: float,
    substrate_epsilon_r: float,
    substrate_sigma_s_per_m: float,
    gas_epsilon_r: float,
    gas_sigma_s_per_m: float,
    gas_dielectric_strength: float,
    surface_condition_factor: float,
    env: Environment,
    include_grid: bool = True,
):
    r1 = electrode_edge_radius_mm / 1000.0
    gap = creepage_distance_mm / 1000.0
    center1 = gap + r1

    sphere1 = cd.Sphere(r1, center1)
    plane = cd.Plane(0.0)

    charges1_unit, charges2_unit = cd.solve_two_conductor(sphere1, 1000.0, plane, 0.0)
    all_unit = charges1_unit + charges2_unit
    e_max_unit, theta, r_pt, z_pt = cd.surface_max_field(sphere1, all_unit)
    k_refraction = _refraction_factor(substrate_epsilon_r)
    k_field = e_max_unit * k_refraction  # V/m per kV, with interface enhancement

    onset_kv_cm = peek_onset_gradient_kv_cm(electrode_edge_radius_mm / 10.0, env, gas_dielectric_strength)
    onset_kv_cm *= surface_condition_factor
    onset_v_per_m = onset_kv_cm * 1e5

    v = voltage_kv * 1000.0
    substrate_thickness = max(substrate_thickness_mm / 1000.0, 1e-6)
    layers = two_layer_fields(v, substrate_thickness, substrate_epsilon_r, substrate_sigma_s_per_m,
                               gap, gas_epsilon_r, gas_sigma_s_per_m)
    share_transient = (layers["layer2_field_transient_v_per_m"] * gap) / v if v > 0 else 0.0
    share_steady = (layers["layer2_field_steady_v_per_m"] * gap) / v if v > 0 else 0.0

    v_inception_transient = onset_v_per_m / (k_field * max(share_transient, 1e-9))
    v_inception_steady = onset_v_per_m / (k_field * max(share_steady, 1e-9))
    v_inception_uniform = onset_v_per_m / k_field  # ignoring the layered-voltage-share effect entirely

    charges1, charges2 = cd.solve_two_conductor(sphere1, v, plane, 0.0)
    all_charges = charges1 + charges2
    e_max_raw, *_ = cd.surface_max_field(sphere1, all_charges)
    e_max = e_max_raw * k_refraction

    grid_out, field_grid, potential_grid = None, None, None
    if include_grid:
        r_max = max(2.0 * gap, 6.0 * r1, 1e-4)
        z_max = center1 + r1 + 0.3 * gap
        nr, nz = 70, 100
        rs = [r_max * i / (nr - 1) for i in range(nr)]
        zs = [-0.1 * gap + (z_max - (-0.1 * gap)) * i / (nz - 1) for i in range(nz)]

        def inside_sphere(r, z):
            return (r**2 + (z - center1) ** 2) < r1**2

        def inside_substrate(r, z):
            return z < 0.0

        field_grid = []
        potential_grid = []
        for z in zs:
            frow, prow = [], []
            for r in rs:
                if inside_sphere(r, z) or inside_substrate(r, z):
                    frow.append(None)
                    prow.append(None)
                    continue
                frow.append(cd.field_magnitude(r, z, all_charges))
                prow.append(cd.potential_at(r, z, all_charges))
            field_grid.append(frow)
            potential_grid.append(prow)
        grid_out = {"r": rs, "z": zs}

    status_transient = "above_onset" if voltage_kv >= v_inception_transient else "below_onset"
    status_steady = "above_onset" if voltage_kv >= v_inception_steady else "below_onset"

    return {
        "grid": grid_out,
        "field_magnitude_v_per_m": field_grid,
        "potential_v": potential_grid,
        "max_field_v_per_m": e_max,
        "max_field_location": {"r": r_pt, "z": z_pt},
        "electrode_geometry": {
            "sphere1": {"radius_m": r1, "center_z_m": center1},
            "plane_z_m": 0.0,
        },
        "surface": {
            "refraction_factor": k_refraction,
            "surface_condition_factor": surface_condition_factor,
            "onset_gradient_kv_cm": onset_kv_cm,
            "voltage_share_transient": share_transient,
            "voltage_share_steady": share_steady,
            "relaxation_time_constant_s": layers["relaxation_time_constant_s"],
            "inception_voltage_uniform_kv": v_inception_uniform,
        },
        "inception": {
            "inception_voltage_transient_kv": v_inception_transient,
            "inception_voltage_steady_kv": v_inception_steady,
            "inception_voltage_kv": v_inception_steady,
            "applied_voltage_kv": voltage_kv,
            "margin_ratio": voltage_kv / v_inception_steady,
            "status": status_steady,
            "status_transient": status_transient,
            "status_steady": status_steady,
        },
        "utilization_factor": _utilization_factor(voltage_kv, gap, e_max),
        "space_charge_time_s": _ion_transit_time_s(all_charges, 1e-9 * gap, gap * (1 - 1e-9)),
    }
