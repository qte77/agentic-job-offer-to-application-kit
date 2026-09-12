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

// Trend granularities (#187/#188): each maps to its published NDJSON (same list as the Makefile
// TRENDS_PUBLISH allowlist), the per-record label key, and a label→Date parser so the time-window
// filter works uniformly across all three. Weekly is the default (and the synthetic-fallback shape).
// `isoWeekToDate` is a hoisted function declaration below, so it's already bound here.
const GRANULARITIES = {
  week: { file: "trends.ndjson", key: "week", toDate: isoWeekToDate },
  day: { file: "trends-daily.ndjson", key: "date", toDate: (d) => new Date(`${d}T00:00:00Z`) },
  month: { file: "trends-monthly.ndjson", key: "month", toDate: (m) => new Date(`${m}-01T00:00:00Z`) },
};
// The active granularity's config; set by loadRealTrends(gran), read by pivot/windowRecords/
// renderTrends so the label-key access stays in one place (DRY). Kept in lockstep with the records
// the orchestrator holds — loadRealTrends only commits it once the matching series has loaded.
let activeGran = GRANULARITIES.week;

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

// Pivot the {<label>,counts}[] log into chart shapes (label = week/date/month per activeGran). `keys`
// is the union of keywords across buckets, ordered by latest-bucket volume (desc) so each keyword
// keeps one stable color across all three charts.
function pivot(records) {
  const labels = records.map((r) => r[activeGran.key]);
  const latest = records.length ? records[records.length - 1].counts : {};
  const keys = [...new Set(records.flatMap((r) => Object.keys(r.counts)))].sort(
    (a, b) => (latest[b] || 0) - (latest[a] || 0) || a.localeCompare(b),
  );
  return { labels, latest, keys };
}

// Fetch one trends source (NDJSON of {<label>,counts}). Returns the parsed records, or null on any miss
// (absent / non-200 / bad line / network error) so the caller can try the next source. Exported so the
// hiring charts (hiring.js) reuse the identical NDJSON parse — including the same-origin-only path for
// the LOCAL per-company series (which must never fall back cross-origin).
export async function fetchTrends(url) {
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
// Load one publishable NDJSON series by filename, preferring the SAME-ORIGIN deploy copy, then the
// `data` branch over raw.githubusercontent (honoring an explicit `?base=`), then null. Shared by the
// keyword loader below and hiring.js's publishable geo-by-field loader — one place owns the fallback
// order so `?base=` behaves identically for both.
export async function loadSeries(file) {
  const sameOrigin = `public/data/${file}`;
  const dataBranch = `${DATA_BASE_URL}/public-data/${file}`;
  const order = new URLSearchParams(location.search).has("base")
    ? [dataBranch, sameOrigin]
    : [sameOrigin, dataBranch];
  for (const url of order) {
    const records = await fetchTrends(url);
    if (records) return records;
  }
  return null;
}

export async function loadRealTrends(gran = "week") {
  const g = GRANULARITIES[gran] ?? GRANULARITIES.week;
  const records = await loadSeries(g.file);
  // Commit the granularity only once its series is in hand, so activeGran never drifts from the
  // records the orchestrator is about to render (a miss leaves the current view untouched).
  if (records) {
    activeGran = g;
    return records;
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
// be windowed by calendar time rather than record count. Exported so hiring.js windows its weekly
// series with the identical calendar math.
export function isoWeekToDate(week) {
  const [y, w] = week.split("-W").map(Number);
  const jan4 = new Date(Date.UTC(y, 0, 4));
  const mondayW1 = new Date(jan4);
  mondayW1.setUTCDate(jan4.getUTCDate() - ((jan4.getUTCDay() + 6) % 7));
  const d = new Date(mondayW1);
  d.setUTCDate(mondayW1.getUTCDate() + (w - 1) * 7);
  return d;
}

// Keep only the trailing calendar window of the sorted series. `value` is the time frame as a
// trailing ISO-week count (the dropdown labels: 3mo=13, 1y=52, …), applied uniformly to every
// granularity by converting each bucket's label to a Date — so "3mo" trims weekly, daily and monthly
// to the same ~91-day span. "all" keeps everything.
function windowRecords(sorted, value) {
  if (value === "all" || sorted.length === 0) return sorted;
  const toMs = (r) => activeGran.toDate(r[activeGran.key]).getTime();
  const cutoff = toMs(sorted[sorted.length - 1]) - (Number(value) - 1) * 7 * 86400000;
  return sorted.filter((r) => toMs(r) >= cutoff);
}

export function renderTrends(trendRecords, range) {
  if (!trendRecords) return;
  // Sort once here (not in pivot) so the line/bar datasets, which map over this same array, stay
  // aligned with the labels. The NDJSON is upsert-appended so it may not be in order; every label
  // format ("YYYY-Www" / "YYYY-MM-DD" / "YYYY-MM", zero-padded) sorts chronologically as a string.
  const key = activeGran.key;
  const sorted = [...trendRecords].sort((a, b) => String(a[key]).localeCompare(String(b[key])));
  const records = windowRecords(sorted, range);
  renderLine(records);
  renderBar(records);
  trendsRendered = true;
}
