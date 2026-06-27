"""Headless-browser smoke test for the dashboard (ui/) — CSP, render, console (#172).

`make check` is Python-only and CI has no browser, so this is the local gate for `ui/` changes:
it serves `ui/` on a throwaway localhost port, loads it in headless Chromium, and fails on any
console error, page error, or render failure (empty shortlist / unsized charts / no fonts). The page
is loaded with `?base=` so the cross-origin `data`-branch trends fetch exercises `connect-src`.

Run it through the sibling polyfetch-scrape venv (which ships patchright + Chromium) so no local
browser install is needed::

    make ui-check                  # uv run --directory $POLYFETCH_DIR python scripts/ui_check.py

Exits non-zero on the first problem. Capture violations via the console (the browser logs CSP
violations there via CDP regardless of the policy) — an in-page `securitypolicyviolation` listener
would itself be blocked under a strict CSP.
"""

from __future__ import annotations

import functools
import http.server
import socketserver
import sys
import threading
from pathlib import Path

from patchright.sync_api import sync_playwright

UI_DIR = Path(__file__).resolve().parent.parent / "ui"
# ?base= forces the cross-origin data-branch trends fetch to be tried first, so a too-strict
# connect-src would fire a violation regardless of whether the network is reachable.
BASE = "https://raw.githubusercontent.com/qte77/agentic-job-offer-to-application-kit/data"


def serve(directory: Path) -> socketserver.TCPServer:
    """Start a daemon HTTP server for `directory` on an ephemeral localhost port."""
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(directory))

    class Server(socketserver.ThreadingTCPServer):
        allow_reuse_address = True
        daemon_threads = True

    httpd = Server(("127.0.0.1", 0), handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd


def check(url: str) -> list[str]:
    """Load `url` in headless Chromium; return a list of failure strings (empty = pass)."""
    console: list[str] = []
    page_errors: list[str] = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
        page = browser.new_page()
        page.on(
            "console",
            lambda m: console.append(m.text) if m.type in ("error", "warning") else None,
        )
        page.on("pageerror", lambda e: page_errors.append(str(e)))
        page.goto(url, wait_until="domcontentloaded", timeout=15000)
        page.wait_for_timeout(2500)  # let async init() + the dynamic marked import run

        rows = page.eval_on_selector_all("tr.offer-row", "els => els.length")
        page.click("#tab-trends")  # charts defer while the panel is hidden
        page.wait_for_timeout(1500)
        canvas = 0
        if page.query_selector("#trends-line"):
            canvas = page.eval_on_selector("#trends-line", "c => c.width")
        fonts = page.evaluate("document.fonts && document.fonts.size > 0")
        browser.close()

    failures = [f"console: {c}" for c in console] + [f"pageerror: {e}" for e in page_errors]
    if not rows:
        failures.append("render: no shortlist rows")
    if not canvas:
        failures.append("render: trends chart not sized")
    if not fonts:
        failures.append("render: no fonts loaded")
    print(f"rows={rows} chart_width={canvas} fonts={fonts}")
    return failures


def main() -> int:
    """Serve ui/, run the headless check, print the verdict, and return an exit code."""
    httpd = serve(UI_DIR)
    try:
        port = httpd.server_address[1]
        failures = check(f"http://127.0.0.1:{port}/?base={BASE}")
    finally:
        httpd.shutdown()
    if failures:
        print(f"ui-check FAILED ({len(failures)}):")
        for f in failures:
            print(f"  - {f}")
        return 1
    print("ui-check PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
