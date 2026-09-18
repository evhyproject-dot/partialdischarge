"""Static metadata describing each geometry's input parameters, used both to
validate requests and to let the frontend build its input form dynamically
(mirrors how COMSOL's parameter table drives its model tree).

Two parameter kinds:
- {"type": "number", ...}: a plain numeric field.
- {"type": "select_gas"/"select_solid", ...}: a material dropdown (options
  come from physics/materials.py). When the user picks "custom", the
  frontend reveals the fields listed in "custom_fields" (plain numeric
  fields with a matching name suffix) for direct entry.
"""
from __future__ import annotations

from .physics.materials import gas_options, solid_options

AMBIENT_GAS_PARAM = {
    "name": "ambient_gas",
    "label": "Ambient gas",
    "type": "select_gas",
    "default": "air",
    "custom_fields": [
        {"name": "ambient_gas_epsilon_r", "label": "Gas relative permittivity", "unit": "", "default": 1.0, "min": 1.0, "max": 1.1},
        {"name": "ambient_gas_sigma", "label": "Gas conductivity", "unit": "S/m", "default": 2e-14, "min": 0.0, "max": 1e-9},
        {"name": "ambient_gas_strength", "label": "Dielectric strength vs. air", "unit": "x air", "default": 1.0, "min": 0.1, "max": 5.0},
    ],
}


def _void_gas_param(name="void_gas"):
    return {
        "name": name,
        "label": "Void gas fill",
        "type": "select_gas",
        "default": "air",
        "custom_fields": [
            {"name": f"{name}_epsilon_r", "label": "Gas relative permittivity", "unit": "", "default": 1.0, "min": 1.0, "max": 1.1},
            {"name": f"{name}_sigma", "label": "Gas conductivity", "unit": "S/m", "default": 2e-14, "min": 0.0, "max": 1e-9},
            {"name": f"{name}_strength", "label": "Dielectric strength vs. air", "unit": "x air", "default": 1.0, "min": 0.1, "max": 5.0},
        ],
    }


def _insulation_material_param(name="insulation_material", label="Insulation material", default="xlpe"):
    return {
        "name": name,
        "label": label,
        "type": "select_solid",
        "default": default,
        "custom_fields": [
            {"name": f"{name}_epsilon_r", "label": "Relative permittivity", "unit": "", "default": 4.0, "min": 1.0, "max": 15.0},
            {"name": f"{name}_sigma", "label": "DC conductivity", "unit": "S/m", "default": 1e-13, "min": 1e-18, "max": 1e-8},
        ],
    }


