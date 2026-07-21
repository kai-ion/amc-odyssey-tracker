# Odyssey 70mm ticket-drop monitor

Watches the 3 IMAX-70mm AMC theatres (Lincoln Square, Metreon, CityWalk) and
emails you when **new** Odyssey 70mm inventory appears:

- **New date drops** — AMC extends the schedule past the current frontier
- **New showtimes** — a new 70mm showing on an already-released date
- **Reopened seats** — a sold-out / past-sell-date showtime becomes buyable
  again (someone forfeited or refunded a ticket)

It diffs against `data/monitor_state.json`, so you're only emailed about genuine
changes — never the same showtime twice.

## How to test it (do this before trusting the cron)

Everything is testable locally, no server needed:

```bash
# 1. Full scan + alert PREVIEW (treats everything as new, prints the email, sends nothing)
python monitor.py --reset --dry-run --after 2026-08-13

# 2. Verify email delivery end-to-end (needs the two env vars below)
GMAIL_USER=you@gmail.com GMAIL_APP_PASSWORD=xxxx python monitor.py --test-email

# 3. Idempotency check — run twice; the second run must report "0 events"
python monitor.py --after 2026-08-13     # cold: finds + saves state
python monitor.py --after 2026-08-13     # warm: 0 changes, no email
```

`--dry-run` never writes state or sends email. `--reset` ignores saved state.
`--after YYYY-MM-DD` only alerts on dates on/after that day.

## Email setup (Gmail app password — free)

The monitor sends via Gmail SMTP. Create an **app password** (not your real
password): Google Account → Security → 2-Step Verification → App passwords.

Locally, export:

```bash
export GMAIL_USER="you@gmail.com"
export GMAIL_APP_PASSWORD="16-char-app-password"
export ALERT_TO="you@gmail.com"   # optional; defaults to GMAIL_USER
```

If these aren't set, the monitor prints the alert instead of sending it — handy
for testing the scan without wiring up email.

## Running it free on GitHub Actions

1. Push this repo to GitHub (it has no remote yet):
   ```bash
   gh repo create amc-odyssey-tracker --private --source=. --push
   ```
2. Add the email secrets (Settings → Secrets and variables → Actions), or via CLI:
   ```bash
   gh secret set GMAIL_USER --body "you@gmail.com"
   gh secret set GMAIL_APP_PASSWORD --body "your-app-password"
   gh secret set ALERT_TO --body "you@gmail.com"
   ```
3. **Test the cron by hand** before waiting: Actions tab → "Odyssey 70mm monitor"
   → "Run workflow" → optionally tick **dry_run** to preview without emailing.
   The `workflow_dispatch` button runs the exact same job the cron does.

The workflow (`.github/workflows/monitor.yml`) runs every 10 min, commits the
updated `monitor_state.json` back to the repo, and is free on public repos (and
within the generous free minutes on private ones).

### Testing the *scheduled* path specifically

The cron and the manual button run identical steps, so a green
`workflow_dispatch` run means the schedule will work too. To force a real alert
on the first scheduled run, delete `data/monitor_state.json` in the repo — the
next run treats everything as new. (Or just wait for AMC to drop a new date.)
