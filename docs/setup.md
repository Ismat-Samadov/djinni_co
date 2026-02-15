# Setup Guide

## Requirements

- Python 3.10+
- pip

## Installation

```bash
pip install aiohttp beautifulsoup4 lxml tqdm python-dotenv
```

Or if a `requirements.txt` exists:

```bash
pip install -r requirements.txt
```

---

## Project structure

```
djinni_co/
├── data/
│   ├── djinni.csv                  # Output — scraped jobs
│   ├── djinni_scraper.log          # Scraper log file
│   ├── .djinni_checkpoint.json     # Resume checkpoint (auto-created)
│   └── cookies.txt                 # Optional: Netscape cookie file
├── docs/
│   ├── setup.md                    # This file
│   ├── scraper.md                  # Scraper architecture
│   └── data_dictionary.md          # CSV column reference
├── scripts/
│   └── djinni.py                   # Main scraper
├── .env                            # Local secrets (gitignored)
├── .env.example                    # Template — copy to .env
└── .gitignore
```

---

## Authentication (required)

Djinni blocks requests without a valid session cookie. You need to log in via
your browser and copy the `sessionid` cookie.

### Step-by-step

1. Open Chrome and go to `https://djinni.co` — make sure you are logged in
2. Open DevTools: **F12** (or right-click → Inspect)
3. Go to the **Application** tab
4. In the left sidebar: **Storage → Cookies → https://djinni.co**
5. Find the row where **Name** = `sessionid`
6. Copy the **Value** from that row

### Add to .env

Open `.env` (copy from `.env.example` if it doesn't exist):

```bash
cp .env.example .env
```

Edit `.env`:

```env
DJINNI_COOKIES="csrftoken=YOUR_CSRF_TOKEN; sessionid=YOUR_SESSION_ID_HERE"
```

Replace `YOUR_SESSION_ID_HERE` with the value you copied.

> The `sessionid` cookie expires in ~10 years (Django default), so you should
> only need to do this once unless you log out.

### Alternative: use a full cookie string

Instead of copying just `sessionid`, you can paste the entire `cookie:` header
from a Network tab request. This gives the scraper all cookies at once:

1. DevTools → **Network** tab
2. Reload the page
3. Click the first `djinni.co` document request (type: `document`)
4. Scroll to **Request Headers** → find the `cookie:` row
5. Copy the entire value and paste it into `.env`

---

## Running

```bash
python scripts/djinni.py
```

Expected output:

```
2026-02-15 22:50:01 [INFO]  Loaded 8 cookies from DJINNI_COOKIES env var
2026-02-15 22:50:01 [INFO]  Total pages: 640
2026-02-15 22:50:01 [INFO]  Page 1: saved 15 jobs
2026-02-15 22:50:01 [INFO]  Fetching 639 listing pages (saving immediately)…
Pages:   5%|▌         | 32/639 [00:18<05:29,  1.84page/s, saved=495]
```

The scraper finishes in ~7 minutes and writes ~9,600 rows to `data/djinni.csv`.

---

## Resuming after interruption

If the scraper is interrupted (Ctrl+C, crash, etc.) it saves a checkpoint to
`data/.djinni_checkpoint.json`. Simply re-run:

```bash
python scripts/djinni.py
```

It will skip already-scraped jobs and continue from where it left off.

To start completely fresh:

```bash
rm -f data/djinni.csv data/.djinni_checkpoint.json
python scripts/djinni.py
```

---

## Troubleshooting

### "IP BLOCKED" in logs

The scraper handles this automatically — it waits 30–45 seconds and retries.
If it keeps blocking, it means your IP is being rate-limited. Possible fixes:

- Make sure `sessionid` is in your `.env` (the most important fix)
- Reduce `CONCURRENCY` in `scripts/djinni.py` from `3` to `1`
- Wait a few minutes before retrying

### Columns are empty

Most columns (`english_level`, `work_format`, `views`, etc.) require the
detail-page scraping phase, which is currently disabled for speed. The listing-only
columns (`title`, `company`, `url`, `salary_*`, `category`, etc.) will be filled.

See [data_dictionary.md](data_dictionary.md) for per-column fill rates.

### ModuleNotFoundError

```bash
pip install aiohttp beautifulsoup4 lxml tqdm python-dotenv
```

### "command not found: rbenv" in stderr

This is a warning from your shell profile, not from the scraper. It can be ignored.
