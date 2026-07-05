// Shortlist table: render + filter + expandable tailor packs (#249 slice E).
// State this module OWNS: the markdown renderer and the raw tailor packs; the shortlist items and
// lane labels are passed in by the orchestrator (app.js) — never imported as mutable bindings.

import { esc, safeUrl, sanitizeHtml, scoreClass } from "./dom-utils.js";

// Tailored CV/cover-letter markdown renderer; set once via loadMarkdownRenderer() from the vendored
// marked ESM build. Stays null if that import fails → renderShortlist falls back to an esc()'d <pre>.
let renderMarkdown = null;
// Raw tailor markdown, index-aligned with the rendered shortlist rows ({cv, cover_letter}). Kept in
// JS rather than inlined per Copy button so multi-KB packs don't bloat the DOM (#52); copyTailor()
// indexes into it by the button's data-offer.
let tailorPacks = [];

// Load the vendored markdown renderer (marked — no CDN) so the tailor packs read as formatted
// docs. A dynamic import keeps a missing/broken vendor file from breaking the whole dashboard:
// renderMarkdown stays null and tailorDoc() falls back to an esc()'d <pre>.
export async function loadMarkdownRenderer() {
  try {
    const { marked } = await import("../public/vendor/marked.esm.min.js");
    // SECURITY BOUNDARY (#52): sanitizeHtml() is the one sanctioned markdown→HTML path. Any new
    // rendered field must route through renderMarkdown — never assign marked.parse() to innerHTML raw.
    renderMarkdown = (md) => sanitizeHtml(marked.parse(String(md ?? "")));
  } catch {
    renderMarkdown = null;
  }
}

// Load a real, LOCAL shortlist if `make preview` bundled one same-origin. The shortlist carries real
// company/title/url (PII), so — UNLIKE the aggregate trends — it is NEVER fetched cross-origin / from
// the `data` branch, and the gh-pages deploy bundles none: published stays synthetic, local shows real,
// by construction. Absent / empty → the caller keeps demo.json's synthetic shortlist.
export async function loadRealShortlist() {
  try {
    const res = await fetch("public/data/shortlist.json");
    if (!res.ok) return null;
    const arr = await res.json();
    return Array.isArray(arr) && arr.length ? arr : null;
  } catch {
    return null;
  }
}

// One tailor-pack pane (CV or cover letter): a head row (title + a Copy button), then
// rendered+sanitized markdown when the vendored renderer loaded, else an esc()'d <pre> fallback so a
// missing/broken vendor file still shows the raw text. The Copy button no longer inlines the raw
// markdown in a data-md attribute (real packs run to tens of KB × every row → DOM bloat); it carries
// the (offer index, field) instead, and copyTailor() looks the raw string up in `tailorPacks` (#52).
function tailorDoc(title, md, idx, field) {
  const body = renderMarkdown
    ? `<div class="tailor-md">${renderMarkdown(md)}</div>`
    : `<pre class="tailor-pre">${esc(md ?? "")}</pre>`;
  return `<section class="tailor-doc">
            <div class="tailor-doc-head">
              <h4>${title}</h4>
              <button type="button" class="tailor-copy" data-offer="${idx}" data-field="${field}" aria-label="Copy ${title} as Markdown" title="Copy raw Markdown">Copy</button>
            </div>
            ${body}
          </section>`;
}

export function renderShortlist(items, laneLabel, filter = "") {
  const body = document.getElementById("shortlist-body");
  const f = filter.trim().toLowerCase();
  const rows = items
    .filter((it) => {
      if (!f) return true;
      const hay = `${it.company} ${it.title} ${laneLabel[it.best_lane] || it.best_lane}`;
      return hay.toLowerCase().includes(f);
    })
    .sort((a, b) => b.score - a.score);

  // Lazy copy source, rebuilt each render so the indices stay aligned with the rows below.
  tailorPacks = rows.map((it) => ({ cv: it.cv, cover_letter: it.cover_letter }));

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
      (it, idx) => `<tr class="offer-row" role="button" tabindex="0" aria-expanded="false" title="Show tailored CV & cover letter">
        <td>${esc(it.company)}</td>
        <td>
          <div class="role-title"><a href="${esc(safeUrl(it.url))}" target="_blank" rel="noopener noreferrer">${esc(it.title)}</a></div>
          <div class="rationale">${esc(it.rationale)}</div>
        </td>
        <td><span class="lane">${esc(laneLabel[it.best_lane] || it.best_lane)}</span></td>
        <td class="num"><span class="score ${scoreClass(it.score)}">${esc(it.score)}</span></td>
        <td><span class="verdict ${it.verdict === "shortlist" ? "is-shortlist" : ""}">${esc(it.verdict)}</span></td>
      </tr>
      <tr class="offer-detail" hidden>
        <td colspan="5">
          <div class="tailor-pack">
            ${tailorDoc("Tailored CV", it.cv, idx, "cv")}
            ${tailorDoc("Cover letter", it.cover_letter, idx, "cover_letter")}
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

// Copy a tailor pane's RAW markdown to the clipboard, with brief "Copied" feedback. The source is
// looked up in tailorPacks by the button's data-offer/data-field (not inlined in the DOM, #52).
// clipboard.writeText needs a secure context (https / localhost) — both the Pages deploy and the
// local preview qualify; a blocked/denied clipboard just no-ops.
function copyTailor(btn) {
  if (!navigator.clipboard) return;
  const pack = tailorPacks[Number(btn.dataset.offer)];
  const md = (pack && pack[btn.dataset.field]) ?? "";
  navigator.clipboard.writeText(md).then(() => {
    btn.textContent = "Copied";
    btn.classList.add("is-copied");
    setTimeout(() => {
      btn.textContent = "Copy";
      btn.classList.remove("is-copied");
    }, 1200);
  }, () => {});
}

export function onShortlistInteract(e) {
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
