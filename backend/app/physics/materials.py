"""Material property presets: relative permittivity and DC volume
conductivity for common insulation materials and insulating gases.

IMPORTANT CAVEAT: DC conductivity of solid/liquid dielectrics is strongly
nonlinear with electric field and temperature -- this is extensively
documented for HVDC-grade XLPE in particular, where conductivity can change
by 1-2 orders of magnitude between room temperature/low field and
operating temperature/rated field. The values below are indicative,
low-field, room-temperature (~20 C) reference points only, meant for
exploring the qualitative transient-vs-steady-state behavior. For real
HVDC design work, use measured conductivity at the actual operating point.

Gas "relative_dielectric_strength" is the breakdown/corona-onset field
strength relative to air at the same pressure, used to scale Peek's law
and Paschen's law constants for non-air gases (e.g. SF6 in GIS equipment).
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class SolidMaterial:
    key: str
    label: str
    epsilon_r: float
    sigma_s_per_m: float


@dataclass
class GasMaterial:
    key: str
    label: str
    epsilon_r: float
    sigma_s_per_m: float
    relative_dielectric_strength: float  # relative to air = 1.0


SOLID_MATERIALS = {
    "epoxy": SolidMaterial("epoxy", "Epoxy resin", 4.0, 1e-13),
    "xlpe": SolidMaterial("xlpe", "XLPE (cross-linked polyethylene)", 2.3, 1e-15),
    "epr_silicone": SolidMaterial("epr_silicone", "EPR / silicone rubber", 3.0, 1e-13),
    "ptfe": SolidMaterial("ptfe", "PTFE (Teflon)", 2.1, 1e-17),
    "oil_impregnated_paper": SolidMaterial("oil_impregnated_paper", "Oil-impregnated paper", 3.6, 5e-13),
    "mineral_oil": SolidMaterial("mineral_oil", "Mineral oil", 2.2, 1e-12),
    "pressboard": SolidMaterial("pressboard", "Pressboard (cellulose)", 4.4, 1e-12),
    "custom": SolidMaterial("custom", "Custom", 4.0, 1e-13),
}

GAS_MATERIALS = {
    "air": GasMaterial("air", "Air", 1.0, 2e-14, 1.0),
    "sf6": GasMaterial("sf6", "SF6", 1.002, 1e-15, 2.7),
    "n2": GasMaterial("n2", "Nitrogen (N2)", 1.0, 2e-14, 1.0),
    "custom": GasMaterial("custom", "Custom", 1.0, 2e-14, 1.0),
}


def resolve_solid(key: str, custom_epsilon_r: float | None, custom_sigma: float | None) -> SolidMaterial:
    if key == "custom":
        return SolidMaterial("custom", "Custom", custom_epsilon_r or 4.0, custom_sigma or 1e-13)
    if key not in SOLID_MATERIALS:
        raise ValueError(f"Unknown solid material '{key}'")
    return SOLID_MATERIALS[key]


def resolve_gas(key: str, custom_epsilon_r: float | None, custom_sigma: float | None, custom_strength: float | None) -> GasMaterial:
    if key == "custom":
        return GasMaterial("custom", "Custom", custom_epsilon_r or 1.0, custom_sigma or 2e-14, custom_strength or 1.0)
    if key not in GAS_MATERIALS:
        raise ValueError(f"Unknown gas material '{key}'")
    return GAS_MATERIALS[key]


def solid_options():
    return [{"key": m.key, "label": m.label, "epsilon_r": m.epsilon_r, "sigma_s_per_m": m.sigma_s_per_m}
            for m in SOLID_MATERIALS.values()]


def gas_options():
    return [{"key": m.key, "label": m.label, "epsilon_r": m.epsilon_r, "sigma_s_per_m": m.sigma_s_per_m,
             "relative_dielectric_strength": m.relative_dielectric_strength}
            for m in GAS_MATERIALS.values()]
