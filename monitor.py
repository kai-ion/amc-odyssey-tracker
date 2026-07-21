#!/usr/bin/env python3
"""
Odyssey 70mm ticket-drop monitor.

Polls the 3 IMAX-70mm AMC theatres, diffs against the last-seen state, and
alerts when something *new* appears:

  * new date drops   — AMC extends the schedule past the current frontier
  * new showtimes    — a new 70mm showing on an already-released date
  * reopened seats   — a sold-out / past-sell-date showtime becomes buyable
                       again (someone forfeited / refunded a ticket)

Designed to run on a cron (GitHub Actions). State lives in
data/monitor_state.json so each run only alerts on genuine changes.

Testability — every layer is exercisable locally:
  python monitor.py --dry-run          # scan + print what it found, no email, no state write
  python monitor.py --reset --dry-run  # treat everything as new (forces a full alert preview)
  python monitor.py --test-email       # send a dummy alert to verify email delivery
  python monitor.py --after 2026-08-13 # only alert on dates on/after 8/13
  python monitor.py                    # real run: scan, diff, email, persist state
"""

import argparse
import json
import os
import smtplib
import sys
import time
from datetime import datetime, timedelta, timezone
from email.mime.text import MIMEText
from pathlib import Path
from zoneinfo import ZoneInfo

from amc_graphql import get_showtimes, get_seat_count

DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)
STATE_FILE = DATA_DIR / "monitor_state.json"

MOVIE_SLUG = "the-odyssey-76238"
FORMATS = {"imax70mm", "70mm"}

# The only 3 AMC theatres with true IMAX 70mm film projectors.
THEATERS = [
    {"id": "amc-lincoln-square-13", "name": "AMC Lincoln Square 13", "tz": "America/New_York"},
    {"id": "amc-metreon-16", "name": "AMC Metreon 16 & IMAX", "tz": "America/Los_Angeles"},
    {"id": "amc-universal-citywalk-19", "name": "Universal Cinema AMC at CityWalk", "tz": "America/Los_Angeles"},
]

# How far ahead to probe, and how many consecutive empty days past the last
# showing before we stop scanning that theatre (the schedule window is
# contiguous, so a run of empties means we've passed the frontier).
MAX_DAYS_AHEAD = 75
EMPTY_STREAK_STOP = 4


def today_utc():
    """Today's date in UTC (cron runs in UTC; theatre-local is close enough for a date range)."""
    return datetime.now(timezone.utc).date()


def fmt_local(utc_str, tz_name):
    """UTC ISO string -> theatre-local 'Tue Aug 13, 7:00 PM'."""
    if not utc_str:
        return "?"
    try:
        dt = datetime.fromisoformat(utc_str.replace("Z", "+00:00")).astimezone(ZoneInfo(tz_name))
        return dt.strftime("%a %b %-d, %-I:%M %p")
    except Exception:
        return utc_str


def scan(after_date=None):
    """
    Probe all theatres forward from today and return a flat state dict:
        { showtimeId: {theater, theaterId, tz, date, datetimeUtc, format, status, available} }

    Stops scanning a theatre after EMPTY_STREAK_STOP consecutive empty days.
    after_date (date) optionally skips dates before it entirely.
    """
    start = today_utc()
    state = {}
    for th in THEATERS:
        empty_streak = 0
        for offset in range(MAX_DAYS_AHEAD):
            d = start + timedelta(days=offset)
            if after_date and d < after_date:
                continue
            date_str = d.isoformat()
            try:
                shows = get_showtimes(th["id"], date_str, movie_slug=MOVIE_SLUG, formats=FORMATS)
            except Exception as e:
                print(f"  ! {th['name']} {date_str}: fetch error {str(e)[:50]}")
                shows = []
                # don't count an error as an empty day
                time.sleep(1.0)
                continue

            if shows:
                empty_streak = 0
                for s in shows:
                    sid = str(s["showtimeId"])
                    is_imax70 = "imax70mm" in s["attributeCodes"]
                    state[sid] = {
                        "theater": th["name"],
                        "theaterId": th["id"],
                        "tz": th["tz"],
                        "date": date_str,
                        "datetimeUtc": s["datetimeUtc"],
                        "format": "IMAX 70mm" if is_imax70 else "70mm",
                        "status": s["status"],
                        "available": s["available"],
                    }
            else:
                empty_streak += 1
                if empty_streak >= EMPTY_STREAK_STOP:
                    break
            time.sleep(0.4)  # be gentle with AMC
    return state


