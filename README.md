# QDArchive — Data Acquisition & Classification

**Course:** Seeding QDArchive — FAU Erlangen, Winter 2025/26 + Summer 2026
**Student:** Jakir Hussain Rifat (23025313)
**Professor:** Dirk Riehle, Professorship for Open-Source Software
**ECTS:** 10 (5 ECTS Part 1 + 5 ECTS Part 2)
**GitHub:** https://github.com/hussainrifat/QDArchive

---

## Overview

This project seeds QDArchive — a new archive for qualitative research data — by scraping two assigned repositories, downloading qualitative research project files, storing all metadata in a structured SQLite database, and classifying each project using the ISIC Rev. 5 taxonomy.

**Assigned repositories:** Dryad (REST API) and FSD Finland (HTML scrape)

---

## Part 1: Data Acquisition

### Submission

| Artifact | Location |
|----------|----------|
| SQLite database | `23025313-seeding.db` (repo root) |
| Git tag | `part-1-release` |
| Downloaded files | https://faubox.rrze.uni-erlangen.de/getlink/fiRAkmdT7TEysXmSouzRjZ/data |
| Professor's grading script | **9 PASS, 2 WARNINGS, 0 ERRORS** |

### Results

| Source | Projects | Files Succeeded | Files Failed | Method |
|--------|----------|-----------------|--------------|--------|
| Dryad | 853 | 1,141 | 3,342 (rate limited) | API-CALL |
| FSD Finland | 403 | 408 (DDI XML) | 396 (login required) | SCRAPING |
| **Total** | **1,256** | **1,549** | **3,738** | |

**Downloaded files on disk:** 28.64 GB

### QDA Analysis Files Found

| Extension | Tool | Count |
|-----------|------|-------|
| `.nvp` | NVivo | 1 |

Only 1 QDA file was found across both repositories. This reflects a known data availability problem — researchers rarely deposit QDA analysis files in open repositories. This is precisely the gap QDArchive is built to address.

### Primary Data Files Downloaded

| Type | Count | Content |
|------|-------|---------|
| `.txt` | 140 | Interview transcripts, coded text |
| `.csv` | 107 | Survey responses, coded data |
| `.xlsx` | 79 | Freetext responses, coding sheets |
| `.docx` | 62 | Interview transcripts, field notes |
| `.pdf` | 26 | Interview protocols, reports |
| `.doc` | 3 | Interview transcripts |
| `.xml` | 403 | FSD DDI-C 2.5 metadata (one per study) |

### Dryad — Search Queries

15 queries were used to find qualitative research projects:

`qualitative research` · `qualitative data` · `interview study` · `qualitative research data` · `qdpx` · `interview transcripts` · `focus group qualitative` · `thematic analysis` · `grounded theory` · `semi structured interview` · `case study qualitative` · `phenomenology` · `content analysis qualitative` · `discourse analysis` · `interview transcript`

### FSD Finland — Catalogue Scrape

Scraped the full FSD qualitative catalogue (9 pages × 50 studies = 403 studies):

```
https://services.fsd.tuni.fi/catalogue/index?limit=50&study_language=en&lang=en
  &page=0&field=publishing_date&direction=descending&data_kind_string_facet=Qualitative
```

DDI-C 2.5 XML metadata was downloaded for all 403 studies (always public). Actual data files require Aila institutional login and were recorded as `FAILED_LOGIN_REQUIRED`.

### Database Schema (Part 1)

The database `23025313-seeding.db` follows the professor's exact schema:

| Table | Rows | Description |
|-------|------|-------------|
| REPOSITORIES | 2 | Dryad (id=1), FSD (id=2) |
| PROJECTS | 1,256 | One row per research project |
| FILES | 4,879 | All files with download status |
| KEYWORDS | 6,884 | Keywords per project |
| PERSON_ROLE | 4,926 | Authors per project |
| LICENSES | 1,256 | License per project |

