#!/usr/bin/env python3
"""
AMC GraphQL client — queries showtimes via graph.amctheatres.com.

Uses curl_cffi with Chrome TLS impersonation to bypass Cloudflare.
No auth key required — the endpoint is open for read queries.

The date is passed as a `Date!` variable on viewer.user.movies(theatreSlug, date).
Format filtering (IMAX 70mm) is done client-side on attribute codes.
"""

from curl_cffi import requests

GRAPH_URL = "https://graph.amctheatres.com"

HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json",
    "Origin": "https://www.amctheatres.com",
    "Referer": "https://www.amctheatres.com/",
}

SHOWTIMES_QUERY = """
query($s: String!, $d: Date!) {
  viewer { user { movies(theatreSlug: $s, date: $d) { items {
    theatres { theatre { name theatreId }
      formats { items { groups(first: 20) { edges { node {
        showtimes(first: 100) { edges { node {
          showtimeId
          showDateTimeUtc
          status
          movie { movieId name slug }
          attributes(first: 16) { edges { node { code name } } }
        } } }
      } } } } }
    }
  } } } }
}
"""

# Attribute codes for premium formats
FORMAT_CODES = {
    "imax70mm": "IMAX 70mm",
    "70mm": "70mm",
    "imax": "IMAX",
    "dolbycinemaatamcprime": "Dolby Cinema",
    "laseratamc": "IMAX with Laser",
}

# Statuses that mean tickets can be bought
AVAILABLE_STATUSES = {"Sellable", "AlmostFull", "Available"}


def get_showtimes(theatre_slug, date_str, movie_slug=None, formats=None):
    """
    Fetch showtimes for a theatre on a date.

    Args:
        theatre_slug: e.g. "amc-lincoln-square-13"
        date_str: ISO date "YYYY-MM-DD"
        movie_slug: optional filter, e.g. "the-odyssey-76238"
        formats: optional set of format codes to filter, e.g. {"imax70mm"}

    Returns list of showtime dicts.
    """
    variables = {"s": theatre_slug, "d": date_str}
    resp = requests.post(
        GRAPH_URL,
        json={"query": SHOWTIMES_QUERY, "variables": variables},
        headers=HEADERS,
        impersonate="chrome",
        timeout=20,
    )
    data = resp.json()

    if "errors" in data:
        raise RuntimeError(f"GraphQL error: {data['errors'][:1]}")

    movies = (((data.get("data") or {}).get("viewer") or {}).get("user") or {}).get("movies") or {}
    items = movies.get("items") or []

    showtimes = []
    for movie_item in items:
        for th in movie_item.get("theatres", []):
            theatre_name = (th.get("theatre") or {}).get("name", "")
            fmt_items = (th.get("formats") or {}).get("items") or []
            for fmt in fmt_items:
                for group_edge in fmt.get("groups", {}).get("edges", []):
                    for st_edge in group_edge["node"].get("showtimes", {}).get("edges", []):
                        n = st_edge["node"]
                        movie = n.get("movie") or {}
                        codes = [e["node"]["code"] for e in n.get("attributes", {}).get("edges", [])]

                        # Filter by movie slug if provided
                        if movie_slug and movie_slug.split("-")[0] not in movie.get("slug", "").lower():
                            if "odyssey" not in movie.get("name", "").lower():
                                continue

                        # Filter by format if provided
                        if formats and not any(c in formats for c in codes):
                            continue

                        showtimes.append({
                            "theatre": theatre_name,
                            "movie": movie.get("name", ""),
                            "movieSlug": movie.get("slug", ""),
                            "showtimeId": n.get("showtimeId"),
                            "datetimeUtc": n.get("showDateTimeUtc"),
                            "status": n.get("status"),
                            "available": n.get("status") in AVAILABLE_STATUSES,
                            "formats": [FORMAT_CODES.get(c, c) for c in codes if c in FORMAT_CODES],
                            "attributeCodes": codes,
                        })

    return showtimes


SEAT_QUERY = """
query($sid: Int!) {
  viewer {
    showtime(id: $sid) {
      showtimeId
      status
      seatingLayout {
        seats { available shouldDisplay }
      }
    }
  }
}
"""


def get_seat_count(showtime_id):
    """
    Return (available_seats, total_seats) for a showtime, or (None, None) if
    unavailable/rate-limited. Only meaningful for reserved-seating showtimes.
    """
    try:
        resp = requests.post(
            GRAPH_URL,
            json={"query": SEAT_QUERY, "variables": {"sid": int(showtime_id)}},
            headers=HEADERS,
            impersonate="chrome",
            timeout=20,
        )
        if resp.status_code == 429:
            return None, None
        data = resp.json()
        st = ((data.get("data") or {}).get("viewer") or {}).get("showtime") or {}
        layout = st.get("seatingLayout") or {}
        seats = layout.get("seats") or []
        if not seats:
            return None, None
        available = sum(1 for s in seats if s.get("available"))
        total = sum(1 for s in seats if s.get("shouldDisplay"))
        return available, total
    except Exception:
        return None, None


def get_selectable_dates(movie_slug):
    """Get the list of dates that have any showings for a movie."""
    query = "{ viewer { selectableDates(movieSlug: \"%s\") { dates selected } } }" % movie_slug
    resp = requests.post(GRAPH_URL, json={"query": query}, headers=HEADERS, impersonate="chrome", timeout=15)
    data = resp.json()
    sd = (((data.get("data") or {}).get("viewer") or {}).get("selectableDates") or {})
    return sd.get("dates", [])


if __name__ == "__main__":
    import sys
    slug = sys.argv[1] if len(sys.argv) > 1 else "amc-lincoln-square-13"
    date = sys.argv[2] if len(sys.argv) > 2 else "2026-07-20"

    print(f"Showtimes for The Odyssey (IMAX 70mm) at {slug} on {date}:\n")
    shows = get_showtimes(slug, date, movie_slug="the-odyssey-76238", formats={"imax70mm"})
    for s in shows:
        avail = "AVAILABLE" if s["available"] else s["status"]
        print(f"  {s['datetimeUtc'][11:16]} UTC | {avail:12} | {', '.join(s['formats'])}")
    if not shows:
        print("  No IMAX 70mm showings found for this date.")
