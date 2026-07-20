#!/usr/bin/env python3
"""
Backend API for AMC Odyssey 70mm Tracker.

Uses the AMC GraphQL API (via curl_cffi Chrome impersonation) to fetch
real showtimes — no browser, no Cloudflare blocks.
"""

import json
from datetime import datetime, timedelta
from pathlib import Path
from flask import Flask, jsonify, request
from flask_cors import CORS

from amc_graphql import get_showtimes, get_selectable_dates

app = Flask(__name__)
CORS(app)

DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)

MOVIE_SLUG = "the-odyssey-76238"

# Theater slug + IANA timezone (to convert UTC showtimes to local)
THEATERS = [
    {"id": "amc-lincoln-square-13", "name": "AMC Lincoln Square 13", "location": "New York, NY", "tz": "America/New_York"},
    {"id": "amc-metreon-16", "name": "AMC Metreon 16", "location": "San Francisco, CA", "tz": "America/Los_Angeles"},
    {"id": "amc-universal-citywalk-19", "name": "AMC Universal CityWalk", "location": "Universal City, CA", "tz": "America/Los_Angeles"},
    {"id": "amc-century-city-15", "name": "AMC Century City 15", "location": "Los Angeles, CA", "tz": "America/Los_Angeles"},
    {"id": "amc-king-of-prussia-16", "name": "AMC King of Prussia 16", "location": "King of Prussia, PA", "tz": "America/New_York"},
    {"id": "amc-navy-pier-imax", "name": "AMC Navy Pier IMAX", "location": "Chicago, IL", "tz": "America/Chicago"},
    {"id": "amc-northpark-15", "name": "AMC NorthPark 15", "location": "Dallas, TX", "tz": "America/Chicago"},
    {"id": "amc-aventura-24", "name": "AMC Aventura 24", "location": "Aventura, FL", "tz": "America/New_York"},
    {"id": "amc-tysons-corner-16", "name": "AMC Tysons Corner 16", "location": "McLean, VA", "tz": "America/New_York"},
    {"id": "amc-garden-state-16", "name": "AMC Garden State 16", "location": "Paramus, NJ", "tz": "America/New_York"},
]
TZ_BY_ID = {t["id"]: t["tz"] for t in THEATERS}

FORMAT_FILTER = {"imax70mm"}  # Only true IMAX 70mm


@app.route("/theaters")
def list_theaters():
    return jsonify({"theaters": THEATERS})


@app.route("/check")
def check_availability():
    """Check all theaters for a given date."""
    date = request.args.get("date", datetime.now().strftime("%Y-%m-%d"))

    cache_file = DATA_DIR / f"cache_{date}.json"
    if cache_file.exists():
        age = datetime.now().timestamp() - cache_file.stat().st_mtime
        if age < 600:  # 10 min cache
            with open(cache_file) as f:
                return jsonify(json.load(f))

    results = {}
    for theater in THEATERS:
        try:
            shows = get_showtimes(theater["id"], date, movie_slug=MOVIE_SLUG, formats=FORMAT_FILTER)
            available = [s for s in shows if s["available"]]
            results[theater["id"]] = {
                "available": len(available) > 0,
                "showtimes": [fmt_time(s["datetimeUtc"], theater["tz"]) for s in available],
                "allShowtimes": len(shows),
                "soldOut": len(shows) > 0 and len(available) == 0,
                "has70mm": len(shows) > 0,
            }
        except Exception as e:
            results[theater["id"]] = {"available": False, "error": str(e)[:80]}

    output = {"date": date, "checked_at": datetime.now().isoformat(), "results": results}
    with open(cache_file, "w") as f:
        json.dump(output, f)
    return jsonify(output)


@app.route("/find-next")
def find_next():
    """Find the next date with available IMAX 70mm tickets at selected theaters."""
    theater_ids = [t for t in request.args.get("theaters", "").split(",") if t]
    if not theater_ids:
        theater_ids = [t["id"] for t in THEATERS]

    # Get dates that have any showings
    try:
        dates = get_selectable_dates(MOVIE_SLUG)
    except Exception:
        today = datetime.now()
        dates = [(today + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(30)]

    theater_map = {t["id"]: t for t in THEATERS}

    for date in dates:
        for tid in theater_ids:
            if tid not in theater_map:
                continue
            try:
                shows = get_showtimes(tid, date, movie_slug=MOVIE_SLUG, formats=FORMAT_FILTER)
                available = [s for s in shows if s["available"]]
                if available:
                    t = theater_map[tid]
                    return jsonify({
                        "found": True,
                        "theater": t["name"],
                        "location": t["location"],
                        "theaterId": tid,
                        "date": date,
                        "dateDisplay": datetime.fromisoformat(date).strftime("%A, %B %-d, %Y"),
                        "showtimes": [fmt_time(s["datetimeUtc"], t["tz"]) for s in available],
                        "url": f"https://www.amctheatres.com/movies/{MOVIE_SLUG}/showtimes/all/{date}/{tid}/all",
                    })
            except Exception:
                continue

    return jsonify({"found": False, "message": "No available IMAX 70mm showings found at your selected theaters."})


@app.route("/dates")
def dates():
    """Return dates that have showings for the movie."""
    try:
        return jsonify({"dates": get_selectable_dates(MOVIE_SLUG)})
    except Exception as e:
        return jsonify({"dates": [], "error": str(e)})


@app.route("/health")
def health():
    return jsonify({"status": "ok", "time": datetime.now().isoformat()})


def fmt_time(utc_str, tz_name="America/New_York"):
    """Convert a UTC datetime string to the theater's local time (e.g. '10:00 PM')."""
    if not utc_str:
        return "?"
    try:
        from zoneinfo import ZoneInfo
        dt = datetime.fromisoformat(utc_str.replace("Z", "+00:00"))
        local = dt.astimezone(ZoneInfo(tz_name))
        return local.strftime("%-I:%M %p")
    except Exception:
        return utc_str[11:16] if len(utc_str) > 16 else utc_str


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
