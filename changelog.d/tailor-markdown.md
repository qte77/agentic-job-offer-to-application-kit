### Changed

- ui: the tailored **CV** and **cover letter** in an expanded shortlist row now render as
  formatted Markdown (headings, bold, lists, paragraphs) instead of raw `<pre>` text, via a
  vendored, version-pinned [marked](https://github.com/markedjs/marked) ESM build (no CDN).
  marked does not sanitize, so its output passes through a tiny tag/attribute allowlist before
  hitting the DOM — keeping the renderer safe for the future #52-gated, model-generated packs.
  Falls back to the esc'd `<pre>` if the vendor import fails. Closes #138.
