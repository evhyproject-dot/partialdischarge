const API_BASE = window.PD_API_BASE || "http://localhost:8000";

const state = {
  geometries: null,
  envParams: null,
  currentGeometry: null,
  paramValues: {},
  envValues: {},
  lastResult: null,
  lastSweep: null,
};

const el = (id) => document.getElementById(id);

async function api(path, opts) {
  const res = await fetch(API_BASE + path, {
    headers: { "Content-Type": "application/json" },
    ...opts,
  });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`${res.status}: ${body}`);
  }
  return res.json();
}

function setStatus(ok, msg) {
  const s = el("connectionStatus");
  s.textContent = msg;
  s.className = "status " + (ok ? "ok" : "err");
}

function buildFormField(spec, values, container) {
  const wrap = document.createElement("div");
  wrap.className = "form-field";
  const label = document.createElement("label");
  label.textContent = spec.label + (spec.unit ? ` (${spec.unit})` : "");
  const input = document.createElement("input");
  input.type = "number";
  input.step = "any";
  input.min = spec.min;
  input.max = spec.max;
  input.value = values[spec.name] ?? spec.default;
  input.dataset.name = spec.name;
  input.addEventListener("change", () => {
    values[spec.name] = parseFloat(input.value);
  });
  wrap.appendChild(label);
  wrap.appendChild(input);
  container.appendChild(wrap);
}

function renderParamsForm() {
  const container = el("paramsForm");
  container.innerHTML = "";
  const schema = state.geometries[state.currentGeometry];
  el("geometryDescription").textContent = schema.description;
  state.paramValues = {};
  for (const p of schema.params) {
    state.paramValues[p.name] = p.default;
    buildFormField(p, state.paramValues, container);
  }
  populateSweepTargets();
}

function renderEnvForm() {
  const container = el("envForm");
  container.innerHTML = "";
  state.envValues = {};
  for (const p of state.envParams) {
    state.envValues[p.name] = p.default;
    buildFormField(p, state.envValues, container);
  }
  updateEnvSummary();
}

function updateEnvSummary() {
  const t = state.envValues.temperature_c;
  const p = state.envValues.pressure_kpa;
  const h = state.envValues.humidity_percent;
  const delta = (p / 101.3) * (293.15 / (t + 273.15));
  el("envSummary").textContent = `Relative air density delta ~= ${delta.toFixed(3)} at T=${t}C, P=${p}kPa, RH=${h}%.`;
}

function populateSweepTargets() {
  const sel = el("sweepTarget");
  sel.innerHTML = "";
  const schema = state.geometries[state.currentGeometry];
  const groupParams = document.createElement("optgroup");
  groupParams.label = "Electrode parameters";
  for (const p of schema.params) {
    const o = document.createElement("option");
    o.value = p.name;
    o.textContent = p.label;
    groupParams.appendChild(o);
  }
  const groupEnv = document.createElement("optgroup");
  groupEnv.label = "Environment";
  for (const p of state.envParams) {
    const o = document.createElement("option");
    o.value = p.name;
    o.textContent = p.label;
    groupEnv.appendChild(o);
  }
  sel.appendChild(groupParams);
  sel.appendChild(groupEnv);
  sel.addEventListener("change", updateSweepDefaults);
  updateSweepDefaults();
}

function findParamSpec(name) {
  const schema = state.geometries[state.currentGeometry];
  return schema.params.find((p) => p.name === name) || state.envParams.find((p) => p.name === name);
}

function updateSweepDefaults() {
  const target = el("sweepTarget").value;
  const spec = findParamSpec(target);
  if (!spec) return;
  el("sweepStart").value = spec.min;
  el("sweepStop").value = spec.max;
}

async function loadGeometries() {
  const data = await api("/api/geometries");
  state.geometries = data.geometries;
  state.envParams = data.environment_params;
  const sel = el("geometrySelect");
  sel.innerHTML = "";
  for (const [key, g] of Object.entries(state.geometries)) {
    const o = document.createElement("option");
    o.value = key;
    o.textContent = g.label;
    sel.appendChild(o);
  }
  state.currentGeometry = Object.keys(state.geometries)[0];
  sel.value = state.currentGeometry;
  sel.addEventListener("change", () => {
    state.currentGeometry = sel.value;
    renderParamsForm();
  });
  renderParamsForm();
  renderEnvForm();
}

// ---------- Field map rendering ----------

