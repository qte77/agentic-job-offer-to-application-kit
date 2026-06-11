# Plan — agentic-job-offer-to-application-kit

Align a portfolio to job offers and generate tailored applications. Concept; not built.

## Goal

Turn a candidate's project portfolio + a job offer into a tailored, ATS-safe,
honest application (CV + cover letter + gap report) — repeatably and cheaply — by
building the evidence **once** and tailoring **many** times.

## Two stages

### Stage 1 — Evidence library (build once)

A dynamic workflow mines the portfolio into a verified brag document:
`tone + inventory -> deep-mine per project -> adversarially verify each bullet ->
assemble`. Output is the structured `LIB` object (skill clusters, master CV
bullets, per-project bullets, a positioning paragraph per target lane, gap
narrative). The adversarial pass (keep / downgrade / drop) keeps it defensible —
no overclaiming. Content is lane-agnostic, weighted to the account's real center
of gravity. See `docs/workflows/evidence-library.js` (functional, config-driven).

### Stage 2 — Per-offer tailoring (repeat, cheap)

Per offer: `ingest (feed / API / paste) -> parse JD into requirements ->
[optional deep-research on the company] -> match requirements to the library ->
tailor CV + cover letter in the company's vocabulary -> ats-check -> honest gap
report`. Retrieval-augmented job-applying: library = index, JD = query, tailored
docs = generation.

## Target lanes

Lanes are configurable. Example default set: CxO (fractional CTO / Chief AI
Officer / advisor), founding engineer, software engineer (senior IC), cloud /
DevOps / platform, software/systems architect. The library emits a per-lane
positioning paragraph for each — each honest about what is missing.

## Templates (composed, not a matrix)

Separate **content** (evidence library + optional work history) from **layout**.
Render = `shape x layout x locale x lane`, composed at render time (DRY — no
template per combination):

- **shape:** chronological | projects-first | hybrid
- **layout tier:** ATS-safe (single column, .docx / clean PDF) | polished
  (Typst / Deedy-style, direct-send only — NOT for ATS portals)
- **locale:** configurable (e.g. CH/DACH with photo + personal data, vs US / UK)
- **lane:** per-lane emphasis delta

## ATS — legitimate optimization, no tricks

No hidden/white text, keyword stuffing, or fabricated keywords (dishonest,
detectable, self-defeating). Instead: parse-safe formatting; honest keyword
alignment (mirror the JD's terms only where the evidence is real); an `ats-check`
step that parse-tests the doc and reports which JD must-haves are covered vs
genuinely missing (the gap feeds the cover letter, not a hidden-text patch).
Format: produce both a clean PDF and a .docx from one markdown source; default
PDF; obey the portal's stated requirement.

## Ingestion (web-access layer)

Job descriptions and company intel come from the web; job boards are typically JS
SPAs where a naive fetch returns 403 or an empty shell. The layer:

1. **Discover** with native WebSearch.
2. **Fetch:** prefer an RSS/Atom feed or a backend JSON API (discoverable in the
   page's JS bundle) over rendering. For page fetches, try native **WebFetch**
   first, then **fall back to polyfetch** (browser-impersonation -> headless tier)
   when WebFetch returns 403, a JS shell, or can't set headers — polyfetch can
   also be the **default replacement** for reliability.
3. **Paste** JD text as the always-available fallback.

The fetcher is a dependency, not vendored.

## Out of scope (YAGNI)

team mode, dual concise/detailed x conservative/ambitious modes, N-loop validation
ceremony, slide decks. Reuse existing tools and skills; don't rebuild.

## Open decisions

- Default locale (e.g. CH/DACH, US, UK) and which to ship first.
- v0 scope: paste-only offers, or feed/API ingestion + deep-research company
  intel from day one.
- Native-first with polyfetch fallback, or polyfetch as the default fetcher.
- Name and visibility (public adds portfolio signal — the tool is itself evidence
  of agentic-workflow orchestration + tooling).
