// EyeRest dashboard shell — vanilla ES module, no build step.
// Renders the synthetic shortlist from public/data/demo.json; the keyword-trends chart shows the
// real aggregate series ({week,counts}, non-PII) fetched at RUNTIME from the deployment's own
// `data` branch (see DATA_BASE_URL), falling back to the synthetic trends on any miss. Issue #11
// skeleton; the live shortlist feed (pseudonymized) stays gated on #52.

// Trends load at runtime from the deployment's own `data` branch (mirrors qte77/analyze-stock-kpi) —
// the data is never bundled into ui/. Auto-derive the base from the GitHub Pages origin so every
// fork self-hosts its own data; `?base=` overrides (local dev / custom domain), else the qte77 default.
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

/** @type {{lanes:{key:string,label:string}[], shortlist:any[], trends:{week:string,counts:Record<string,number>}[], generated:string}|null} */
let data = null;
let laneLabel = {};
/** @type {any} Chart.js instances (rebuilt on theme flip to re-read tokens). */
let lineChart = null;
let barChart = null;
let trendsRendered = false; // charts in a hidden tab panel size to 0 → render on first reveal
let trendsRange = "13"; // default time-frame window: 3mo (13 ISO weeks); "all" or a trailing-week count
// Tailored CV/cover-letter markdown renderer; set once in init() from the vendored marked ESM build.
// Stays null if that import fails → renderShortlist falls back to an esc()'d <pre>.
let renderMarkdown = null;

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

// marked does NOT sanitize its output (the upstream `sanitize` option was removed), and we assign
// that output to innerHTML in the tailor pack — so run it through a tiny allowlist: keep only
// formatting tags, drop every attribute except an http(s) href on <a>. The demo cv/cover_letter are
// trusted synthetic strings, but this keeps the renderer safe-by-construction for the future
// #52-gated, model-generated offer packs (results/offers/<slug>/*.md).
const TAILOR_TAGS = new Set([
  "H1", "H2", "H3", "H4", "H5", "H6", "P", "UL", "OL", "LI",
  "STRONG", "EM", "B", "I", "CODE", "PRE", "BR", "A", "BLOCKQUOTE", "HR",
]);
function sanitizeHtml(html) {
  const tpl = document.createElement("template");
  tpl.innerHTML = html;
  for (const el of tpl.content.querySelectorAll("*")) {
    if (!TAILOR_TAGS.has(el.tagName)) {
      el.replaceWith(...el.childNodes); // unwrap anything off-list (scripts/img/tables) to plain text
      continue;
    }
    // getAttributeNames() is a static snapshot, so removing during iteration is safe (a live
    // el.attributes would skip entries as it shrinks).
    for (const name of el.getAttributeNames()) {
      const okHref =
        el.tagName === "A" && name === "href" && /^https?:\/\//i.test(el.getAttribute(name) || "");
      if (!okHref) el.removeAttribute(name); // strips on*=, style, javascript:/data: hrefs, …
    }
    if (el.tagName === "A") {
      el.setAttribute("target", "_blank");
      el.setAttribute("rel", "noopener");
    }
  }
  return tpl.innerHTML;
}

// ── Shortlist table ──
function scoreClass(score) {
  return score >= 4 ? "score-good" : score >= 3 ? "score-mid" : "score-bad";
}

// One tailor-pack pane (CV or cover letter): a head row (title + a Copy button that copies the RAW
// markdown), then rendered+sanitized markdown when the vendored renderer loaded, else an esc()'d
// <pre> fallback so a missing/broken vendor file still shows the raw text. The raw md rides in
// data-md via esc() (escapes & < > " → no breakout of the double-quoted attr; newlines preserved);
// copyTailor() reads btn.dataset.md, which the browser decodes back to the raw string.
function tailorDoc(title, md) {
  const body = renderMarkdown
    ? `<div class="tailor-md">${renderMarkdown(md)}</div>`
    : `<pre class="tailor-pre">${esc(md ?? "")}</pre>`;
  return `<section class="tailor-doc">
            <div class="tailor-doc-head">
              <h4>${title}</h4>
              <button type="button" class="tailor-copy" data-md="${esc(md ?? "")}" aria-label="Copy ${title} as Markdown" title="Copy raw Markdown">Copy</button>
            </div>
            ${body}
          </section>`;
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

  // Each offer is a clickable row (role=button) that toggles a sibling detail row holding the
  // tailored CV + cover letter. cv/cover_letter are the canonical tailor-pack keys (persist_offer.py
  // ARTIFACTS); here they are synthetic demo strings — real packs stay local (results/offers/, #52).
  body.innerHTML = rows
    .map(
      (it) => `<tr class="offer-row" role="button" tabindex="0" aria-expanded="false" title="Show tailored CV & cover letter">
        <td>${esc(it.company)}</td>
        <td>
          <div class="role-title"><a href="${esc(safeUrl(it.url))}" target="_blank" rel="noopener">${esc(it.title)}</a></div>
          <div class="rationale">${esc(it.rationale)}</div>
        </td>
        <td><span class="lane">${esc(laneLabel[it.best_lane] || it.best_lane)}</span></td>
        <td class="num"><span class="score ${scoreClass(it.score)}">${esc(it.score)}</span></td>
        <td><span class="verdict ${it.verdict === "shortlist" ? "is-shortlist" : ""}">${esc(it.verdict)}</span></td>
      </tr>
      <tr class="offer-detail" hidden>
        <td colspan="5">
          <div class="tailor-pack">
            ${tailorDoc("Tailored CV", it.cv)}
            ${tailorDoc("Cover letter", it.cover_letter)}
          </div>
        </td>
      </tr>`,
    )
    .join("");
}

