"""
FSD Finland scraper — HTML catalogue scraper
Professor's example:
  https://services.fsd.tuni.fi/catalogue/index?limit=50&study_language=en
  &lang=en&page=0&field=publishing_date&direction=descending
  &data_kind_string_facet=Qualitative

Note: FSD catalogue uses JavaScript pagination — page numbers are incremented
directly rather than following next-page links.
Total qualitative studies in English: ~403 (as shown on the catalogue page)
At 50 per page = 9 pages (pages 0-8)
"""

import re
import time
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timezone
from pathlib import Path

from db.database import (
    insert_project, insert_file, insert_keyword,
    insert_person, insert_license, project_exists,
    STATUS_SUCCESS, STATUS_LOGIN_REQUIRED,
    STATUS_HTTP_404, STATUS_HTTP_ERROR,
    STATUS_NO_DOWNLOAD_LINK, STATUS_TIMEOUT,
    ROLE_AUTHOR
)
from pipeline.downloader import download_file

CATALOGUE_BASE = "https://services.fsd.tuni.fi/catalogue/index"
STUDY_BASE     = "https://services.fsd.tuni.fi/catalogue"
DDI_PATTERN    = "https://services.fsd.tuni.fi/catalogue/{sid}/DDI/{sid}_eng.xml"

REPO_FOLDER = "fsd"
REPO_ID     = 2
REPO_URL    = "https://www.fsd.tuni.fi"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    )
}

# Professor's exact query parameters
CATALOGUE_PARAMS = {
    "study_language":         "en",
    "lang":                   "en",
    "field":                  "publishing_date",
    "direction":              "descending",
    "data_kind_string_facet": "Qualitative",
    "limit":                  50,
}

# FSD has ~403 qualitative studies in English at 50/page = 9 pages (0-8)
MAX_PAGES = 10


def get_soup(url: str, params: dict = None) -> BeautifulSoup | None:
    try:
        r = requests.get(url, headers=HEADERS, params=params, timeout=30)
        r.raise_for_status()
        return BeautifulSoup(r.text, "lxml")
    except Exception as e:
        print(f"  [HTTP ERROR] {url}: {e}")
        return None


def parse_catalogue_page(soup: BeautifulSoup) -> list[dict]:
    """Extract study rows from the catalogue listing table."""
    studies = []
    for row in soup.select("table tr"):
        cells = row.find_all("td")
        if len(cells) < 5:
            continue
        link = cells[0].find("a")
        if not link:
            continue
        study_id = link.text.strip()
        if not study_id.startswith("FSD"):
            continue
        studies.append({
            "study_id":     study_id,
            "title":        cells[1].get_text(strip=True),
            "availability": cells[2].get_text(strip=True).split()[0],  # A/B/C/D
            "project_url":  f"{STUDY_BASE}/{study_id}?lang=en&study_language=en",
            "published":    cells[4].get_text(strip=True),
        })
    return studies


def parse_study_detail(soup: BeautifulSoup) -> dict:
    """Extract abstract, authors, keywords, license from a study detail page."""
    result = {"abstract": "", "authors": [], "keywords": [], "license": ""}

    # Abstract
    for h2 in soup.find_all("h2"):
        if "abstract" in h2.get_text(strip=True).lower():
            parts = []
            for sib in h2.find_next_siblings():
                if sib.name in ("h1", "h2", "h3"):
                    break
                text = sib.get_text(" ", strip=True)
                if text:
                    parts.append(text)
            result["abstract"] = " ".join(parts)
            break

    # Authors
    for h2 in soup.find_all("h2"):
        if h2.get_text(strip=True).lower() == "authors":
            sibling = h2.find_next_sibling(["ul", "ol", "p"])
            if sibling:
                for li in sibling.find_all("li"):
                    name = li.get_text(" ", strip=True).split("(")[0].strip()
                    if name:
                        result["authors"].append(name)
            break

    # Keywords
    for h2 in soup.find_all("h2"):
        if h2.get_text(strip=True).lower() == "keywords":
            sibling = h2.find_next_sibling()
            if sibling:
                for kw in sibling.get_text(strip=True).split(","):
                    kw = kw.strip()
                    if kw:
                        result["keywords"].append(kw)
            break

    # License / access condition
    access_tag = soup.find(string=re.compile(r"dataset is \([ABCD]\)", re.I))
    if access_tag:
        result["license"] = access_tag.strip()[:500]

    return result