def diff(old_showtimes, new_showtimes, after_date=None):
    """
    Compare old vs new state and return a list of alert events.

    Event kinds:
      new_date     — a date with no prior showtimes now has 70mm showings
      new_showtime — a new showtime on an already-known date
      reopened     — a known showtime went from not-buyable -> buyable
    """
    events = []

    old_dates = {(v["theaterId"], v["date"]) for v in old_showtimes.values()}
    new_by_date = {}  # (theaterId, date) -> list of showtime dicts
    for sid, v in new_showtimes.items():
        new_by_date.setdefault((v["theaterId"], v["date"]), []).append((sid, v))

    def passes_after(date_str):
        if not after_date:
            return True
        return datetime.fromisoformat(date_str).date() >= after_date

    for (tid, date_str), shows in new_by_date.items():
        if not passes_after(date_str):
            continue
        if (tid, date_str) not in old_dates:
            # brand-new date — summarize as one event, not one per showtime
            avail = [s for _, s in shows if s["available"]]
            events.append({
                "kind": "new_date",
                "theater": shows[0][1]["theater"],
                "theaterId": tid,
                "date": date_str,
                "count": len(shows),
                "availCount": len(avail),
                "showtimeIds": [sid for sid, _ in shows if _["available"]],
            })
        else:
            # known date — look for new showtimes and reopened ones
            for sid, v in shows:
                if not passes_after(v["date"]):
                    continue
                if sid not in old_showtimes:
                    if v["available"]:
                        events.append({"kind": "new_showtime", **_evt(sid, v)})
                else:
                    was = old_showtimes[sid]
                    if v["available"] and not was.get("available"):
                        events.append({"kind": "reopened", "wasStatus": was.get("status"), **_evt(sid, v)})
    return events


def _evt(sid, v):
    return {
        "theater": v["theater"], "theaterId": v["theaterId"], "date": v["date"],
        "datetimeUtc": v["datetimeUtc"], "tz": v["tz"], "format": v["format"],
        "status": v["status"], "showtimeId": sid,
    }


def enrich_seats(events):
    """Fetch seat counts only for the (few) showtimes in an alert — keeps calls low.

    The seat endpoint rate-limits at ~1 call / several seconds, so space calls
    out (~5s). get_seat_count itself retries with backoff on a 429. Alerts have
    few showtimes, so total added latency stays modest.
    """
    SEAT_CALL_GAP = 5.0
    for e in events:
        if e["kind"] == "new_date":
            # count seats across the first couple of available showtimes
            counts = []
            for sid in e.get("showtimeIds", [])[:2]:
                avail, total = get_seat_count(sid)
                if avail is not None:
                    counts.append((avail, total))
                time.sleep(SEAT_CALL_GAP)
            if counts:
                e["seatSummary"] = ", ".join(f"{a}/{t}" for a, t in counts)
        elif e.get("showtimeId"):
            avail, total = get_seat_count(e["showtimeId"])
            if avail is not None:
                e["seats"] = f"{avail}/{total}"
            time.sleep(SEAT_CALL_GAP)


