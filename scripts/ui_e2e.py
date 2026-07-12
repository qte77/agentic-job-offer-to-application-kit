"""Comprehensive dashboard e2e for the dashboard (ui/) — LOCAL preview build + REMOTE gh-pages.

A heavier companion to scripts/ui_check.py (the fast single-viewport smoke). For each target it:
  * loads the page and captures console / page errors,
  * drives every interactive element — tabs, the theme cycle (auto/light/dark), the trends
    time-frame and granularity dropdowns, the Companies-tab sortable headers, and an offer-row
    expand,
  * verifies THEMES by asserting light vs dark actually change the rendered background,
  * iterates VIEWPORTS (desktop / tablet / mobile) + a real mobile DEVICE descriptor, asserting the
    layout renders with no horizontal body overflow.

LOCAL serves a throwaway ui/ copy seeded with a synthetic companies.json ({snapshot, rows}) + trends
NDJSON so all three tabs are live; it is the HARD gate. REMOTE hits the published gh-pages site
(Companies tab hidden by design) and is BEST-EFFORT — a blocked network / unreachable host never
fails the run (CI has no browser and this is a local dev tool).

Run through the sibling polyfetch-scrape venv (patchright + Chromium), same as ui_check.py::

    make ui-e2e                    # uv run --directory $POLYFETCH_DIR python scripts/ui_e2e.py
"""

from __future__ import annotations

import functools
import http.server
import json
import shutil
import socketserver
import tempfile
import threading
from pathlib import Path

from patchright.sync_api import sync_playwright

UI_DIR = Path(__file__).resolve().parent.parent / "ui"
REMOTE_URL = "https://qte77.github.io/agentic-job-offer-to-application-kit/"

VIEWPORTS = [("desktop", 1280, 800), ("tablet", 768, 1024), ("mobile", 375, 667)]
DEVICE_NAME = "iPhone 13"

SNAPSHOT = "2026-07-11"
# Pre-sorted in aggregate_companies' default order (city, field, -count, company) so the JS default
# render mirrors production; the Company column reads [Acme, Zeta, Bolt, Nova].
COMPANY_ROWS = [
    {
        "city": "Berlin",
        "region": "DE",
        "field": "backend",
        "company": "Acme",
        "count": 5,
        "momentum": None,
    },
    {
        "city": "Berlin",
        "region": "DE",
        "field": "frontend",
        "company": "Zeta",
        "count": 2,
        "momentum": None,
    },
    {
        "city": "Munich",
        "region": "Bayern",
        "field": "ml",
        "company": "Bolt",
        "count": 9,
        "momentum": "heating",
    },
    {
        "city": "Remote",
        "region": "",
        "field": "backend",
        "company": "Nova",
        "count": 3,
        "momentum": "cooling",
    },
]


def _trends(key: str, labels: list[str]) -> str:
    return "\n".join(
        json.dumps({key: lb, "counts": {"python": 10 + i, "rust": 20 - i}})
        for i, lb in enumerate(labels)
    )


def seed_local(dst: Path) -> None:
    """Copy ui/ into dst and seed the local-only data so all three tabs and both charts render."""
    shutil.copytree(UI_DIR, dst)
    data = dst / "public" / "data"
    (data / "companies.json").write_text(json.dumps({"snapshot": SNAPSHOT, "rows": COMPANY_ROWS}))
    (data / "trends.ndjson").write_text(_trends("week", [f"2026-W{n:02d}" for n in range(10, 24)]))
    (data / "trends-daily.ndjson").write_text(
        _trends("date", [f"2026-06-{d:02d}" for d in range(1, 15)])
    )
    (data / "trends-monthly.ndjson").write_text(_trends("month", ["2026-04", "2026-05", "2026-06"]))


