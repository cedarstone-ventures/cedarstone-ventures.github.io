"""Render the homepage rate-change signup band (#alerts) for the Chairman's look.

Isolated browser context on purpose: the shared playwright MCP profiles are held by a
peer session, and this vault's standing rule is never to fight one for a lock.

Writes proof shots + hard geometry numbers. The numbers matter as much as the pictures:
the 2026-07-28 nav fix was regressed once already by a change that "looked fine" but
overflowed at 320px, so every render here asserts scrollWidth <= viewport width.
"""
import asyncio
import sys
from pathlib import Path

from playwright.async_api import async_playwright

URL = "http://127.0.0.1:8791/"
OUT = Path(__file__).resolve().parent.parent / "proof"

VIEWPORTS = [
    ("desktop-1440", 1440, 900),
    ("laptop-1280", 1280, 800),
    ("phone-390", 390, 844),
    ("phone-320", 320, 720),
]


async def main() -> int:
    OUT.mkdir(exist_ok=True)
    failures = []

    async with async_playwright() as pw:
        browser = await pw.chromium.launch()
        for name, w, h in VIEWPORTS:
            page = await browser.new_page(viewport={"width": w, "height": h})
            await page.goto(URL, wait_until="networkidle")

            # --- horizontal overflow guard (the regression this repo already paid for)
            sw = await page.evaluate("() => document.documentElement.scrollWidth")
            if sw > w:
                failures.append(f"{name}: scrollWidth {sw} > viewport {w} (horizontal overflow)")

            # --- the band exists, is visible, and its button is a real tap target
            box = await page.evaluate(
                """() => {
                  const s = document.querySelector('#alerts');
                  const b = document.querySelector('#alerts .btn');
                  if (!s || !b) return null;
                  const sb = s.getBoundingClientRect(), bb = b.getBoundingClientRect();
                  return {
                    sectionW: Math.round(sb.width),
                    btnW: Math.round(bb.width), btnH: Math.round(bb.height),
                    btnText: b.textContent.trim(), href: b.getAttribute('href'),
                    lines: Math.round(bb.height / 24),
                  };
                }"""
            )
            if box is None:
                failures.append(f"{name}: #alerts or its button NOT FOUND in the live DOM")
            else:
                if box["btnH"] < 44:
                    failures.append(f"{name}: button height {box['btnH']}px < 44px tap target")
                if box["href"] != "https://deedwell.gumroad.com/subscribe":
                    failures.append(f"{name}: button href is {box['href']!r}")
                print(f"{name:14} scrollW={sw:5} {box}")

            await page.locator("#alerts").screenshot(path=str(OUT / f"alerts-{name}.png"))
            if name == "desktop-1440":
                await page.screenshot(path=str(OUT / "homepage-full.png"), full_page=True)
            if name == "phone-390":
                # the free-checklist magnet immediately above, to prove the two read as
                # gift-then-optional-ask and not as a gate in front of the free thing
                await page.locator("#free").screenshot(path=str(OUT / "free-then-alerts-390.png"))
            await page.close()
        await browser.close()

    print()
    if failures:
        print("FAIL:")
        for f in failures:
            print("  -", f)
        return 1
    print(f"PASS - all {len(VIEWPORTS)} viewports. Shots in {OUT}")
    return 0


sys.exit(asyncio.run(main()))
