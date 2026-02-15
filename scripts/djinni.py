"""
Djinni.co async job scraper
────────────────────────────────────────────────────────────────────
Features
  • asyncio + aiohttp — concurrent fetching (configurable concurrency)
  • Two-pass scrape: listing pages → detail pages
  • Rich field extraction: JSON-LD + HTML fallback on detail pages
  • Crash-proof: incremental CSV append, JSON checkpoint, SIGINT/SIGTERM
  • Automatic retries with exponential back-off + jitter
  • Resumable: skips already-scraped job URLs on restart
  • Rate-limited via asyncio.Semaphore
  • Progress bar via tqdm
"""

from __future__ import annotations

import asyncio
import csv
import json
import logging
import os
import random
import re
import signal
import sys
import time
from pathlib import Path
from typing import Any

import aiohttp
from bs4 import BeautifulSoup
from tqdm.asyncio import tqdm

# ── Config ────────────────────────────────────────────────────────────────────
BASE_URL        = "https://djinni.co"
JOBS_URL        = f"{BASE_URL}/jobs/"
CONCURRENCY     = 3          # parallel HTTP requests (low to avoid IP block)
MAX_RETRIES     = 5          # retries per URL
BACKOFF_BASE    = 2.0        # seconds (doubles each retry + jitter)
REQUEST_TIMEOUT = 25         # seconds per request
MIN_DELAY       = 1.0        # seconds between requests per worker
OUTPUT_PATH     = Path(__file__).parent.parent / "data" / "djinni.csv"
CHECKPOINT_PATH = Path(__file__).parent.parent / "data" / ".djinni_checkpoint.json"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Referer": "https://djinni.co/",
}

# All CSV columns
CSV_FIELDS = [
    # ── from listing page (JSON-LD) ──────────────────────────────────────
    "title",
    "company",
    "url",
    "salary_min",
    "salary_max",
    "salary_currency",
    "job_type",           # FULL_TIME / PART_TIME / CONTRACTOR …
    "category",           # e.g. Python, React.js
    "date_posted",
    "location_type",      # TELECOMMUTE / INPERSON
    "location_regions",   # e.g. Ukraine, Worldwide
    "experience_months",
    # ── from detail page (HTML) ──────────────────────────────────────────
    "english_level",      # e.g. Upper Intermediate
    "experience_years",   # e.g. 3 years
    "work_format",        # Remote / Office / Hybrid
    "city",
    "country",
    "domain",             # e.g. FinTech, Healthcare
    "company_type",       # e.g. Product / Outsource / Startup
    "company_size",       # e.g. 51-200
    "views",
    "applications",
    "skills",             # comma-separated tags
    "description",        # full plain-text description
]

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(
            Path(__file__).parent.parent / "data" / "djinni_scraper.log",
            encoding="utf-8",
        ),
    ],
)
log = logging.getLogger(__name__)

# ── Checkpoint helpers ────────────────────────────────────────────────────────

def load_checkpoint() -> dict:
    if CHECKPOINT_PATH.exists():
        try:
            return json.loads(CHECKPOINT_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"done_urls": [], "last_page": 0}


def save_checkpoint(done_urls: set[str], last_page: int) -> None:
    CHECKPOINT_PATH.parent.mkdir(parents=True, exist_ok=True)
    CHECKPOINT_PATH.write_text(
        json.dumps({"done_urls": list(done_urls), "last_page": last_page}, ensure_ascii=False),
        encoding="utf-8",
    )


# ── CSV helpers ───────────────────────────────────────────────────────────────

def init_csv() -> None:
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not OUTPUT_PATH.exists():
        with open(OUTPUT_PATH, "w", newline="", encoding="utf-8") as f:
            csv.DictWriter(f, fieldnames=CSV_FIELDS).writeheader()


def append_rows(rows: list[dict]) -> None:
    if not rows:
        return
    with open(OUTPUT_PATH, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=CSV_FIELDS, extrasaction="ignore")
        w.writerows(rows)