function colorFor(t) {
  // t in [0,1]; low->mid->high three-stop ramp
  const stops = [
    [11, 22, 60], // deep blue
    [242, 199, 68], // amber
    [215, 38, 61], // red
  ];
  const scaled = Math.max(0, Math.min(1, t)) * (stops.length - 1);
  const i = Math.floor(scaled);
  const frac = scaled - i;
  const a = stops[Math.min(i, stops.length - 1)];
  const b = stops[Math.min(i + 1, stops.length - 1)];
  return [
    Math.round(a[0] + (b[0] - a[0]) * frac),
    Math.round(a[1] + (b[1] - a[1]) * frac),
    Math.round(a[2] + (b[2] - a[2]) * frac),
  ];
}

function drawLegend(minVal, maxVal, unitLabel) {
  const legend = el("fieldLegend");
  legend.innerHTML = "";
  const title = document.createElement("div");
  title.textContent = unitLabel;
  title.style.fontWeight = "600";
  legend.appendChild(title);
  const steps = 6;
  for (let i = steps; i >= 0; i--) {
    const t = i / steps;
    const val = minVal + (maxVal - minVal) * t;
    const row = document.createElement("div");
    row.className = "swatch-row";
    const sw = document.createElement("div");
    sw.className = "swatch";
    const [r, g, b] = colorFor(t);
    sw.style.background = `rgb(${r},${g},${b})`;
    row.appendChild(sw);
    const txt = document.createElement("span");
    txt.textContent = formatSci(val);
    row.appendChild(txt);
    legend.appendChild(row);
  }
}

function formatSci(v) {
  if (Math.abs(v) >= 1000 || (Math.abs(v) < 0.01 && v !== 0)) {
    return v.toExponential(2);
  }
  return v.toFixed(2);
}

function buildGridImage(grid2d, nx, ny) {
  // grid2d: array[row][col], row along "y" (already oriented top-first)
  const flat = [];
  for (const row of grid2d) for (const v of row) if (v !== null && v !== undefined) flat.push(v);
  const logVals = flat.filter((v) => v > 0).map((v) => Math.log10(v));
  const minL = Math.min(...logVals);
  const maxL = Math.max(...logVals);

  const canvas = document.createElement("canvas");
  canvas.width = nx;
  canvas.height = ny;
  const ctx = canvas.getContext("2d");
  const img = ctx.createImageData(nx, ny);
  for (let y = 0; y < ny; y++) {
    for (let x = 0; x < nx; x++) {
      const v = grid2d[y][x];
      const idx = (y * nx + x) * 4;
      if (v === null || v === undefined) {
        img.data[idx] = 20;
        img.data[idx + 1] = 24;
        img.data[idx + 2] = 30;
        img.data[idx + 3] = 255;
        continue;
      }
      const lv = v > 0 ? Math.log10(v) : minL;
      const t = maxL > minL ? (lv - minL) / (maxL - minL) : 0.5;
      const [r, g, b] = colorFor(t);
      img.data[idx] = r;
      img.data[idx + 1] = g;
      img.data[idx + 2] = b;
      img.data[idx + 3] = 255;
    }
  }
  ctx.putImageData(img, 0, 0);
  return { canvas, minL, maxL };
}

function drawContours(ctx, potential2d, nx, ny, scaleX, scaleY, levels = 10) {
  const flat = [];
  for (const row of potential2d) for (const v of row) if (v !== null && v !== undefined) flat.push(v);
  if (!flat.length) return;
  const minV = Math.min(...flat);
  const maxV = Math.max(...flat);
  if (maxV === minV) return;
  const step = (maxV - minV) / levels;

  ctx.strokeStyle = "rgba(255,255,255,0.35)";
  ctx.lineWidth = 1;
  const levelOf = (v) => (v === null || v === undefined ? null : Math.floor((v - minV) / step));

  for (let y = 0; y < ny; y++) {
    for (let x = 0; x < nx - 1; x++) {
      const l1 = levelOf(potential2d[y][x]);
      const l2 = levelOf(potential2d[y][x + 1]);
      if (l1 !== null && l2 !== null && l1 !== l2) {
        ctx.beginPath();
        ctx.moveTo((x + 1) * scaleX, y * scaleY);
        ctx.lineTo((x + 1) * scaleX, (y + 1) * scaleY);
        ctx.stroke();
      }
    }
  }
  for (let y = 0; y < ny - 1; y++) {
    for (let x = 0; x < nx; x++) {
      const l1 = levelOf(potential2d[y][x]);
      const l2 = levelOf(potential2d[y + 1][x]);
      if (l1 !== null && l2 !== null && l1 !== l2) {
        ctx.beginPath();
        ctx.moveTo(x * scaleX, (y + 1) * scaleY);
        ctx.lineTo((x + 1) * scaleX, (y + 1) * scaleY);
        ctx.stroke();
      }
    }
  }
}

