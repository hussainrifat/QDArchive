# QDArchive — Part 1: Data Acquisition

**Course:** Seeding QDArchive — FAU Erlangen, Winter 2025/26
**Student:** Jakir Hussain Rifat
**Part:** 1 of 3 — Data Acquisition (5 ECTS)
**Deadline:** April 17th, 2026
**GitHub:** https://github.com/hussainrifat/QDArchive

---

## What This Project Does

This project seeds the QDArchive by automatically scraping and downloading qualitative research datasets from two assigned repositories. It collects metadata into a structured SQLite database following the professor's exact schema, downloads all available project files, and exports everything to CSV.

---

## Assigned Repositories

| # | Name | URL | Approach |
|---|------|-----|----------|
| 1 | Dryad | https://datadryad.org | REST API v2 |
| 2 | Finnish Social Science Data Archive (FSD) | https://www.fsd.tuni.fi/en | HTML catalogue scrape |

**Search queries used (Dryad):**

- `qualitative research`
- `qualitative data`
- `interview study`
- `qualitative research data`
- `qdpx`
- `interview transcripts`
- `focus group qualitative`
- `thematic analysis`

**FSD:** Full catalogue scraped using professor's exact URL:
`https://services.fsd.tuni.fi/catalogue/index?limit=50&study_language=en&lang=en&page=0&field=publishing_date&direction=descending&data_kind_string_facet=Qualitative`

---

## Results Summary

| Source | Projects | Files (SUCCESS) | Files (FAILED) | Method |
|--------|----------|----------------|----------------|--------|
| Dryad | 787 | 338 | 3,296 (rate limited, retry in progress) | API-CALL |
| FSD Finland | 403 | 408 (DDI XML) | 396 (login required) | SCRAPING |
| **Total** | **1,190** | **1141+** | **3,715** | |

**File types successfully downloaded from Dryad:**
`.docx` (30), `.pdf` (24), `.csv` (47), `.xlsx` (27), `.xml` (5), `.zip` (10), `.r` (18), `.md` (13), `.txt` (13), and more.
1 QDA analysis file found: `.nvp` (NVivo project file).

**FSD:** 403 DDI-C 2.5 XML metadata files downloaded (always public). Actual data files (interview transcripts, written responses) require Aila account registration — recorded as `FAILED_LOGIN_REQUIRED`.

---

## Database Schema

Six tables per professor's specification (`db/schema.sql`):

| Table | Rows | Description |
|-------|------|-------------|
| REPOSITORIES | 2 | Dryad (id=1), FSD (id=2) |
| PROJECTS | 1,190 | One row per research project, all required fields populated |
| FILES | 4,460 | One row per file with descriptive download status |
| KEYWORDS | 6,574 | Keywords per project |
| PERSON_ROLE | 4,661 | Authors per project with role |
| LICENSES | 1,190 | License per project |

**Download status values used in FILES.status:**

- `SUCCESS` — file downloaded to disk
- `FAILED_LOGIN_REQUIRED` — file requires account login
- `FAILED_HTTP_429` — rate limited, retry in progress
- `FAILED_HTTP_404` — file not found
- `FAILED_NO_DOWNLOAD_LINK` — no download URL available

---

## Project Structure
QDArchive/
├── main.py                    # Entry point — run all scrapers
├── requirements.txt           # Python dependencies
├── .env                       # Dryad API credentials (not in git)
├── metadata.db                # SQLite database (6 tables, 1,190 projects)
├── scrapers/
│   ├── dryad_scraper.py       # Dryad REST API v2 scraper
│   └── fsd_scraper.py         # FSD HTML catalogue scraper
├── db/
│   ├── schema.sql             # Professor's exact SQLite schema
│   └── database.py            # DB connection and insert helpers
├── pipeline/
│   └── downloader.py          # File download with status tracking
├── export/
│   ├── csv_exporter.py        # Export metadata.db to CSV
│   └── metadata.csv           # Flat CSV export of all 1,190 projects
├── scripts/
│   └── retry_429.py           # Retry all FAILED_HTTP_429 files
└── data/                      # Downloaded files (not in git — too large)
├── dryad/
│   └── {dataset_id}/      # e.g. data/dryad/16857/
└── fsd/
└── {study_id}/        # e.g. data/fsd/FSD3753/

