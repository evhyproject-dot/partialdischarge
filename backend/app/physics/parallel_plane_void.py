"""Parallel-plane electrodes with a solid insulation sample containing an
internal void -- the standard IEC 60270-style lab PD test cell, as opposed
to the coaxial-cable-specific geometry in coaxial_void.py.

Parallel-plate (no fringing) assumption: electrode diameter is assumed much
larger than the sample thickness, so the field is uniform and purely
through-thickness except locally at the void. Same two-layer
transient/steady-state (Maxwell-Wagner) treatment as coaxial_void.py.
"""
from __future__ import annotations

import math

from .dielectric_layers import two_layer_fields, voltage_for_layer2_field
from .environment import Environment, paschen_breakdown_voltage_v

EPS0 = 8.8541878128e-12


def analyze_parallel_plane_void(
    electrode_diameter_mm: float,
    sample_thickness_mm: float,
    voltage_kv: float,
    insulation_epsilon_r: float,
    insulation_sigma_s_per_m: float,
    void_position_mm: float,
    void_thickness_mm: float,
    void_diameter_mm: float,
    void_gas_epsilon_r: float,
    void_gas_sigma_s_per_m: float,
    void_gas_dielectric_strength: float,
    env: Environment,
):
    thickness = sample_thickness_mm / 1000.0
    electrode_r = electrode_diameter_mm / 2000.0
    v = voltage_kv * 1000.0

    t_void = void_thickness_mm / 1000.0
    d_solid = max(thickness - t_void, 1e-6)
    void_pos = min(max(void_position_mm / 1000.0, 0.0), thickness - t_void)

    e_bulk = v / thickness

    layers = two_layer_fields(v, d_solid, insulation_epsilon_r, insulation_sigma_s_per_m,
                               t_void, void_gas_epsilon_r, void_gas_sigma_s_per_m)
    e_void_transient = layers["layer2_field_transient_v_per_m"]
    e_void_steady = layers["layer2_field_steady_v_per_m"]
    e_solid_transient = layers["layer1_field_transient_v_per_m"]
    e_solid_steady = layers["layer1_field_steady_v_per_m"]

    v_breakdown_void = paschen_breakdown_voltage_v(void_thickness_mm / 10.0, env, void_gas_dielectric_strength)
    e_void_breakdown = v_breakdown_void / t_void

    v_inception_transient = voltage_for_layer2_field(
        e_void_breakdown, d_solid, insulation_epsilon_r, insulation_sigma_s_per_m,
        t_void, void_gas_epsilon_r, void_gas_sigma_s_per_m, "transient") / 1000.0
    v_inception_steady = voltage_for_layer2_field(
        e_void_breakdown, d_solid, insulation_epsilon_r, insulation_sigma_s_per_m,
        t_void, void_gas_epsilon_r, void_gas_sigma_s_per_m, "steady") / 1000.0

    void_r = void_diameter_mm / 2000.0
    a_void = math.pi * void_r**2
    remaining_solid = max(thickness - (void_pos + t_void / 2.0), 1e-6)
    ca = EPS0 * void_gas_epsilon_r * a_void / t_void
    cb = EPS0 * insulation_epsilon_r * a_void / remaining_solid
    apparent_charge_pc = ca * v_breakdown_void * 1e12

    # Cross-section render: x = lateral distance from axis, y = depth
    # (0 = HV electrode, thickness = ground electrode). Field is uniform
    # through the solid at any given x (1-D parallel-plate approximation);
    # the void only shows up as a locally enhanced band where it exists
    # laterally and in depth. This does not resolve the true 3-D fringing
    # field right at the void's edges.
    nx, ny = 140, 140
    x_extent = max(electrode_r * 1.05, void_r * 3.0)
    xs = [-x_extent + 2 * x_extent * i / (nx - 1) for i in range(nx)]
    ys = [thickness * i / (ny - 1) for i in range(ny)]

    field_grid = []
    for y in ys:
        row = []
        for x in xs:
            if abs(x) > electrode_r:
                row.append(None)
                continue
            in_void_band = void_pos <= y <= void_pos + t_void
            if in_void_band and abs(x) <= void_r:
                row.append(e_void_steady)
            else:
                row.append(e_solid_steady)
        field_grid.append(row)

    status_transient = "above_onset" if voltage_kv >= v_inception_transient else "below_onset"
    status_steady = "above_onset" if voltage_kv >= v_inception_steady else "below_onset"

    return {
        "geometry": {
            "thickness_m": thickness,
            "electrode_radius_m": electrode_r,
            "void_depth_m": void_pos,
            "void_radius_m": void_r,
            "bulk_average_field_v_per_m": e_bulk,
        },
        "grid": {"x": xs, "y": ys, "field_v_per_m": field_grid},
        "void": {
            "field_transient_v_per_m": e_void_transient,
            "field_steady_v_per_m": e_void_steady,
            "breakdown_voltage_v": v_breakdown_void,
            "breakdown_field_v_per_m": e_void_breakdown,
            "capacitance_ca_f": ca,
            "capacitance_cb_f": cb,
            "apparent_charge_pc": apparent_charge_pc,
            "relaxation_time_constant_s": layers["relaxation_time_constant_s"],
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
        "max_field_v_per_m": max(e_void_steady, e_solid_steady),
    }
