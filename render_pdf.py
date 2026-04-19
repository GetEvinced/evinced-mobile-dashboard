#!/usr/bin/env python3
"""Render the mobile-products-dashboard HTML to PDF using Playwright/Chromium.
Handles Playwright installation automatically if needed."""
import asyncio, sys, os, subprocess, glob

BASE    = os.path.dirname(os.path.abspath(__file__))
OUTPUTS = os.path.join(BASE, "..")  # mnt/outputs/

HTML_PATH = os.path.join(OUTPUTS, "mobile-products-dashboard.html")
PDF_PATH  = os.path.join(OUTPUTS, "mobile-products-dashboard.pdf")

def find_chromium():
    """Find Chromium binary installed by Playwright, searching common cache locations."""
    patterns = [
        os.path.expanduser("~/.cache/ms-playwright/chromium-*/chrome-linux64/chrome"),
        "/root/.cache/ms-playwright/chromium-*/chrome-linux64/chrome",
        "/sessions/*/. cache/ms-playwright/chromium-*/chrome-linux64/chrome",
    ]
    for pattern in patterns:
        matches = glob.glob(pattern)
        if matches:
            return sorted(matches)[-1]  # latest version
    return None

def ensure_playwright():
    """Install Playwright + Chromium if not already available."""
    # Try importing first
    try:
        import playwright  # noqa
        chrome = find_chromium()
        if chrome:
            return chrome
    except ImportError:
        pass

    print("Installing Playwright…")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "playwright",
                           "--break-system-packages", "-q"])
    print("Installing Chromium…")
    subprocess.check_call([sys.executable, "-m", "playwright", "install", "chromium"])

    chrome = find_chromium()
    if not chrome:
        raise RuntimeError("Chromium not found after install")
    return chrome

async def render(chrome_path):
    # Add site-packages to path so playwright is importable
    for sp in glob.glob(os.path.expanduser("~/.local/lib/python*/site-packages")):
        if sp not in sys.path:
            sys.path.insert(0, sp)

    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            executable_path=chrome_path,
            args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"]
        )
        page = await browser.new_page()
        await page.set_viewport_size({"width": 1600, "height": 900})
        await page.goto(f"file://{HTML_PATH}", wait_until="networkidle", timeout=30000)
        await page.wait_for_timeout(4000)  # let Chart.js render

        await page.pdf(
            path=PDF_PATH,
            format="A3",
            landscape=True,
            print_background=True,
            margin={"top": "8mm", "bottom": "8mm", "left": "8mm", "right": "8mm"},
            scale=0.82,
        )
        size = os.path.getsize(PDF_PATH)
        print(f"PDF saved → {PDF_PATH}  ({size:,} bytes)")
        await browser.close()

if __name__ == "__main__":
    chrome = ensure_playwright()
    print(f"Using Chromium: {chrome}")
    asyncio.run(render(chrome))