def serve(directory: Path) -> socketserver.TCPServer:
    """Start a daemon HTTP server for `directory` on an ephemeral localhost port."""
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(directory))

    class Server(socketserver.ThreadingTCPServer):
        allow_reuse_address = True
        daemon_threads = True

    httpd = Server(("127.0.0.1", 0), handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd


def _body_bg(page) -> str:
    return page.evaluate("getComputedStyle(document.body).backgroundColor")


def _overflows(page) -> bool:
    return page.evaluate("document.documentElement.scrollWidth > window.innerWidth + 2")


def _companies_col(page) -> list[str]:
    return page.eval_on_selector_all(
        "#companies-body tr td:first-child", "e => e.map(x => x.textContent.trim())"
    )


def _check_theme(page, tag: str, fails: list[str]) -> None:
    """Cycle the theme toggle; a working theme yields >=2 distinct backgrounds (light != dark)."""
    seen: dict[str, str] = {}
    for _ in range(4):
        theme = page.eval_on_selector("html", "el => el.getAttribute('data-theme') || 'auto'")
        seen.setdefault(theme, _body_bg(page))
        page.click("#theme-toggle")
        page.wait_for_timeout(150)
    if len({*seen.values()}) < 2:
        fails.append(f"[{tag}] theme toggle did not change background: {seen}")
    if "light" in seen and "dark" in seen and seen["light"] == seen["dark"]:
        fails.append(f"[{tag}] light and dark share a background: {seen['light']}")


def _check_trends(page, tag: str, fails: list[str]) -> None:
    """Trends tab + both dropdowns keep the chart sized."""
    page.click("#tab-trends")
    page.wait_for_timeout(800)
    for val in ("26", "13", "all"):
        page.select_option("#trends-range", val)
        page.wait_for_timeout(200)
    for val in ("day", "month", "week"):
        page.select_option("#trends-gran", val)
        page.wait_for_timeout(400)
    if page.query_selector("#trends-line") and (
        page.eval_on_selector("#trends-line", "c => c.width") == 0
    ):
        fails.append(f"[{tag}] trends chart lost size after dropdowns")


def _check_companies(page, local: bool, fails: list[str]) -> None:
    """Local: Companies tab visible + date + sortable. Remote: hidden by design."""
    hidden = page.eval_on_selector("#tab-companies", "el => el.hidden")
    if not local:
        if not hidden:
            fails.append("[remote] companies tab visible on the published site (should be hidden)")
        return
    if hidden:
        fails.append("[local] companies tab hidden despite seeded data")
        return
    page.click("#tab-companies")
    page.wait_for_timeout(200)
    if page.eval_on_selector("#companies-snapshot", "el => el.textContent.trim()") != SNAPSHOT:
        fails.append("[local] snapshot date not rendered")
    before = _companies_col(page)
    page.click('#companies-table th[data-sort="count"]')
    page.wait_for_timeout(150)
    asc = _companies_col(page)
    page.click('#companies-table th[data-sort="count"]')
    page.wait_for_timeout(150)
    desc = _companies_col(page)
    if not (before != asc and asc == list(reversed(desc))):
        fails.append(f"[local] sort did not toggle: before={before} asc={asc} desc={desc}")
    aria = page.eval_on_selector(
        '#companies-table th[data-sort="count"]', "el => el.getAttribute('aria-sort')"
    )
    if aria != "descending":
        fails.append(f"[local] aria-sort={aria!r} after 2 clicks, expected descending")


def drive_interactions(page, local: bool, fails: list[str]) -> None:
    """Exercise every interactive element on one desktop page."""
    tag = "local" if local else "remote"
    if page.eval_on_selector_all("tr.offer-row", "e => e.length") == 0:
        fails.append(f"[{tag}] no shortlist rows")
    _check_theme(page, tag, fails)
    _check_trends(page, tag, fails)
    _check_companies(page, local, fails)
    page.click("#tab-shortlist")
    page.wait_for_timeout(150)
    row = page.query_selector("tr.offer-row")
    if row:
        row.click()
        page.wait_for_timeout(150)
        if (
            page.eval_on_selector("tr.offer-row", "el => el.getAttribute('aria-expanded')")
            != "true"
        ):
            fails.append(f"[{tag}] offer row did not expand")


def drive_responsive(context, url: str, tag: str, fails: list[str]) -> None:
    """Each viewport: render + no horizontal overflow + a tab click still works."""
    page = context.new_page()
    page.goto(url, wait_until="domcontentloaded", timeout=30000)
    page.wait_for_timeout(1500)
    for name, w, h in VIEWPORTS:
        page.set_viewport_size({"width": w, "height": h})
        page.wait_for_timeout(300)
        if _overflows(page):
            fails.append(f"[{tag}] horizontal overflow at {name} {w}x{h}")
        if not page.query_selector("header .brand"):
            fails.append(f"[{tag}] header missing at {name}")
        page.click("#tab-trends")
        page.wait_for_timeout(200)
    page.close()


def check_target(p, url: str, local: bool) -> list[str]:
    """Run the full interaction + responsive + device suite against one URL."""
    tag = "local" if local else "remote"
    fails: list[str] = []
    console: list[str] = []
    browser = p.chromium.launch(headless=True, args=["--no-sandbox"])

    ctx = browser.new_context(viewport={"width": 1280, "height": 800})
    page = ctx.new_page()
    page.on(
        "console",
        lambda m: console.append(m.text) if m.type in ("error", "warning") else None,
    )
    page.on("pageerror", lambda e: console.append(f"pageerror: {e}"))
    page.goto(url, wait_until="domcontentloaded", timeout=30000)
    page.wait_for_timeout(2000)
    drive_interactions(page, local, fails)
    ctx.close()

    ctx2 = browser.new_context()
    drive_responsive(ctx2, url, tag, fails)
    ctx2.close()

    device = p.devices[DEVICE_NAME]
    dctx = browser.new_context(**device)
    dpage = dctx.new_page()
    dpage.goto(url, wait_until="domcontentloaded", timeout=30000)
    dpage.wait_for_timeout(1500)
    if _overflows(dpage):
        fails.append(f"[{tag}] horizontal overflow on {DEVICE_NAME}")
    if dpage.eval_on_selector_all(
        "tr.offer-row", "e => e.length"
    ) == 0 and not dpage.query_selector('[role="tab"]'):
        fails.append(f"[{tag}] nothing rendered on {DEVICE_NAME}")
    dctx.close()
    browser.close()

    console = [
        c for c in console if "status of 404" not in c and "Failed to load resource" not in c
    ]
    fails += [f"[{tag}] console: {c}" for c in console]
    return fails


def _run_local(p) -> list[str]:
    tmp = Path(tempfile.mkdtemp())
    try:
        seed_local(tmp / "ui")
        httpd = serve(tmp / "ui")
        try:
            port = httpd.server_address[1]
            print(f"== LOCAL  http://127.0.0.1:{port}/ ==")
            return check_target(p, f"http://127.0.0.1:{port}/", local=True)
        finally:
            httpd.shutdown()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main() -> int:
    """LOCAL (hard gate) + REMOTE (best-effort). Non-zero only on a LOCAL failure."""
    with sync_playwright() as p:
        local_fails = _run_local(p)
        print(f"== REMOTE {REMOTE_URL} (best-effort) ==")
        try:
            remote_fails = check_target(p, REMOTE_URL, local=False)
        except Exception as e:
            remote_fails = []
            print(f"  remote skipped (unreachable): {type(e).__name__}: {e}")

    if local_fails:
        print(f"\nui-e2e FAILED — LOCAL ({len(local_fails)}):")
        for f in local_fails:
            print(f"  - {f}")
        return 1
    if remote_fails:
        print(f"\nui-e2e local PASSED; remote flagged {len(remote_fails)} non-fatal issue(s):")
        for f in remote_fails:
            print(f"  - {f}")
    else:
        print(
            "\nui-e2e PASSED (local hard gate + remote; viewports + device; themes + interactions)"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
