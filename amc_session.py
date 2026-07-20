#!/usr/bin/env python3
"""
AMC Session Manager

Handles Cloudflare bypass for AMC using Playwright with stealth.
Opens a visible browser ONCE to pass the challenge, saves cookies,
then reuses them for all subsequent headless requests.

Usage:
    # First time: opens browser, you wait for Cloudflare to pass, cookies are saved
    python amc_session.py --init

    # After that: headless requests use saved cookies
    from amc_session import get_amc_page
"""

import asyncio
import json
import os
from pathlib import Path
from datetime import datetime

COOKIES_FILE = Path(__file__).parent / "data" / "amc_cookies.json"
STATE_FILE = Path(__file__).parent / "data" / "amc_state.json"


async def init_session():
    """Open a visible browser to AMC, wait for Cloudflare to pass, save cookies."""
    from playwright.async_api import async_playwright

    COOKIES_FILE.parent.mkdir(parents=True, exist_ok=True)

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            args=["--disable-blink-features=AutomationControlled"],
        )
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1440, "height": 900},
        )
        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            delete navigator.__proto__.webdriver;
        """)

        page = await context.new_page()

        print("Opening AMC website... Wait for Cloudflare challenge to pass.")
        print("(This may take a few seconds — don't close the browser)")
        await page.goto("https://www.amctheatres.com/movies", wait_until="domcontentloaded", timeout=60000)

        # Wait for Cloudflare to pass (page title changes from "Attention Required")
        print("Waiting for page to load past Cloudflare...")
        for _ in range(30):
            title = await page.title()
            if "attention" not in title.lower() and "cloudflare" not in title.lower():
                print(f"  Page loaded: {title}")
                break
            await page.wait_for_timeout(2000)
        else:
            print("  WARNING: Cloudflare may not have passed. Try again.")

        # Wait a bit more for cookies to settle
        await page.wait_for_timeout(3000)

        # Save cookies
        cookies = await context.cookies()
        with open(COOKIES_FILE, "w") as f:
            json.dump(cookies, f, indent=2)
        print(f"  Saved {len(cookies)} cookies to {COOKIES_FILE}")

        # Save storage state (includes localStorage, sessionStorage)
        await context.storage_state(path=str(STATE_FILE))
        print(f"  Saved browser state to {STATE_FILE}")

        print("\nSession initialized! You can now close the browser.")
        print("The backend will use these cookies for headless requests.")

        # Keep browser open briefly so user can see it worked
        await page.wait_for_timeout(3000)
        await browser.close()


async def get_amc_page(url, timeout=20000):
    """Fetch an AMC page using saved session cookies (headless)."""
    from playwright.async_api import async_playwright

    if not STATE_FILE.exists():
        raise RuntimeError("No saved session. Run: python amc_session.py --init")

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled"],
        )
        context = await browser.new_context(
            storage_state=str(STATE_FILE),
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1440, "height": 900},
        )
        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
        """)

        page = await context.new_page()
        await page.goto(url, wait_until="domcontentloaded", timeout=timeout)
        await page.wait_for_timeout(2000)

        content = await page.content()
        title = await page.title()

        # Check if Cloudflare blocked us (session expired)
        if "attention required" in title.lower() or "cloudflare" in title.lower():
            await browser.close()
            raise RuntimeError("Session expired. Run: python amc_session.py --init")

        await browser.close()
        return content, title


def is_session_valid():
    """Check if we have a saved session that's less than 24h old."""
    if not STATE_FILE.exists():
        return False
    age_hours = (datetime.now().timestamp() - STATE_FILE.stat().st_mtime) / 3600
    return age_hours < 24


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--init", action="store_true", help="Initialize session (opens browser)")
    parser.add_argument("--test", help="Test fetching a URL with saved session")
    args = parser.parse_args()

    if args.init:
        asyncio.run(init_session())
    elif args.test:
        content, title = asyncio.run(get_amc_page(args.test))
        print(f"Title: {title}")
        print(f"Content length: {len(content)}")
        print(f"Has showtimes: {'showtime' in content.lower()}")
    else:
        if is_session_valid():
            print("Session is valid (< 24h old)")
        else:
            print("No valid session. Run: python amc_session.py --init")
