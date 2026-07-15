import os
import json
import base64
import logging
from pathlib import Path
from playwright.async_api import async_playwright, Browser, BrowserContext, Page

logger = logging.getLogger(__name__)


def _load_auth_state() -> dict | None:
    """
    Load LinkedIn auth state from:
    1. LINKEDIN_AUTH_STATE environment variable (base64 encoded) — used on Render
    2. auth_state.json file in the backend directory — used locally/DigitalOcean
    Returns a dict suitable for browser.new_context(storage_state=...) or None.
    """
    # Try environment variable first (Render deployment)
    auth_b64 = os.getenv("LINKEDIN_AUTH_STATE", "").strip()
    if auth_b64:
        try:
            state_json = base64.b64decode(auth_b64).decode("utf-8")
            state = json.loads(state_json)
            logger.info("✅ LinkedIn auth state loaded from LINKEDIN_AUTH_STATE env variable.")
            return state
        except Exception as e:
            logger.warning(f"Failed to decode LINKEDIN_AUTH_STATE env variable: {e}")

    # Try local file fallback
    auth_file = Path(__file__).parent.parent / "auth_state.json"
    if auth_file.exists():
        try:
            with open(auth_file, "r") as f:
                state = json.load(f)
            logger.info(f"✅ LinkedIn auth state loaded from {auth_file}.")
            return state
        except Exception as e:
            logger.warning(f"Failed to load auth_state.json: {e}")

    logger.info("No LinkedIn auth state found. Running without saved session.")
    return None


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
            auth_state = _load_auth_state()
            context_kwargs = dict(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                viewport={"width": 1280, "height": 800}
            )
            if auth_state:
                context_kwargs["storage_state"] = auth_state
            cls._context = await browser.new_context(**context_kwargs)
        return cls._context

    @classmethod
    async def new_page(cls) -> Page:
        context = await cls.get_context()
        page = await context.new_page()

        async def intercept_route(route):
            if route.request.resource_type in ["image", "media", "font", "stylesheet"]:
                await route.abort()
            else:
                await route.continue_()

        await page.route("**/*", intercept_route)
        return page

    @classmethod
    async def close_browser(cls):
        if cls._context:
            try:
                await cls._context.close()
            except Exception:
                pass
            cls._context = None
        if cls._browser:
            try:
                await cls._browser.close()
            except Exception:
                pass
            cls._browser = None
        if cls._playwright:
            try:
                await cls._playwright.stop()
            except Exception:
                pass
            cls._playwright = None
