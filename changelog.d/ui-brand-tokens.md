### Changed

- `ui/`: converged theming onto the shared qte77 brand-kit naming (#112) — renamed CSS custom
  properties (`--panel`→`--surface`, `--muted`→`--text-muted`, `--accent`→`--primary`) across
  `style.css` + `app.js`, the theme storage key (`theme`→`qte77-theme`), and the auto mode label
  (`Auto`→`System`); added `clip-path: inset(50%)` to `.sr-only`. Zero behavior change (renames).
  JetBrains Mono (issue item 5) deferred — no mono consumer yet.
