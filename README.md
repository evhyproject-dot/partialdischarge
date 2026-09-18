# Partial Discharge / Corona Analyzer

An interactive, COMSOL-flavored electric field and corona/PD inception-voltage
explorer for **DC** high-voltage geometries. Pick a geometry, set electrode
dimensions, voltage and atmospheric conditions, and get a field heatmap with
equipotential contours, an inception-voltage verdict, and a parameter-sweep
tool with CSV export.

This is an **analytical-formula** tool (exact point-charge / image-charge
electrostatics + classical empirical corona/PD laws), not a mesh-based FEM
solver. It's meant for fast, interactive exploration and teaching/design
intuition — see [Physics & assumptions](#physics--assumptions) for what that
does and doesn't buy you, and for where a real FEM engine (e.g. scikit-fem)
would be the natural next step.

## Geometries supported

- **Needle - Plane** — sharp needle tip over a grounded plane (classic corona geometry).
- **Sphere - Sphere / Rod - Rod gap** — two equal spheres, one energized, one grounded.
- **Sphere - Plane** — a sphere electrode over a grounded plane.
- **Coaxial cable with internal void** — cable cross-section with a gas cavity in the dielectric (internal PD, not surface corona).

## Running it

### Backend (FastAPI)

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate   # optional but recommended
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

The API comes up at `http://localhost:8000` (docs at `/docs`).

> This sandbox's outbound connection to PyPI was down for the whole build
> session (503s from the egress gateway on both `pypi.org` and
> `registry.npmjs.org`), so `pip install` could not be exercised here. The
> physics and the full analyze/sweep request logic were verified directly in
> Python (bypassing FastAPI) and the frontend was verified against a
> stdlib-only stand-in server with Playwright screenshots, so the logic is
> confirmed correct — but do run `pip install -r requirements.txt` and a
> real `uvicorn` boot on your machine before relying on it, in case something
> FastAPI/Pydantic-version-specific surfaces there.

### Frontend

Static files, no build step:

```bash
cd frontend
python3 -m http.server 8080
```

Open `http://localhost:8080`. If your backend isn't on
`http://localhost:8000`, set `window.PD_API_BASE` before `app.js` loads (e.g.
add `<script>window.PD_API_BASE = "https://your-api-host";</script>` in
`index.html`).

## What you can do

- Choose a geometry, edit electrode parameters and environment (temperature,
  pressure, relative humidity) in the sidebar, and click **Analyze**.
- The **Field Map** tab shows a log-scaled electric field heatmap with
  equipotential contour lines, mirrored around the symmetry axis for the
  point-gap geometries, or the true cable cross-section for the coaxial-void
  geometry (with the void's location marked).
- The inception card reports the Peek's-law onset gradient (point-gap
  geometries) or void breakdown voltage (coaxial-void), the computed
  inception voltage, whether the applied voltage is above or below it, the
  max field, and (where applicable) an indicative corona current or IEC
  60270 apparent charge.
- The **Parameter Sweep** tab varies any single electrode or environmental
  parameter over a range and plots/tables the resulting inception voltage,
  max field, and current/charge, with CSV export for further analysis.

## Physics & assumptions

**Point-gap geometries (needle-plane, sphere-plane, sphere-sphere/rod-rod):**
solved *exactly* (up to series truncation) with the classical method of
successive images — the same technique used to build the IEC 60052 sphere-gap
calibration tables. The needle is modeled as a small sphere whose radius
equals the needle's tip radius; this is a standard approximation for the tip
region and avoids needing a separate hyperboloid solution while still solving
Laplace's equation exactly for that shape.

**Corona onset** uses Peek's empirical DC formula,
`g0 = 30 * delta * (1 + 0.301/sqrt(delta * r))` kV/cm, with `delta` the
relative air density from temperature and pressure, plus a humidity
correction multiplier that is intentionally isolated in
`backend/app/physics/environment.py` so it can be replaced with a more
rigorous model (e.g. the full IEC 60060-1 iterative procedure) without
touching anything else.

**Indicative corona current** (V-I curve above onset) uses the classical
Townsend/Kaptzov `I ∝ V(V-V0)` scaling, which is well established
*qualitatively*; the prefactor here is a simplified adaptation from the
wire-cylinder formula and should be read as order-of-magnitude only, not a
calibrated prediction.

**Coaxial cable with void:** bulk field is the standard
`E(r) = V / (r * ln(R2/R1))` coaxial formula. Field inside a thin, flat void
perpendicular to the local field is enhanced by the dielectric's relative
permittivity (`E_void = eps_r * E_dielectric`, from displacement-field
continuity). The void breaks down per **Paschen's law** for its local gas gap.
Apparent charge uses the classical "abc" equivalent-circuit model (Whitehead
1951 / Gemant & Philippoff 1932) for internal PD, simplified with the common
`Cc >> Cb` assumption (bulk cable capacitance much larger than the void's
series branch), i.e. `q_apparent ≈ Ca * ΔV_void`.

### Known limitations / natural next steps

- All formulas are DC-specific (no AC phase, no PRPD pattern) — that was a
  deliberate scope choice for this v1.
- Corona current and apparent-charge magnitudes are order-of-magnitude
  indicators, not calibrated/certified measurements.
- The coaxial-void field map shows the axisymmetric bulk field; it does not
  resolve the local 3D field perturbation the void itself creates (only its
  location is marked).
- A real mesh-based FEM solver (e.g. `scikit-fem`) would be the natural
  upgrade path for arbitrary geometries beyond these four, and is the obvious
  next step if closer-to-COMSOL fidelity is needed later.
- Ion mobility (used in the corona-current estimate) is currently a fixed
  constant, not yet a UI parameter.
