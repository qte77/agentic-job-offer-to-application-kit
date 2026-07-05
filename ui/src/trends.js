// Keyword-trends charts (vendored Chart.js — no CDN) (#249 slice E).
// State this module OWNS: the two Chart.js instances and the rendered-once flag; the trend records
// and range window are passed in by the orchestrator. `Chart` stays a bare global from the vendored
// UMD <script defer> — set on window before DOMContentLoaded, so no import is needed.
//
// Trends load at runtime from the deployment's own `data` branch (mirrors qte77/analyze-stock-kpi) —
// the data is never bundled into ui/. Auto-derive the base from the GitHub Pages origin so every
// fork self-hosts its own data; `?base=` overrides (local dev / custom domain), else the qte77 default.

import { cssVar } from "./dom-utils.js";

function defaultDataBase() {
  const m = location.hostname.match(/^([^.]+)\.github\.io$/);
  const repo = location.pathname.split("/").filter(Boolean)[0];
  return m && repo
    ? `https://raw.githubusercontent.com/${m[1]}/${repo}/data`
    : "https://raw.githubusercontent.com/qte77/agentic-job-offer-to-application-kit/data";
}
const DATA_BASE_URL = (
  new URLSearchParams(location.search).get("base") ?? defaultDataBase()
).replace(/\/$/, "");

/** @type {any} Chart.js instances (rebuilt on theme flip to re-read tokens). */
let lineChart = null;
let barChart = null;
let trendsRendered = false; // charts in a hidden tab panel size to 0 → render on first reveal

// The orchestrator reads this before first reveal / re-render decisions…
export function trendsPainted() {
  return trendsRendered;
}

// …and calls this on themechange (Chart.js caches CSS-variable colors at construction time).
export function invalidateTrends() {
  trendsRendered = false;
}

// Categorical zero-blue palette from the data arc + accent (re-read each render so a theme flip
// repaints the charts).
const chartPalette = () => [
  cssVar("--data-positive"),
  cssVar("--data-alt"),
  cssVar("--data-caution"),
  cssVar("--primary"),
  cssVar("--data-negative"),
];

// Pivot the {week,counts}[] log into chart shapes. `keys` is the union of keywords across weeks,
// ordered by latest-week volume (desc) so each keyword keeps one stable color across all three charts.
function pivot(records) {
  const labels = records.map((r) => r.week);
  const latest = records.length ? records[records.length - 1].counts : {};
  const keys = [...new Set(records.flatMap((r) => Object.keys(r.counts)))].sort(
    (a, b) => (latest[b] || 0) - (latest[a] || 0) || a.localeCompare(b),
  );
  return { labels, latest, keys };
}

// Fetch one trends source (NDJSON of {week,counts}). Returns the parsed records, or null on any miss
// (absent / non-200 / bad line / network error) so the caller can try the next source.
async function fetchTrends(url) {
  try {
    const res = await fetch(url);
    if (!res.ok) return null;
    const records = (await res.text())
      .split("\n")
      .filter((line) => line.trim())
      .map((line) => JSON.parse(line));
    return records.length ? records : null;
  } catch {
    return null;
  }
}

// Load the real aggregate trends, preferring a SAME-ORIGIN copy bundled into the Pages deploy by
// gh-pages.yaml. That avoids the cross-origin request to raw.githubusercontent that some networks /
// extensions block (a CORS failure that otherwise drops the dashboard silently to synthetic data).
// Falls back to the `data` branch over raw.githubusercontent (freshest; the local-dev / fork path),
// then to null so the caller uses the synthetic set. An explicit `?base=` is honored first.
export async function loadRealTrends() {
  const sameOrigin = "public/data/trends.ndjson";
  const dataBranch = `${DATA_BASE_URL}/public-data/trends.ndjson`;
  const order = new URLSearchParams(location.search).has("base")
    ? [dataBranch, sameOrigin]
    : [sameOrigin, dataBranch];
  for (const url of order) {
    const records = await fetchTrends(url);
    if (records) return records;
  }
  return null;
}

