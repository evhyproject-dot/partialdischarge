from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .geometry_registry import (
    ENVIRONMENT_PARAMS,
    GEOMETRIES,
    default_environment,
    default_params,
    material_library,
    numeric_param_names,
)
from .physics.coaxial_void import analyze_coaxial_void
from .physics.electrode_geometries import (
    analyze_needle_plane,
    analyze_sphere_plane,
    analyze_sphere_sphere,
)
from .physics.environment import Environment
from .physics.materials import resolve_gas, resolve_solid
from .physics.parallel_plane_void import analyze_parallel_plane_void
from .physics.surface_discharge import analyze_surface_discharge

app = FastAPI(title="Partial Discharge / Corona Analyzer")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

GeometryName = Literal[
    "needle_plane",
    "sphere_plane",
    "sphere_sphere",
    "parallel_plane_void",
    "coaxial_void",
    "surface_discharge",
]


class EnvironmentInput(BaseModel):
    temperature_c: float = 20.0
    pressure_kpa: float = 101.3
    humidity_percent: float = 50.0


class AnalyzeRequest(BaseModel):
    geometry: GeometryName
    params: dict[str, Any]
    environment: EnvironmentInput = Field(default_factory=EnvironmentInput)


class SweepRequest(BaseModel):
    geometry: GeometryName
    params: dict[str, Any]
    environment: EnvironmentInput = Field(default_factory=EnvironmentInput)
    target: str
    start: float
    stop: float
    steps: int = 20


def _env_from_input(e: EnvironmentInput) -> Environment:
    return Environment(
        temperature_c=e.temperature_c,
        pressure_kpa=e.pressure_kpa,
        humidity_percent=e.humidity_percent,
    )


def _validate_params(geometry: str, params: dict[str, Any]) -> dict[str, Any]:
    merged = default_params(geometry)
    merged.update(params or {})
    return merged


def _gas(params: dict[str, Any], name: str):
    key = params.get(name, "air")
    return resolve_gas(key, params.get(f"{name}_epsilon_r"), params.get(f"{name}_sigma"), params.get(f"{name}_strength"))


def _solid(params: dict[str, Any], name: str):
    key = params.get(name, "xlpe")
    return resolve_solid(key, params.get(f"{name}_epsilon_r"), params.get(f"{name}_sigma"))


def _run_geometry(geometry: str, params: dict[str, Any], env: Environment, include_grid: bool = True) -> dict[str, Any]:
    if geometry == "needle_plane":
        gas = _gas(params, "ambient_gas")
        return analyze_needle_plane(params["tip_radius_mm"], params["gap_mm"], params["voltage_kv"], env, gas.relative_dielectric_strength, include_grid)
    if geometry == "sphere_plane":
        gas = _gas(params, "ambient_gas")
        return analyze_sphere_plane(params["sphere_radius_mm"], params["gap_mm"], params["voltage_kv"], env, gas.relative_dielectric_strength, include_grid)
    if geometry == "sphere_sphere":
        gas = _gas(params, "ambient_gas")
        return analyze_sphere_sphere(params["electrode_radius_mm"], params["gap_mm"], params["voltage_kv"], env, gas.relative_dielectric_strength, include_grid)
    if geometry == "parallel_plane_void":
        insulation = _solid(params, "insulation_material")
        void_gas = _gas(params, "void_gas")
        return analyze_parallel_plane_void(
            params["electrode_diameter_mm"], params["sample_thickness_mm"], params["voltage_kv"],
            insulation.epsilon_r, insulation.sigma_s_per_m,
            params["void_position_mm"], params["void_thickness_mm"], params["void_diameter_mm"],
            void_gas.epsilon_r, void_gas.sigma_s_per_m, void_gas.relative_dielectric_strength,
            env, include_grid,
        )
    if geometry == "coaxial_void":
        insulation = _solid(params, "insulation_material")
        void_gas = _gas(params, "void_gas")
        return analyze_coaxial_void(
            params["conductor_radius_mm"], params["insulation_thickness_mm"], params["voltage_kv"],
            insulation.epsilon_r, insulation.sigma_s_per_m,
            params["void_position_mm"], params["void_thickness_mm"], params["void_diameter_mm"],
            void_gas.epsilon_r, void_gas.sigma_s_per_m, void_gas.relative_dielectric_strength,
            env, include_grid,
        )
    if geometry == "surface_discharge":
        substrate = _solid(params, "substrate_material")
        gas = _gas(params, "ambient_gas")
        return analyze_surface_discharge(
            params["creepage_distance_mm"], params["electrode_edge_radius_mm"], params["voltage_kv"],
            params["substrate_thickness_mm"], substrate.epsilon_r, substrate.sigma_s_per_m,
            gas.epsilon_r, gas.sigma_s_per_m, gas.relative_dielectric_strength,
            params["surface_condition_factor"], env, include_grid,
        )
    raise HTTPException(status_code=400, detail=f"Unknown geometry {geometry}")


