"""Coaxial cable with an internal void: internal (cavity) PD analysis.

This is physically distinct from the corona geometries -- there is no
surface streamer into open air, the discharge happens inside a small gas
cavity embedded in the solid dielectric. The model used here:

1. Bulk field in the (void-free) dielectric follows the standard coaxial
   capacitor formula E(r) = V / (r * ln(R2/R1)).
2. The void and the surrounding solid insulation are treated as a two-layer
   series dielectric stack (physics/dielectric_layers.py) to get BOTH the
   transient (capacitive, permittivity-divided) and steady-state (resistive,
   conductivity-divided) void field and inception voltage -- the DC
   Maxwell-Wagner effect. Steady state is usually far more severe for a gas
   void, since gas conductivity is typically much lower than the solid's.
3. The void breaks down per Paschen's law for its local gas gap thickness.
4. Apparent charge (IEC 60270) uses the classical "abc" equivalent-circuit
   model (Whitehead 1951, after Gemant & Philippoff 1932), simplified with
   the common Cc >> Cb assumption (bulk cable capacitance much larger than
   the void's series branch), so apparent charge approximately equals the
   real charge released in the void: q_apparent ~= Ca * dV_void.
"""
from __future__ import annotations

import math

from .dielectric_layers import two_layer_fields, voltage_for_layer2_field
from .environment import Environment, paschen_breakdown_voltage_v

EPS0 = 8.8541878128e-12


def analyze_coaxial_void(
    conductor_radius_mm: float,
    insulation_thickness_mm: float,
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
    include_grid: bool = True,
):
    r1 = conductor_radius_mm / 1000.0
    thickness = insulation_thickness_mm / 1000.0
    r2 = r1 + thickness
    ln_ratio = math.log(r2 / r1)

    v = voltage_kv * 1000.0

    def e_dielectric(r):
        return v / (r * ln_ratio)

    r_void = r1 + void_position_mm / 1000.0
    r_void = min(max(r_void, r1 + 1e-6), r2 - 1e-6)
    t_void = void_thickness_mm / 1000.0
    d_solid = max(thickness - t_void, 1e-6)

    e_diel_at_void_bulk = e_dielectric(r_void)

    layers = two_layer_fields(v, d_solid, insulation_epsilon_r, insulation_sigma_s_per_m,
                               t_void, void_gas_epsilon_r, void_gas_sigma_s_per_m)
    e_void_transient = layers["layer2_field_transient_v_per_m"]
    e_void_steady = layers["layer2_field_steady_v_per_m"]

    v_breakdown_void = paschen_breakdown_voltage_v(void_thickness_mm / 10.0, env, void_gas_dielectric_strength)
    e_void_breakdown = v_breakdown_void / t_void

    v_inception_transient = voltage_for_layer2_field(
        e_void_breakdown, d_solid, insulation_epsilon_r, insulation_sigma_s_per_m,
        t_void, void_gas_epsilon_r, void_gas_sigma_s_per_m, "transient") / 1000.0
    v_inception_steady = voltage_for_layer2_field(
        e_void_breakdown, d_solid, insulation_epsilon_r, insulation_sigma_s_per_m,
        t_void, void_gas_epsilon_r, void_gas_sigma_s_per_m, "steady") / 1000.0

    a_void = math.pi * (void_diameter_mm / 1000.0 / 2.0) ** 2
    remaining_solid = max(r2 - (r_void + t_void / 2.0), 1e-6)
    ca = EPS0 * void_gas_epsilon_r * a_void / t_void
    cb = EPS0 * insulation_epsilon_r * a_void / remaining_solid

    apparent_charge_pc = ca * v_breakdown_void * 1e12

    radial_profile_out, grid_out = None, None
    if include_grid:
        n_r = 120
        radii = [r1 + (r2 - r1) * i / (n_r - 1) for i in range(n_r)]
        field_profile = [e_dielectric(r) for r in radii]
        radial_profile_out = {"r_m": radii, "field_v_per_m": field_profile}

        n_grid = 140
        extent = r2 * 1.15
        xs = [-extent + 2 * extent * i / (n_grid - 1) for i in range(n_grid)]
        ys = list(xs)
        field_grid = []
        for y in ys:
            row = []
            for x in xs:
                r = math.hypot(x, y)
                if r < r1 or r > r2:
                    row.append(None)
                else:
                    row.append(e_dielectric(r))
            field_grid.append(row)
        grid_out = {"x": xs, "y": ys, "field_v_per_m": field_grid}

    void_angle = 0.0
    void_x = r_void * math.cos(void_angle)
    void_y = r_void * math.sin(void_angle)

    status_transient = "above_onset" if voltage_kv >= v_inception_transient else "below_onset"
    status_steady = "above_onset" if voltage_kv >= v_inception_steady else "below_onset"

    return {
        "geometry": {
            "conductor_radius_m": r1,
            "outer_radius_m": r2,
            "void_radius_m": r_void,
            "void_marker_xy": {"x": void_x, "y": void_y},
        },
        "radial_profile": radial_profile_out,
        "grid": grid_out,
        "void": {
            "field_transient_v_per_m": e_void_transient,
            "field_steady_v_per_m": e_void_steady,
            "field_bulk_dielectric_v_per_m": e_diel_at_void_bulk,
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
        "max_field_v_per_m": e_dielectric(r1),
        "utilization_factor": (v / thickness) / e_dielectric(r1),
    }
