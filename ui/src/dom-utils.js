// Shared DOM/text utilities for the dashboard modules (#249 slice E) — vanilla ES module, no build.

export const cssVar = (name) =>
  getComputedStyle(document.body).getPropertyValue(name).trim();

export const esc = (s) =>
  String(s).replace(
    /[&<>"]/g,
    (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c],
  );

// Only allow http(s) hrefs — blocks javascript:/data: even if the (future
// data-branch) feed is tampered with. esc() then handles quote-breakout.
export const safeUrl = (u) => (/^https?:\/\//i.test(String(u)) ? String(u) : "#");

// marked does NOT sanitize its output (the upstream `sanitize` option was removed), and we assign
// that output to innerHTML in the tailor pack — so run it through a tiny allowlist: keep only
// formatting tags, drop every attribute except an http(s) href on <a>. The demo cv/cover_letter are
// trusted synthetic strings, but this keeps the renderer safe-by-construction for the future
// #52-gated, model-generated offer packs (results/offers/<slug>/*.md).
const TAILOR_TAGS = new Set([
  "H1", "H2", "H3", "H4", "H5", "H6", "P", "UL", "OL", "LI",
  "STRONG", "EM", "B", "I", "CODE", "PRE", "BR", "A", "BLOCKQUOTE", "HR",
]);
export function sanitizeHtml(html) {
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
      // noreferrer (not just noopener): don't leak the dashboard URL via Referer on
      // model-supplied links in the future #52-gated offer packs.
      el.setAttribute("rel", "noopener noreferrer");
    }
  }
  return tpl.innerHTML;
}

export function scoreClass(score) {
  return score >= 4 ? "score-good" : score >= 3 ? "score-mid" : "score-bad";
}
