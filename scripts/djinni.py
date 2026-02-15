"""
Djinni.co job listings scraper
Scrapes all job postings from djinni.co/jobs and saves to data/djinni.csv
"""

import csv
import json
import logging
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger(__name__)

BASE_URL = "https://djinni.co/jobs/"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}
DELAY = 1.5  # seconds between requests
OUTPUT_PATH = Path(__file__).parent.parent / "data" / "djinni.csv"

CSV_FIELDS = [
    "title",
    "company",
    "url",
    "salary_min",
    "salary_max",
    "salary_currency",
    "location",
    "job_type",
    "experience_months",
    "english_level",
    "category",
    "date_posted",
    "description_snippet",
]


def get_soup(url: str, session: requests.Session) -> BeautifulSoup:
    response = session.get(url, headers=HEADERS, timeout=15)
    response.raise_for_status()
    return BeautifulSoup(response.text, "html.parser")


def parse_json_ld(soup: BeautifulSoup) -> list[dict]:
    """Extract jobs from JSON-LD structured data embedded in the page."""
    jobs = []
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or "")
        except (json.JSONDecodeError, TypeError):
            continue

        # Top-level ItemList
        if isinstance(data, dict) and data.get("@type") == "ItemList":
            for item in data.get("itemListElement", []):
                job = item if item.get("@type") == "JobPosting" else item.get("item", {})
                if job.get("@type") == "JobPosting":
                    jobs.append(_extract_job(job))

        # Single JobPosting
        elif isinstance(data, dict) and data.get("@type") == "JobPosting":
            jobs.append(_extract_job(data))

        # List of JobPostings
        elif isinstance(data, list):
            for entry in data:
                if isinstance(entry, dict) and entry.get("@type") == "JobPosting":
                    jobs.append(_extract_job(entry))

    return jobs


def _extract_job(job: dict) -> dict:
    salary = job.get("baseSalary", {})
    salary_value = salary.get("value", {})
    min_val = salary_value.get("minValue", "")
    max_val = salary_value.get("maxValue", "")
    currency = salary.get("currency", "USD")

    org = job.get("hiringOrganization", {})
    company = org.get("name", "") if isinstance(org, dict) else ""

    exp = job.get("experienceRequirements", {})
    exp_months = exp.get("monthsOfExperience", "") if isinstance(exp, dict) else ""

    location_type = job.get("jobLocationType", "")
    applicant_locations = job.get("applicantLocationRequirements", [])
    if isinstance(applicant_locations, dict):
        applicant_locations = [applicant_locations]
    location_names = [loc.get("name", "") for loc in applicant_locations if isinstance(loc, dict)]
    location = location_type + (" / " + ", ".join(location_names) if location_names else "")

    description = job.get("description", "")
    snippet = description[:300].replace("\n", " ").strip() if description else ""

    return {
        "title": job.get("title", ""),
        "company": company,
        "url": job.get("url", ""),
        "salary_min": min_val,
        "salary_max": max_val,
        "salary_currency": currency if (min_val or max_val) else "",
        "location": location,
        "job_type": job.get("employmentType", ""),
        "experience_months": exp_months,
        "english_level": "",          # not in JSON-LD; filled from HTML below
        "category": job.get("category", ""),
        "date_posted": job.get("datePosted", ""),
        "description_snippet": snippet,
    }


def parse_html_jobs(soup: BeautifulSoup) -> list[dict]:
    """
    Fallback / supplemental parser that reads the rendered HTML job cards.
    Djinni renders cards with class 'job-list-item'.
    """
    jobs = []
    for card in soup.select("ul.list-jobs li.job-list-item, li.list-jobs__item"):
        job: dict = {f: "" for f in CSV_FIELDS}

        # Title + URL
        title_el = card.select_one("a.job-list-item__link")
        if title_el:
            job["title"] = title_el.get_text(strip=True)
            href = title_el.get("href", "")
            job["url"] = "https://djinni.co" + href if href.startswith("/") else href

        # Company
        company_el = card.select_one("a.job-list-item__company-link, a[data-analytics='company']")
        if company_el:
            job["company"] = company_el.get_text(strip=True)

        # Salary
        salary_el = card.select_one(".public-salary-item, span.salary")
        if salary_el:
            raw = salary_el.get_text(strip=True)
            job["salary_min"] = raw  # store raw string when range parsing is unclear

        # Meta badges (location, remote, English, experience)
        for badge in card.select(".job-list-item__job-info span, .badge, .nobr"):
            text = badge.get_text(strip=True).lower()
            if "remote" in text or "office" in text or "hybrid" in text:
                job["location"] = badge.get_text(strip=True)
            elif "english" in text or "upper" in text or "intermediate" in text or "advanced" in text:
                job["english_level"] = badge.get_text(strip=True)

        # Posted date
        date_el = card.select_one("span.mr-2 nobr, time, .job-list-item__applied-time, span[title]")
        if date_el:
            job["date_posted"] = date_el.get("title", "") or date_el.get_text(strip=True)

        if job["title"]:
            jobs.append(job)

    return jobs


def get_total_pages(soup: BeautifulSoup) -> int:
    """Read pagination to find the last page number."""
    # Try standard pagination links
    pages = soup.select("ul.pagination li a[href*='page=']")
    numbers = []
    for a in pages:
        href = a.get("href", "")
        try:
            numbers.append(int(href.split("page=")[-1].split("&")[0]))
        except ValueError:
            pass
    if numbers:
        return max(numbers)

    # Fallback: look for total count text
    count_el = soup.select_one(".total-jobs-count, h1.h4")
    if count_el:
        text = count_el.get_text()
        import re
        m = re.search(r"([\d\s,]+)", text)
        if m:
            total = int(m.group(1).replace(" ", "").replace(",", ""))
            return max(1, (total + 19) // 20)

    return 1


def scrape_page(page: int, session: requests.Session) -> tuple[list[dict], int]:
    url = f"{BASE_URL}?page={page}"
    log.info("Fetching page %d — %s", page, url)
    soup = get_soup(url, session)

    total_pages = get_total_pages(soup) if page == 1 else 0

    # Try JSON-LD first; fall back to HTML parser
    jobs = parse_json_ld(soup)
    if not jobs:
        log.warning("No JSON-LD jobs on page %d, trying HTML parser", page)
        jobs = parse_html_jobs(soup)

    log.info("  Found %d jobs on page %d", len(jobs), page)
    return jobs, total_pages


def save_csv(rows: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    log.info("Saved %d rows → %s", len(rows), path)


def main() -> None:
    session = requests.Session()
    all_jobs: list[dict] = []

    # --- Page 1: discover total pages ---
    first_jobs, total_pages = scrape_page(1, session)
    all_jobs.extend(first_jobs)

    if total_pages < 1:
        total_pages = 1
    log.info("Total pages discovered: %d", total_pages)

    # --- Remaining pages ---
    for page in range(2, total_pages + 1):
        time.sleep(DELAY)
        jobs, _ = scrape_page(page, session)
        if not jobs:
            log.warning("No jobs on page %d — stopping early", page)
            break
        all_jobs.extend(jobs)

    log.info("Total jobs scraped: %d", len(all_jobs))
    save_csv(all_jobs, OUTPUT_PATH)


if __name__ == "__main__":
    main()