function renderPointGapField(result) {
  const rs = result.grid.r;
  const zs = result.grid.z;
  const nr = rs.length;
  const nz = zs.length;
  const width = 2 * nr - 1;

  // Build mirrored, vertically-flipped grids: row 0 = z_max (top)
  const fieldGrid = [];
  const potGrid = [];
  for (let zi = nz - 1; zi >= 0; zi--) {
    const frow = new Array(width);
    const prow = new Array(width);
    for (let c = 0; c < width; c++) {
      const ri = Math.abs(c - (nr - 1));
      frow[c] = result.field_magnitude_v_per_m[zi][ri];
      prow[c] = result.potential_v[zi][ri];
    }
    fieldGrid.push(frow);
    potGrid.push(prow);
  }

  const { canvas: gridCanvas, minL, maxL } = buildGridImage(fieldGrid, width, nz);
  const target = el("fieldCanvas");
  const ctx = target.getContext("2d");
  ctx.imageSmoothingEnabled = true;
  ctx.clearRect(0, 0, target.width, target.height);
  ctx.drawImage(gridCanvas, 0, 0, target.width, target.height);
  drawContours(ctx, potGrid, width, nz, target.width / width, target.height / nz);

  drawLegend(Math.pow(10, minL), Math.pow(10, maxL), "Field magnitude (V/m, log scale)");
}

function renderCoaxialField(result) {
  const xs = result.grid.x;
  const ys = result.grid.y;
  const nx = xs.length;
  const ny = ys.length;
  const grid = result.grid.field_v_per_m.slice().reverse();

  const { canvas: gridCanvas, minL, maxL } = buildGridImage(grid, nx, ny);
  const target = el("fieldCanvas");
  const ctx = target.getContext("2d");
  ctx.imageSmoothingEnabled = true;
  ctx.clearRect(0, 0, target.width, target.height);
  ctx.drawImage(gridCanvas, 0, 0, target.width, target.height);

  // mark void location
  const marker = result.geometry.void_marker_xy;
  const extent = xs[xs.length - 1];
  const px = ((marker.x + extent) / (2 * extent)) * target.width;
  const py = target.height - ((marker.y + extent) / (2 * extent)) * target.height;
  ctx.strokeStyle = "#ffffff";
  ctx.lineWidth = 2;
  ctx.beginPath();
  ctx.arc(px, py, 6, 0, Math.PI * 2);
  ctx.stroke();

  drawLegend(Math.pow(10, minL), Math.pow(10, maxL), "Field magnitude (V/m, log scale)");
}

function renderInceptionCard(result) {
  const card = el("inceptionCard");
  const inc = result.inception;
  const statusBadge = inc.status === "above_onset"
    ? `<span class="badge above">ABOVE ONSET</span>`
    : `<span class="badge below">below onset</span>`;

  let extra = "";
  if ("corona_current_ma" in result) {
    extra += row("Indicative corona current", `${result.corona_current_ma.toExponential(2)} mA`);
  }
  if (result.void) {
    extra += row("Void field", `${result.void.field_v_per_m.toExponential(2)} V/m`);
    extra += row("Void breakdown voltage", `${result.void.breakdown_voltage_v.toFixed(0)} V`);
    extra += row("Apparent charge (IEC 60270)", `${result.void.apparent_charge_pc.toFixed(1)} pC`);
  }

  function row(label, val) {
    return `<div class="row"><span>${label}</span><span>${val}</span></div>`;
  }

  card.innerHTML = `
    <div class="row"><span>Status</span>${statusBadge}</div>
    ${inc.onset_gradient_kv_cm ? row("Peek onset gradient", `${inc.onset_gradient_kv_cm.toFixed(2)} kV/cm`) : ""}
    ${row("Inception voltage", `${inc.inception_voltage_kv.toFixed(3)} kV`)}
    ${row("Applied voltage", `${inc.applied_voltage_kv.toFixed(3)} kV`)}
    ${row("Margin (applied / inception)", inc.margin_ratio.toFixed(2))}
    ${row("Max field", `${result.max_field_v_per_m.toExponential(2)} V/m`)}
    ${extra}
  `;
}

async function runAnalyze() {
  setStatus(true, "analyzing…");
  try {
    const body = {
      geometry: state.currentGeometry,
      params: state.paramValues,
      environment: state.envValues,
    };
    const result = await api("/api/analyze", { method: "POST", body: JSON.stringify(body) });
    state.lastResult = result;
    if (result.grid.r) renderPointGapField(result);
    else renderCoaxialField(result);
    renderInceptionCard(result);
    setStatus(true, "connected");
  } catch (e) {
    setStatus(false, "error: " + e.message);
  }
}

