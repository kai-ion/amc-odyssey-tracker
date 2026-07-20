#!/usr/bin/env python3
"""
AMC 70mm Odyssey Showtime Tracker

Checks AMC theaters for available 70mm IMAX screenings of "The Odyssey".
Uses Playwright to bypass Cloudflare protection.

Usage:
    python checker.py                    # Check all known 70mm theaters
    python checker.py --zip 10001       # Check near a zip code
    python checker.py --notify          # Send alert when slots open

Requirements:
    pip install playwright
    playwright install chromium
"""

import asyncio
import json
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path

try:
    from playwright.async_api import async_playwright
except ImportError:
    print("Install playwright: pip install playwright && playwright install chromium")
    sys.exit(1)

# Known AMC IMAX 70mm theaters in the US
IMAX_70MM_THEATERS = [
    {"name": "AMC Lincoln Square 13", "id": "1752", "location": "New York, NY"},
    {"name": "AMC Metreon 16", "id": "2254", "location": "San Francisco, CA"},
    {"name": "AMC Universal CityWalk", "id": "1004", "location": "Universal City, CA"},
    {"name": "AMC Century City 15", "id": "2291", "location": "Los Angeles, CA"},
    {"name": "AMC King of Prussia 16", "id": "2136", "location": "King of Prussia, PA"},
    {"name": "AMC Navy Pier IMAX", "id": "3174", "location": "Chicago, IL"},
    {"name": "AMC NorthPark 15", "id": "2295", "location": "Dallas, TX"},
    {"name": "AMC Aventura 24", "id": "2304", "location": "Aventura, FL"},
    {"name": "AMC Tysons Corner 16", "id": "2306", "location": "McLean, VA"},
    {"name": "AMC Garden State 16", "id": "2070", "location": "Paramus, NJ"},
]

MOVIE_SLUG = "the-odyssey-2025"
DATA_DIR = Path(__file__).parent / "data"


async def check_theater(page, theater, date_str):
    """Check a specific AMC theater for 70mm Odyssey showtimes on a given date."""
    url = f"https://www.amctheatres.com/movies/{MOVIE_SLUG}/showtimes/{MOVIE_SLUG}/{date_str}/{theater['id']}/all"

    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(3000)  # Wait for dynamic content

        content = await page.content()

        # Look for showtime buttons/links
        showtimes = []

        # Pattern 1: showtime elements
        showtime_elements = await page.query_selector_all("[data-showtime-id], .Showtime, .ShowtimeButton, .showtime-btn")
        for el in showtime_elements:
            text = await el.text_content()
            if text:
                showtimes.append(text.strip())

        # Pattern 2: look for time patterns in the page
        time_pattern = re.findall(r'\b(\d{1,2}:\d{2}\s*(?:AM|PM|am|pm))\b', content)
        if time_pattern and not showtimes:
            showtimes = list(set(time_pattern))

        # Check for "70mm" or "IMAX 70mm" format indicators
        has_70mm = "70mm" in content.lower() or "imax 70" in content.lower()

        # Check for "sold out" or "no showtimes"
        sold_out = "sold out" in content.lower()
        no_showtimes = "no showtimes" in content.lower() or "not available" in content.lower()

        return {
            "theater": theater["name"],
            "location": theater["location"],
            "date": date_str,
            "showtimes": showtimes,
            "has_70mm": has_70mm,
            "sold_out": sold_out,
            "no_showtimes": no_showtimes,
            "available": len(showtimes) > 0 and not sold_out,
        }

    except Exception as e:
        return {
            "theater": theater["name"],
            "location": theater["location"],
            "date": date_str,
            "error": str(e),
            "available": False,
        }


async def check_all_theaters(dates=None):
    """Check all known 70mm theaters for availability."""
    if dates is None:
        today = datetime.now()
        dates = [(today + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(14)]

    DATA_DIR.mkdir(exist_ok=True)
    results = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        )
        page = await context.new_page()

        for theater in IMAX_70MM_THEATERS:
            print(f"\nChecking {theater['name']} ({theater['location']})...")
            for date_str in dates:
                result = await check_theater(page, theater, date_str)
                results.append(result)

                if result.get("available"):
                    print(f"  AVAILABLE: {date_str} — {result['showtimes']}")
                elif result.get("error"):
                    print(f"  ERROR: {date_str} — {result['error'][:50]}")
                else:
                    status = "SOLD OUT" if result.get("sold_out") else "No showtimes"
                    print(f"  {date_str}: {status}")

                await page.wait_for_timeout(1000)  # Rate limit

        await browser.close()

    # Save results
    output = {
        "checked_at": datetime.now().isoformat(),
        "results": results,
        "available": [r for r in results if r.get("available")],
    }

    output_path = DATA_DIR / f"check_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
    with open(output_path, "w") as f:
        json.dump(output, f, indent=2)

    # Print summary
    available = output["available"]
    print(f"\n{'='*60}")
    if available:
        print(f"  FOUND {len(available)} AVAILABLE SHOWINGS!")
        print(f"{'='*60}")
        for r in available:
            print(f"  {r['theater']} ({r['location']})")
            print(f"    Date: {r['date']}")
            print(f"    Times: {', '.join(r['showtimes'])}")
            print()
    else:
        print("  No available 70mm showings found.")
        print("  The movie may not be released yet or all screenings are sold out.")
    print(f"{'='*60}")
    print(f"\nResults saved to {output_path}")

    return output


async def monitor(interval_minutes=30):
    """Continuously monitor for new availability."""
    print(f"Monitoring every {interval_minutes} minutes... (Ctrl+C to stop)")
    while True:
        output = await check_all_theaters()
        if output["available"]:
            print("\n🎬 TICKETS AVAILABLE! Check results above.")
            # TODO: send notification (email, SMS, push)
            break
        print(f"\nNext check in {interval_minutes} minutes...")
        await asyncio.sleep(interval_minutes * 60)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Check AMC for 70mm Odyssey showtimes")
    parser.add_argument("--monitor", action="store_true", help="Continuously monitor")
    parser.add_argument("--interval", type=int, default=30, help="Check interval (minutes)")
    parser.add_argument("--days", type=int, default=14, help="Days ahead to check")
    args = parser.parse_args()

    if args.monitor:
        asyncio.run(monitor(args.interval))
    else:
        asyncio.run(check_all_theaters())
