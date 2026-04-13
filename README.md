# Amazon Price Tracker

Automated Amazon price scraper with Telegram alerts and a Streamlit dashboard. Monitors product prices on a schedule, detects significant price changes, and notifies you instantly via Telegram.

Built with [Camoufox](https://github.com/nickoala/camoufox) — a stealthy browser automation library designed to minimize bot detection.

## Features

- **Scheduled scraping** — polls Amazon product pages every 30 minutes (configurable)
- **Price change alerts** — sends Telegram notifications when a price drops or rises beyond a configurable threshold (default 15%)
- **Streamlit dashboard** — visualize price history, trends, and alert logs
- **CSV price history** — every price point is logged with ASIN, URL, price, and timestamp
- **Test mode** — validate notification logic locally with `dummy_prices.csv`, no browser needed
- **Configurable** — threshold, poll interval, and Telegram credentials via `.env`

## Bot Detection Avoidance

Amazon actively blocks automated scrapers. This project uses several techniques to reduce detection:

- **Camoufox** — Firefox-based browser with randomized fingerprints
- **Human-like behavior** — random mouse movements, scrolling, and typing delays before extracting data
- **Search-first navigation** — products are found via Amazon's search bar instead of direct URL hits, mimicking real browsing patterns
- **Session warmup** — opens Amazon homepage and performs random searches before scraping to build a natural session history
- **Randomized timing** — random delays between pages and cycles to avoid predictable request patterns
- **Interstitial handling** — automatically clicks through "Continue shopping" prompts
- **Retry with backoff** — failed attempts back off with increasing delays (5s → 15s → 30s)
- **Failure screenshots** — saves full-page screenshots and error logs when all retries fail for debugging

> **Note:** No anti-bot technique is foolproof. Amazon may still serve CAPTCHAs or block requests. The scraper detects these cases and skips gracefully, retrying on the next cycle.


## Usage

run realtime dashboard

```bash
    uv run streamlit run dashboard.py
```

run scraping
```bash
    uv run scraper.py
```

run scraping in test mode to test telegram notifications
```bash
    uv run scraper.py --test
```
