// Companies-hiring table: render the LOCAL market-intel snapshot (#284) — who's hiring, by location
// x field, with per-company active-role counts and an optional heating/cooling momentum tag.
// State this module OWNS: nothing — rows are passed in by the orchestrator (app.js).
//
// Same-origin ONLY: like the real shortlist (and UNLIKE the aggregate trends), company + geo is
// business data — NEVER fetched cross-origin / from the `data` branch, and gh-pages bundles none.
// Absent (the published site, or no local corpus) -> the caller leaves the Companies tab hidden.

import { esc } from "./dom-utils.js";

export async function loadRealCompanies() {
  try {
    const res = await fetch("public/data/companies.json");
    if (!res.ok) return null;
    const arr = await res.json();
    return Array.isArray(arr) && arr.length ? arr : null;
  } catch {
    return null;
  }
}

// Labels for the momentum tag; the class `is-<momentum>` drives the color (style.css). Absent
// momentum (shallow history) renders nothing — the snapshot ships without a heating/cooling claim.
const MOMENTUM_LABEL = { heating: "▲ heating", cooling: "▼ cooling", steady: "steady" };

export function renderCompanies(rows) {
  document.getElementById("companies-count").textContent = String(rows.length);
  const body = document.getElementById("companies-body");
  body.innerHTML = rows
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