// Shared Chart.js builder for the two trends charts: resolves the canvas, pivots the records, and
// re-reads the theme tokens each call (so a theme flip repaints). `dataset(color)` supplies the
// per-series style and `scales(grid, tick)` the axes; `interaction` is line-only. Destroys `prev` only
// once it's safe to rebuild and returns the new Chart — or `prev` untouched when the canvas / Chart.js
// isn't ready (a hidden panel sizes to 0), preserving the old guard-then-build order.
function renderChart(canvasId, type, records, prev, { dataset, scales, interaction }) {
  const canvas = document.getElementById(canvasId);
  if (!canvas || typeof Chart === "undefined") return prev;
  const { labels, keys } = pivot(records);
  const pal = chartPalette();
  const grid = cssVar("--border");
  const tick = cssVar("--text-muted");
  const label = cssVar("--text");

  if (prev) prev.destroy();
  return new Chart(canvas, {
    type,
    data: {
      labels,
      datasets: keys.map((k, i) => ({
        label: k,
        data: records.map((r) => r.counts[k] || 0),
        ...dataset(pal[i % pal.length]),
      })),
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      ...(interaction ? { interaction } : {}),
      scales: scales(grid, tick),
      plugins: { legend: { labels: { color: label } } },
    },
  });
}

function renderLine(records) {
  lineChart = renderChart("trends-line", "line", records, lineChart, {
    dataset: (c) => ({
      borderColor: c,
      backgroundColor: c,
      tension: 0.3,
      pointRadius: 2,
      borderWidth: 2,
    }),
    scales: (grid, tick) => ({
      x: { grid: { color: grid }, ticks: { color: tick } },
      y: { beginAtZero: true, grid: { color: grid }, ticks: { color: tick } },
    }),
    interaction: { mode: "index", intersect: false },
  });
}

// Vertical stacked bars: one column per ISO week, keywords piled. Each week is its own counts
// (no running total across weeks).
function renderBar(records) {
  barChart = renderChart("trends-bar", "bar", records, barChart, {
    dataset: (c) => ({ backgroundColor: c, borderWidth: 0 }),
    scales: (grid, tick) => ({
      x: { stacked: true, grid: { color: grid }, ticks: { color: tick } },
      y: { stacked: true, beginAtZero: true, grid: { color: grid }, ticks: { color: tick } },
    }),
  });
}

// Monday (UTC) of an ISO week "YYYY-Www" — Jan 4 is always in ISO week 1. Lets the (sparse) series
// be windowed by calendar time rather than record count.
function isoWeekToDate(week) {
  const [y, w] = week.split("-W").map(Number);
  const jan4 = new Date(Date.UTC(y, 0, 4));
  const mondayW1 = new Date(jan4);
  mondayW1.setUTCDate(jan4.getUTCDate() - ((jan4.getUTCDay() + 6) % 7));
  const d = new Date(mondayW1);
  d.setUTCDate(mondayW1.getUTCDate() + (w - 1) * 7);
  return d;
}

// Keep only the trailing window of the sorted series (value = # of ISO weeks back from the latest,
// or "all"). Filters by date so sparse weeks aren't miscounted.
function windowRecords(sorted, value) {
  if (value === "all" || sorted.length === 0) return sorted;
  const cutoff =
    isoWeekToDate(sorted[sorted.length - 1].week).getTime() -
    (Number(value) - 1) * 7 * 86400000;
  return sorted.filter((r) => isoWeekToDate(r.week).getTime() >= cutoff);
}

export function renderTrends(trendRecords, range) {
  if (!trendRecords) return;
  // Sort once here (not in pivot) so the line/bar datasets, which map over this same array, stay
  // aligned with the labels. Real trends.ndjson is upsert-appended so it may not be in order;
  // ISO-week strings ("YYYY-Www", zero-padded) sort chronologically as plain strings.
  const sorted = [...trendRecords].sort((a, b) => a.week.localeCompare(b.week));
  const records = windowRecords(sorted, range);
  renderLine(records);
  renderBar(records);
  trendsRendered = true;
}
