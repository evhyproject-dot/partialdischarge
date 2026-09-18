"""Static metadata describing each geometry's input parameters, used both to
validate requests and to let the frontend build its input form dynamically
(mirrors how COMSOL's parameter table drives its model tree)."""
from __future__ import annotations

GEOMETRIES = {
    "needle_plane": {
        "label": "Needle - Plane (corona)",
        "description": "Sharp needle tip above a grounded plane. Classic geometry for studying corona onset at a point of high field concentration.",
        "params": [
            {"name": "tip_radius_mm", "label": "Needle tip radius", "unit": "mm", "default": 0.05, "min": 0.005, "max": 5.0},
            {"name": "gap_mm", "label": "Gap distance", "unit": "mm", "default": 20.0, "min": 1.0, "max": 500.0},
            {"name": "voltage_kv", "label": "Applied DC voltage", "unit": "kV", "default": 15.0, "min": 0.0, "max": 500.0},
        ],
    },
    "sphere_sphere": {
        "label": "Sphere - Sphere / Rod - Rod gap",
        "description": "Two equal-radius spherical electrodes facing each other; one energized, one grounded. Used for more uniform-field corona/breakdown studies.",
        "params": [
            {"name": "electrode_radius_mm", "label": "Electrode radius", "unit": "mm", "default": 12.5, "min": 0.5, "max": 200.0},
            {"name": "gap_mm", "label": "Gap distance", "unit": "mm", "default": 30.0, "min": 1.0, "max": 1000.0},
            {"name": "voltage_kv", "label": "Applied DC voltage", "unit": "kV", "default": 40.0, "min": 0.0, "max": 1000.0},
        ],
    },
    "sphere_plane": {
        "label": "Sphere - Plane",
        "description": "A sphere electrode above a grounded plane. Common in HV equipment insulation and standard sphere-gap test setups.",
        "params": [
            {"name": "sphere_radius_mm", "label": "Sphere radius", "unit": "mm", "default": 12.5, "min": 0.5, "max": 200.0},
            {"name": "gap_mm", "label": "Gap distance", "unit": "mm", "default": 30.0, "min": 1.0, "max": 1000.0},
            {"name": "voltage_kv", "label": "Applied DC voltage", "unit": "kV", "default": 40.0, "min": 0.0, "max": 1000.0},
        ],
    },
    "coaxial_void": {
        "label": "Coaxial cable with internal void",
        "description": "Cylindrical HV cable cross-section with a small internal gas cavity inside the solid dielectric. Classic internal-PD scenario (distinct from surface corona).",
        "params": [
            {"name": "conductor_radius_mm", "label": "Inner conductor radius", "unit": "mm", "default": 8.0, "min": 0.5, "max": 100.0},
            {"name": "insulation_thickness_mm", "label": "Insulation thickness", "unit": "mm", "default": 6.0, "min": 0.5, "max": 60.0},
            {"name": "voltage_kv", "label": "Applied DC voltage", "unit": "kV", "default": 60.0, "min": 0.0, "max": 1000.0},
            {"name": "relative_permittivity", "label": "Insulation relative permittivity", "unit": "", "default": 2.3, "min": 1.5, "max": 10.0},
            {"name": "void_position_mm", "label": "Void position (from conductor surface)", "unit": "mm", "default": 3.0, "min": 0.05, "max": 59.0},
            {"name": "void_thickness_mm", "label": "Void thickness (radial)", "unit": "mm", "default": 0.2, "min": 0.01, "max": 3.0},
            {"name": "void_diameter_mm", "label": "Void diameter", "unit": "mm", "default": 1.0, "min": 0.05, "max": 10.0},
        ],
    },
}

ENVIRONMENT_PARAMS = [
    {"name": "temperature_c", "label": "Temperature", "unit": "°C", "default": 20.0, "min": -40.0, "max": 80.0},
    {"name": "pressure_kpa", "label": "Pressure", "unit": "kPa", "default": 101.3, "min": 30.0, "max": 110.0},
    {"name": "humidity_percent", "label": "Relative humidity", "unit": "%", "default": 50.0, "min": 0.0, "max": 100.0},
]


def default_params(geometry: str) -> dict:
    return {p["name"]: p["default"] for p in GEOMETRIES[geometry]["params"]}


def default_environment() -> dict:
    return {p["name"]: p["default"] for p in ENVIRONMENT_PARAMS}