# ── HTTP helpers ──────────────────────────────────────────────────────────────

async def fetch(
    session: aiohttp.ClientSession,
    url: str,
    sem: asyncio.Semaphore,
    *,
    retries: int = MAX_RETRIES,
) -> str | None:
    """Fetch URL with retries, back-off, and semaphore-based rate limiting."""
    async with sem:
        for attempt in range(1, retries + 1):
            try:
                await asyncio.sleep(MIN_DELAY + random.uniform(0, 0.5))
                async with session.get(
                    url,
                    headers=HEADERS,
                    timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT),
                    allow_redirects=True,
                ) as resp:
                    if resp.status == 429:
                        wait = BACKOFF_BASE ** attempt + random.uniform(2, 5)
                        log.warning("429 rate-limit on %s — waiting %.1fs", url, wait)
                        await asyncio.sleep(wait)
                        continue
                    if resp.status == 403:
                        wait = BACKOFF_BASE ** attempt + random.uniform(2, 5)
                        log.warning("403 on %s — waiting %.1fs", url, wait)
                        await asyncio.sleep(wait)
                        continue
                    if resp.status == 404:
                        return None
                    resp.raise_for_status()
                    text = await resp.text(encoding="utf-8", errors="replace")
                    # Detect IP block page (short response with "blocked" message)
                    if len(text) < 500 and "blocked" in text.lower():
                        wait = 30 + random.uniform(5, 15)
                        log.warning("IP BLOCKED on %s — waiting %.0fs before retry", url, wait)
                        await asyncio.sleep(wait)
                        continue
                    return text
            except (aiohttp.ClientError, asyncio.TimeoutError) as exc:
                wait = BACKOFF_BASE ** attempt + random.uniform(0, 2)
                log.warning(
                    "Attempt %d/%d failed for %s (%s) — retrying in %.1fs",
                    attempt, retries, url, exc, wait,
                )
                await asyncio.sleep(wait)
        log.error("Gave up on %s after %d attempts", url, retries)
        return None


# ── Listing page parser ───────────────────────────────────────────────────────

def _safe_int(v: Any) -> str:
    try:
        return str(int(v))
    except (TypeError, ValueError):
        return str(v) if v else ""