### Technical Challenges with Data (Part 1)

**1. FSD data files require institutional login**
All FSD research files (interview transcripts, written responses, survey data) are stored behind the Aila Data Service, requiring an institutional account from a Finnish university. I recorded these as `FAILED_LOGIN_REQUIRED`. The only always-public file per study is the DDI-C 2.5 XML metadata record, downloaded for all 403 studies. This affects 396 file entries.

**2. Dryad rate limiting (HTTP 429)**
Dryad enforces strict per-IP rate limits on file downloads. Requests faster than their threshold return HTTP 429. Solved with a 2-second polite delay and a dedicated retry script (`scripts/retry_429.py`). Despite this, 3,342 files remain `FAILED_SERVER_UNRESPONSIVE`. These files exist in the repository and can be retried — they are not missing data.

**3. Only 1 QDA analysis file found publicly**
Across 1,256 projects and 15 targeted search queries, only a single QDA file was found — a NVivo `.nvp` file. Researchers who produce QDA analysis files with NVivo, MAXQDA, or QDAcity rarely deposit those files in open repositories. They deposit final papers, datasets, and transcripts, but keep the analysis files private. This is the fundamental problem QDArchive is designed to solve.

**4. Dryad search returns natural-science datasets using "qualitative" scientifically**
Queries like "qualitative research" return biology, chemistry, and ecology projects using "qualitative" in a scientific sense (e.g., "qualitative analysis of soil composition"). These contain `.fas` DNA sequence files, `.gjf` chemistry simulation files, and `.stl` 3D models — none of which are qualitative research data in the social science sense. Per the professor's instruction to download the complete project folder, all files were downloaded. Filtering to true qualitative research projects is handled in Part 2.

**5. 149 Dryad projects have no keywords**
149 of 853 Dryad datasets have no keywords in their API metadata. KEYWORDS table has no entries for these. Following the professor's principle of not modifying data during acquisition, missing fields were left empty.

**6. FSD licenses are access categories, not CC strings**
FSD publishes access categories rather than standard Creative Commons license strings: A (CC BY 4.0, open), B (research and education), C (research only), D (by permission). Only Category A datasets have a true open license enabling reuse. Category B–D are stored as their original descriptive string.

**7. Dryad bulk download endpoint returns HTTP 401**
The `/api/v2/datasets/{doi}/download` bulk ZIP endpoint returns 401 Unauthorized even with a valid OAuth2 Bearer token. Individual file download via `/api/v2/files/{id}/download` works correctly. All files were downloaded individually.

**8. FSD catalogue uses JavaScript-rendered pagination**
The FSD catalogue next-page button has `href="#"` — not a real URL — making standard link-following impossible. Solved by identifying that the page number is a URL query parameter and incrementing it directly from 0 to 8 (9 pages × 50 = 403 studies).

---

## Part 2: Data Classification

### Submission

| Artifact | Location |
|----------|----------|
| Classification database | `23025313-sq26-classification.db` (repo root) |
| XLSX report | `export/23025313-sq26-classification.xlsx` |
| PDF report | `export/23025313-classification-report.pdf` |
| Git tag | `classification-results` |

### Step 1 — Project Type Classification

Each project was classified by examining all its file records (including failed downloads) to determine what files the project contains:

| Type | Rule |
|------|------|
| `QDA_PROJECT` | Has a file with a QDA extension (`.qdpx`, `.nvp`, `.mx24`, `.mqda`, etc.) |
| `QD_PROJECT` | No QDA file but has primary data files (`.pdf`, `.doc`, `.docx`, `.txt`, `.rtf`, etc.) |
| `OTHER_PROJECT` | No QDA or primary files but has other valid data files |
| `NOT_A_PROJECT` | No file type information can be derived |

> **Important:** Classification used ALL file records including failed downloads. Using only successfully downloaded files would have incorrectly classified 729 Dryad projects as `NOT_A_PROJECT` because their files were rate-limited during acquisition, not absent.

