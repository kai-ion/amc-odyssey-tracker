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

import time
from amc_graphql import get_showtimes as amc_get_showtimes, get_selectable_dates, get_seat_count
import fandango

app = Flask(__name__)
CORS(app)

DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)

MOVIE_SLUG = "the-odyssey-76238"

# Only these 3 AMC theaters have true IMAX 70mm film projectors (per r-imax/imaxguide).
# amcSlug -> AMC GraphQL fallback; fandangoTms -> Fandango primary source.
THEATERS = [
    {"id": "amc-lincoln-square-13", "name": "AMC Lincoln Square 13", "location": "New York, NY",
     "tz": "America/New_York", "fandangoTms": "AAEWU"},
    {"id": "amc-metreon-16", "name": "AMC Metreon 16 & IMAX", "location": "San Francisco, CA",
     "tz": "America/Los_Angeles", "fandangoTms": "AANEM"},
    {"id": "amc-universal-citywalk-19", "name": "Universal Cinema AMC at CityWalk", "location": "Universal City, CA",
     "tz": "America/Los_Angeles", "fandangoTms": "AAWKH"},
]
TZ_BY_ID = {t["id"]: t["tz"] for t in THEATERS}


def fetch_showtimes(theater, date_str):
    """
    Get 70mm showtimes for a theater on a date.
    Tries Fandango first (no Cloudflare/rate limits), falls back to AMC GraphQL.
    Returns (showtime_details list, source string).
    """
    # --- Primary: Fandango ---
    if theater.get("fandangoTms"):
        try:
            shows = fandango.get_showtimes(theater["fandangoTms"], date_str)
            if shows:
                details = []
                for s in shows:
                    if not s["available"]:
                        continue
                    details.append({
                        "time": normalize_ampm(s["time"]),
                        "format": s["format"],
                        "isImax70": s["isImax70"],
                        "seatsAvailable": None,
                        "seatsTotal": None,
                    })
                return details, "fandango"
        except Exception:
            pass

    # --- Fallback: AMC GraphQL ---
    try:
        shows = amc_get_showtimes(theater["id"], date_str, movie_slug=MOVIE_SLUG,
                                  formats={"imax70mm", "70mm"})
        available = [s for s in shows if s["available"]]
        details = []
        for s in available:
            is_imax70 = "imax70mm" in s["attributeCodes"]
            details.append({
                "time": fmt_time(s["datetimeUtc"], theater["tz"]),
                "format": "IMAX 70mm" if is_imax70 else "70mm",
                "isImax70": is_imax70,
                "seatsAvailable": None,
                "seatsTotal": None,
            })
        return details, "amc"
    except Exception as e:
        return None, f"error: {str(e)[:60]}"


def normalize_ampm(t):
    """Convert Fandango '10:00a'/'2:00p' to '10:00 AM'/'2:00 PM'."""
    t = t.strip()
    if t.endswith("a"):
        return t[:-1] + " AM"
    if t.endswith("p"):
        return t[:-1] + " PM"
    return t

# Both premium 70mm formats — IMAX 70mm (premium large format) and standard 70mm
FORMAT_FILTER = {"imax70mm", "70mm"}


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
        details, source = fetch_showtimes(theater, date)
        if details is None:
            results[theater["id"]] = {"available": False, "error": source}
            continue
        has_imax70 = any(d["isImax70"] for d in details)
        results[theater["id"]] = {
            "available": len(details) > 0,
            "showtimes": [d["time"] for d in details],
            "showtimeDetails": details,
            "hasImax70": has_imax70,
            "has70mm": True,
            "source": source,
        }

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
            t = theater_map[tid]
            details, source = fetch_showtimes(t, date)
            if details:
                return jsonify({
                    "found": True,
                    "theater": t["name"],
                    "location": t["location"],
                    "theaterId": tid,
                    "date": date,
                    "dateDisplay": datetime.fromisoformat(date).strftime("%A, %B %-d, %Y"),
                    "showtimes": [d["time"] for d in details],
                    "showtimeDetails": details,
                    "url": f"https://www.amctheatres.com/movies/{MOVIE_SLUG}/showtimes/all/{date}/{tid}/all",
                })
            time.sleep(0.2)

    return jsonify({"found": False, "message": "No available 70mm showings found at your selected theaters."})


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
