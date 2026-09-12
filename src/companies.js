// Companies-hiring table: render the LOCAL market-intel snapshot (#284) — who's hiring, by location
// x field, with per-company active-role counts and an optional heating/cooling momentum tag.
// State this module OWNS: the loaded rows + the active sort column/direction (#4). app.js hands the
// snapshot in once; sorting is driven entirely from here off the table's own header clicks.
//
// Same-origin ONLY: like the real shortlist (and UNLIKE the aggregate trends), company + geo is
// business data — NEVER fetched cross-origin / from the `data` branch, and gh-pages bundles none.
// Absent (the published site, or no local corpus) -> the caller leaves the Companies tab hidden.

import { esc } from "./dom-utils.js";

// Contract (#3): companies.json is `{snapshot, rows}` (was a bare rows array). Only this module and
// scripts/build_ui_companies.py know the shape — the Companies tab is never published, so no
// cross-origin/back-compat consumer exists.
export async function loadRealCompanies() {
  try {
    const res = await fetch("public/data/companies.json");
    if (!res.ok) return null;
    const data = await res.json();
    const rows = data && Array.isArray(data.rows) ? data.rows : null;
    return rows && rows.length ? { snapshot: data.snapshot || "", rows } : null;
  } catch {
    return null;
  }
}

// Labels for the momentum tag; the class `is-<momentum>` drives the color (style.css). Absent
// momentum (shallow history) renders nothing — the snapshot ships without a heating/cooling claim.
const MOMENTUM_LABEL = { heating: "▲ heating", cooling: "▼ cooling", steady: "steady" };
// Ordinal so the Momentum column sorts by intensity (heating > steady > cooling > dormant), not
// alphabetically; dormant (null) momentum ranks last in an ascending pass.
const MOMENTUM_RANK = { heating: 3, steady: 2, cooling: 1 };

// Per-column sort accessor (#4), keyed by each header's `data-sort`. `location` folds city + region
// into one comparable string so it sorts the way it renders; `count` stays numeric.
const SORT_KEYS = {
  company: (r) => r.company.toLowerCase(),
  location: (r) => `${r.city} ${r.region}`.trim().toLowerCase(),
  field: (r) => r.field.toLowerCase(),
  count: (r) => r.count,
  momentum: (r) => MOMENTUM_RANK[r.momentum] ?? 0,
};

// col === null means "untouched": keep aggregate_companies' default order (city, field, -count,
// company). dir is +1 asc / -1 desc.
const state = { rows: [], col: null, dir: 1 };
let wired = false;

export function renderCompanies(data) {
  state.rows = data.rows;
  state.col = null;
  state.dir = 1;
  document.getElementById("companies-count").textContent = String(state.rows.length);
  const asOf = document.getElementById("companies-snapshot");
  if (asOf) asOf.textContent = data.snapshot || "n/a";
  wireHeaders();
  paint();
}

// Click / Enter / Space on a sortable header sorts by it, toggling asc<->desc; a fresh column starts
// ascending. Delegated on <thead> and wired once (survives re-paints).
function wireHeaders() {
  if (wired) return;
  const thead = document.querySelector("#companies-table thead");
  if (!thead) return;
  const onSort = (th) => {
    const col = th.getAttribute("data-sort");
    if (!SORT_KEYS[col]) return;
    state.dir = state.col === col ? -state.dir : 1;
    state.col = col;
    paint();
  };
  thead.addEventListener("click", (e) => {
    const th = e.target.closest("th[data-sort]");
    if (th) onSort(th);
  });
  thead.addEventListener("keydown", (e) => {
    if (e.key !== "Enter" && e.key !== " ") return;
    const th = e.target.closest("th[data-sort]");
    if (th) {
      e.preventDefault();
      onSort(th);
    }
  });
  wired = true;
}

function paint() {
  updateHeaderState();
  const body = document.getElementById("companies-body");
  body.innerHTML = sortedRows()
    .map((r) => {
      const geo = r.region ? `${esc(r.city)} · ${esc(r.region)}` : esc(r.city);
      const momentum = r.momentum
        ? `<span class="momentum is-${esc(r.momentum)}">${esc(MOMENTUM_LABEL[r.momentum] || r.momentum)}</span>`
        : "";
      return `<tr>
        <td>${esc(r.company)}</td>
        <td>${geo}</td>
        <td><span class="lane">${esc(r.field)}</span></td>
        <td class="num">${esc(r.count)}</td>
        <td>${momentum}</td>
      </tr>`;
    })
    .join("");
}

function sortedRows() {
  if (!state.col) return state.rows; // untouched -> the aggregate's default ordering
  const key = SORT_KEYS[state.col];
  // Copy before sorting so returning to the default order stays possible; tie-break by company for
  // a stable, deterministic result.
  return [...state.rows].sort((a, b) => {
    const va = key(a);
    const vb = key(b);
    const base = va < vb ? -1 : va > vb ? 1 : 0;
    return base ? base * state.dir : a.company.localeCompare(b.company);
  });
}

function updateHeaderState() {
  document.querySelectorAll("#companies-table thead th[data-sort]").forEach((th) => {
    const active = th.getAttribute("data-sort") === state.col;
    th.setAttribute("aria-sort", active ? (state.dir === 1 ? "ascending" : "descending") : "none");
    const ind = th.querySelector(".sort-ind");
    if (ind) ind.textContent = active ? (state.dir === 1 ? "▲" : "▼") : "";
  });
}
