#!/usr/bin/env python3
"""
Backend API server for AMC Odyssey Tracker.
Wraps the Playwright checker and serves results to the React frontend.
"""

import asyncio
import json
from datetime import datetime
from pathlib import Path
from flask import Flask, jsonify, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)


@app.route("/check")
def check_availability():
    """Check all theaters for a given date."""
    date = request.args.get("date", datetime.now().strftime("%Y-%m-%d"))

    # Check if we have recent cached results (< 10 min old)
    cache_file = DATA_DIR / f"cache_{date}.json"
    if cache_file.exists():
        cache_age = datetime.now().timestamp() - cache_file.stat().st_mtime
        if cache_age < 600:  # 10 minutes
            with open(cache_file) as f:
                return jsonify(json.load(f))

    # Check session validity
    from amc_session import is_session_valid
    if not is_session_valid():
        return jsonify({"error": "Session expired. Run: python amc_session.py --init", "results": {}})

    # Run the checker
    from checker import IMAX_70MM_THEATERS
    results = asyncio.run(run_check(date))

    # Cache results
    output = {"date": date, "checked_at": datetime.now().isoformat(), "results": results}
    with open(cache_file, "w") as f:
        json.dump(output, f)

    return jsonify(output)


@app.route("/theaters")
def list_theaters():
    """Return list of known 70mm theaters."""
    from checker import IMAX_70MM_THEATERS
    return jsonify({"theaters": IMAX_70MM_THEATERS})


@app.route("/find-next")
def find_next_available():
    """Scan dates until we find one with available tickets."""
    theater_ids = request.args.get("theaters", "").split(",")
    days = int(request.args.get("days", 30))

    from checker import IMAX_70MM_THEATERS
    theaters = [t for t in IMAX_70MM_THEATERS if t["id"] in theater_ids] if theater_ids[0] else IMAX_70MM_THEATERS

    result = asyncio.run(run_find_next(theaters, days))
    return jsonify(result)


@app.route("/health")
def health():
    return jsonify({"status": "ok", "time": datetime.now().isoformat()})


async def run_check(date_str):
    """Run checks using saved AMC session cookies."""
    from amc_session import get_amc_page
    from checker import IMAX_70MM_THEATERS
    import re

    results = {}

    for theater in IMAX_70MM_THEATERS:
        url = f"https://www.amctheatres.com/movies/the-odyssey-76238/showtimes/the-odyssey-76238/{date_str}/{theater['id']}/all"
        try:
            content, title = await get_amc_page(url)

            showtimes = re.findall(r'\b(\d{1,2}:\d{2}\s*(?:AM|PM))\b', content)
            has_70mm = "70mm" in content.lower()
            sold_out = "sold out" in content.lower()
            wheelchair_only = "wheelchair" in content.lower() and not showtimes

            results[theater["id"]] = {
                "available": len(showtimes) > 0 and not sold_out and not wheelchair_only,
                "showtimes": list(set(showtimes))[:6],
                "soldOut": sold_out or wheelchair_only,
                "has70mm": has_70mm,
            }
        except RuntimeError as e:
            results[theater["id"]] = {"available": False, "error": str(e)}
        except Exception as e:
            results[theater["id"]] = {"available": False, "error": str(e)[:50]}

    return results


async def run_find_next(theaters, max_days):
    """Scan dates across theaters — check the AMC listing page which shows all dates at once."""
    from playwright.async_api import async_playwright
    from datetime import timedelta
    import re

    results = {"found": False, "date": None, "theater": None, "showtimes": []}

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled"],
        )
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1440, "height": 900},
        )
        await context.add_init_script("Object.defineProperty(navigator, 'webdriver', { get: () => undefined });")
        page = await context.new_page()

        for theater in theaters:
            # AMC's movie page for a theater shows all available dates
            url = f"https://www.amctheatres.com/movies/the-odyssey-76238/showtimes/the-odyssey-76238/{datetime.now().strftime('%Y-%m-%d')}/{theater['id']}/all"
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=20000)
                await page.wait_for_timeout(3000)

                content = await page.content()

                # Look for any available showtime on ANY date shown on the page
                # AMC pages often list multiple dates with showtimes
                has_showtimes = bool(re.findall(r'\b\d{1,2}:\d{2}\s*(?:AM|PM)\b', content))
                not_sold_out = "sold out" not in content.lower()
                has_70mm = "70mm" in content.lower()

                if has_showtimes and not_sold_out and has_70mm:
                    times = re.findall(r'\b(\d{1,2}:\d{2}\s*(?:AM|PM))\b', content)
                    results = {
                        "found": True,
                        "theater": theater["name"],
                        "location": theater["location"],
                        "theaterId": theater["id"],
                        "showtimes": list(set(times))[:5],
                        "url": url,
                    }
                    await browser.close()
                    return results

            except Exception as e:
                continue

            await page.wait_for_timeout(1000)

        await browser.close()

    return results


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