// ---------- Sweep ----------

function drawSweepChart(rows, target) {
  const canvas = el("sweepCanvas");
  const ctx = canvas.getContext("2d");
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  const pad = { l: 60, r: 20, t: 20, b: 40 };
  const w = canvas.width - pad.l - pad.r;
  const h = canvas.height - pad.t - pad.b;

  const xs = rows.map((r) => r.target_value);
  const ys = rows.map((r) => r.max_field_v_per_m);
  const xMin = Math.min(...xs), xMax = Math.max(...xs);
  const yMin = Math.min(...ys), yMax = Math.max(...ys);

  ctx.strokeStyle = "#5b6675";
  ctx.beginPath();
  ctx.moveTo(pad.l, pad.t);
  ctx.lineTo(pad.l, pad.t + h);
  ctx.lineTo(pad.l + w, pad.t + h);
  ctx.stroke();

  ctx.fillStyle = "#93a0b3";
  ctx.font = "11px sans-serif";
  ctx.fillText(target, pad.l + w / 2 - 20, canvas.height - 8);
  ctx.save();
  ctx.translate(14, pad.t + h / 2 + 30);
  ctx.rotate(-Math.PI / 2);
  ctx.fillText("Max field (V/m)", 0, 0);
  ctx.restore();

  const xTo = (v) => pad.l + ((v - xMin) / (xMax - xMin || 1)) * w;
  const yTo = (v) => pad.t + h - ((v - yMin) / (yMax - yMin || 1)) * h;

  ctx.strokeStyle = "#4f8fef";
  ctx.lineWidth = 2;
  ctx.beginPath();
  rows.forEach((r, i) => {
    const x = xTo(r.target_value);
    const y = yTo(r.max_field_v_per_m);
    if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
  });
  ctx.stroke();

  rows.forEach((r) => {
    const x = xTo(r.target_value);
    const y = yTo(r.max_field_v_per_m);
    ctx.fillStyle = r.status === "above_onset" ? "#d7263d" : "#1c8a4b";
    ctx.beginPath();
    ctx.arc(x, y, 3, 0, Math.PI * 2);
    ctx.fill();
  });
}

function renderSweepTable(rows) {
  const wrap = el("sweepTableWrap");
  const cols = Object.keys(rows[0]);
  let html = "<table><thead><tr>" + cols.map((c) => `<th>${c}</th>`).join("") + "</tr></thead><tbody>";
  for (const r of rows) {
    html += "<tr>" + cols.map((c) => `<td>${typeof r[c] === "number" ? formatSci(r[c]) : r[c]}</td>`).join("") + "</tr>";
  }
  html += "</tbody></table>";
  wrap.innerHTML = html;
}

async function runSweep() {
  const target = el("sweepTarget").value;
  const start = parseFloat(el("sweepStart").value);
  const stop = parseFloat(el("sweepStop").value);
  const steps = parseInt(el("sweepSteps").value, 10);
  try {
    const body = {
      geometry: state.currentGeometry,
      params: state.paramValues,
      environment: state.envValues,
      target,
      start,
      stop,
      steps,
    };
    const result = await api("/api/sweep", { method: "POST", body: JSON.stringify(body) });
    state.lastSweep = result;
    drawSweepChart(result.rows, target);
    renderSweepTable(result.rows);
  } catch (e) {
    alert("Sweep failed: " + e.message);
  }
}

function exportCsv() {
  if (!state.lastSweep) {
    alert("Run a sweep first.");
    return;
  }
  const rows = state.lastSweep.rows;
  const cols = Object.keys(rows[0]);
  const lines = [cols.join(",")];
  for (const r of rows) lines.push(cols.map((c) => r[c]).join(","));
  const blob = new Blob([lines.join("\n")], { type: "text/csv" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = `pd_sweep_${state.currentGeometry}_${state.lastSweep.target}.csv`;
  a.click();
}

function setupTabs() {
  document.querySelectorAll(".tab-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".tab-btn").forEach((b) => b.classList.remove("active"));
      document.querySelectorAll(".tab-content").forEach((c) => c.classList.add("hidden"));
      btn.classList.add("active");
      el("tab-" + btn.dataset.tab).classList.remove("hidden");
    });
  });
}

async function init() {
  setupTabs();
  el("analyzeBtn").addEventListener("click", runAnalyze);
  el("sweepBtn").addEventListener("click", runSweep);
  el("exportCsvBtn").addEventListener("click", exportCsv);
  try {
    await loadGeometries();
    setStatus(true, "connected");
    await runAnalyze();
  } catch (e) {
    setStatus(false, "cannot reach API at " + API_BASE);
  }
}

init();
