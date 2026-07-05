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

/** @type {{lanes:{key:string,label:string}[], shortlist:any[], trends:{week:string,counts:Record<string,number>}[], generated:string}|null} */
let data = null;
let laneLabel = {};
let trendsRange = "13"; // default time-frame window: 3mo (13 ISO weeks); "all" or a trailing-week count

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
    if (tab.getAttribute("aria-controls") === "trends-section" && !trendsPainted()) {
      renderTrends(data?.trends, trendsRange);
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
    if (!document.getElementById("trends-section").hidden) renderTrends(data.trends, trendsRange);
  });

  data = await fetch("public/data/demo.json").then((r) => r.json());
  // Trends are aggregate {week,counts} (non-PII), so the real backfilled series can be shown when
  // present; the shortlist stays synthetic/local. Any miss keeps demo.json's synthetic trends.
  const realTrends = await loadRealTrends();
  if (realTrends) data.trends = realTrends;
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
  });

  initTabs();
}

document.addEventListener("DOMContentLoaded", init);
