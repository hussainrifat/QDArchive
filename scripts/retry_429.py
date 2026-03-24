"""
Retry all Dryad files that previously failed with FAILED_HTTP_429.
Uses a smarter approach: longer delays, skip on persistent 429 instead of waiting.

Run: python3 scripts/retry_429.py
"""

import sys
import time
import requests
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from db.database import get_connection, STATUS_SUCCESS, STATUS_LOGIN_REQUIRED
from scrapers.dryad_scraper import get_oauth_token, build_headers

DATA_ROOT    = Path(__file__).parent.parent / "data"
FILE_DELAY   = 5.0   # seconds between each file — slower = less 429
BATCH_PAUSE  = 60    # seconds pause every 100 files
BATCH_SIZE   = 100


def update_file_status(file_id: int, new_status: str):
    conn = get_connection()
    conn.execute("UPDATE FILES SET status = ? WHERE id = ?", (new_status, file_id))
    conn.commit()
    conn.close()


def get_failed_files():
    conn = get_connection()
    rows = conn.execute("""
        SELECT
            f.id,
            f.file_name,
            f.file_type,
            p.download_project_folder,
            p.doi
        FROM FILES f
        JOIN PROJECTS p ON p.id = f.project_id
        WHERE f.status = 'FAILED_HTTP_429'
        ORDER BY p.id, f.id
    """).fetchall()
    conn.close()
    return rows


def get_file_download_url(doi: str, file_name: str, headers: dict) -> str | None:
    """Re-query the Dryad API to get a fresh download URL for a specific file."""
    BASE = "https://datadryad.org/api/v2"

    encoded = requests.utils.quote(doi, safe="")
    r = requests.get(f"{BASE}/datasets/{encoded}", headers=headers, timeout=30)
    if r.status_code != 200:
        return None

    ds = r.json()
    version_href = (
        ds.get("_links", {})
          .get("stash:version", {})
          .get("href", "")
    )
    if not version_href:
        return None

    try:
        version_id = int(version_href.rstrip("/").split("/")[-1])
    except ValueError:
        return None

    r2 = requests.get(
        f"{BASE}/versions/{version_id}/files",
        headers=headers,
        params={"per_page": 1000},
        timeout=30
    )
    if r2.status_code != 200:
        return None

    files = r2.json().get("_embedded", {}).get("stash:files", [])
    for f in files:
        if f.get("path", "") == file_name:
            href = (
                f.get("_links", {})
                 .get("stash:download", {})
                 .get("href", "")
            )
            if href:
                return href if href.startswith("http") else f"https://datadryad.org{href}"
    return None


def download_file_once(url: str, dest_path: Path, headers: dict) -> str:
    """
    Single attempt download — no long waits.
    Returns STATUS immediately, caller decides what to do on 429.
    """
    if dest_path.exists():
        return STATUS_SUCCESS

    dest_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        r = requests.get(url, headers=headers, timeout=120, stream=True)

        if r.status_code == 200:
            with open(dest_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
            return STATUS_SUCCESS
        elif r.status_code == 429:
            return "FAILED_HTTP_429"
        elif r.status_code in (401, 403):
            return STATUS_LOGIN_REQUIRED
        elif r.status_code == 404:
            return "FAILED_HTTP_404"
        else:
            return f"FAILED_HTTP_{r.status_code}"

    except requests.Timeout:
        return "FAILED_TIMEOUT"
    except Exception:
        return "FAILED_HTTP_ERROR"


def main():
    print("Getting OAuth token...")
    token   = get_oauth_token()
    headers = build_headers(token)

    if not token:
        print("ERROR: No token. Add DRYAD_CLIENT_ID and DRYAD_CLIENT_SECRET to .env")
        return

    failed = get_failed_files()
    total  = len(failed)
    print(f"Found {total} files to retry\n")

    fixed        = 0
    still_failed = 0
    skipped      = 0

    for i, row in enumerate(failed):
        file_id     = row[0]
        file_name   = row[1]
        project_dir = row[3]
        doi         = row[4]

        if not doi:
            skipped += 1
            continue

        raw_doi   = doi.replace("https://doi.org/", "")
        dest_dir  = DATA_ROOT / "dryad" / project_dir
        dest_path = dest_dir / Path(file_name).name

        # Already downloaded in a previous retry run
        if dest_path.exists():
            update_file_status(file_id, STATUS_SUCCESS)
            fixed += 1
            continue

        print(f"  [{i+1}/{total}] {file_name[:60]}")

        # Get fresh download URL
        dl_url = get_file_download_url(raw_doi, file_name, headers)
        if not dl_url:
            print(f"    Could not find URL — skipping")
            skipped += 1
            continue

        status = download_file_once(dl_url, dest_path, headers)
        update_file_status(file_id, status)

        if status == STATUS_SUCCESS:
            print(f"    Downloaded")
            fixed += 1
        elif status == "FAILED_HTTP_429":
            # Don't wait — just leave as 429 and come back next run
            print(f"    Rate limited — will retry next run")
            still_failed += 1
        else:
            print(f"    {status}")
            still_failed += 1

        time.sleep(FILE_DELAY)

        # Longer pause every BATCH_SIZE files
        if (i + 1) % BATCH_SIZE == 0:
            remaining = total - (i + 1)
            print(f"\n  --- Batch pause {BATCH_PAUSE}s --- "
                  f"({fixed} fixed, {still_failed} failed, {remaining} remaining)\n")
            time.sleep(BATCH_PAUSE)

    print(f"\nRetry session complete:")
    print(f"  Fixed:        {fixed}")
    print(f"  Still failed: {still_failed}")
    print(f"  Skipped:      {skipped}")
    print(f"\nRun again to retry remaining FAILED_HTTP_429 files.")


if __name__ == "__main__":
    main()