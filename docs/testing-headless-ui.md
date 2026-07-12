# Headless UI testing — dos & don'ts

Reusable patterns for headless-browser UI checks with Playwright / patchright — the approach behind
`scripts/ui_check.py` (fast smoke) and `scripts/ui_e2e.py` (full e2e). Framework-agnostic: this repo's
`ui/` is no-build vanilla ES modules, but the browser-driving gotchas apply to any static site or SPA,
so other projects can lift these directly.

## Setup

Borrow a sibling project's patchright + Chromium venv instead of installing a browser locally:

```bash
uv run --directory ../polyfetch-scrape python scripts/ui_e2e.py
```

Serve the build on an **ephemeral** localhost port (`127.0.0.1:0`) from a daemon thread — never
hard-code a port.

## Two tiers

- **Smoke** (`ui_check.py`) — one viewport, default/bundled data; asserts render + no console errors.
  The fast pre-commit gate.
- **E2E** (`ui_e2e.py`) — the local build (**hard gate**, seeded with synthetic data) plus the deployed
  remote (**best-effort**); iterates viewports + a device descriptor; drives every control; verifies
  themes.

## Do

- **Capture errors via the console.** Subscribe to `page.on("console")` (error/warning) and
  `page.on("pageerror")`. Under a strict CSP an in-page `securitypolicyviolation` listener is itself
  blocked — CSP violations surface through the console / CDP instead, so listen there.
- **Guard optional selectors.** `query_selector` returns null and `eval_on_selector_all` returns `[]`
  — use them for anything that may be absent (e.g. a control not yet on the deployed remote).
- **Render charts on tab reveal.** A canvas/chart inside a `hidden` panel lays out at size 0. Assert
  its width only once the panel is visible, and (re)render on first reveal — not at init.
- **Test real viewports.** Iterate desktop / tablet / mobile via `set_viewport_size`, and assert no
  horizontal body overflow: `scrollWidth <= innerWidth + slack`.
- **Emulate a real device.** `browser.new_context(**p.devices["iPhone 13"])` sets the user-agent, DPR,
  touch and `isMobile` — a viewport size alone does none of that.
- **Verify themes by effect.** Cycle the theme control and assert the computed background actually
  changes (light vs dark differ) — not merely that a `data-theme` attribute flipped.
- **Allowlist by-design 404s.** Data a given build does not bundle will 404 as expected; allowlist
  those suffixes (both same-origin and data-branch paths) so the check does not false-fail.

## Don't

- **Don't `eval_on_selector` an element that might not exist** — it **throws** on no match (unlike
  `eval_on_selector_all`, which returns `[]`). A control absent on an older or remote build crashes
  the whole run.
- **Don't fail the run on remote-only problems.** The deployed site is best-effort: a blocked network
  or a not-yet-deployed change must not red the gate. Keep the local build the hard gate.
- **Don't assume a hidden element has size.** Zero-sized canvases and un-laid-out nodes give false
  failures — drive the UI to reveal them first.
- **Don't lean on fixed sleeps.** Prefer explicit waits / re-checks over arbitrary timeouts where the
  harness allows; sleeps make the suite flaky and slow.

## Reference

`scripts/ui_check.py` (smoke) and `scripts/ui_e2e.py` (e2e) are the worked implementations. Both run
via `make ui-check` / `make ui-e2e` (which borrow `POLYFETCH_DIR`'s patchright venv).
