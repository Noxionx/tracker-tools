from __future__ import annotations

import asyncio
import logging
from typing import Any

from playwright.async_api import Page, async_playwright

from app.core.config import Settings, get_settings
from app.core.exceptions import MissingCredentialsError, ScrapingError
from app.core.files import load_config_file, write_config_file
from app.core.http import DEFAULT_USER_AGENT

logger = logging.getLogger(__name__)

TOKEN_FILE = "torr9_token.txt"
LOGIN_PAGE_URL = "https://torr9.net/login"
USER_STATS_URL = "https://api.torr9.net/api/v1/users/me"


def is_enabled(settings: Settings) -> bool:
    username = settings.torr9_user or settings.tor9_user
    password = settings.torr9_password or settings.torr9_pass or settings.tor9_pass
    return bool(username and password)


def _resolve_credentials() -> tuple[str | None, str | None]:
    settings = get_settings()
    username = settings.torr9_user or settings.tor9_user
    password = settings.torr9_password or settings.torr9_pass or settings.tor9_pass
    return username, password


async def _refresh_token(page: Page) -> str | None:
    """Log in and retrieve the API token stored in localStorage."""

    username, password = _resolve_credentials()
    if not username or not password:
        raise MissingCredentialsError("Missing Torr9 credentials")

    try:
        await page.goto(LOGIN_PAGE_URL)
        await page.fill('input[placeholder*="utilisateur"]', username)
        await page.fill('input[placeholder*="mot de passe"]', password)
        await asyncio.sleep(1)

        button = await page.query_selector('button:has-text("Se connecter")')
        if button:
            await button.click()
        else:
            await page.keyboard.press("Enter")

        await page.wait_for_load_state("networkidle", timeout=15000)

        for _ in range(10):
            token = await page.evaluate("() => localStorage.getItem('token')")
            if token:
                write_config_file(TOKEN_FILE, token)
                return token
            await asyncio.sleep(1)
    except Exception as exc:
        logger.error("Torr9 login failed: %s", exc)

    return None


async def get_stats(headless: bool = True) -> dict[str, Any]:
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=headless)
        context = await browser.new_context(user_agent=DEFAULT_USER_AGENT)
        page = await context.new_page()

        try:
            try:
                token = str(load_config_file(TOKEN_FILE)).strip()
            except FileNotFoundError:
                token = await _refresh_token(page)

            if not token:
                raise MissingCredentialsError("Unable to acquire Torr9 token")

            response = await context.request.get(USER_STATS_URL, headers={"Authorization": f"Bearer {token}"})
            if response.status == 401:
                token = await _refresh_token(page)
                if token:
                    response = await context.request.get(
                        USER_STATS_URL,
                        headers={"Authorization": f"Bearer {token}"},
                    )

            if not response.ok:
                raise ScrapingError(f"Torr9 API error {response.status}")

            data = await response.json()
            bonus_up = float(data.get("bonus_uploaded", 0))
            bonus_down = float(data.get("bonus_downloaded", 0))

            return {
                "raw_upload": float(data.get("total_uploaded_bytes", 0)) + bonus_up,
                "raw_download": float(data.get("total_downloaded_bytes", 0)) + bonus_down,
                "bonus": float(data.get("jeton_balance", 0)),
            }
        except Exception as exc:
            if isinstance(exc, (MissingCredentialsError, ScrapingError)):
                raise
            raise ScrapingError(str(exc)) from exc
        finally:
            await browser.close()