**Results:**

| Type | Dryad | FSD | Total |
|------|-------|-----|-------|
| `QDA_PROJECT` | 1 | 0 | 1 |
| `QD_PROJECT` | 340 | 4 | **344** |
| `OTHER_PROJECT` | 498 | 399 | 897 |
| `NOT_A_PROJECT` | 14 | 0 | 14 |
| **Total** | **853** | **403** | **1,256** |

### Step 2 — ISIC Rev. 5 Classification

All 1,256 projects were classified into ISIC Rev. 5 Section + Division using the Anthropic Claude API. The classifier uses each project's title, description, and keywords as input and returns the most appropriate section (letter A–V) and division (2-digit code).

**Script:** `scripts/isic_classifier.py`

**New columns added to PROJECTS table:**

| Column | Example |
|--------|---------|
| `isic_section_code` | `R` |
| `isic_section_name` | `Human health and social work activities` |
| `isic_division_code` | `86` |
| `isic_division_name` | `Human health activities` |
| `isic_confidence` | `high` / `medium` / `low` |

**Overall distribution (all 1,256 projects):**

| Section | Name | Count |
|---------|------|-------|
| N | Professional, scientific and technical activities | 649 |
| R | Human health and social work activities | 384 |
| A | Agriculture, forestry and fishing | 84 |
| Q | Education | 77 |
| S | Arts, entertainment and recreation | 43 |
| P | Public administration and defence | 18 |
| L | Financial and insurance activities | 1 |

### Step 3 — The 4 Required Distributions

Primary data files within QDA and QD projects were also individually classified using filename and parent project context.

**Distribution 1 — Dryad × QDA_PROJECT (1 project)**

| Code | Division | Count |
|------|----------|-------|
| N-72 | Scientific research and development | 1 |

**Distribution 2 — Dryad × QD_PROJECT (340 projects)**

| Code | Division | Count |
|------|----------|-------|
| N-72 | Scientific research and development | 205 |
| R-86 | Human health activities | 92 |
| A-01 | Crop and animal production | 30 |
| Q-85 | Education | 6 |
| P-84 | Public administration and defence | 2 |
| R-88 | Social work activities without accommodation | 2 |
| A-03 | Fishing and aquaculture | 1 |
| S-91 | Libraries, archives, museums and cultural activities | 1 |
| S-90 | Creative, arts and entertainment activities | 1 |

**Distribution 3 — FSD × QDA_PROJECT (0 projects)**

No QDA projects in FSD. All FSD data files require institutional login — no QDA analysis files are accessible. FSD studies were acquired from DDI-C 2.5 XML metadata only.

**Distribution 4 — FSD × QD_PROJECT (4 projects)**

| Code | Division | Count |
|------|----------|-------|
| S-91 | Libraries, archives, museums and cultural activities | 2 |
| N-72 | Scientific research and development | 1 |
| Q-85 | Education | 1 |

### Technical Challenges with Data (Part 2)

**1. No QDA projects in FSD due to access restrictions**
All 403 FSD studies require Aila institutional login to access actual data files. Without downloadable files, no project can be classified as `QDA_PROJECT`. FSD projects were classified purely from DDI-C 2.5 XML metadata. Only 4 FSD projects qualified as `QD_PROJECT` (those with public PDF attachments). This severely limits FSD's contribution to the QD_PROJECT and QDA_PROJECT distributions.

**2. 729 Dryad projects initially appeared as NOT_A_PROJECT**
A naive implementation classifying only successfully downloaded files would have left 729 Dryad projects as `NOT_A_PROJECT` — because their files were rate-limited during acquisition, not absent. The correct approach is to classify based on all file records (including failed downloads), since the file type is always recorded regardless of download success. This was the most significant data quality decision in Part 2.

