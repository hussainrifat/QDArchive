# QDArchive — Part 1: Data Acquisition

**Course:** Seeding QDArchive — FAU Erlangen, Winter 2025/26
**Student:** Jakir Hussain Rifat (23025313)
**Part:** 1 of 3 — Data Acquisition (5 ECTS)
**Deadline:** April 17th, 2026
**GitHub:** https://github.com/hussainrifat/QDArchive
**Submission file:** `23025313-seeding.db`

---

## What This Project Does

This project is part of the Seeding QDArchive seminar at FAU Erlangen. The goal is to populate QDArchive — a new repository for qualitative research data — by scraping and downloading qualitative research projects from publicly available data repositories.

I was assigned two repositories: **Dryad** and **FSD Finland**. For each repository I built an automated scraper, downloaded as many qualitative research project files as possible, and stored all metadata in a SQLite database following the professor's exact schema.

---

## Assigned Repositories

| # | Name | URL | Method |
|---|------|-----|--------|
| 1 | Dryad | https://datadryad.org | REST API v2 (API-CALL) |
| 2 | Finnish Social Science Data Archive (FSD) | https://www.fsd.tuni.fi/en | HTML catalogue scrape (SCRAPING) |

### Dryad — Search Queries Used

I used the following queries to find qualitative research projects on Dryad, based on the professor's suggested smart queries and additional qualitative research methods:

- `qualitative research`
- `qualitative data`
- `interview study`
- `qualitative research data`
- `qdpx`
- `interview transcripts`
- `focus group qualitative`
- `thematic analysis`
- `grounded theory`
- `semi structured interview`
- `case study qualitative`
- `phenomenology`
- `content analysis qualitative`
- `discourse analysis`
- `interview transcript`

### FSD Finland — Catalogue Scrape

I scraped the full FSD qualitative catalogue using the professor's exact example URL, paginating through all 9 pages (403 studies total):

`https://services.fsd.tuni.fi/catalogue/index?limit=50&study_language=en&lang=en&page=0&field=publishing_date&direction=descending&data_kind_string_facet=Qualitative`

---

## Results Summary

| Source | Projects | Files Downloaded | Files Failed | Method |
|--------|----------|-----------------|--------------|--------|
| Dryad | 787 | 1,141 | 3,342 (server/rate limit) | API-CALL |
| FSD Finland | 403 | 408 (DDI XML) | 396 (login required) | SCRAPING |
| **Total** | **1,190** | **1,549** | **3,738** | |

### File Types Successfully Downloaded