@app.get("/api/geometries")
def get_geometries():
    return {
        "geometries": GEOMETRIES,
        "environment_params": ENVIRONMENT_PARAMS,
        "materials": material_library(),
        "defaults": {
            "environment": default_environment(),
            **{f"params_{name}": default_params(name) for name in GEOMETRIES},
        },
    }


@app.post("/api/analyze")
def analyze(req: AnalyzeRequest):
    if req.geometry not in GEOMETRIES:
        raise HTTPException(status_code=400, detail="Unknown geometry")
    params = _validate_params(req.geometry, req.params)
    env = _env_from_input(req.environment)
    result = _run_geometry(req.geometry, params, env)
    result["environment_summary"] = env.summary()
    return result


@app.post("/api/sweep")
def sweep(req: SweepRequest):
    if req.geometry not in GEOMETRIES:
        raise HTTPException(status_code=400, detail="Unknown geometry")
    if req.steps < 2 or req.steps > 200:
        raise HTTPException(status_code=422, detail="steps must be between 2 and 200")

    base_params = _validate_params(req.geometry, req.params)
    base_env_dict = req.environment.model_dump()

    numeric_names = numeric_param_names(req.geometry)
    env_field_names = {p["name"] for p in ENVIRONMENT_PARAMS}

    if req.target not in numeric_names and req.target not in env_field_names:
        raise HTTPException(status_code=422, detail=f"Unknown or non-numeric sweep target '{req.target}'")

    rows = []
    for i in range(req.steps):
        frac = i / (req.steps - 1)
        value = req.start + (req.stop - req.start) * frac

        params = dict(base_params)
        env_dict = dict(base_env_dict)
        if req.target in numeric_names:
            params[req.target] = value
        else:
            env_dict[req.target] = value

        env = Environment(**env_dict)
        result = _run_geometry(req.geometry, params, env, include_grid=False)
        inception = result.get("inception", {})
        row = {
            "target_value": value,
            "inception_voltage_kv": inception.get("inception_voltage_kv"),
            "applied_voltage_kv": inception.get("applied_voltage_kv"),
            "margin_ratio": inception.get("margin_ratio"),
            "status": inception.get("status"),
            "max_field_v_per_m": result.get("max_field_v_per_m"),
        }
        if "inception_voltage_transient_kv" in inception:
            row["inception_voltage_transient_kv"] = inception["inception_voltage_transient_kv"]
            row["inception_voltage_steady_kv"] = inception["inception_voltage_steady_kv"]
        if "corona_current_ma" in result:
            row["corona_current_ma"] = result["corona_current_ma"]
        if "void" in result:
            row["apparent_charge_pc"] = result["void"]["apparent_charge_pc"]
        if "utilization_factor" in result:
            row["utilization_factor"] = result["utilization_factor"]
        if "space_charge_time_s" in result:
            row["space_charge_time_s"] = result["space_charge_time_s"]
        rows.append(row)

    return {"target": req.target, "rows": rows}


@app.get("/api/health")
def health():
    return {"status": "ok"}


# Serve the frontend (static HTML/CSS/JS) from the same process, so the whole
# app is a single deployable service on a single port. Mounted last so it
# doesn't shadow the /api/* routes above.
_FRONTEND_DIR = Path(__file__).resolve().parent.parent.parent / "frontend"
if _FRONTEND_DIR.is_dir():
    app.mount("/", StaticFiles(directory=str(_FRONTEND_DIR), html=True), name="frontend")