// Collapse a single offer row (clear aria-expanded + hide its detail sibling).
function collapseOfferRow(row) {
  row.setAttribute("aria-expanded", "false");
  const detail = row.nextElementSibling;
  if (detail && detail.classList.contains("offer-detail")) detail.hidden = true;
}

// Expand/collapse a shortlist row to reveal its tailored CV + cover letter (the detail row is the
// main row's next sibling). Bound once via delegation in init() so it survives re-renders.
// Accordion: opening a row collapses any other open one, so only one detail shows at a time.
function toggleOfferRow(row) {
  const open = row.getAttribute("aria-expanded") === "true";
  if (open) {
    collapseOfferRow(row);
    return;
  }
  document
    .querySelectorAll('.offer-row[aria-expanded="true"]')
    .forEach(collapseOfferRow);
  row.setAttribute("aria-expanded", "true");
  const detail = row.nextElementSibling;
  if (detail && detail.classList.contains("offer-detail")) detail.hidden = false;
}

// Copy a tailor pane's RAW markdown (from data-md) to the clipboard, with brief "Copied" feedback.
// clipboard.writeText needs a secure context (https / localhost) — both the Pages deploy and the
// local preview qualify; a blocked/denied clipboard just no-ops.
function copyTailor(btn) {
  if (!navigator.clipboard) return;
  navigator.clipboard.writeText(btn.dataset.md ?? "").then(() => {
    btn.textContent = "Copied";
    btn.classList.add("is-copied");
    setTimeout(() => {
      btn.textContent = "Copy";
      btn.classList.remove("is-copied");
    }, 1200);
  }, () => {});
}

function onShortlistInteract(e) {
  // The Copy button lives in the detail row (not .offer-row), so it never toggles — handle it
  // first and return regardless of event type (a keydown Enter/Space fires the button's native click).
  const copyBtn = e.target.closest(".tailor-copy");
  if (copyBtn) {
    if (e.type === "click") copyTailor(copyBtn);
    return;
  }
  if (e.target.closest("a")) return; // let the role-title link open the offer
  const row = e.target.closest(".offer-row");
  if (!row) return;
  if (e.type === "keydown") {
    if (e.key !== "Enter" && e.key !== " ") return;
    e.preventDefault(); // Space would otherwise scroll
  }
  toggleOfferRow(row);
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
async function loadRealTrends() {
  const sameOrigin = "public/data/trends.ndjson";
  const dataBranch = `${DATA_BASE_URL}/results/trends.ndjson`;
  const order = new URLSearchParams(location.search).has("base")
    ? [dataBranch, sameOrigin]
    : [sameOrigin, dataBranch];
  for (const url of order) {
    const records = await fetchTrends(url);
    if (records) return records;
  }
  return null;
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

function renderTrends() {
  if (!data) return;
  // Sort once here (not in pivot) so the line/bar datasets, which map over this same array, stay
  // aligned with the labels. Real trends.ndjson is upsert-appended so it may not be in order;
  // ISO-week strings ("YYYY-Www", zero-padded) sort chronologically as plain strings.
  const sorted = [...data.trends].sort((a, b) => a.week.localeCompare(b.week));
  const records = windowRecords(sorted, trendsRange);
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

  // Load the vendored markdown renderer (marked — no CDN) so the tailor packs read as formatted
  // docs. A dynamic import keeps a missing/broken vendor file from breaking the whole dashboard:
  // renderMarkdown stays null and tailorDoc() falls back to an esc()'d <pre>.
  try {
    const { marked } = await import("../public/vendor/marked.esm.min.js");
    renderMarkdown = (md) => sanitizeHtml(marked.parse(String(md ?? "")));
  } catch {
    renderMarkdown = null;
  }

  renderShortlist();
  document
    .getElementById("filter")
    .addEventListener("input", (e) => renderShortlist(e.target.value));

  // Delegated once on the tbody (survives renderShortlist re-renders): click / Enter / Space
  // toggles a row's tailored CV + cover-letter detail.
  const shortlistBody = document.getElementById("shortlist-body");
  shortlistBody.addEventListener("click", onShortlistInteract);
  shortlistBody.addEventListener("keydown", onShortlistInteract);

  // Time-frame picker: re-window the trends charts. It lives inside the trends panel, so it's only
  // reachable once that tab is open (canvases sized) — a direct renderTrends() is safe.
  document.getElementById("trends-range").addEventListener("change", (e) => {
    trendsRange = e.target.value;
    if (data) renderTrends();
  });

  initTabs();
}

document.addEventListener("DOMContentLoaded", init);
