# Data Dictionary — `data/djinni.csv`

All columns extracted from the Djinni.co listing pages via Schema.org JSON-LD
(`application/ld+json`, type `JobPosting`).

Total rows: ~9,600 (one row per job posting)

---

## Columns

### Job identity

| Column | Type | Example | Description |
|---|---|---|---|
| `title` | string | `Senior Python Developer` | Job title as listed |
| `company` | string | `Binariks` | Hiring company name |
| `url` | string | `https://djinni.co/jobs/804822-...` | Full URL to the job detail page |

---

### Salary

| Column | Type | Example | Notes |
|---|---|---|---|
| `salary_min` | integer | `3000` | Minimum monthly salary (gross) |
| `salary_max` | integer | `5000` | Maximum monthly salary (gross) |
| `salary_currency` | string | `USD` | Currency code (ISO 4217). Usually `USD`. Empty if not specified. |

Salary fields are empty when the company did not disclose compensation.

---

### Job classification

| Column | Type | Example | Possible values |
|---|---|---|---|
| `job_type` | string | `FULL_TIME` | `FULL_TIME`, `PART_TIME`, `CONTRACTOR`, `TEMPORARY`, `INTERN`, `VOLUNTEER` |
| `category` | string | `Python` | Technology or domain (e.g. `React.js`, `DevOps`, `QA`, `Product Manager`) |
| `date_posted` | ISO 8601 datetime | `2026-02-15T20:46:02.912021` | When the job was published |

---

### Location

| Column | Type | Example | Description |
|---|---|---|---|
| `location_type` | string | `TELECOMMUTE` | `TELECOMMUTE` = remote; `INPERSON` = office; empty = unspecified |
| `location_regions` | string | `Ukraine, Worldwide` | Comma-separated list of allowed regions/countries |

---

### Experience

| Column | Type | Example | Description |
|---|---|---|---|
| `experience_months` | integer | `24` | Minimum experience required in months (from JSON-LD `monthsOfExperience`) |
| `english_level` | string | `Upper Intermediate` | Required English level. Extracted from detail page text. Often empty in listing-only mode. |
| `experience_years` | string | `3 years` | Required experience in years. Extracted from detail page text. Often empty in listing-only mode. |

---

### Work format & location detail

> These columns are populated only when the detail-page scraping phase is enabled.
> In listing-only mode (current default) they will be empty.

| Column | Type | Example | Description |
|---|---|---|---|
| `work_format` | string | `Remote` | `Remote`, `Office`, `Hybrid` |
| `city` | string | `Kyiv` | Office city (from JSON-LD `addressLocality`) |
| `country` | string | `UA` | ISO country code (from JSON-LD `addressCountry`) |

---

### Company details

> These columns are populated only when the detail-page scraping phase is enabled.

| Column | Type | Example | Description |
|---|---|---|---|
| `domain` | string | `FinTech` | Industry / product domain (from JSON-LD `industry`) |
| `company_type` | string | `Product` | `Product`, `Outsource`, `Outstaff`, `Startup`, `Agency` |
| `company_size` | string | `51-200` | Employee count range |

---

### Engagement metrics

> These columns are populated only when the detail-page scraping phase is enabled.

| Column | Type | Example | Description |
|---|---|---|---|
| `views` | integer | `1240` | Number of times the job was viewed |
| `applications` | integer | `47` | Number of candidates who applied |

---

### Skills & description

> `skills` and `description` are populated only when the detail-page scraping phase
> is enabled.

| Column | Type | Example | Description |
|---|---|---|---|
| `skills` | string | `Python, Django, PostgreSQL` | Comma-separated skill tags linked in the job post |
| `description` | string | `We are looking for…` | Full plain-text job description (truncated at 2000 chars) |

---

## Fill rates (listing-only mode)

Based on a run of 9,596 jobs collected on 2026-02-15:

| Column | Approx. fill rate |
|---|---|
| `title` | ~100% |
| `company` | ~100% |
| `url` | 100% |
| `salary_min` / `salary_max` | ~40% (companies that disclose salary) |
| `salary_currency` | ~40% |
| `job_type` | ~100% |
| `category` | ~95% |
| `date_posted` | ~100% |
| `location_type` | ~60% |
| `location_regions` | ~55% |
| `experience_months` | ~85% |
| `english_level` | 0% (detail-page only) |
| `experience_years` | 0% (detail-page only) |
| `work_format` | 0% (detail-page only) |
| `city` / `country` | 0% (detail-page only) |
| `domain` | 0% (detail-page only) |
| `company_type` | 0% (detail-page only) |
| `company_size` | 0% (detail-page only) |
| `views` / `applications` | 0% (detail-page only) |
| `skills` | 0% (detail-page only) |
| `description` | 0% (detail-page only) |

---

## Notes

- All text fields use UTF-8 encoding.
- Salary values are integers (no decimal places).
- `date_posted` is in ISO 8601 format with microseconds; convert with
  `pd.to_datetime(df['date_posted'])` in pandas.
- `location_regions` may contain multiple comma-separated values; split with
  `df['location_regions'].str.split(', ')` if needed.
- Duplicate jobs are deduplicated by URL during scraping.