def parse_listing_page(html: str) -> tuple[list[dict], int]:
    """
    Returns (list_of_job_stubs, total_pages).
    Stubs contain all fields extractable from JSON-LD on the listing page.
    """
    soup = BeautifulSoup(html, "lxml")
    jobs: list[dict] = []

    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or "")
        except (json.JSONDecodeError, TypeError):
            continue

        postings: list[dict] = []
        if isinstance(data, dict):
            if data.get("@type") == "ItemList":
                for item in data.get("itemListElement", []):
                    p = item if item.get("@type") == "JobPosting" else item.get("item", {})
                    if p.get("@type") == "JobPosting":
                        postings.append(p)
            elif data.get("@type") == "JobPosting":
                postings.append(data)
        elif isinstance(data, list):
            postings = [d for d in data if isinstance(d, dict) and d.get("@type") == "JobPosting"]

        for p in postings:
            salary      = p.get("baseSalary", {}) or {}
            sal_val     = salary.get("value", {}) or {}
            org         = p.get("hiringOrganization", {}) or {}
            exp         = p.get("experienceRequirements", {}) or {}
            al          = p.get("applicantLocationRequirements", []) or []
            if isinstance(al, dict):
                al = [al]
            regions = ", ".join(x.get("name", "") for x in al if isinstance(x, dict) and x.get("name"))

            jobs.append({
                "title":            p.get("title", ""),
                "company":          org.get("name", "") if isinstance(org, dict) else "",
                "url":              p.get("url", ""),
                "salary_min":       _safe_int(sal_val.get("minValue", "")),
                "salary_max":       _safe_int(sal_val.get("maxValue", "")),
                "salary_currency":  salary.get("currency", "") if sal_val else "",
                "job_type":         p.get("employmentType", ""),
                "category":         p.get("category", ""),
                "date_posted":      p.get("datePosted", ""),
                "location_type":    p.get("jobLocationType", ""),
                "location_regions": regions,
                "experience_months": _safe_int(exp.get("monthsOfExperience", "")) if isinstance(exp, dict) else "",
                # detail fields filled later
                "english_level": "", "experience_years": "", "work_format": "",
                "city": "", "country": "", "domain": "", "company_type": "",
                "company_size": "", "views": "", "applications": "",
                "skills": "", "description": "",
            })

    # Pagination: find max page number in pagination links
    total_pages = 1
    for a in soup.select("ul.pagination li a[href*='page=']"):
        href = a.get("href", "")
        m = re.search(r"page=(\d+)", href)
        if m:
            total_pages = max(total_pages, int(m.group(1)))

    # Fallback: parse total count from heading
    if total_pages == 1:
        h = soup.find(string=re.compile(r"\d[\d\s,]+jobs?", re.I))
        if h:
            m = re.search(r"([\d\s,]+)", h)
            if m:
                n = int(m.group(1).replace(" ", "").replace(",", ""))
                total_pages = max(1, (n + 14) // 15)

    return jobs, total_pages


# ── Detail page parser ────────────────────────────────────────────────────────

def _text(el) -> str:
    return el.get_text(" ", strip=True) if el else ""


def parse_detail_page(html: str, stub: dict) -> dict:
    """
    Enrich a job stub with fields scraped from the detail page.
    Djinni renders most meta as bare <span> tags with no CSS classes,
    so we rely on full body-text regex + JSON-LD.
    Returns None if the page is an IP-block response.
    """
    # Detect IP block / empty page
    if len(html) < 500 and ("blocked" in html.lower() or "contact us" in html.lower()):
        return None

    soup = BeautifulSoup(html, "lxml")
    job  = dict(stub)  # copy

    # ── JSON-LD ───────────────────────────────────────────────────────────
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or "")
        except (json.JSONDecodeError, TypeError):
            continue
        if not isinstance(data, dict) or data.get("@type") != "JobPosting":
            continue

        # City & country from jobLocation
        jp_loc = data.get("jobLocation", {}) or {}
        addr   = jp_loc.get("address", {}) or {}
        if isinstance(addr, dict):
            loc = addr.get("addressLocality", "")
            job["city"]    = job["city"]    or (loc[0] if isinstance(loc, list) else loc)
            job["country"] = job["country"] or addr.get("addressCountry", "")

        # Domain / industry — JSON-LD has explicit 'industry' key on detail pages
        job["domain"] = job["domain"] or data.get("industry", "")

        # Location regions from applicantLocationRequirements
        if not job["location_regions"]:
            alr = data.get("applicantLocationRequirements", [])
            if isinstance(alr, dict):
                alr = [alr]
            regions: list[str] = []
            for a in (alr or []):
                if isinstance(a, dict):
                    name = a.get("name", "")
                    inner_addr = a.get("address", {}) or {}
                    country = inner_addr.get("addressCountry", "") if isinstance(inner_addr, dict) else ""
                    regions.append(name or country)
            job["location_regions"] = ", ".join(r for r in regions if r)

        # Full description
        if not job["description"]:
            raw_desc = data.get("description", "")
            if raw_desc:
                desc_soup = BeautifulSoup(raw_desc, "lxml")
                job["description"] = desc_soup.get_text(" ", strip=True)[:2000]

    # ── Full body text — all detail fields are bare <span> with no classes ─
    body_text = soup.get_text(" ", strip=True)

    # Views
    m = re.search(r"(\d+)\s*views?", body_text, re.I)
    if m:
        job["views"] = job["views"] or m.group(1)

    # Applications
    m = re.search(r"(\d+)\s*application", body_text, re.I)
    if m:
        job["applications"] = job["applications"] or m.group(1)

    # English level — ordered most-specific first
    for pat, val in [
        (r"upper[\s\-]?intermediate",  "Upper Intermediate"),
        (r"lower[\s\-]?intermediate",  "Lower Intermediate"),
        (r"no\s+english",              "No English"),
        (r"c2",                        "C2 Proficient"),
        (r"c1",                        "C1 Advanced"),
        (r"b2",                        "B2 Upper Intermediate"),
        (r"b1",                        "B1 Intermediate"),
        (r"advanced",                  "Advanced"),
        (r"fluent",                    "Fluent"),
        (r"intermediate",              "Intermediate"),
    ]:
        if re.search(pat, body_text, re.I):
            job["english_level"] = job["english_level"] or val
            break

    # Work format
    for pat, val in [
        (r"hybrid",       "Hybrid"),
        (r"office\s+work","Office"),
        (r"\boffice\b",   "Office"),
        (r"remote\s+work","Remote"),
        (r"\bremote\b",   "Remote"),
    ]:
        if re.search(pat, body_text, re.I):
            job["work_format"] = job["work_format"] or val
            break

    # Experience years (e.g. "5 years", "3+ years")
    m = re.search(r"(\d+)\+?\s*years?\s+of\s+exp|(\d+)\+?\s*years?\s+exp|(\d+)\s+years?\b", body_text, re.I)
    if m:
        yrs = next(g for g in m.groups() if g)
        job["experience_years"] = job["experience_years"] or yrs + " years"

    # Company type
    for pat, val in [
        (r"product\s+company", "Product"),
        (r"outsource",         "Outsource"),
        (r"outstaf",           "Outstaff"),
        (r"startup",           "Startup"),
        (r"agency",            "Agency"),
    ]:
        if re.search(pat, body_text, re.I):
            job["company_type"] = job["company_type"] or val
            break

    # Company size (e.g. "51-200 employees", "200+ people")
    m = re.search(r"(\d+[\+\-–]\d*)\s*(people|employees|specialists|engineers)?", body_text, re.I)
    if m:
        job["company_size"] = job["company_size"] or m.group(1).strip()

    # Skills — Djinni links keywords in job descriptions / tag lists
    if not job["skills"]:
        skill_els = soup.select(
            "a[href*='primary_keyword='], "
            "a[href*='?keyword='], "
            "a[href*='/jobs/?page=1&keywords=']"
        )
        if skill_els:
            job["skills"] = ", ".join(
                dict.fromkeys(el.get_text(strip=True) for el in skill_els if el.get_text(strip=True))
            )

    # Description fallback — look for the main content div
    if not job["description"]:
        for sel in [
            "div[data-original-text]",
            ".job-description__text",
            ".job-description",
            "#job-description",
            "section.col-xs-12",
        ]:
            el = soup.select_one(sel)
            if el:
                job["description"] = el.get_text(" ", strip=True)[:2000]
                break

    # Title fallback
    if not job["title"]:
        h1 = soup.find("h1")
        if h1:
            job["title"] = _text(h1)

    # Company fallback
    if not job["company"]:
        el = soup.select_one("a[href*='/jobs/company-']")
        if el:
            job["company"] = _text(el)

    return job


