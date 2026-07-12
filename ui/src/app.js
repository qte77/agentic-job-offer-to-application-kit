// EyeRest dashboard shell — vanilla ES module, no build step. Orchestrator only (#249 slice E):
// owns the loaded data + UI state and wires the listeners; rendering lives in the sibling modules
// (dom-utils.js · shortlist.js · trends.js), composed via same-origin static imports (CSP `'self'`).
// Renders the synthetic shortlist from public/data/demo.json, OVERRIDDEN by a real LOCAL shortlist
// (public/data/shortlist.json, bundled same-origin by `make preview`) when present — never published
// (PII). The keyword-trends chart shows the real aggregate series ({week,counts}, non-PII) fetched at
// RUNTIME from the deployment's own `data` branch, falling back to synthetic on a miss. Issue #11
// skeleton; the PUBLISHED shortlist feed (pseudonymized) stays gated on #52.

import {
  loadMarkdownRenderer,
  loadRealShortlist,
  onShortlistInteract,
  renderShortlist,
} from "./shortlist.js";
import { invalidateTrends, loadRealTrends, renderTrends, trendsPainted } from "./trends.js";
import { loadRealCompanies, renderCompanies } from "./companies.js";
import {
  hiringPainted,
  invalidateHiring,
  loadLocalHiring,
  loadRealHiring,
  localHiringPainted,
  renderHiring,
  renderLocalHiring,
} from "./hiring.js";

/** @type {{lanes:{key:string,label:string}[], shortlist:any[], trends:{week:string,counts:Record<string,number>}[], generated:string}|null} */
let data = null;
let laneLabel = {};
let trendsRange = "13"; // default time-frame window: 3mo (13 ISO weeks); "all" or a trailing-week count
let trendsGran = "week"; // default trend granularity: week | day | month (#187/#188)
let hiringData = null; // publishable geo-by-field {records, gran} — Market-trends tab (plan 006)
let localHiringData = null; // local per-company {records, gran} — Companies tab, preview-only

// ── Tabs (WAI-ARIA tabs pattern: roving tabindex + arrow keys) ──
function initTabs() {
  // Skip hidden tabs (the local-only Companies tab stays hidden on the published site) so arrow-key
  // roving and selection never land on an invisible tab.
  const tabs = Array.from(document.querySelectorAll('[role="tab"]')).filter((t) => !t.hidden);
  function select(tab) {
    tabs.forEach((t) => {
      const on = t === tab;
      t.setAttribute("aria-selected", String(on));
      t.tabIndex = on ? 0 : -1;
      const panel = document.getElementById(t.getAttribute("aria-controls"));
      if (panel) panel.hidden = !on;
    });
    // Charts in a hidden panel render at 0 size — (re)render on first reveal of each tab.
    const panelId = tab.getAttribute("aria-controls");
    if (panelId === "trends-section") {
      if (!trendsPainted()) renderTrends(data?.trends, trendsRange);
      if (hiringData && !hiringPainted()) renderHiring(hiringData, trendsRange);
    }
    if (panelId === "companies-section" && localHiringData && !localHiringPainted()) {
      renderLocalHiring(localHiringData, trendsRange);
    }
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
    invalidateTrends();
    invalidateHiring();
    if (!document.getElementById("trends-section").hidden) {
      renderTrends(data.trends, trendsRange);
      if (hiringData) renderHiring(hiringData, trendsRange);
    }
    if (localHiringData && !document.getElementById("companies-section").hidden) {
      renderLocalHiring(localHiringData, trendsRange);
    }
  });

  data = await fetch("public/data/demo.json").then((r) => r.json());
  // Trends are aggregate {week,counts} (non-PII), so the real backfilled series can be shown when
  // present; the shortlist stays synthetic/local. Any miss keeps demo.json's synthetic trends.
  const realTrends = await loadRealTrends(trendsGran);
  if (realTrends) data.trends = realTrends;
  // Publishable geo-by-field hiring series (aggregate, no company names) — same load path as the
  // keyword trends; reveal its chart block when reachable, render it on the trends-tab reveal.
  hiringData = await loadRealHiring(trendsGran);
  if (hiringData) document.getElementById("hiring-block").hidden = false;
  // A real shortlist (results/<lane>/shortlist.json, aggregated into the throwaway copy by
  // `make preview`) overrides the synthetic demo set LOCALLY; never present on gh-pages (PII).
  const realShortlist = await loadRealShortlist();
  if (realShortlist) data.shortlist = realShortlist;
  laneLabel = Object.fromEntries(data.lanes.map((l) => [l.key, l.label]));

  await loadMarkdownRenderer();

  renderShortlist(data.shortlist, laneLabel);
  document
    .getElementById("filter")
    .addEventListener("input", (e) => renderShortlist(data.shortlist, laneLabel, e.target.value));

  // Delegated once on the tbody (survives renderShortlist re-renders): click / Enter / Space
  // toggles a row's tailored CV + cover-letter detail.
  const shortlistBody = document.getElementById("shortlist-body");
  shortlistBody.addEventListener("click", onShortlistInteract);
  shortlistBody.addEventListener("keydown", onShortlistInteract);

  // Time-frame picker: re-window the trends charts. It lives inside the trends panel, so it's only
  // reachable once that tab is open (canvases sized) — a direct renderTrends() is safe.
  document.getElementById("trends-range").addEventListener("change", (e) => {
    trendsRange = e.target.value;
    if (data) renderTrends(data.trends, trendsRange);
    // The picker lives in the (visible) trends panel, so the hiring chart can re-window immediately.
    if (hiringData) renderHiring(hiringData, trendsRange);
  });

  // Granularity picker (#187/#188): swap the trend series (week|day|month) — each is a separate
  // published NDJSON. On a miss (a granularity whose series isn't reachable) keep the current view
  // and revert the control, so the charts never render against a mismatched label key.
  document.getElementById("trends-gran").addEventListener("change", async (e) => {
    const next = e.target.value;
    const records = await loadRealTrends(next);
    if (records) {
      trendsGran = next;
      data.trends = records;
      renderTrends(data.trends, trendsRange);
    } else {
      e.target.value = trendsGran;
    }
    // Swap the hiring series to the effective granularity too (each accrues independently, so a miss
    // just leaves the current hiring chart untouched).
    if (hiringData) {
      const h = await loadRealHiring(e.target.value);
      if (h) {
        hiringData = h;
        renderHiring(hiringData, trendsRange);
      }
    }
  });

  // A real LOCAL company-hiring snapshot (results/corpus.json aggregated by `make preview`) reveals
  // the Companies tab; absent on gh-pages (business data, never published) so the tab stays hidden.
  const realCompanies = await loadRealCompanies();
  if (realCompanies) {
    document.getElementById("tab-companies").hidden = false;
    renderCompanies(realCompanies);
    // Local per-company hiring detail (business data, make-preview bundle only) — reveal its block;
    // it renders on the Companies-tab reveal (a chart in a hidden panel would size to 0).
    localHiringData = await loadLocalHiring();
    if (localHiringData) document.getElementById("hiring-companies-block").hidden = false;
  }

  initTabs();
}

document.addEventListener("DOMContentLoaded", init);
