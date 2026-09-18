"""Two-layer series dielectric solver for DC transient vs. steady-state field
redistribution (the Maxwell-Wagner effect).

When a DC voltage is first applied to two dielectrics in series (e.g. a
solid insulation slab with an embedded gas void, or a gas surface path
backed by a solid substrate), the field divides according to permittivity
(capacitive divider, D continuous):

    E_i = V / (eps_i * sum_j(d_j / eps_j))

Given enough time for charge to accumulate at the interface (governed by
the relaxation time constant below), the field instead divides according
to conductivity (resistive divider, J continuous):

    E_i = V / (sigma_i * sum_j(d_j / sigma_j))

Because gases have extremely low (but nonzero) DC conductivity, the
steady-state field across a gas layer in series with a solid can be far
higher than the transient/capacitive value -- a well documented and
important effect for internal voids and surface interfaces under HVDC
stress (this is why DC PD behavior in internal voids and at HVDC
insulator/spacer surfaces differs qualitatively from AC).

Reference: Maxwell-Wagner interfacial polarization theory, widely used in
HVDC insulation coordination literature.
"""
from __future__ import annotations

EPS0 = 8.8541878128e-12


def two_layer_fields(v_applied: float, d1: float, eps_r1: float, sigma1: float,
                      d2: float, eps_r2: float, sigma2: float):
    """Layer 1 = bulk solid/substrate, layer 2 = gas void/surface path.
    Returns dict with transient and steady-state field magnitudes (V/m) in
    each layer, plus the interfacial relaxation time constant (s).
    """
    sum_d_over_eps = d1 / eps_r1 + d2 / eps_r2
    e1_transient = v_applied / (eps_r1 * sum_d_over_eps)
    e2_transient = v_applied / (eps_r2 * sum_d_over_eps)

    sigma1 = max(sigma1, 1e-20)
    sigma2 = max(sigma2, 1e-20)
    sum_d_over_sigma = d1 / sigma1 + d2 / sigma2
    e1_steady = v_applied / (sigma1 * sum_d_over_sigma)
    e2_steady = v_applied / (sigma2 * sum_d_over_sigma)

    tau_mw = EPS0 * (eps_r1 * d2 + eps_r2 * d1) / (sigma1 * d2 + sigma2 * d1)

    return {
        "layer1_field_transient_v_per_m": e1_transient,
        "layer2_field_transient_v_per_m": e2_transient,
        "layer1_field_steady_v_per_m": e1_steady,
        "layer2_field_steady_v_per_m": e2_steady,
        "relaxation_time_constant_s": tau_mw,
    }


def voltage_for_layer2_field(target_field: float, d1: float, eps_r1: float, sigma1: float,
                              d2: float, eps_r2: float, sigma2: float, regime: str) -> float:
    """Inverse of two_layer_fields: applied voltage that puts layer 2 at
    target_field, under the given regime ("transient" or "steady")."""
    if regime == "transient":
        sum_d_over_eps = d1 / eps_r1 + d2 / eps_r2
        return target_field * eps_r2 * sum_d_over_eps
    sigma1 = max(sigma1, 1e-20)
    sigma2 = max(sigma2, 1e-20)
    sum_d_over_sigma = d1 / sigma1 + d2 / sigma2
    return target_field * sigma2 * sum_d_over_sigma