---

## Setup

```bash
git clone https://github.com/hussainrifat/QDArchive.git
cd QDArchive
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Create a `.env` file with your Dryad API credentials:
DRYAD_CLIENT_ID=your_client_id
DRYAD_CLIENT_SECRET=your_client_secret

Get credentials at: https://datadryad.org → Login → My Account → API credentials

---

## Usage

```bash
python3 main.py                    # run all scrapers (Dryad + FSD)
python3 main.py --source dryad     # Dryad only
python3 main.py --source fsd       # FSD only
python3 main.py --export           # export metadata.db to CSV
python3 main.py --stats            # show download statistics
python3 scripts/retry_429.py       # retry all FAILED_HTTP_429 files
```

---

## Technical Challenges (Data)

The professor asked to report on technical challenges with **data**, not programming.

### 1. FSD data files are behind a login wall

All FSD data files (interview transcripts, written responses, survey data) require registration and login to the Aila Data Service. Without an institutional account, files cannot be downloaded. These are recorded as `FAILED_LOGIN_REQUIRED` in the FILES table. Only the DDI-C 2.5 XML metadata file is always publicly available for each study.

### 2. Dryad rate limiting (HTTP 429)

Dryad enforces rate limits on file downloads. When downloading too fast, the API returns HTTP 429 Too Many Requests. A dedicated retry script (`scripts/retry_429.py`) handles these cases with polite delays. 3,296 files were initially rate-limited and are being retried.

### 3. Very few QDA analysis files publicly available

Neither Dryad nor FSD regularly publish QDA analysis files (`.qdpx`, `.nvp`, `.mx24`) publicly. Only 1 QDA file was found — a NVivo `.nvp` file from Dryad. This is expected: QDA files are typically created by researchers using tools like QDAcity, NVivo, or MAXQDA and are rarely deposited in open repositories.

### 4. Dryad search returns non-qualitative datasets

Searching Dryad for "qualitative" returns many biology, physics, and ecology datasets that use the word "qualitative" in a different sense (e.g. "qualitative analysis of soil samples"). These datasets were still collected since the professor's instruction is to collect everything and filter in Part 2.

### 5. 149 Dryad projects have no keywords

Some Dryad datasets have no keywords in their metadata. The KEYWORDS table has no entry for these projects. Per the professor's instruction, data quality issues are downloaded as-is and will be resolved in a later step.

### 6. FSD licenses are access categories, not CC licenses

FSD assigns access levels (A=open, B=research and education, C=research only, D=by permission) rather than standard CC license strings. These are recorded in the LICENSES table as-is. Only availability A datasets have a proper CC BY 4.0 license.

### 7. Dryad bulk download requires authentication

The Dryad API endpoint `/api/v2/datasets/{doi}/download` returns HTTP 401 even with a valid token for some datasets. Individual file download via `/api/v2/files/{id}/download` works reliably with the Bearer token.

---

## Technical Challenges (Programming)

- **Dryad HTTP 403:** AWS load balancer blocks requests without a real browser User-Agent — solved with Chrome User-Agent header
- **Dryad authentication:** File downloads require OAuth2 Bearer token — implemented client credentials flow via `/oauth/token`
- **FSD HTML catalogue:** The catalogue URL returns HTML not JSON — scraped with BeautifulSoup
- **FSD pagination:** JavaScript-driven pagination — solved by directly incrementing the page parameter (pages 0–8, 50 studies per page, 403 total)

---

## Download Links

The `metadata.db` SQLite database and `data/` folder (downloaded files) are available here:

- **metadata.db:** *(add Google Drive link)*
- **data/ folder:** *(add Google Drive link)*