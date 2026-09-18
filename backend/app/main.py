from __future__ import annotations

from typing import Any, Literal

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .geometry_registry import ENVIRONMENT_PARAMS, GEOMETRIES, default_environment, default_params
from .physics.coaxial_void import analyze_coaxial_void
from .physics.electrode_geometries import (
    analyze_needle_plane,
    analyze_sphere_plane,
    analyze_sphere_sphere,
)
from .physics.environment import Environment

app = FastAPI(title="Partial Discharge / Corona Analyzer")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

GeometryName = Literal["needle_plane", "sphere_plane", "sphere_sphere", "coaxial_void"]


class EnvironmentInput(BaseModel):
    temperature_c: float = 20.0
    pressure_kpa: float = 101.3
    humidity_percent: float = 50.0


class AnalyzeRequest(BaseModel):
    geometry: GeometryName
    params: dict[str, float]
    environment: EnvironmentInput = Field(default_factory=EnvironmentInput)


class SweepRequest(BaseModel):
    geometry: GeometryName
    params: dict[str, float]
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


def _validate_params(geometry: str, params: dict[str, float]) -> dict[str, float]:
    schema = GEOMETRIES[geometry]["params"]
    merged = default_params(geometry)
    merged.update(params or {})
    missing = [p["name"] for p in schema if p["name"] not in merged]
    if missing:
        raise HTTPException(status_code=422, detail=f"Missing parameters: {missing}")
    return merged


def _run_geometry(geometry: str, params: dict[str, float], env: Environment) -> dict[str, Any]:
    if geometry == "needle_plane":
        return analyze_needle_plane(params["tip_radius_mm"], params["gap_mm"], params["voltage_kv"], env)
    if geometry == "sphere_plane":
        return analyze_sphere_plane(params["sphere_radius_mm"], params["gap_mm"], params["voltage_kv"], env)
    if geometry == "sphere_sphere":
        return analyze_sphere_sphere(params["electrode_radius_mm"], params["gap_mm"], params["voltage_kv"], env)
    if geometry == "coaxial_void":
        return analyze_coaxial_void(
            params["conductor_radius_mm"],
            params["insulation_thickness_mm"],
            params["voltage_kv"],
            params["relative_permittivity"],
            params["void_position_mm"],
            params["void_thickness_mm"],
            params["void_diameter_mm"],
            env,
        )
    raise HTTPException(status_code=400, detail=f"Unknown geometry {geometry}")


@app.get("/api/geometries")
def get_geometries():
    return {
        "geometries": GEOMETRIES,
        "environment_params": ENVIRONMENT_PARAMS,
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

    param_field_names = {p["name"] for p in GEOMETRIES[req.geometry]["params"]}
    env_field_names = {p["name"] for p in ENVIRONMENT_PARAMS}

    if req.target not in param_field_names and req.target not in env_field_names:
        raise HTTPException(status_code=422, detail=f"Unknown sweep target '{req.target}'")

    rows = []
    for i in range(req.steps):
        frac = i / (req.steps - 1)
        value = req.start + (req.stop - req.start) * frac

        params = dict(base_params)
        env_dict = dict(base_env_dict)
        if req.target in param_field_names:
            params[req.target] = value
        else:
            env_dict[req.target] = value

        env = Environment(**env_dict)
        result = _run_geometry(req.geometry, params, env)
        inception = result.get("inception", {})
        row = {
            "target_value": value,
            "inception_voltage_kv": inception.get("inception_voltage_kv"),
            "applied_voltage_kv": inception.get("applied_voltage_kv"),
            "margin_ratio": inception.get("margin_ratio"),
            "status": inception.get("status"),
            "max_field_v_per_m": result.get("max_field_v_per_m"),
        }
        if "corona_current_ma" in result:
            row["corona_current_ma"] = result["corona_current_ma"]
        if "void" in result:
            row["apparent_charge_pc"] = result["void"]["apparent_charge_pc"]
        rows.append(row)

    return {"target": req.target, "rows": rows}


@app.get("/api/health")
def health():
    return {"status": "ok"}