**3. ISIC classification of non-social-science datasets**
Dryad's `OTHER_PROJECT` category contains many natural science datasets (ecology, marine biology, agriculture) that were collected by the qualitative search queries but are not social science research. These projects still receive valid ISIC codes (primarily N-72 Scientific Research, A-01 Agriculture, A-03 Fishing), but the large N-72 count reflects both genuine social science research and generic "we don't know" fallback classifications.

**4. FSD ISIC classification from metadata only**
For FSD projects, only the DDI-C 2.5 XML title and abstract were available for classification. No file content could be read. This makes FSD classifications less precise than Dryad, where file content and multiple keywords were available. All FSD confidences are recorded as `medium` or `low`.

---

## Project Structure

```
QDArchive/
├── 23025313-seeding.db              # Part 1 submission database
├── 23025313-sq26-classification.db  # Part 2 submission database
├── main.py                          # Entry point — run all scrapers
├── requirements.txt                 # Python dependencies
├── .env                             # API credentials (not in git)
├── scrapers/
│   ├── dryad_scraper.py             # Dryad REST API v2 scraper
│   └── fsd_scraper.py               # FSD HTML catalogue scraper
├── db/
│   ├── schema.sql                   # SQLite schema
│   └── database.py                  # DB connection and helpers
├── pipeline/
│   └── downloader.py                # File downloader with status tracking
├── scripts/
│   ├── retry_429.py                 # Retry rate-limited Dryad files
│   ├── isic_classifier.py           # ISIC Rev. 5 project classifier (Claude API)
│   ├── classify_files.py            # ISIC Rev. 5 file-level classifier
│   ├── export_classification_xlsx.py # Generate Step 4c XLSX
│   └── generate_report_pdf.py       # Generate Step 4d PDF report
├── export/
│   ├── metadata.csv                  # Flat CSV of all 1,256 projects
│   ├── 23025313-sq26-classification.xlsx  # Part 2 Step 4c submission
│   └── 23025313-classification-report.pdf # Part 2 Step 4d report
└── data/                             # Downloaded files (not in git — 28.64 GB)
    ├── dryad/{dataset_id}/
    └── fsd/{study_id}/
```

---

## Setup

```bash
git clone https://github.com/hussainrifat/QDArchive.git
cd QDArchive

# Part 1 environment
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Part 2 environment (includes anthropic, openpyxl, matplotlib)
python3 -m venv .venv-1
source .venv-1/bin/activate
pip install -r requirements.txt anthropic openpyxl matplotlib
```

Create a `.env` file in the project root:
```
DRYAD_CLIENT_ID=your_client_id
DRYAD_CLIENT_SECRET=your_client_secret
ANTHROPIC_API_KEY=your_api_key
```

Get Dryad API credentials at: https://datadryad.org → Login → My Account → API credentials

---

## Usage

```bash
# Part 1 — Data acquisition
python3 main.py                    # run all scrapers
python3 main.py --source dryad     # Dryad only
python3 main.py --source fsd       # FSD only
python3 main.py --export           # export database to CSV
python3 main.py --stats            # show download statistics
python3 scripts/retry_429.py       # retry rate-limited files

# Part 2 — Classification (use .venv-1)
python3 scripts/isic_classifier.py          # classify projects (ISIC Rev. 5)
python3 scripts/classify_files.py           # classify primary data files
python3 scripts/export_classification_xlsx.py  # generate Step 4c XLSX
python3 scripts/generate_report_pdf.py         # generate Step 4d PDF report
```

---

## Download Links

The `data/` folder is not stored in git due to size (28.64 GB).

| Resource | Link |
|----------|------|
| Part 1 database | https://github.com/hussainrifat/QDArchive/blob/main/23025313-seeding.db |
| Part 2 database | https://github.com/hussainrifat/QDArchive/blob/main/23025313-sq26-classification.db |
| Downloaded data files | https://faubox.rrze.uni-erlangen.de/getlink/fiRAkmdT7TEysXmSouzRjZ/data |