def format_alert(events):
    """Build (subject, body) for an alert email."""
    n_dates = sum(1 for e in events if e["kind"] == "new_date")
    n_reopen = sum(1 for e in events if e["kind"] == "reopened")
    n_new = sum(1 for e in events if e["kind"] == "new_showtime")

    bits = []
    if n_dates:
        bits.append(f"{n_dates} new date{'s' if n_dates != 1 else ''}")
    if n_reopen:
        bits.append(f"{n_reopen} reopened")
    if n_new:
        bits.append(f"{n_new} new showtime{'s' if n_new != 1 else ''}")
    subject = "🎬 Odyssey 70mm: " + ", ".join(bits)

    lines = ["New Odyssey IMAX 70mm availability:\n"]
    for e in events:
        if e["kind"] == "new_date":
            seats = f"  (seats: {e['seatSummary']})" if e.get("seatSummary") else ""
            lines.append(f"• NEW DATE — {e['theater']} on {e['date']}: "
                         f"{e['availCount']}/{e['count']} showtimes available{seats}")
        elif e["kind"] == "reopened":
            seats = f"  ({e['seats']} seats)" if e.get("seats") else ""
            lines.append(f"• REOPENED — {e['theater']}, {fmt_local(e['datetimeUtc'], e['tz'])} "
                         f"[{e['format']}] was {e['wasStatus']}{seats}")
        elif e["kind"] == "new_showtime":
            seats = f"  ({e['seats']} seats)" if e.get("seats") else ""
            lines.append(f"• NEW SHOWTIME — {e['theater']}, {fmt_local(e['datetimeUtc'], e['tz'])} "
                         f"[{e['format']}]{seats}")

    # Booking links (one per theater involved)
    theaters = {(e["theaterId"], e.get("date")) for e in events}
    lines.append("\nBook:")
    for tid, date in sorted(theaters):
        lines.append(f"  https://www.amctheatres.com/movies/{MOVIE_SLUG}/showtimes/all/{date}/{tid}/all")

    return subject, "\n".join(lines)


def send_email(subject, body, dry_run=False):
    """Send via Gmail SMTP (app password). Prints instead if creds absent or dry-run."""
    user = os.environ.get("GMAIL_USER")
    pw = os.environ.get("GMAIL_APP_PASSWORD")
    to = os.environ.get("ALERT_TO", user)

    if dry_run or not (user and pw):
        reason = "dry-run" if dry_run else "no GMAIL_USER/GMAIL_APP_PASSWORD"
        print(f"\n=== EMAIL NOT SENT ({reason}) — preview ===")
        print(f"To: {to or '(unset)'}\nSubject: {subject}\n\n{body}\n=== end preview ===")
        return False
    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = user
    msg["To"] = to
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as s:
        s.login(user, pw)
        s.send_message(msg)
    print(f"Email sent to {to}")
    return True


def load_state():
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except Exception:
            pass
    return {"showtimes": {}, "last_run": None}


def save_state(showtimes):
    STATE_FILE.write_text(json.dumps({
        "showtimes": showtimes,
        "last_run": datetime.now(timezone.utc).isoformat(),
    }, indent=2))


def main():
    ap = argparse.ArgumentParser(description="Odyssey 70mm ticket-drop monitor")
    ap.add_argument("--dry-run", action="store_true", help="scan + diff + print, but don't email or write state")
    ap.add_argument("--reset", action="store_true", help="ignore saved state (treat everything found as new)")
    ap.add_argument("--test-email", action="store_true", help="send a dummy alert to verify email delivery, then exit")
    ap.add_argument("--after", metavar="YYYY-MM-DD", help="only alert on dates on/after this date")
    args = ap.parse_args()

    if args.test_email:
        subject, body = format_alert([{
            "kind": "new_date", "theater": "AMC Lincoln Square 13",
            "theaterId": "amc-lincoln-square-13", "date": "2026-08-13",
            "count": 4, "availCount": 4, "showtimeIds": [], "seatSummary": "TEST",
        }])
        sent = send_email("[TEST] " + subject, "This is a test alert.\n\n" + body, dry_run=args.dry_run)
        print("test-email:", "sent" if sent else "printed (no creds / dry-run)")
        return

    after_date = datetime.fromisoformat(args.after).date() if args.after else None

    print(f"=== Odyssey 70mm monitor — {datetime.now(timezone.utc).isoformat()} ===")
    if after_date:
        print(f"Alerting only on dates on/after {after_date}")

    old = {} if args.reset else load_state().get("showtimes", {})
    print(f"Prior state: {len(old)} known showtimes"
          + (" (ignored — --reset)" if args.reset else ""))

    new = scan(after_date=after_date)
    print(f"Scanned: {len(new)} showtimes across {len(THEATERS)} theatres")

    events = diff(old, new, after_date=after_date)
    print(f"Changes: {len(events)} event(s)")

    if events:
        enrich_seats(events)
        subject, body = format_alert(events)
        send_email(subject, body, dry_run=args.dry_run)
    else:
        print("No new availability.")

    if args.dry_run:
        print("\n(dry-run: state NOT saved)")
    else:
        save_state(new)
        print(f"State saved: {STATE_FILE}")


if __name__ == "__main__":
    main()
