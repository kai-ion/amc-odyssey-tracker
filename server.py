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

    # Run the checker
    from checker import check_theater, IMAX_70MM_THEATERS
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


@app.route("/health")
def health():
    return jsonify({"status": "ok", "time": datetime.now().isoformat()})


async def run_check(date_str):
    """Run Playwright checks for all theaters on a given date."""
    from playwright.async_api import async_playwright
    from checker import check_theater, IMAX_70MM_THEATERS

    results = {}

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        )
        page = await context.new_page()

        for theater in IMAX_70MM_THEATERS:
            result = await check_theater(page, theater, date_str)
            results[theater["id"]] = {
                "available": result.get("available", False),
                "showtimes": result.get("showtimes", []),
                "soldOut": result.get("sold_out", False),
                "has70mm": result.get("has_70mm", False),
                "error": result.get("error"),
            }
            await page.wait_for_timeout(500)

        await browser.close()

    return results


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
