#!/usr/bin/env python3
"""
Fandango showtime client — primary data source.

Uses Fandango's undocumented `napi` JSON API. No Cloudflare, no rate limits,
no auth. Returns showtimes with format labels (IMAX 70mm vs 70mm) already in
theater-local time.

Endpoint: /napi/theaterMovieShowtimes/<TMS_ID>?startDate=YYYY-MM-DD
"""

import requests

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "x-requested-with": "XMLHttpRequest",
    "Referer": "https://www.fandango.com/",
    "Accept": "application/json",
}

MOVIE_NAME_MATCH = "odyssey"


def get_showtimes(tms_id, date_str):
    """
    Fetch The Odyssey showtimes at a Fandango theater (TMS ID) for a date.

    Returns list of showtime dicts with format labels and availability.
    date_str: "YYYY-MM-DD"
    """
    url = f"https://www.fandango.com/napi/theaterMovieShowtimes/{tms_id}?startDate={date_str}&isdesktop=true"
    resp = requests.get(url, headers=HEADERS, timeout=20)
    resp.raise_for_status()
    vm = resp.json().get("viewModel", {})

    results = []
    for movie in vm.get("movies", []):
        if MOVIE_NAME_MATCH not in (movie.get("title") or "").lower():
            continue
        for variant in movie.get("variants", []):
            for group in variant.get("amenityGroups", []):
                amenities = [a.get("name", "") for a in group.get("amenities", [])]
                amenity_str = group.get("amenityString", "")

                is_imax70 = any("70MM" in a.upper() for a in amenities)
                is_70mm = is_imax70 or "70mm" in amenity_str.lower() or "70 mm" in amenity_str.lower()

                # Only care about 70mm formats
                if not is_70mm:
                    continue

                for s in group.get("showtimes", []):
                    stype = s.get("type", "")
                    expired = s.get("expired", False) or stype == "pastshowtime"
                    sold_out = stype == "soldout"
                    results.append({
                        "time": s.get("date", ""),  # e.g. "10:00a" (local)
                        "ticketingDate": s.get("ticketingDate", ""),
                        "format": "IMAX 70mm" if is_imax70 else "70mm",
                        "isImax70": is_imax70,
                        "available": not expired and not sold_out,
                        "soldOut": sold_out,
                        "expired": expired,
                        "hashCode": s.get("showtimeHashCode", ""),
                        "ticketUrl": s.get("ticketingJumpPageURL", ""),
                    })

    return results


def get_seat_count(hash_code):
    """
    Return (available, total) seats for a showtime via Fandango seat map.
    Returns (None, None) if unavailable.
    """
    if not hash_code:
        return None, None
    try:
        url = f"https://www.fandango.com/napi/seatMap/{hash_code}"
        resp = requests.get(url, headers=HEADERS, timeout=15)
        if resp.status_code != 200:
            return None, None
        data = resp.json()
        vm = data.get("viewModel", data)
        seats = []
        # Seat map structure: viewModel.seatMap.rows[].seats[] with status
        seat_map = vm.get("seatMap") or vm
        rows = seat_map.get("rows") or seat_map.get("seatRows") or []
        for row in rows:
            for seat in row.get("seats", []):
                seats.append(seat)
        if not seats:
            return None, None
        available = sum(1 for s in seats if s.get("status", "").lower() in ("available", "open") or s.get("available"))
        total = len(seats)
        return available, total
    except Exception:
        return None, None


if __name__ == "__main__":
    import sys
    tms = sys.argv[1] if len(sys.argv) > 1 else "AANEM"  # AMC Metreon 16
    date = sys.argv[2] if len(sys.argv) > 2 else "2026-07-20"
    shows = get_showtimes(tms, date)
    print(f"The Odyssey 70mm showtimes at {tms} on {date}:\n")
    for s in shows:
        status = "AVAILABLE" if s["available"] else ("SOLD OUT" if s["soldOut"] else "past")
        print(f"  {s['time']:8} | {s['format']:10} | {status}")
