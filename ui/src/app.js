// EyeRest dashboard shell — vanilla ES module, no build step.
// Renders the synthetic shortlist from public/data/demo.json; the keyword-trends chart shows the
// real backfilled aggregate series from public/data/trends.ndjson (non-PII {week,counts}) when present, else
// the synthetic trends. Issue #11 skeleton; the live shortlist feed (pseudonymized, from the
// `data` branch at runtime) stays gated on #52.

/** @type {{lanes:{key:string,label:string}[], shortlist:any[], trends:{week:string,counts:Record<string,number>}[], generated:string}|null} */
let data = null;
let laneLabel = {};
/** @type {any} Chart.js instances (rebuilt on theme flip to re-read tokens). */
let lineChart = null;
let barChart = null;
let trendsRendered = false; // charts in a hidden tab panel size to 0 → render on first reveal

const cssVar = (name) =>
  getComputedStyle(document.body).getPropertyValue(name).trim();

const esc = (s) =>
  String(s).replace(
    /[&<>"]/g,
    (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c],
  );

// Only allow http(s) hrefs — blocks javascript:/data: even if the (future
// data-branch) feed is tampered with. esc() then handles quote-breakout.
const safeUrl = (u) => (/^https?:\/\//i.test(String(u)) ? String(u) : "#");

// ── Shortlist table ──
function scoreClass(score) {
  return score >= 4 ? "score-good" : score >= 3 ? "score-mid" : "score-bad";
}

function renderShortlist(filter = "") {
  const body = document.getElementById("shortlist-body");
  const f = filter.trim().toLowerCase();
  const rows = data.shortlist
    .filter((it) => {
      if (!f) return true;
      const hay = `${it.company} ${it.title} ${laneLabel[it.best_lane] || it.best_lane}`;
      return hay.toLowerCase().includes(f);
    })
    .sort((a, b) => b.score - a.score);

  document.getElementById("shortlist-count").textContent = String(rows.length);

  if (rows.length === 0) {
    body.innerHTML = `<tr><td colspan="5" class="empty-state">No matching offers</td></tr>`;
    return;
  }

  body.innerHTML = rows
    .map(
      (it) => `<tr>
        <td>${esc(it.company)}</td>
        <td>
          <div class="role-title"><a href="${esc(safeUrl(it.url))}" target="_blank" rel="noopener">${esc(it.title)}</a></div>
          <div class="rationale">${esc(it.rationale)}</div>
        </td>
        <td><span class="lane">${esc(laneLabel[it.best_lane] || it.best_lane)}</span></td>
        <td class="num"><span class="score ${scoreClass(it.score)}">${esc(it.score)}</span></td>
        <td><span class="verdict ${it.verdict === "shortlist" ? "is-shortlist" : ""}">${esc(it.verdict)}</span></td>
      </tr>`,
    )
    .join("");
}

// ── Keyword trends (vendored Chart.js — no CDN) ──
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

// Load the real backfilled trends from public/data/trends.ndjson (one {week,counts} JSON record per
// line, written by `ajoa-kit trend-snapshot` and copied in via `make trends-ui`). Returns null on
// any miss (absent file / non-200 / bad line) so the caller falls back to the synthetic set.
async function loadRealTrends() {
  try {
    const res = await fetch("public/data/trends.ndjson");
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

function renderLine(records) {
  const canvas = document.getElementById("trends-line");
  if (!canvas || typeof Chart === "undefined") return;
  const { labels, keys } = pivot(records);
  const pal = chartPalette();
  const grid = cssVar("--border");
  const tick = cssVar("--text-muted");
  const label = cssVar("--text");

  if (lineChart) lineChart.destroy();
  lineChart = new Chart(canvas, {
    type: "line",
    data: {
      labels,
      datasets: keys.map((k, i) => ({
        label: k,
        data: records.map((r) => r.counts[k] || 0),
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

// Vertical stacked bars: one column per ISO week, keywords piled. Each week is its own counts
// (no running total across weeks).
function renderBar(records) {
  const canvas = document.getElementById("trends-bar");
  if (!canvas || typeof Chart === "undefined") return;
  const { labels, keys } = pivot(records);
  const pal = chartPalette();
  const grid = cssVar("--border");
  const tick = cssVar("--text-muted");
  const label = cssVar("--text");

  if (barChart) barChart.destroy();
  barChart = new Chart(canvas, {
    type: "bar",
    data: {
      labels,
      datasets: keys.map((k, i) => ({
        label: k,
        data: records.map((r) => r.counts[k] || 0),
        backgroundColor: pal[i % pal.length],
        borderWidth: 0,
      })),
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        x: { stacked: true, grid: { color: grid }, ticks: { color: tick } },
        y: { stacked: true, beginAtZero: true, grid: { color: grid }, ticks: { color: tick } },
      },
      plugins: { legend: { labels: { color: label } } },
    },
  });
}

function renderTrends() {
  if (!data) return;
  // Sort once here (not in pivot) so the line/bar datasets, which map over this same array, stay
  // aligned with the labels. Real trends.ndjson is upsert-appended so it may not be in order;
  // ISO-week strings ("YYYY-Www", zero-padded) sort chronologically as plain strings.
  const records = [...data.trends].sort((a, b) => a.week.localeCompare(b.week));
  renderLine(records);
  renderBar(records);
  trendsRendered = true;
}

// ── Tabs (WAI-ARIA tabs pattern: roving tabindex + arrow keys) ──
function initTabs() {
  const tabs = Array.from(document.querySelectorAll('[role="tab"]'));
  function select(tab) {
    tabs.forEach((t) => {
      const on = t === tab;
      t.setAttribute("aria-selected", String(on));
      t.tabIndex = on ? 0 : -1;
      const panel = document.getElementById(t.getAttribute("aria-controls"));
      if (panel) panel.hidden = !on;
    });
    // Charts in a hidden panel render at 0 size — (re)render on first reveal of the trends tab.
    if (tab.getAttribute("aria-controls") === "trends-section" && !trendsRendered) renderTrends();
  }
  tabs.forEach((tab) => {
    tab.addEventListener("click", () => select(tab));
    tab.addEventListener("keydown", (e) => {
      const i = tabs.indexOf(tab);
      let j = -1;
      if (e.key === "ArrowRight") j = (i + 1) % tabs.length;
      else if (e.key === "ArrowLeft") j = (i - 1 + tabs.length) % tabs.length;
      if (j < 0) return;
      e.preventDefault();
      tabs[j].focus();
      select(tabs[j]);
    });
  });
}

// ── Init ──
async function init() {
  // theme.js owns the toggle (sets data-theme on <html>); rebuild the charts when it flips, since
  // Chart.js caches the CSS-variable colors at construction time. When the trends tab is hidden,
  // defer to its next reveal — a hidden canvas would size to 0.
  document.addEventListener("themechange", () => {
    if (!data) return;
    trendsRendered = false;
    if (!document.getElementById("trends-section").hidden) renderTrends();
  });

  data = await fetch("public/data/demo.json").then((r) => r.json());
  // Trends are aggregate {week,counts} (non-PII), so the real backfilled series can be shown when
  // present; the shortlist stays synthetic/local. Any miss keeps demo.json's synthetic trends.
  const realTrends = await loadRealTrends();
  if (realTrends) data.trends = realTrends;
  laneLabel = Object.fromEntries(data.lanes.map((l) => [l.key, l.label]));

  renderShortlist();
  document
    .getElementById("filter")
    .addEventListener("input", (e) => renderShortlist(e.target.value));

  initTabs();
}

document.addEventListener("DOMContentLoaded", init);
