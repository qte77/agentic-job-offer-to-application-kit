// Hiring charts (#2 / plan 006 S2b) — vendored Chart.js (global) + trends.js's fetch/URL helpers.
// TWO top-N line charts (the geo-by-field / company space is unbounded, so plotting every key would
// be an unreadable hundred-line chart — only the most-hiring buckets are drawn):
//   * PUBLISHABLE geo-by-field — Market-trends tab; loaded same-origin-first then the `data` branch,
//     exactly like the keyword trends (aggregate `{week,counts}`, no company names).
//   * LOCAL per-company — Companies tab; SAME-ORIGIN only (business data, never cross-origin; present
//     only in `make preview`'s bundle), so the published site never shows it.
//
// State this module OWNS: its two Chart.js instances + painted flags. Records + range are passed in
// by the orchestrator (app.js), mirroring trends.js.

import { cssVar } from "./dom-utils.js";
import { fetchTrends, isoWeekToDate, loadSeries } from "./trends.js";

const TOP_N = 10; // most-hiring buckets to plot; the long tail is dropped (unreadable otherwise).

// Publishable geo-by-field granularities — same three-file shape as the keyword trends, distinct
// filenames (hiring-weekly/daily/monthly.ndjson, matching the Makefile TRENDS_PUBLISH allowlist).
const HIRING = {
  week: { file: "hiring-weekly.ndjson", key: "week", toDate: isoWeekToDate },
  day: { file: "hiring-daily.ndjson", key: "date", toDate: (d) => new Date(`${d}T00:00:00Z`) },
  month: { file: "hiring-monthly.ndjson", key: "month", toDate: (m) => new Date(`${m}-01T00:00:00Z`) },
};
// The local per-company series is weekly-only ({week, counts:{company:n}}).
const LOCAL_GRAN = { key: "week", toDate: isoWeekToDate };

let geoChart = null;
let companyChart = null;
let geoPainted = false;
let companyPainted = false;

export function hiringPainted() {
  return geoPainted;
}
export function localHiringPainted() {
  return companyPainted;
}
export function invalidateHiring() {
  geoPainted = false;
  companyPainted = false;
}

// Publishable geo-by-field: same-origin first, then the data branch (like loadRealTrends). Returns
// `{records, gran}` (the gran travels with the records so there is no shared module-global to drift).
export async function loadRealHiring(gran = "week") {
  const g = HIRING[gran] ?? HIRING.week;
  const records = await loadSeries(g.file);
  return records ? { records, gran: g } : null;
}

// Local per-company: SAME-ORIGIN only — business data, never fetched cross-origin (mirrors
// companies.js). Present only in the make-preview bundle; absent -> the Companies-tab chart stays hidden.
export async function loadLocalHiring() {
  const records = await fetchTrends("public/data/hiring-companies.ndjson");
  return records ? { records, gran: LOCAL_GRAN } : null;
}

const palette = () => [
  cssVar("--data-positive"),
  cssVar("--data-alt"),
  cssVar("--data-caution"),
  cssVar("--primary"),
  cssVar("--data-negative"),
];

// The TOP_N keys by total volume across the (windowed) records — desc, tie-broken by name so colors
// stay stable. Dropping the long tail is what keeps the chart legible.
function topKeys(records, n) {
  const totals = {};
  for (const r of records) {
    for (const [k, v] of Object.entries(r.counts)) totals[k] = (totals[k] || 0) + v;
  }
  return Object.keys(totals)
    .sort((a, b) => (totals[b] || 0) - (totals[a] || 0) || a.localeCompare(b))
    .slice(0, n);
}

// Trailing calendar window (same 7-day-per-unit math as trends.js), keyed by the series' own label
// parser so weekly/daily/monthly all trim to the same span. "all" keeps everything.
function windowRecords(sorted, value, gran) {
  if (value === "all" || sorted.length === 0) return sorted;
  const toMs = (r) => gran.toDate(r[gran.key]).getTime();
  const cutoff = toMs(sorted[sorted.length - 1]) - (Number(value) - 1) * 7 * 86400000;
  return sorted.filter((r) => toMs(r) >= cutoff);
}

// Build a top-N line chart on `canvasId`; returns the new Chart (or `prev` untouched when the canvas /
// Chart.js isn't ready — a hidden tab panel sizes to 0). Destroys `prev` only once it's safe to rebuild.
function renderTopN(canvasId, payload, range, prev) {
  const canvas = document.getElementById(canvasId);
  if (!canvas || typeof Chart === "undefined") return prev;
  const { records, gran } = payload;
  const sorted = [...records].sort((a, b) => String(a[gran.key]).localeCompare(String(b[gran.key])));
  const windowed = windowRecords(sorted, range, gran);
  const keys = topKeys(windowed, TOP_N);
  const labels = windowed.map((r) => r[gran.key]);
  const pal = palette();
  const grid = cssVar("--border");
  const tick = cssVar("--text-muted");
  const label = cssVar("--text");
  if (prev) prev.destroy();
  return new Chart(canvas, {
    type: "line",
    data: {
      labels,
      datasets: keys.map((k, i) => ({
        label: k,
        data: windowed.map((r) => r.counts[k] || 0),
        borderColor: pal[i % pal.length],
        backgroundColor: pal[i % pal.length],
        tension: 0.3,
        pointRadius: 2,
        borderWidth: 2,
      })),
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: "index", intersect: false },
      scales: {
        x: { grid: { color: grid }, ticks: { color: tick } },
        y: { beginAtZero: true, grid: { color: grid }, ticks: { color: tick } },
      },
      plugins: { legend: { labels: { color: label } } },
    },
  });
}

export function renderHiring(payload, range) {
  if (!payload) return;
  geoChart = renderTopN("hiring-line", payload, range, geoChart);
  geoPainted = true;
}

export function renderLocalHiring(payload, range) {
  if (!payload) return;
  companyChart = renderTopN("hiring-companies-line", payload, range, companyChart);
  companyPainted = true;
}
