import os
from playwright.async_api import async_playwright, Browser, BrowserContext, Page

class BrowserManager:
    _playwright = None
    _browser: Browser = None
    _context: BrowserContext = None

    @classmethod
    async def get_browser(cls) -> Browser:
        if cls._browser is None:
            cls._playwright = await async_playwright().start()
            headless = os.getenv("HEADLESS", "true").lower() == "true"
            cls._browser = await cls._playwright.chromium.launch(
                headless=headless,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                    "--disable-setuid-sandbox"
                ]
            )
        return cls._browser

    @classmethod
    async def get_context(cls) -> BrowserContext:
        if cls._context is None:
            browser = await cls.get_browser()
            cls._context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                viewport={"width": 1280, "height": 800}
            )
        return cls._context

    @classmethod
    async def new_page(cls) -> Page:
        context = await cls.get_context()
        page = await context.new_page()
        return page

    @classmethod
    async def close_browser(cls):
        if cls._context:
            await cls._context.close()
            cls._context = None
        if cls._browser:
            await cls._browser.close()
            cls._browser = None
        if cls._playwright:
            await cls._playwright.stop()
            cls._playwright = None
