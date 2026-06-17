// EyeRest dashboard shell — vanilla ES module, no build step.
// Renders synthetic demo data (shortlist + keyword trends). Becomes the
// issue #11 skeleton; the live version swaps data/demo.json for pseudonymized
// data fetched from the `data` branch at runtime.

const THEMES = ["system", "light", "dark"];

/** @type {{lanes:{key:string,label:string}[], shortlist:any[], trends:{weeks:string[], series:{keyword:string,counts:number[]}[]}, generated:string}|null} */
let data = null;
let laneLabel = {};
/** @type {any} Chart.js instance (rebuilt on theme flip to re-read tokens). */
let trendsChart = null;

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

// ── Theme: system / light / dark, persisted to localStorage + URL ──
function resolveTheme() {
  const fromUrl = new URL(location.href).searchParams.get("theme");
  const t = fromUrl || localStorage.getItem("theme") || "system";
  return THEMES.includes(t) ? t : "system";
}

function applyTheme(theme) {
  document.body.classList.remove("theme-system", "theme-light", "theme-dark");
  document.body.classList.add(`theme-${theme}`);
  for (const b of document.querySelectorAll("#theme-toggle button")) {
    b.setAttribute("aria-pressed", String(b.dataset.theme === theme));
  }
}

function setTheme(theme) {
  applyTheme(theme);
  localStorage.setItem("theme", theme);
  const url = new URL(location.href);
  url.searchParams.set("theme", theme);
  history.replaceState(null, "", url);
  if (data) renderTrends(data.trends); // tokens changed → rebuild chart colors
}

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

// ── Keyword trends (Chart.js) ──
function renderTrends(trends) {
  const canvas = document.getElementById("trends-chart");
  if (!canvas || typeof Chart === "undefined") return;

  // Categorical zero-blue palette from the data arc + accent.
  const palette = [
    cssVar("--data-positive"),
    cssVar("--data-alt"),
    cssVar("--data-caution"),
    cssVar("--accent"),
    cssVar("--data-negative"),
  ];
  const grid = cssVar("--border");
  const tick = cssVar("--muted");
  const label = cssVar("--text");

  if (trendsChart) trendsChart.destroy();
  trendsChart = new Chart(canvas, {
    type: "line",
    data: {
      labels: trends.weeks,
      datasets: trends.series.map((s, i) => ({
        label: s.keyword,
        data: s.counts,
        borderColor: palette[i % palette.length],
        backgroundColor: palette[i % palette.length],
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

// ── Init ──
async function init() {
  applyTheme(resolveTheme());
  for (const b of document.querySelectorAll("#theme-toggle button")) {
    b.addEventListener("click", () => setTheme(b.dataset.theme));
  }

  data = await fetch("data/demo.json").then((r) => r.json());
  laneLabel = Object.fromEntries(data.lanes.map((l) => [l.key, l.label]));
  document.getElementById("generated").textContent = data.generated;

  renderShortlist();
  document
    .getElementById("filter")
    .addEventListener("input", (e) => renderShortlist(e.target.value));

  renderTrends(data.trends);
}

document.addEventListener("DOMContentLoaded", init);
