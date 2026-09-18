# Partial Discharge / Corona Analyzer

An interactive, COMSOL-flavored electric field and PD/corona inception-voltage
explorer for **DC** high-voltage insulation systems. Pick a geometry — open-gas
corona, an internal void, or surface discharge along an insulator — set
electrode/sample dimensions, materials, voltage and atmospheric conditions,
and get a field heatmap, an inception-voltage verdict (including **transient
vs. steady-state** DC behavior for layered dielectrics), and a parameter-sweep
tool with CSV export.

This is an **analytical-formula** tool (exact point-charge / image-charge
electrostatics + classical empirical corona/PD laws), not a mesh-based FEM
solver. It's meant for fast, interactive exploration and teaching/design
intuition — see [Physics & assumptions](#physics--assumptions) for what that
does and doesn't buy you, and for where a real FEM engine (e.g. scikit-fem)
would be the natural next step.

## Geometries supported

**Corona (open gas gap)** — no solid dielectric involved, pure gas-gap physics:
- **Needle - Plane** — sharp needle tip over a grounded plane.
- **Sphere - Sphere / Rod - Rod gap** — two equal spheres, one energized, one grounded.
- **Sphere - Plane** — a sphere electrode over a grounded plane.

All three let you pick the ambient gas (Air / SF6 / N2 / custom), which scales
the Peek's-law onset gradient by that gas's dielectric strength relative to
air.

**Internal discharge (embedded void)** — a solid insulation sample with a gas
cavity inside it:
- **Parallel-plane test cell with void** — the standard IEC 60270-style lab PD
  cell: two flat electrodes, a solid sample of chosen material and thickness,
  a void of chosen size/depth/gas fill.
- **Coaxial cable with internal void** — the same idea in a cable's cylindrical
  cross-section.

**Surface discharge** — an HV electrode edge and a grounded counter-electrode
separated by a creepage path across a solid insulator's surface, exposed to
an ambient gas.

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

- Choose a geometry (grouped by category in the dropdown), edit electrode/
  sample parameters, pick materials from the preset library (or switch a
  material to "Custom" to type your own permittivity/conductivity), set the
  environment (temperature, pressure, relative humidity), and click
  **Analyze**.
- The **Field Map** tab shows a log-scaled electric field heatmap — mirrored
  around the symmetry axis for point-gap and surface-discharge geometries, or
  the true cross-section for the two void geometries (void location marked).
- The inception card reports:
  - For corona geometries: Peek's-law onset gradient, inception voltage,
    above/below-onset status, max field, and an indicative corona current.
  - For internal-void and surface-discharge geometries: **both** a transient
    (t=0+, capacitive) and a steady-state (t→∞, resistive) inception voltage
    and status, plus the interfacial relaxation time constant τ that governs
    how long it takes to transition between the two — see below.
- The **Parameter Sweep** tab varies any single numeric parameter (electrode/
  sample dimensions, material properties, or environment) over a range and
  plots/tables the resulting inception voltage(s), max field, and current/
  charge, with CSV export.

## Physics & assumptions

### Corona (open gas gap)

Solved *exactly* (up to series truncation) with the classical method of
successive images — the same technique used to build the IEC 60052 sphere-gap
calibration tables. The needle is modeled as a small sphere whose radius
equals the needle's tip radius; this is a standard approximation for the tip
region and avoids needing a separate hyperboloid solution while still solving
Laplace's equation exactly for that shape.

**Corona onset** uses Peek's empirical DC formula,
`g0 = 30 * delta * (1 + 0.301/sqrt(delta * r))` kV/cm, with `delta` the
relative air density from temperature and pressure, a humidity correction
multiplier (isolated in `backend/app/physics/environment.py` so it can be
swapped for a more rigorous model later), and a gas dielectric-strength
multiplier for non-air fills (`backend/app/physics/materials.py`).

**Indicative corona current** (V-I curve above onset) uses the classical
Townsend/Kaptzov `I ∝ V(V-V0)` scaling, which is well established
*qualitatively*; the prefactor here is a simplified adaptation from the
wire-cylinder formula and should be read as order-of-magnitude only.

### Internal discharge (embedded void) and the transient/steady-state effect

Both void geometries treat the void and surrounding solid as a **two-layer
series dielectric stack** (`backend/app/physics/dielectric_layers.py`) and
report the field/inception voltage under two limits:

- **Transient (t=0+):** right when voltage is applied, the field divides
  by *permittivity* (capacitive divider, D continuous):
  `E_i = V / (eps_i * sum_j(d_j/eps_j))`.
- **Steady-state (t→∞):** once enough time has passed for charge to
  redistribute, the field instead divides by *conductivity* (resistive
  divider, J continuous): `E_i = V / (sigma_i * sum_j(d_j/sigma_j))`.
- The **relaxation time constant** `tau = eps0*(eps1*d2+eps2*d1) /
  (sigma1*d2+sigma2*d1)` (the classical Maxwell-Wagner interfacial
  polarization time) tells you roughly how long the transition takes.

This is a real and important DC-specific effect: because gases have very low
(but nonzero) DC conductivity, a void's steady-state field can be dramatically
higher *or* lower than its transient field depending on how the void gas's
conductivity compares to the solid's — which is exactly why the tool lets you
pick/override both. This is a major reason internal PD behavior differs
between AC and DC in real HVDC equipment.

The void breaks down per **Paschen's law** for its local gas gap. Apparent
charge uses the classical "abc" equivalent-circuit model (Whitehead 1951 /
Gemant & Philippoff 1932), simplified with the common `Cc >> Cb` assumption,
i.e. `q_apparent ~= Ca * dV_void`.

The parallel-plane test cell assumes electrode diameter >> sample thickness
(no fringing) and shows the void as a locally enhanced patch in an otherwise
uniform through-thickness field — it does not resolve the true 3-D field
right at the void's edges. The coaxial-void geometry shows the true radial
bulk field with the void's location marked.

### Surface discharge

True field modeling at the electrode/insulator/gas triple junction is a
research-grade problem (a field singularity whose exponent depends on the
local wedge angle and permittivity ratio). This tool uses a documented
engineering approximation instead (see `backend/app/physics/
surface_discharge.py` for full detail):

1. The electrode edge is modeled as a small sphere (its radius of curvature)
   facing a grounded plane across the creepage distance — reusing the exact
   image-charge solver from the corona geometries.
2. A classical flat-interface refraction factor `k = 2*eps_r/(eps_r+1)`
   approximates the local field enhancement the substrate produces.
3. A user-set **surface condition factor** (0-1) derates the clean-gas-gap
   Peek onset gradient for real-surface effects (moisture, contamination).
4. Transient-vs-steady-state uses the same two-layer analogy as the void
   geometries (substrate thickness vs. the surface gas path), which is an
   **illustrative simplification** — real HVDC surface charge accumulation on
   insulators/spacers is governed by *surface* conductivity from adsorbed
   layers, not the substrate's bulk conductivity used here.

### Material properties

`backend/app/physics/materials.py` provides preset relative permittivity and
DC volume conductivity for common gases (Air, SF6, N2) and solids/liquids
(epoxy, XLPE, EPR/silicone, PTFE, oil-impregnated paper, mineral oil,
pressboard), or you can switch any material to "Custom" and enter your own.

**Important:** these presets are indicative, low-field, room-temperature
reference points. Real dielectric DC conductivity is strongly nonlinear with
electric field and temperature — extensively documented for HVDC-grade XLPE
in particular, where conductivity can shift by 1-2 orders of magnitude
between low-field/ambient and rated-field/operating-temperature conditions.
For meaningful steady-state predictions, use measured conductivity at your
actual operating point.

### Known limitations / natural next steps

- All formulas are DC-specific (no AC phase, no PRPD pattern) — a deliberate
  scope choice.
- Corona current and apparent-charge magnitudes are order-of-magnitude
  indicators, not calibrated/certified measurements.
- The transient/steady-state split for surface discharge is a documented
  analogy, not a rigorous surface-charge transport model.
- Neither void geometry resolves the true 3-D field right at the void's
  edges (fringing).
- A real mesh-based FEM solver (e.g. `scikit-fem`) would be the natural
  upgrade path for arbitrary geometries and true fringing/singularity
  resolution, and is the obvious next step if closer-to-COMSOL fidelity is
  needed later.
- Ion mobility (used in the corona-current estimate) and Paschen's A/B/gamma
  constants are fixed values, not yet per-gas-calibrated beyond the single
  "relative dielectric strength" scaling factor.
