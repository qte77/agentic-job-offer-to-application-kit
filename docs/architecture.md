# Architecture — agentic-job-offer-to-application-kit

Mirrors the `agentic-market-research-to-gtm` shape (config -> pipeline ->
results), with three deliberate corrections so it reflects how the approach
actually works.

## Three mechanics that define it

1. **Orchestration = Claude Code Workflow tool, not make/node.** The Stage-1
   workflow runs via `Workflow({ scriptPath: 'docs/workflows/evidence-library.js',
   args })`, resumable and cached by run id (it can be edited + resumed to
   re-assemble without re-mining). Its subagents are inline `agent()` calls, so
   there are **no `.claude/agents/*.md` definitions and no team mode**. The
   reference's `make orchestrated` / AGENTS-prose model is what this replaces. The
   `.js` is the **Claude Code reference implementation**; the phased pipeline is
   described agent-agnostically here so other coding agents can implement it.
2. **The evidence library is structured data, not a markdown blob.** The workflow
   returns the `LIB` object (skill clusters, master CV bullets, per-lane angles).
   That JSON is the retrieval index the tailoring step queries; markdown is only a
   human render. So `results/` holds `evidence-library.json` (source of truth)
   AND a rendered `.md`.
3. **A web-access layer wraps native tools + polyfetch (fallback / replacement).**
   `lib/ingest.py` chains: native **WebSearch** (discover) -> native **WebFetch**
   (fetch, tried first) -> **polyfetch** (browser-impersonation -> headless tier)
   on 403 / JS-shell / header needs; an RSS/Atom feed or backend API is preferred
   over rendering; paste is the reliable fallback. polyfetch can also fully
   **replace** WebFetch where reliability matters. Never reimplement fetching (DRY).

## Repo structure

```text
agentic-job-offer-to-application-kit/
├── README.md / AGENTS.md
├── docs/
│   ├── plans/two-stage-tailoring.md
│   ├── architecture.md
│   ├── research.md
│   └── workflows/
│       ├── evidence-library.js   # Stage 1 (functional): tone+inv -> mine -> adversarial-verify -> assemble; Claude Code reference impl
│       └── tailor-offer.js       # Stage 2 (designed): ingest -> parse -> [deep-research company] -> match -> tailor -> ats-check -> gap
├── config/
│   ├── portfolio.md              # workspace root + repos that feed the evidence base
│   ├── work-history.md           # optional employment history
│   ├── lanes.md                  # target lanes (configurable)
│   ├── locale.md                 # target locale(s)
│   └── offers/                   # offer URLs or pasted JD text
├── lib/ingest.py                 # web-access layer: WebSearch/WebFetch + polyfetch fallback (feed/API-first, paste fallback)
├── templates/                    # base(ats-safe | polished/typst) x shape(chrono|projects|hybrid) x locale x lane (composed)
├── results/
│   ├── evidence-library.json     # structured index = matching source of truth
│   ├── evidence-library.md       # human render
│   └── offers/<slug>/{match.md, cv.{md,docx,pdf}, cover-letter.*, gap-report.md, ats-check.md}
└── pyproject.toml                # deps: an HTTP fetcher (git), pandoc/typst optional
```

## Components

- **docs/workflows/** — the dynamic workflows (Claude Code reference implementation).
- **config/** — portfolio + workspace root, optional work history, lanes, locale, offers.
- **lib/ingest.py** — web-access layer (WebSearch / WebFetch -> polyfetch fallback; feed -> API -> paste).
- **templates/** — composable `shape x layout x locale x lane`.
- **results/** — structured library (json) + render (md) + per-offer outputs.

## Built vs designed

- **Built / functional:** `docs/workflows/evidence-library.js`.
- **Designed, not built:** `tailor-offer.js`, `lib/ingest.py`, templates,
  ats-check, config scaffolding.
- **Dropped (YAGNI):** team mode, dual modes, validation ceremony, slide decks.
