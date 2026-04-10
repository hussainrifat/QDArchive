"""
Dryad scraper — Dryad REST API v2
Professor's example: https://datadryad.org/search?q=qualitative+research

Confirmed behaviour:
  - Search and metadata endpoints work with browser User-Agent
  - File downloads require OAuth2 Bearer token
  - Rate limit: HTTP 429 returned when downloading too fast — retry with backoff
  - Get credentials from: datadryad.org -> Login -> My Account -> API credentials
  - Add DRYAD_CLIENT_ID and DRYAD_CLIENT_SECRET to your .env file
"""

import os
import time
import requests
from dotenv import load_dotenv
from datetime import datetime, timezone
from pathlib import Path

from db.database import (
    insert_project, insert_file, insert_keyword,
    insert_person, insert_license, project_exists,
    STATUS_SUCCESS, STATUS_LOGIN_REQUIRED, STATUS_HTTP_404,
    STATUS_HTTP_ERROR, STATUS_NO_DOWNLOAD_LINK,
    STATUS_TIMEOUT, STATUS_UNKNOWN, ROLE_AUTHOR
)

load_dotenv()

BASE_API    = "https://datadryad.org/api/v2"
REPO_FOLDER = "dryad"
REPO_ID     = 1
REPO_URL    = "https://datadryad.org"

DRYAD_CLIENT_ID     = os.getenv("DRYAD_CLIENT_ID", "")
DRYAD_CLIENT_SECRET = os.getenv("DRYAD_CLIENT_SECRET", "")

# Queries aligned with professor's worklog + additional qualitative methods
QUERIES = [
    "qualitative research",
    "qualitative data",
    "interview study",
    "qualitative research data",
    "qdpx",
    "interview transcripts",
    "focus group qualitative",
    "thematic analysis",
    "grounded theory",
    "semi structured interview",
    "case study qualitative",
    "phenomenology",
    "content analysis qualitative",
    "discourse analysis",
    "interview transcript",
]

PER_PAGE       = 100
MAX_PAGES      = 20
DOWNLOAD_DELAY = 2.0


def get_oauth_token() -> str:
    if not DRYAD_CLIENT_ID or not DRYAD_CLIENT_SECRET:
        return ""
    try:
        r = requests.post(
            "https://datadryad.org/oauth/token",
            data={
                "grant_type":    "client_credentials",
                "client_id":     DRYAD_CLIENT_ID,
                "client_secret": DRYAD_CLIENT_SECRET,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded;charset=UTF-8"},
            timeout=30,
        )
        if r.status_code == 200:
            token = r.json().get("access_token", "")
            print(f"[Dryad] OAuth token obtained successfully")
            return token
        else:
            print(f"[Dryad] Token request failed: {r.status_code} {r.text[:100]}")
            return ""
    except Exception as e:
        print(f"[Dryad] Token error: {e}")
        return ""


def build_headers(token: str) -> dict:
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/122.0.0.0 Safari/537.36"
        ),
        "Accept": "application/json",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def api_get(path: str, headers: dict, params: dict = None) -> dict | None:
    url = f"{BASE_API}/{path.lstrip('/')}"
    try:
        r = requests.get(url, headers=headers, params=params, timeout=30)
        if r.status_code == 200:
            return r.json()
        print(f"  [API {r.status_code}] {url}")
        return None
    except requests.Timeout:
        print(f"  [TIMEOUT] {url}")
        return None
    except Exception as e:
        print(f"  [ERROR] {url}: {e}")
        return None


def search_datasets(query: str, headers: dict):
    """Yield dataset dicts from all pages of search results."""
    for page in range(1, MAX_PAGES + 1):
        data = api_get("search", headers, {
            "q": query, "per_page": PER_PAGE, "page": page
        })
        if not data:
            break
        datasets = data.get("_embedded", {}).get("stash:datasets", [])
        if not datasets:
            break
        for ds in datasets:
            yield ds
        if len(datasets) < PER_PAGE:
            break
        time.sleep(0.5)


def get_latest_version_id(dataset_id: int, headers: dict) -> int | None:
    """Get the latest version ID for a dataset."""
    data = api_get(f"datasets/{dataset_id}/versions", headers, {"per_page": 1})
    if not data:
        return None
    versions = data.get("_embedded", {}).get("stash:versions", [])
    return versions[0].get("id") if versions else None


def get_file_list(version_id: int, headers: dict) -> list[dict]:
    """Return all file metadata dicts for a version."""
    data = api_get(f"versions/{version_id}/files", headers, {"per_page": 1000})
    if not data:
        return []
    return data.get("_embedded", {}).get("stash:files", [])