# ── Graceful shutdown ─────────────────────────────────────────────────────────

_shutdown = False

def _handle_signal(sig, frame):
    global _shutdown
    log.warning("Signal %s received — finishing current batch then saving...", sig)
    _shutdown = True


signal.signal(signal.SIGINT,  _handle_signal)
signal.signal(signal.SIGTERM, _handle_signal)


# ── Main orchestration ────────────────────────────────────────────────────────

async def scrape_detail(
    session: aiohttp.ClientSession,
    sem: asyncio.Semaphore,
    stub: dict,
) -> dict | None:
    url = stub.get("url", "")
    if not url:
        return stub
    if not url.startswith("http"):
        url = BASE_URL + url
    html = await fetch(session, url, sem)
    if html is None:
        return stub  # return with listing-only data
    return parse_detail_page(html, stub)


async def collect_all_urls(
    session: aiohttp.ClientSession,
    sem: asyncio.Semaphore,
    start_page: int,
) -> tuple[list[dict], int]:
    """Fetch all listing pages and return stubs + total pages discovered."""
    log.info("Fetching page 1 to discover total pages…")
    html = await fetch(session, f"{JOBS_URL}?page=1", sem)
    if not html:
        log.error("Failed to fetch page 1 — aborting")
        return [], 0

    first_stubs, total_pages = parse_listing_page(html)
    log.info("Total pages: %d", total_pages)

    all_stubs: list[dict] = first_stubs if start_page <= 1 else []

    pages = list(range(max(2, start_page), total_pages + 1))

    async def fetch_page(page: int) -> list[dict]:
        if _shutdown:
            return []
        h = await fetch(session, f"{JOBS_URL}?page={page}", sem)
        if not h:
            log.warning("Empty response on listing page %d", page)
            return []
        stubs, _ = parse_listing_page(h)
        return stubs

    log.info("Fetching %d listing pages concurrently…", len(pages))
    results = await tqdm.gather(
        *[fetch_page(p) for p in pages],
        desc="Listing pages",
        unit="page",
    )
    for r in results:
        all_stubs.extend(r)

    return all_stubs, total_pages


