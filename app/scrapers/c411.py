from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from playwright.async_api import BrowserContext, Page, async_playwright

from app.core.config import Settings, get_settings
from app.core.exceptions import MissingCredentialsError, ScrapingError
from app.core.files import load_config_file, write_config_file
from app.core.http import DEFAULT_USER_AGENT

logger = logging.getLogger(__name__)

COOKIES_FILE = "c411_cookies.json"
LOGIN_PAGE_URL = "https://c411.org/login"
USER_STATS_URL = "https://c411.org/api/auth/me"


def is_enabled(settings: Settings) -> bool:
    return bool(settings.c411_user and settings.c411_pass)


async def _refresh_cookies(context: BrowserContext, page: Page) -> bool:
    """Log in and persist session cookies to the config directory."""

    settings = get_settings()
    if not settings.c411_user or not settings.c411_pass:
        raise MissingCredentialsError("Missing C411 credentials")

    try:
        await page.goto(LOGIN_PAGE_URL)
        await page.fill('input[placeholder*="Pseudo"]', settings.c411_user)
        await page.fill('input[placeholder*="Mot de passe"]', settings.c411_pass)
        await asyncio.sleep(1)

        button = await page.query_selector('button:has-text("Connexion"), button.bg-emerald-500')
        if button:
            await button.click()
        else:
            await page.keyboard.press("Enter")

        await asyncio.sleep(5)
        await page.goto(USER_STATS_URL)
        payload = json.loads(await page.inner_text("body"))

        if payload.get("authenticated"):
            write_config_file(COOKIES_FILE, json.dumps(await context.cookies()))
            return True
    except Exception as exc:
        logger.error("C411 login failed: %s", exc)

    return False


async def get_stats(headless: bool = True) -> dict[str, Any]:
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=headless)
        context = await browser.new_context(user_agent=DEFAULT_USER_AGENT)
        page = await context.new_page()

        try:
            try:
                cookies = load_config_file(COOKIES_FILE, as_json=True)
            except FileNotFoundError:
                await _refresh_cookies(context, page)
                cookies = load_config_file(COOKIES_FILE, as_json=True)

            await context.add_cookies(cookies)
            response = await context.request.get(USER_STATS_URL)
            data = await response.json() if response.ok else {}

            if not data.get("authenticated"):
                refreshed = await _refresh_cookies(context, page)
                if not refreshed:
                    raise ScrapingError("C411 authentication failed")

                cookies = load_config_file(COOKIES_FILE, as_json=True)
                await context.add_cookies(cookies)
                response = await context.request.get(USER_STATS_URL)
                data = await response.json() if response.ok else {}

            user = data.get("user")
            if not user:
                return {"raw_upload": 0.0, "raw_download": 0.0, "bonus": 0.0}

            return {
                "raw_upload": float(user.get("uploaded", 0)),
                "raw_download": float(user.get("downloaded", 0)),
                "bonus": 0.0,
            }
        except Exception as exc:
            if isinstance(exc, (MissingCredentialsError, ScrapingError)):
                raise
            raise ScrapingError(str(exc)) from exc
        finally:
            await browser.close()