**QDA analysis files (professor's primary target):**
- `.nvp` — 1 file (NVivo project file from Dryad)

**Primary data files (interview transcripts, survey data):**
- `.docx` — 62 files
- `.pdf` — 26 files
- `.txt` — 140 files
- `.doc` — 3 files
- `.csv` — 107 files (survey responses, coded data)
- `.xlsx` — 79 files (freetext responses, coding sheets)

**FSD metadata:**
- `.xml` — 403 DDI-C 2.5 XML files (one per FSD study, always public)

**Additional files from complete project folders:**
- `.zip`, `.md`, `.fig`, `.rar`, `.sav`, `.mp4` and others

---

## Database Schema

The SQLite database `23025313-seeding.db` follows the professor's exact schema with six tables:

| Table | Rows | Description |
|-------|------|-------------|
| REPOSITORIES | 2 | Dryad (id=1), FSD (id=2) |
| PROJECTS | 1,190 | One row per research project — all required fields populated |
| FILES | 4,879 | One row per file with descriptive download status |
| KEYWORDS | 6,574 | Keywords extracted per project |
| PERSON_ROLE | 4,661 | Authors per project |
| LICENSES | 1,190 | License per project |

### Download Status Values (FILES.status)

Per the professor's DOWNLOAD_RESULT enum:

| Status | Meaning |
|--------|---------|
| `SUCCEEDED` | File successfully downloaded to disk |
| `FAILED_LOGIN_REQUIRED` | File requires account login (FSD Aila, some Dryad) |
| `FAILED_SERVER_UNRESPONSIVE` | Rate limited (HTTP 429), server error, or timeout |
| `FAILED_TOO_LARGE` | Not used — no files were too large |

### License Values (LICENSES.license)

Per the professor's LICENSE enum:

| Value | Source |
|-------|--------|
| `CC0` | Dryad datasets with CC0 license |
| `CC BY 4.0` | Dryad datasets with CC BY 4.0 and open FSD (class A) |
| `FAILED_LOGIN_REQUIRED` | FSD datasets with restricted access (class B/C/D) |

---

## Project Structure

```
QDArchive/
├── 23025313-seeding.db        # Submission SQLite database
├── main.py                    # Entry point — run all scrapers
├── requirements.txt           # Python dependencies
├── .env                       # Dryad API credentials (not in git)
├── scrapers/
│   ├── dryad_scraper.py       # Dryad REST API v2 scraper
│   └── fsd_scraper.py         # FSD HTML catalogue scraper
├── db/
│   ├── schema.sql             # Professor's exact SQLite schema
│   └── database.py            # DB connection and insert helpers
├── pipeline/
│   └── downloader.py          # File download with status tracking
├── export/
│   ├── csv_exporter.py        # Export DB to CSV
│   └── metadata.csv           # Flat CSV of all 1,190 projects
├── scripts/
│   └── retry_429.py           # Retry FAILED_SERVER_UNRESPONSIVE files
└── data/                      # Downloaded files (not in git — too large)
    ├── dryad/
    │   └── {dataset_id}/      # e.g. data/dryad/16857/
    └── fsd/
        └── {study_id}/        # e.g. data/fsd/FSD3753/
```

---

## Setup

```bash
git clone https://github.com/hussainrifat/QDArchive.git
cd QDArchive
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Create a `.env` file in the project root:
DRYAD_CLIENT_ID=your_client_id
DRYAD_CLIENT_SECRET=your_client_secret

Get Dryad API credentials at: https://datadryad.org → Login → My Account → API credentials

---

## Usage

```bash
python3 main.py                    # run all scrapers (Dryad + FSD)
python3 main.py --source dryad     # Dryad only
python3 main.py --source fsd       # FSD only
python3 main.py --export           # export database to CSV
python3 main.py --stats            # show download statistics
python3 scripts/retry_429.py       # retry failed downloads
```

---

## Technical Challenges with Data

*The professor asked to report on technical challenges with the data, not programming.*

### 1. FSD data files require institutional login

All FSD data files — interview transcripts, written responses, and survey data — are stored behind the Aila Data Service login. Without an institutional account from a Finnish university, the actual research files cannot be downloaded. I recorded these as `FAILED_LOGIN_REQUIRED` in the FILES table. The only file always publicly available per study is the DDI-C 2.5 XML metadata record, which I downloaded for all 403 studies. This affects 396 file entries.

### 2. Dryad rate limiting (HTTP 429)

Dryad enforces strict rate limits on file downloads. When I downloaded files faster than their threshold, the API returned HTTP 429 Too Many Requests. I solved this with a 2-second polite delay between each file download and built a dedicated retry script (`scripts/retry_429.py`). Despite this, 3,342 files are still recorded as `FAILED_SERVER_UNRESPONSIVE` and continue to be retried.

### 3. No QDA analysis files publicly available

The professor's primary interest is QDA analysis files (`.qdpx`, `.nvp`, `.mx24`, `.mqda` etc). I found only 1 QDA file across both repositories — a NVivo `.nvp` file from Dryad. This is a fundamental data availability problem: researchers who use QDAcity, NVivo, or MAXQDA rarely deposit their analysis files in open repositories. The QDArchive project itself exists to solve this gap, which is why it needs to be seeded.

### 4. Dryad search returns non-qualitative science datasets

Searching Dryad for qualitative research methods returns many natural science datasets that use "qualitative" in a scientific sense — for example "qualitative analysis of soil samples" or "qualitative assessment of gene expression". These projects contain `.fas` DNA sequence files, `.gjf` chemistry simulation files, `.stl` 3D model files, and `.tif` image files — none of which are qualitative research data. Per the professor's instruction to download the complete project folder and resolve quality issues in Part 2, I downloaded all files. Filtering non-qualitative projects will be the task in Part 2 classification.

### 5. 149 Dryad projects have no keywords

A significant number of Dryad datasets (149 out of 787) have no keywords in their API metadata. The KEYWORDS table has no entry for these projects. Per the professor's primary rule — "do not change data when downloading; data quality issues will be resolved in a second step" — I stored what was available and left missing fields empty.

### 6. FSD licenses are access categories, not standard CC strings

FSD does not publish standard Creative Commons license strings for its datasets. Instead, it uses access categories: A (openly available, CC BY 4.0), B (research and education), C (research only), D (by permission only). I stored the access class information in the LICENSES table. Only category A datasets have a proper CC BY 4.0 license that allows open reuse.

### 7. Dryad bulk download returns HTTP 401

The Dryad API provides a bulk download endpoint (`/api/v2/datasets/{doi}/download`) that should return the entire dataset as a ZIP file. In testing this returned HTTP 401 Unauthorized even with a valid Bearer token. Individual file download via `/api/v2/files/{id}/download` worked correctly. I switched to per-file downloads for all Dryad datasets.

### 8. FSD catalogue uses JavaScript pagination

The FSD catalogue page uses JavaScript to render pagination controls. The next page button has `href="#"` rather than a real URL, making standard next-link detection impossible. I solved this by discovering that the page number is a URL parameter and directly incrementing it from 0 to 8 (9 pages × 50 studies = 403 studies total).

---

## Technical Challenges with Programming

- **Dryad HTTP 403:** AWS load balancer returns 403 for requests without a real browser User-Agent — solved by using a Chrome User-Agent header
- **Dryad OAuth2:** File downloads require an OAuth2 Bearer token obtained via client credentials flow at `/oauth/token`
- **FSD HTML scraping:** The catalogue URL returns HTML not JSON — scraped with BeautifulSoup and `lxml`
- **SQLite constraint errors:** Initial schema used a CHECK constraint on FILES.status that was too restrictive for dynamic HTTP error codes — solved by using free-text status strings matching the professor's DOWNLOAD_RESULT enum

---

## Download Links

The `data/` folder with all downloaded files is not stored in git due to size.

## Download Links

- **23025313-seeding.db (SQLite database):** https://github.com/hussainrifat/QDArchive/blob/main/23025313-seeding.db

- **data/ folder (downloaded files):** https://faubox.rrze.uni-erlangen.de/getlink/fiRAkmdT7TEysXmSouzRjZ/data
