# QDArchive — Part 1: Data Acquisition

**Course:** Seeding QDArchive — FAU Erlangen, Winter 2025/26  
**Student:** Jakir Hussain Rifat  
**Part:** 1 of 3 — Data Acquisition (5 ECTS)  

## Assigned Repositories

| # | Repository | URL |
|---|-----------|-----|
| 1 | Dryad | https://datadryad.org |
| 2 | Finnish Social Science Data Archive (FSD) | https://www.fsd.tuni.fi/en |

## Results Summary

| Source | Projects | Files Downloaded | Method |
|--------|----------|-----------------|--------|
| Dryad | 787 | 554+ | REST API v2 (API-CALL) |
| FSD Finland | 403 | 403 DDI XML files | HTML catalogue scrape (SCRAPING) |
| **Total** | **1,190** | **554+** | |

## Project Structure

\`\`\`
QDArchive/
├── main.py                  # Entry point
├── requirements.txt         # Python dependencies
├── scrapers/
│   ├── dryad_scraper.py     # Dryad REST API v2 scraper
│   └── fsd_scraper.py       # FSD HTML catalogue scraper
├── db/
│   ├── schema.sql           # SQLite schema (6 tables)
│   └── database.py          # DB helpers
├── pipeline/
│   └── downloader.py        # File download utility
├── export/
│   ├── csv_exporter.py      # Export DB to CSV
│   └── metadata.csv         # Exported metadata (1,190 projects)
├── scripts/
│   └── retry_429.py         # Retry rate-limited downloads
└── metadata.db              # SQLite database (not in git)
\`\`\`

## Setup

\`\`\`bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
# Add to .env: DRYAD_CLIENT_ID and DRYAD_CLIENT_SECRET
\`\`\`

## Usage

\`\`\`bash
python3 main.py                  # run all scrapers
python3 main.py --source dryad   # Dryad only
python3 main.py --source fsd     # FSD only
python3 main.py --export         # export DB to CSV
python3 main.py --stats          # show download statistics
python3 scripts/retry_429.py     # retry rate-limited files
\`\`\`

## Database Schema

Six tables per professor's specification:
- REPOSITORIES — seeded with Dryad (id=1) and FSD (id=2)
- PROJECTS — one row per research project (1,190 total)
- FILES — one row per file with download status
- KEYWORDS — keywords per project
- PERSON_ROLE — authors per project
- LICENSES — license per project

## Technical Challenges

### Dryad
- AWS load balancer blocks requests without a real browser User-Agent (HTTP 403) — solved with Chrome User-Agent header
- File downloads require OAuth2 Bearer token — implemented client credentials flow
- Rate limiting (HTTP 429) — solved with polite delays and a dedicated retry script
- Bulk zip download endpoint returns 401 — individual file download works with token

### FSD Finland
- Catalogue URL returns HTML not JSON — solved with BeautifulSoup scraping
- JavaScript-driven pagination — solved by directly incrementing page parameter (pages 0-8)
- Data files require Aila login — recorded as FAILED_LOGIN_REQUIRED in FILES table
- DDI-C 2.5 XML metadata always public — downloaded for every study

## Download Links

The metadata.db and data/ folder are not in git due to size.
Download link for database and files: (provided via submission form)
