"""Coaxial cable with an internal void: internal (cavity) PD analysis.

This is physically distinct from the corona geometries -- there is no
surface streamer into open air, the discharge happens inside a small gas
cavity embedded in the solid dielectric. The model used here:

1. Bulk field in the (void-free) dielectric follows the standard coaxial
   capacitor formula E(r) = V / (r * ln(R2/R1)).
2. Field inside a thin, flat void whose faces are perpendicular to the local
   field is enhanced by the relative permittivity of the surrounding solid
   dielectric (displacement-field continuity: D is continuous across the
   void/dielectric interface, and D = eps0*eps_r*E_dielectric = eps0*E_void):
        E_void = eps_r * E_dielectric(r_void)
   This is the standard textbook approximation used in cable PD analysis
   (e.g. Bartnikas, "Engineering Dielectrics").
3. The void breaks down per Paschen's law for its local gas gap thickness.
4. Apparent charge (IEC 60270) uses the classical "abc" equivalent-circuit
   model (Whitehead 1951, after Gemant & Philippoff 1932), simplified with
   the common Cc >> Cb assumption (bulk cable capacitance much larger than
   the void's series branch), so apparent charge approximately equals the
   real charge released in the void: q_apparent ~= Ca * dV_void.
"""
from __future__ import annotations

import math

from .environment import Environment, paschen_breakdown_voltage_v

EPS0 = 8.8541878128e-12


def analyze_coaxial_void(
    conductor_radius_mm: float,
    insulation_thickness_mm: float,
    voltage_kv: float,
    relative_permittivity: float,
    void_position_mm: float,
    void_thickness_mm: float,
    void_diameter_mm: float,
    env: Environment,
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

    e_diel_at_void = e_dielectric(r_void)
    e_void = relative_permittivity * e_diel_at_void

    v_breakdown_void = paschen_breakdown_voltage_v(void_thickness_mm / 10.0, env)
    e_void_breakdown = v_breakdown_void / t_void

    v_inception_v = e_void_breakdown * r_void * ln_ratio / relative_permittivity
    v_inception_kv = v_inception_v / 1000.0

    a_void = math.pi * (void_diameter_mm / 1000.0 / 2.0) ** 2
    remaining_solid = max(r2 - (r_void + t_void / 2.0), 1e-6)
    ca = EPS0 * a_void / t_void
    cb = EPS0 * relative_permittivity * a_void / remaining_solid

    apparent_charge_pc = ca * v_breakdown_void * 1e12

    n_r = 120
    radii = [r1 + (r2 - r1) * i / (n_r - 1) for i in range(n_r)]
    field_profile = [e_dielectric(r) for r in radii]

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

    void_angle = 0.0
    void_x = r_void * math.cos(void_angle)
    void_y = r_void * math.sin(void_angle)

    return {
        "geometry": {
            "conductor_radius_m": r1,
            "outer_radius_m": r2,
            "void_radius_m": r_void,
            "void_marker_xy": {"x": void_x, "y": void_y},
        },
        "radial_profile": {"r_m": radii, "field_v_per_m": field_profile},
        "grid": {"x": xs, "y": ys, "field_v_per_m": field_grid},
        "void": {
            "field_v_per_m": e_void,
            "field_in_dielectric_at_void_v_per_m": e_diel_at_void,
            "breakdown_voltage_v": v_breakdown_void,
            "breakdown_field_v_per_m": e_void_breakdown,
            "capacitance_ca_f": ca,
            "capacitance_cb_f": cb,
            "apparent_charge_pc": apparent_charge_pc,
        },
        "inception": {
            "inception_voltage_kv": v_inception_kv,
            "applied_voltage_kv": voltage_kv,
            "margin_ratio": voltage_kv / v_inception_kv,
            "status": "above_onset" if voltage_kv >= v_inception_kv else "below_onset",
        },
        "max_field_v_per_m": e_dielectric(r1),
    }
