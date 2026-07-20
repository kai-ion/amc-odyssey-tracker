# AMC Odyssey 70mm Tracker

Monitors AMC theaters for available IMAX 70mm screenings of "The Odyssey" (Christopher Nolan, 2025).

## Setup

```bash
pip install playwright
playwright install chromium
```

## Usage

```bash
# Check all known 70mm IMAX theaters (next 14 days)
python checker.py

# Monitor continuously (check every 30 min, alert when available)
python checker.py --monitor

# Check more days ahead
python checker.py --days 30

# Custom interval
python checker.py --monitor --interval 15
```

## How it works

1. Checks AMC's website for each known IMAX 70mm theater
2. Looks for available showtimes for "The Odyssey" in 70mm format
3. Reports which theaters have open seats and at what times
4. In monitor mode, loops until tickets are found

## Known IMAX 70mm AMC Theaters

| Theater | Location |
|---------|----------|
| AMC Lincoln Square 13 | New York, NY |
| AMC Metreon 16 | San Francisco, CA |
| AMC Universal CityWalk | Universal City, CA |
| AMC Century City 15 | Los Angeles, CA |
| AMC King of Prussia 16 | King of Prussia, PA |
| AMC Navy Pier IMAX | Chicago, IL |
| AMC NorthPark 15 | Dallas, TX |
| AMC Aventura 24 | Aventura, FL |
| AMC Tysons Corner 16 | McLean, VA |
| AMC Garden State 16 | Paramus, NJ |

## Output

Results saved to `data/check_YYYYMMDD_HHMM.json` with:
- Available theaters + dates + showtimes
- Sold-out status
- 70mm format confirmation
