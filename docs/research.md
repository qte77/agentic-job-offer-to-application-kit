# Research — agentic-job-offer-to-application-kit

Research dimensions the design relies on. A run produces the candidate-specific
instances (positioning, matched offers) in `results/`; this doc stays generic.

## Portfolio positioning

Stage 1 extracts the account's *through-line* — its real center of gravity — from
the project repos (and an optional profile README), then frames all evidence in
that voice rather than as a scattered skills list. Output: a one-line headline, a
positioning summary, skill clusters, and a positioning paragraph per target lane,
each honest about gaps. An adversarial verification pass (keep / downgrade / drop)
keeps every bullet defensible. For breadth-heavy portfolios, the framing reads
breadth as architectural range (one pattern applied across domains), not "jack of
all trades".

## Target lanes

Lanes are configurable. Example set: CxO (fractional CTO / advisor), founding
engineer, software engineer (senior IC), cloud / DevOps / platform, software /
systems architect — each with an honest gap note.

## Fetching (web-access layer)

- **Native WebFetch** takes only url + prompt — no custom headers — so it cannot
  pass header/UA-based blocks; a UA swap alone fails against TLS/JA3 fingerprinting.
  On JS SPAs it returns only an HTML shell. **WebSearch** returns links, not content.
- So the layer uses native tools first (WebSearch to discover, WebFetch to fetch)
  and **falls back to — or is replaced by — polyfetch**: tier-1 (httpx) already
  beats some 403s; tier-2 (curl_cffi) impersonates a real browser TLS handshake;
  tier-3 (headless) renders JS.
- Prefer a **feed/API over rendering**: job boards are typically SPAs, but often
  publish an RSS/Atom feed or call a backend JSON API discoverable in the page's
  JS bundle — far lighter and more ToS-aligned than a headless browser. **Paste**
  is the always-available fallback.

## Market / boards

Source boards by target region and industry (general dev boards, research / RSE
boards, startup boards, domain-specific boards). Most are JS SPAs — apply the
fetching strategy above (feed/API first, paste fallback).

## ATS

Modern ATS parse both PDF and .docx **if the doc is clean** (single column,
standard headings, no tables / text-boxes / graphics) — layout matters more than
the extension. Default to a clean text-based PDF; keep .docx for older / enterprise
ATS and editable requests; obey the portal. Dense two-column templates (e.g.
Deedy) are for human eyes / direct sends, not ATS portals. No hidden-text /
keyword-stuffing tricks (dishonest, detectable, self-defeating) — use parse-safe
formatting + honest keyword alignment instead.

## Reference pattern

`agentic-market-research-to-gtm`: `config(sources, targets) -> multi-phase agentic
pipeline -> results`, with shared subagent guidelines and dual-mode / validation
ceremony. This concept reuses the skeleton and modernizes the engine (the Workflow
tool) while dropping the ceremony (KISS / YAGNI).

## Common gaps to address (narrative, once)

Solo / open-source portfolios often lack verifiable employment history, team-scale
work, or production-at-scale ops. The gap narrative addresses such gaps honestly
once and reuses them across applications — not patched per offer.