async def main() -> None:
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    # Load checkpoint
    ckpt       = load_checkpoint()
    done_urls  = set(ckpt["done_urls"])
    last_page  = ckpt["last_page"]

    if done_urls:
        log.info("Resuming — %d jobs already scraped", len(done_urls))

    init_csv()

    connector = aiohttp.TCPConnector(limit=CONCURRENCY, ssl=False)
    sem       = asyncio.Semaphore(CONCURRENCY)

    async with aiohttp.ClientSession(connector=connector) as session:

        # ── Phase 1: collect all job stubs from listing pages ─────────────
        all_stubs, total_pages = await collect_all_urls(session, sem, start_page=last_page + 1)

        # Filter already-done jobs
        pending = [s for s in all_stubs if s.get("url") and s["url"] not in done_urls]
        log.info(
            "Jobs discovered: %d total, %d pending (skipping %d already done)",
            len(all_stubs), len(pending), len(done_urls),
        )

        # ── Phase 2: fetch detail pages ───────────────────────────────────
        BATCH = 50  # save every N completions

        async def do_detail(stub: dict) -> dict | None:
            if _shutdown:
                return None
            return await scrape_detail(session, sem, stub)

        pbar   = tqdm(total=len(pending), desc="Detail pages", unit="job")
        buffer: list[dict] = []

        tasks = [asyncio.create_task(do_detail(s)) for s in pending]

        for coro in asyncio.as_completed(tasks):
            result = await coro
            pbar.update(1)
            if result is None:
                continue
            buffer.append(result)
            done_urls.add(result.get("url", ""))

            if len(buffer) >= BATCH or _shutdown:
                append_rows(buffer)
                save_checkpoint(done_urls, total_pages)
                log.info("Saved batch of %d | total done: %d", len(buffer), len(done_urls))
                buffer.clear()

            if _shutdown:
                log.warning("Shutdown requested — flushing and exiting")
                # Cancel remaining tasks
                for t in tasks:
                    t.cancel()
                break

        pbar.close()

        # Final flush
        if buffer:
            append_rows(buffer)
            save_checkpoint(done_urls, total_pages)
            log.info("Final flush: %d rows", len(buffer))

    total_rows = sum(1 for _ in open(OUTPUT_PATH, encoding="utf-8")) - 1  # minus header
    log.info("Done. %d total rows in %s", total_rows, OUTPUT_PATH)

    if not _shutdown:
        # Clean checkpoint on clean exit
        CHECKPOINT_PATH.unlink(missing_ok=True)
        log.info("Checkpoint cleared (clean finish)")


if __name__ == "__main__":
    asyncio.run(main())
