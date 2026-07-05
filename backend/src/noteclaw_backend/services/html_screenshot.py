"""Render HTML strings to PNG via headless Chromium (Playwright).

Browser is launched lazily on first use and reused for the process lifetime.
If Playwright or Chromium is unavailable, callers should detect the OSError
and fall back to a different rendering path.
"""
from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

_DEFAULT_SIZE = (1280, 720)
_browser_lock = asyncio.Lock()
_browser = None
_browser_warned = False


async def html_to_png(
    html: str,
    out_path: Path,
    *,
    size: tuple[int, int] = _DEFAULT_SIZE,
) -> Optional[Path]:
    """Render a single HTML string to a PNG file. Returns path or None on failure."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    page = None
    try:
        page = await _new_page(size)
        await page.set_content(html, wait_until="load")
        await page.screenshot(path=str(out_path), full_page=False, omit_background=False)
        return out_path
    except Exception as exc:  # noqa: BLE001
        logger.warning("html_to_png failed for %s: %s", out_path.name, exc)
        return None
    finally:
        if page is not None:
            try:
                await page.close()
            except Exception:  # noqa: BLE001
                pass


async def html_batch_to_png(
    items: list[tuple[str, Path]],
    *,
    size: tuple[int, int] = _DEFAULT_SIZE,
) -> list[Path]:
    """Render many HTML strings. Returns list of successful paths (may be shorter than input)."""
    if not items:
        return []
    results: list[Path] = []
    for html, out_path in items:
        rendered = await html_to_png(html, out_path, size=size)
        if rendered is not None:
            results.append(rendered)
    return results


async def _new_page(size: tuple[int, int]):
    browser = await _get_browser()
    if browser is None:
        raise OSError("playwright browser unavailable")
    context = await browser.new_context(viewport={"width": size[0], "height": size[1]})
    page = await context.new_page()
    await context.close()  # we only need the page; reuse browser
    return page


async def _get_browser():
    global _browser, _browser_warned
    if _browser is not None:
        return _browser
    async with _browser_lock:
        if _browser is not None:
            return _browser
        try:
            from playwright.async_api import async_playwright  # type: ignore
        except Exception as exc:  # noqa: BLE001
            if not _browser_warned:
                logger.warning("playwright not installed: %s", exc)
                _browser_warned = True
            return None
        try:
            pw = await async_playwright().start()
            _browser = await pw.chromium.launch(headless=True, args=["--no-sandbox"])
            logger.info("playwright chromium browser launched")
        except Exception as exc:  # noqa: BLE001
            if not _browser_warned:
                logger.warning(
                    "playwright chromium launch failed (%s). Run `playwright install chromium`.",
                    exc,
                )
                _browser_warned = True
            return None
    return _browser


async def shutdown_browser() -> None:
    global _browser
    if _browser is None:
        return
    try:
        await _browser.close()
    except Exception:  # noqa: BLE001
        pass
    _browser = None