def download_single_file(url: str, dest_path: Path, headers: dict,
                         max_retries: int = 3) -> str:
    """
    Download one file with retry logic for rate limiting (HTTP 429).
    On 429: waits 60s per attempt then retries up to max_retries times.
    """
    if dest_path.exists():
        return STATUS_SUCCESS

    dest_path.parent.mkdir(parents=True, exist_ok=True)

    for attempt in range(1, max_retries + 1):
        try:
            r = requests.get(url, headers=headers, timeout=120, stream=True)

            if r.status_code == 200:
                with open(dest_path, "wb") as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)
                return STATUS_SUCCESS

            elif r.status_code == 429:
                wait = 60 * attempt
                print(f"    [429] attempt {attempt}/{max_retries} — waiting {wait}s...")
                time.sleep(wait)
                continue

            elif r.status_code in (401, 403):
                return STATUS_LOGIN_REQUIRED
            elif r.status_code == 404:
                return STATUS_HTTP_404
            else:
                return f"FAILED_HTTP_{r.status_code}"

        except requests.Timeout:
            if attempt < max_retries:
                time.sleep(10)
                continue
            return STATUS_TIMEOUT
        except Exception as e:
            print(f"    [DL ERROR] {url}: {e}")
            return STATUS_HTTP_ERROR

    return "FAILED_HTTP_429"


def run(data_root: Path, query_override: str = None):
    token = get_oauth_token()
    if token:
        print("[Dryad] Token obtained — file downloads enabled")
    else:
        print("[Dryad] No credentials — metadata only")
        print("        Add DRYAD_CLIENT_ID and DRYAD_CLIENT_SECRET to .env")

    headers   = build_headers(token)
    queries   = [query_override] if query_override else QUERIES
    seen_dois = set()

    for query in queries:
        print(f"\n[Dryad] Query: '{query}'")
        new_count = 0

        for ds in search_datasets(query, headers):
            doi = ds.get("identifier", "")
            if not doi or doi in seen_dois:
                continue
            seen_dois.add(doi)

            project_url = f"https://datadryad.org/dataset/{doi}"
            if project_exists(project_url):
                continue

            # ── Metadata ──────────────────────────────────────────────
            title       = (ds.get("title") or "Untitled")[:500]
            description = (ds.get("abstract") or "")[:2000]
            upload_date = ds.get("publicationDate") or ""
            doi_url     = f"https://doi.org/{doi}"
            dataset_id  = ds.get("id")

            authors = []
            for a in ds.get("authors") or []:
                first = (a.get("firstName") or "").strip()
                last  = (a.get("lastName")  or "").strip()
                name  = f"{first} {last}".strip()
                if name:
                    authors.append(name)

            keywords    = [k for k in (ds.get("keywords") or []) if k]
            license_str = ds.get("license") or ""

            # Extract version ID from _links to avoid extra API call
            version_href = (
                ds.get("_links", {})
                  .get("stash:version", {})
                  .get("href", "")
            )
            version_id = None
            if version_href:
                try:
                    version_id = int(version_href.rstrip("/").split("/")[-1])
                except ValueError:
                    pass

            project_folder = str(dataset_id)
            dest_dir       = data_root / REPO_FOLDER / project_folder
            dest_dir.mkdir(parents=True, exist_ok=True)

            download_date = datetime.now(timezone.utc).isoformat()

            project_data = {
                "query_string":               query,
                "repository_id":              REPO_ID,
                "repository_url":             REPO_URL,
                "project_url":                project_url,
                "version":                    None,
                "title":                      title,
                "description":                description,
                "language":                   "en",
                "doi":                        doi_url,
                "upload_date":                upload_date,
                "download_date":              download_date,
                "download_repository_folder": REPO_FOLDER,
                "download_project_folder":    project_folder,
                "download_version_folder":    None,
                "download_method":            "API-CALL",
            }
            project_id = insert_project(project_data)
            print(f"  [NEW] {doi} — {title[:55]}")

            for kw in keywords:
                insert_keyword(project_id, str(kw))
            for name in authors:
                insert_person(project_id, name, ROLE_AUTHOR)
            if license_str:
                insert_license(project_id, license_str[:500])

            # ── Files ─────────────────────────────────────────────────
            if not version_id:
                version_id = get_latest_version_id(dataset_id, headers)

            if not version_id:
                insert_file(project_id, "dataset_files", "", STATUS_UNKNOWN)
                new_count += 1
                time.sleep(1)
                continue

            files = get_file_list(version_id, headers)

            if not files:
                insert_file(project_id, "dataset_files", "", STATUS_NO_DOWNLOAD_LINK)
            else:
                downloaded = 0
                for f in files:
                    fname   = f.get("path") or "unknown_file"
                    ext     = Path(fname).suffix.lstrip(".").lower()
                    dl_href = (
                        f.get("_links", {})
                         .get("stash:download", {})
                         .get("href", "")
                    )

                    if not dl_href:
                        insert_file(project_id, fname, ext, STATUS_NO_DOWNLOAD_LINK)
                        continue

                    full_url  = (
                        dl_href if dl_href.startswith("http")
                        else f"https://datadryad.org{dl_href}"
                    )
                    dest_path = dest_dir / Path(fname).name
                    status    = download_single_file(
                        full_url, dest_path, headers, max_retries=3
                    )
                    insert_file(project_id, fname, ext, status)

                    if status == STATUS_SUCCESS:
                        downloaded += 1

                    time.sleep(DOWNLOAD_DELAY)

                print(f"    → {len(files)} files, {downloaded} downloaded")

            new_count += 1
            time.sleep(1)

        print(f"  Query '{query}' done — {new_count} new projects")