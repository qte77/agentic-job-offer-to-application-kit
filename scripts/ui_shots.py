"""Regenerate the README screencast GIFs (light + dark) — a headless dashboard walkthrough.

Replicates the sibling `agenthud-agui-a2ui` pattern: theme-aware `<picture>` GIFs in a `<details>`
screencast block. Drives the local preview build (seeded with synthetic PII-free data via
`ui_e2e.seed_local`), forces each theme, steps Shortlist -> Market trends -> Companies capturing a
frame per interaction, and assembles them into `assets/images/usage-<theme>.gif` with Pillow.

Deterministic + reproducible: re-run on any UI change instead of hand-capturing. Run via the
polyfetch venv (which ships patchright + Chromium), adding Pillow for the GIF assembly:

    make ui_shots   # uv run --directory $POLYFETCH_DIR --with pillow python scripts/ui_shots.py
"""

from __future__ import annotations

import io
import shutil
import tempfile
from pathlib import Path

from patchright.sync_api import sync_playwright
from PIL import Image
from ui_e2e import seed_local, serve

OUT_DIR = Path(__file__).resolve().parent.parent / "assets" / "images"
VIEWPORT = {"width": 1280, "height": 860}
FRAME_MS = 1400  # per-frame hold in the looping GIF
GIF_WIDTH = 1024  # downscale for a lighter README asset (crisper-per-KB than full 1280)


def _force_theme(page, theme: str) -> None:
    """Pin the dashboard to `theme` (light/dark) and repaint the charts (Chart.js caches colors)."""
    page.evaluate(
        "(t) => { document.documentElement.setAttribute('data-theme', t);"
        " document.dispatchEvent(new Event('themechange')); }",
        theme,
    )
    page.wait_for_timeout(400)


def _frame(page, frames: list) -> None:
    img = Image.open(io.BytesIO(page.screenshot())).convert("RGB")
    if img.width != GIF_WIDTH:
        img = img.resize((GIF_WIDTH, round(img.height * GIF_WIDTH / img.width)))
    frames.append(img)


def _walk(page, frames: list) -> None:
    """Step through the three tabs + a couple of interactions, one captured frame per step."""
    page.wait_for_timeout(300)
    _frame(page, frames)  # Shortlist
    row = page.query_selector("tr.offer-row")
    if row:
        row.click()  # expand the first offer -> tailored CV + cover letter
        page.wait_for_timeout(500)
        _frame(page, frames)
    page.click("#tab-trends")  # Market trends: keyword charts + geo-by-field hiring chart
    page.wait_for_timeout(1000)
    _frame(page, frames)
    page.select_option("#trends-gran", "month")  # granularity dropdown
    page.wait_for_timeout(800)
    _frame(page, frames)
    if not page.eval_on_selector("#tab-companies", "el => el.hidden"):
        page.click("#tab-companies")  # Companies: snapshot date + table + per-company chart
        page.wait_for_timeout(600)
        _frame(page, frames)
        page.click('#companies-table th[data-sort="count"]')  # click-to-sort a column
        page.wait_for_timeout(500)
        _frame(page, frames)


def _capture(p, url: str, theme: str) -> list:
    browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
    page = browser.new_context(viewport=VIEWPORT).new_page()
    page.goto(url, wait_until="domcontentloaded", timeout=30000)
    page.wait_for_timeout(1500)
    _force_theme(page, theme)
    frames: list = []
    _walk(page, frames)
    browser.close()
    return frames


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    tmp = Path(tempfile.mkdtemp())
    try:
        seed_local(tmp / "ui")
        httpd = serve(tmp / "ui")
        try:
            url = f"http://127.0.0.1:{httpd.server_address[1]}/"
            with sync_playwright() as p:
                for theme in ("light", "dark"):
                    frames = _capture(p, url, theme)
                    out = OUT_DIR / f"usage-{theme}.gif"
                    frames[0].save(
                        out,
                        save_all=True,
                        append_images=frames[1:],
                        duration=FRAME_MS,
                        loop=0,
                        optimize=True,
                    )
                    print(f"wrote {out} ({len(frames)} frames, {out.stat().st_size // 1024} KB)")
        finally:
            httpd.shutdown()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
