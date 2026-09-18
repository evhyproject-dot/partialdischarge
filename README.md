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

## Running it locally

It's a single service: FastAPI serves both the `/api/*` endpoints and the
frontend's static files (HTML/CSS/JS) from the same process and port.

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate   # optional but recommended
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Open **http://localhost:8000** — that's the app. (API docs are at `/docs`.)

> This sandbox's outbound connection to PyPI was down for the whole build
> session (503s from the egress gateway on both `pypi.org` and
> `registry.npmjs.org`), so `pip install` could not be exercised here. The
> physics, the full analyze/sweep request logic, and the combined
> frontend+API serving were all verified directly (bypassing FastAPI/pip)
> with a stdlib-only stand-in server and Playwright screenshots, so the
> logic is confirmed correct — but do run `pip install -r requirements.txt`
> and a real `uvicorn` boot on your machine before relying on it, in case
> something FastAPI/Pydantic-version-specific surfaces there.

If you ever want to host the frontend separately from the API (e.g. a CDN
for the static files, a different host for the backend), the frontend still
works standalone — just set `window.PD_API_BASE = "https://your-api-host"`
before `app.js` loads in `index.html`, and serve `frontend/` with any static
file server.

## Deploying it somewhere you can share a link

Since it's one FastAPI process, any host that can run a Python web service
works. Two easy free/cheap options:

**Render.com** (probably the fastest path to a shareable URL). This repo
includes a `render.yaml` blueprint, so:
1. Push this branch (or merge it to `main`).
2. In Render: "New +" → "Blueprint" → connect the `partialdischarge` repo →
   pick the branch. Render reads `render.yaml` and fills in the settings
   itself (root dir `backend`, build/start commands, free plan).
3. Deploy. Render gives you a `https://<name>.onrender.com` URL — that's the
   whole app, frontend included.

(No blueprint handy? The manual settings are the same: root directory
`backend`, build command `pip install -r requirements.txt`, start command
`uvicorn app.main:app --host 0.0.0.0 --port $PORT`.)

**Railway.app** works almost identically (connect the repo, set the same
root directory/build/start commands, it detects Python automatically).

**Fly.io** if you want a Dockerfile-based deploy instead — ask and I can add
a `Dockerfile` (it's just `pip install -r backend/requirements.txt` then
`uvicorn app.main:app --host 0.0.0.0 --port 8080`, run from `backend/`).

Any of these need you to actually own/connect the GitHub repo and the
hosting account — that's not something I can do from here, but I can add
config files (e.g. a `render.yaml` or `Dockerfile`) if you tell me which
host you want to use.

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
    above/below-onset status, max field, an indicative corona current, the
    **field utilization factor** (η = E_avg/E_max — 1.0 for a perfectly
    uniform field like parallel plates, much less than 1 for a sharp point),
    and a **DC space-charge (ion transit) time** — the characteristic time
    for ions to sweep across the gap under the local field, a first-order
    estimate of how long space-charge effects take to stabilize (see below
    for its caveats).
  - For internal-void and surface-discharge geometries: **both** a transient
    (t=0+, capacitive) and a steady-state (t→∞, resistive) inception voltage
    and status, plus the interfacial relaxation time constant τ that governs
    how long it takes to transition between the two — see below.
- The **Parameter Sweep** tab varies any single numeric parameter (electrode/
  sample dimensions, material properties, or environment) over a range —
  including pushing voltage well past onset to see the knock-on effects on
  every other output — and lets you pick **any** resulting metric (inception
  voltage, max field, utilization factor, space-charge time, current/charge,
  margin) to plot on the Y-axis, with a full table and CSV export. This is
  the tool for "if I change just this one thing, what else moves" questions.

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

**Field utilization factor** `eta = E_avg / E_max` (E_avg = V/gap) is the
standard HV engineering figure of merit for how non-uniform a gap's field
is — 1.0 for parallel plates, much less than 1 for a sharp point. Reported
for all corona geometries plus coaxial-void (bulk field) and surface
discharge.

**DC space-charge (ion transit) time** integrates `dz / (mobility * E(z))`
along the gap's symmetry axis using the actual (non-uniform) field profile,
giving the characteristic time for an ion to sweep from the stressed
electrode to the counter-electrode. This uses the space-charge-*free*
(Laplacian) field as an approximation -- it does **not** solve the
self-consistent, space-charge-augmented field equation, so real space-charge
stabilization to a steady ionic distribution typically takes a few multiples
of this single-transit-time estimate, not exactly this value. Treat it as
"this order of magnitude and faster/slower with these parameters", not a
calibrated stabilization time.

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
