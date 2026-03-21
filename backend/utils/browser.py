"""Playwright session manager — connects to user's running Chrome."""

from playwright.async_api import async_playwright, Browser, Page
from backend.config import get_settings


async def get_browser() -> Browser:
    """Connect to Chrome running with --remote-debugging-port."""
    settings = get_settings()
    pw = await async_playwright().start()
    browser = await pw.chromium.connect_over_cdp(
        f"http://localhost:{settings.chrome_debug_port}"
    )
    return browser


async def new_page(browser: Browser) -> Page:
    """Create a new page in the connected browser."""
    context = browser.contexts[0] if browser.contexts else await browser.new_context()
    page = await context.new_page()
    return page