GEOMETRIES = {
    "needle_plane": {
        "label": "Needle - Plane (corona)",
        "category": "Corona (open gas gap)",
        "description": "Sharp needle tip above a grounded plane. Classic geometry for studying corona onset at a point of high field concentration.",
        "params": [
            {"name": "tip_radius_mm", "label": "Needle tip radius", "unit": "mm", "type": "number", "default": 0.05, "min": 0.005, "max": 5.0},
            {"name": "gap_mm", "label": "Gap distance", "unit": "mm", "type": "number", "default": 20.0, "min": 1.0, "max": 500.0},
            {"name": "voltage_kv", "label": "Applied DC voltage", "unit": "kV", "type": "number", "default": 15.0, "min": 0.0, "max": 500.0},
            AMBIENT_GAS_PARAM,
        ],
    },
    "sphere_sphere": {
        "label": "Sphere - Sphere / Rod - Rod gap",
        "category": "Corona (open gas gap)",
        "description": "Two equal-radius spherical electrodes facing each other; one energized, one grounded. Used for more uniform-field corona/breakdown studies.",
        "params": [
            {"name": "electrode_radius_mm", "label": "Electrode radius", "unit": "mm", "type": "number", "default": 12.5, "min": 0.5, "max": 200.0},
            {"name": "gap_mm", "label": "Gap distance", "unit": "mm", "type": "number", "default": 30.0, "min": 1.0, "max": 1000.0},
            {"name": "voltage_kv", "label": "Applied DC voltage", "unit": "kV", "type": "number", "default": 40.0, "min": 0.0, "max": 1000.0},
            AMBIENT_GAS_PARAM,
        ],
    },
    "sphere_plane": {
        "label": "Sphere - Plane",
        "category": "Corona (open gas gap)",
        "description": "A sphere electrode above a grounded plane. Common in HV equipment insulation and standard sphere-gap test setups.",
        "params": [
            {"name": "sphere_radius_mm", "label": "Sphere radius", "unit": "mm", "type": "number", "default": 12.5, "min": 0.5, "max": 200.0},
            {"name": "gap_mm", "label": "Gap distance", "unit": "mm", "type": "number", "default": 30.0, "min": 1.0, "max": 1000.0},
            {"name": "voltage_kv", "label": "Applied DC voltage", "unit": "kV", "type": "number", "default": 40.0, "min": 0.0, "max": 1000.0},
            AMBIENT_GAS_PARAM,
        ],
    },
    "parallel_plane_void": {
        "label": "Parallel-plane test cell with void (internal PD)",
        "category": "Internal discharge (embedded void)",
        "description": "Two flat electrodes with a solid insulation sample between them containing an internal gas void. The standard IEC 60270-style lab PD test cell.",
        "params": [
            {"name": "electrode_diameter_mm", "label": "Electrode diameter", "unit": "mm", "type": "number", "default": 50.0, "min": 5.0, "max": 300.0},
            {"name": "sample_thickness_mm", "label": "Sample thickness", "unit": "mm", "type": "number", "default": 3.0, "min": 0.2, "max": 50.0},
            {"name": "voltage_kv", "label": "Applied DC voltage", "unit": "kV", "type": "number", "default": 20.0, "min": 0.0, "max": 500.0},
            _insulation_material_param(),
            {"name": "void_position_mm", "label": "Void depth (from top electrode)", "unit": "mm", "type": "number", "default": 1.0, "min": 0.05, "max": 49.0},
            {"name": "void_thickness_mm", "label": "Void thickness", "unit": "mm", "type": "number", "default": 0.1, "min": 0.005, "max": 3.0},
            {"name": "void_diameter_mm", "label": "Void diameter", "unit": "mm", "type": "number", "default": 1.0, "min": 0.05, "max": 20.0},
            _void_gas_param(),
        ],
    },
    "coaxial_void": {
        "label": "Coaxial cable with internal void",
        "category": "Internal discharge (embedded void)",
        "description": "Cylindrical HV cable cross-section with a small internal gas cavity inside the solid dielectric.",
        "params": [
            {"name": "conductor_radius_mm", "label": "Inner conductor radius", "unit": "mm", "type": "number", "default": 8.0, "min": 0.5, "max": 100.0},
            {"name": "insulation_thickness_mm", "label": "Insulation thickness", "unit": "mm", "type": "number", "default": 6.0, "min": 0.5, "max": 60.0},
            {"name": "voltage_kv", "label": "Applied DC voltage", "unit": "kV", "type": "number", "default": 60.0, "min": 0.0, "max": 1000.0},
            _insulation_material_param(),
            {"name": "void_position_mm", "label": "Void position (from conductor surface)", "unit": "mm", "type": "number", "default": 3.0, "min": 0.05, "max": 59.0},
            {"name": "void_thickness_mm", "label": "Void thickness (radial)", "unit": "mm", "type": "number", "default": 0.2, "min": 0.01, "max": 3.0},
            {"name": "void_diameter_mm", "label": "Void diameter", "unit": "mm", "type": "number", "default": 1.0, "min": 0.05, "max": 10.0},
            _void_gas_param(),
        ],
    },
    "surface_discharge": {
        "label": "Surface discharge along an insulator",
        "category": "Surface discharge",
        "description": "An HV electrode edge and a grounded counter-electrode separated by a creepage path across a solid insulator's surface, exposed to an ambient gas.",
        "params": [
            {"name": "creepage_distance_mm", "label": "Creepage (surface path) distance", "unit": "mm", "type": "number", "default": 30.0, "min": 1.0, "max": 500.0},
            {"name": "electrode_edge_radius_mm", "label": "Electrode edge radius", "unit": "mm", "type": "number", "default": 0.2, "min": 0.01, "max": 10.0},
            {"name": "voltage_kv", "label": "Applied DC voltage", "unit": "kV", "type": "number", "default": 20.0, "min": 0.0, "max": 500.0},
            {"name": "substrate_thickness_mm", "label": "Substrate thickness", "unit": "mm", "type": "number", "default": 5.0, "min": 0.5, "max": 100.0},
            _insulation_material_param("substrate_material", "Substrate material", default="epoxy"),
            {"name": "surface_condition_factor", "label": "Surface condition factor (1 = clean/dry)", "unit": "", "type": "number", "default": 0.7, "min": 0.1, "max": 1.0},
            AMBIENT_GAS_PARAM,
        ],
    },
}

ENVIRONMENT_PARAMS = [
    {"name": "temperature_c", "label": "Temperature", "unit": "°C", "type": "number", "default": 20.0, "min": -40.0, "max": 80.0},
    {"name": "pressure_kpa", "label": "Pressure", "unit": "kPa", "type": "number", "default": 101.3, "min": 30.0, "max": 110.0},
    {"name": "humidity_percent", "label": "Relative humidity", "unit": "%", "type": "number", "default": 50.0, "min": 0.0, "max": 100.0},
]


def _all_field_names(spec: dict) -> list[str]:
    names = [spec["name"]]
    for cf in spec.get("custom_fields", []):
        names.append(cf["name"])
    return names


def default_params(geometry: str) -> dict:
    out = {}
    for p in GEOMETRIES[geometry]["params"]:
        out[p["name"]] = p["default"]
        for cf in p.get("custom_fields", []):
            out[cf["name"]] = cf["default"]
    return out


def default_environment() -> dict:
    return {p["name"]: p["default"] for p in ENVIRONMENT_PARAMS}


def material_library():
    return {"solids": solid_options(), "gases": gas_options()}


def numeric_param_names(geometry: str) -> set[str]:
    """Field names that are plain numbers and therefore valid sweep targets
    (material-select fields are categorical, not sweepable; their custom
    numeric sub-fields are)."""
    names = set()
    for p in GEOMETRIES[geometry]["params"]:
        if p["type"] == "number":
            names.add(p["name"])
        for cf in p.get("custom_fields", []):
            names.add(cf["name"])
    return names