def download_ddi_xml(study_id: str, dest_dir: Path) -> str:
    """Download the DDI XML metadata file — always publicly available."""
    url  = DDI_PATTERN.format(sid=study_id)
    dest = dest_dir / f"{study_id}_eng.xml"
    if dest.exists():
        return STATUS_SUCCESS
    try:
        r = requests.get(url, headers=HEADERS, timeout=30)
        if r.status_code == 404:
            return STATUS_HTTP_404
        r.raise_for_status()
        dest.write_bytes(r.content)
        return STATUS_SUCCESS
    except requests.Timeout:
        return STATUS_TIMEOUT
    except Exception:
        return STATUS_HTTP_ERROR


def try_download_open_files(study_id: str, soup: BeautifulSoup,
                            dest_dir: Path) -> list[dict]:
    """For availability=A datasets try to download actual data files."""
    results = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if re.search(
            r'\.(zip|pdf|txt|docx|rtf|qdpx|qda|xlsx|csv|odt|doc)$',
            href, re.I
        ):
            fname    = href.split("/")[-1].split("?")[0]
            ext      = Path(fname).suffix.lstrip(".")
            full_url = (
                href if href.startswith("http")
                else f"https://services.fsd.tuni.fi{href}"
            )
            status = download_file(full_url, dest_dir / fname)
            results.append({"file_name": fname, "file_type": ext, "status": status})
    return results


def run(data_root: Path):
    print("\n[FSD] Scraping catalogue (professor's exact URL)...")
    total_new  = 0
    total_skip = 0

    for page in range(MAX_PAGES):
        params = {**CATALOGUE_PARAMS, "page": page}
        print(f"\n  Page {page}...")
        soup = get_soup(CATALOGUE_BASE, params)
        if soup is None:
            print(f"  Failed to fetch page {page}, stopping.")
            break

        studies = parse_catalogue_page(soup)
        if not studies:
            print(f"  No studies on page {page} — reached end.")
            break

        print(f"  Found {len(studies)} studies on page {page}")
        download_date = datetime.now(timezone.utc).isoformat()

        for s in studies:
            study_id     = s["study_id"]
            project_url  = s["project_url"]
            availability = s["availability"]

            if project_exists(project_url):
                total_skip += 1
                continue

            # Get detail page for full metadata
            detail_soup = get_soup(
                f"{STUDY_BASE}/{study_id}",
                {"lang": "en", "study_language": "en"}
            )
            detail = parse_study_detail(detail_soup) if detail_soup else {}

            dest_dir = data_root / REPO_FOLDER / study_id
            dest_dir.mkdir(parents=True, exist_ok=True)

            project_data = {
                "query_string":               "data_kind_string_facet=Qualitative lang=en",
                "repository_id":              REPO_ID,
                "repository_url":             REPO_URL,
                "project_url":                project_url,
                "version":                    None,
                "title":                      s["title"][:500],
                "description":                detail.get("abstract", "")[:2000],
                "language":                   "en",
                "doi":                        None,
                "upload_date":                s["published"],
                "download_date":              download_date,
                "download_repository_folder": REPO_FOLDER,
                "download_project_folder":    study_id,
                "download_version_folder":    None,
                "download_method":            "SCRAPING",
            }
            project_id = insert_project(project_data)
            print(f"  [NEW] {study_id} ({availability}) — {s['title'][:50]}")

            for kw in detail.get("keywords", []):
                insert_keyword(project_id, kw)
            for name in detail.get("authors", []):
                insert_person(project_id, name, ROLE_AUTHOR)

            license_str = detail.get("license") or f"Availability class {availability}"
            insert_license(project_id, license_str)

            # Always download DDI XML (always public)
            ddi_status = download_ddi_xml(study_id, dest_dir)
            insert_file(project_id, f"{study_id}_eng.xml", "xml", ddi_status)

            # Try actual data files for open (A) datasets
            if availability == "A" and detail_soup:
                file_results = try_download_open_files(
                    study_id, detail_soup, dest_dir
                )
                if file_results:
                    for f in file_results:
                        insert_file(
                            project_id, f["file_name"],
                            f["file_type"], f["status"]
                        )
                else:
                    insert_file(
                        project_id, "data_files", "",
                        STATUS_NO_DOWNLOAD_LINK
                    )
            else:
                # B/C/D requires Aila login — cannot download without account
                insert_file(project_id, "data_files", "", STATUS_LOGIN_REQUIRED)

            total_new += 1
            time.sleep(0.8)

        time.sleep(1)

    print(f"\n[FSD] Done. New: {total_new}, Skipped: {total_skip}")