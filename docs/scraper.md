# Djinni.co Scraper — Architecture & Usage

## Overview

`scripts/djinni.py` is an async Python scraper that collects all job listings from
[djinni.co/jobs](https://djinni.co/jobs/) and saves them to `data/djinni.csv`.

| Property | Value |
|---|---|
| Target | https://djinni.co/jobs/ |
| Output | `data/djinni.csv` |
| Language | Python 3.10+ |
| Concurrency | `asyncio` + `aiohttp` (3 parallel workers) |
| Total jobs | ~9,600 across ~640 pages |
| Runtime | ~7 minutes |

---

## Architecture

### Two-phase flow (current — listing-only mode)

```
Page 1  ──► parse JSON-LD ──► extract stubs ──► append to CSV immediately
Page 2  ──►      ...
  ...
Page 640──►      ...
```

Each listing page returns up to 15 job stubs via embedded `application/ld+json`
(Schema.org `JobPosting` objects). Stubs are written to CSV as soon as each page
completes — no buffering until the end.

### Key components

| Component | Location | Purpose |
|---|---|---|
| `load_cookies()` | line 62 | Load auth cookies from `.env` or `data/cookies.txt` |
| `fetch()` | line 184 | HTTP GET with retries, back-off, IP-block detection |
| `parse_listing_page()` | line 243 | Parse JSON-LD stubs + detect total page count |
| `fetch_and_save_page()` | line 570 | Fetch one page and immediately append rows to CSV |
| `main()` | line 528 | Orchestrates session, semaphore, progress bar |

### Resilience features

- **IP block detection** — any response under 500 bytes containing "blocked" triggers
  a 30–45 second wait and retry (up to 5 attempts)
- **HTTP 429 / 403 handling** — exponential back-off (`2^attempt + jitter` seconds)
- **Checkpoint** — `data/.djinni_checkpoint.json` tracks completed URLs and last page;
  resuming skips already-scraped jobs
- **Incremental CSV writes** — data is appended per page; a crash loses at most
  the current in-flight batch (≤3 pages = ≤45 rows)
- **SIGINT / SIGTERM handler** — graceful shutdown flushes buffer and saves checkpoint

---

## Configuration

All tunable constants are at the top of `scripts/djinni.py`:

| Constant | Default | Description |
|---|---|---|
| `CONCURRENCY` | `3` | Parallel HTTP workers (keep low to avoid blocks) |
| `MAX_RETRIES` | `5` | Retries per URL before giving up |
| `BACKOFF_BASE` | `2.0` | Seconds; doubles each retry |
| `REQUEST_TIMEOUT` | `25` | Per-request timeout in seconds |
| `MIN_DELAY` | `1.0` | Minimum sleep between requests per worker |
| `OUTPUT_PATH` | `data/djinni.csv` | CSV output path |
| `CHECKPOINT_PATH` | `data/.djinni_checkpoint.json` | Resume checkpoint |
| `COOKIES_FILE` | `data/cookies.txt` | Optional Netscape cookie file |

---

## Running

```bash
# First time
python scripts/djinni.py

# Resume after interruption (checkpoint is kept)
python scripts/djinni.py

# Force full re-scrape
rm -f data/djinni.csv data/.djinni_checkpoint.json
python scripts/djinni.py
```

---

## Cookie authentication

Djinni blocks unauthenticated scrapers after a few requests. You must provide a
valid `sessionid` cookie. See [setup.md](setup.md) for step-by-step instructions.

Cookie priority order:
1. `DJINNI_COOKIES` environment variable (highest)
2. `.env` file (loaded via `python-dotenv`)
3. `data/cookies.txt` (Netscape format)

---

## Logs

The scraper writes to both stdout and `data/djinni_scraper.log`:

```
2026-02-15 22:50:01 [INFO]  Loaded 8 cookies from DJINNI_COOKIES env var
2026-02-15 22:50:01 [INFO]  Total pages: 640
2026-02-15 22:50:01 [INFO]  Page 1: saved 15 jobs
2026-02-15 22:50:01 [INFO]  Fetching 639 listing pages (saving immediately)…
```

Warning signs to watch for:
- `IP BLOCKED` — scraper is being rate-limited; it retries automatically
- `Gave up on … after 5 attempts` — URL permanently unreachable; skipped
- `Empty response on listing page N` — page returned no data; skipped
