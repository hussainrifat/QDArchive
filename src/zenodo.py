from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import requests

from src.util import ensure_dir, is_qda_file, safe_slug, try_download_file, get_json_with_retries

ZENODO_API = "https://zenodo.org/api/records"


def _broad_query() -> str:
    return (
        '(qualitative OR "qualitative data" OR interview OR transcript OR "focus group" OR ethnograph* '
        'OR "grounded theory" OR "thematic analysis" OR "content analysis" OR "coding") '
        'AND (NVivo OR MAXQDA OR "ATLAS.ti" OR "Atlas.ti" OR REFI OR QDA OR qdpx OR nvpx OR atlasproj OR mx24 OR mx22 OR mx20)'
    )


def search_records_overfetch(
    *,
    qda_exts: List[str],  # kept for signature compatibility
    session: requests.Session,
    connect_timeout: int,
    read_timeout: int,
    user_agent: str,
    overfetch: int
) -> List[Dict]:
    q = _broad_query()
    headers = {"User-Agent": user_agent}

    results: List[Dict] = []
    page = 1
    size = 25
    max_pages = 80

    while len(results) < overfetch:
        params = {"q": q, "page": page, "size": size}

        if page == 1 or page % 5 == 0:
            print(f"Zenodo search: requesting page {page}, collected {len(results)}/{overfetch}")

        data = get_json_with_retries(
            ZENODO_API,
            session=session,
            headers=headers,
            params=params,
            connect_timeout=connect_timeout,
            read_timeout=read_timeout,
            max_retries=4,
        )

        hits = (data.get("hits") or {}).get("hits") or []
        if not hits:
            break

        results.extend(hits)
        page += 1

        if page > max_pages:
            print(f"Zenodo search: reached max_pages={max_pages}, stopping search phase.")
            break

    return results[:overfetch]


def extract_license(record: Dict) -> Optional[str]:
    md = record.get("metadata") or {}
    lic = md.get("license")
    if isinstance(lic, dict):
        return lic.get("id") or lic.get("title")
    if isinstance(lic, str):
        return lic
    return None


def extract_uploader(record: Dict) -> Tuple[Optional[str], Optional[str]]:
    md = record.get("metadata") or {}
    creators = md.get("creators") or []
    if creators and isinstance(creators, list):
        c0 = creators[0] or {}
        return c0.get("name"), None
    return None, None


def record_has_qda_file(record: Dict, qda_exts: List[str]) -> bool:
    files = record.get("files") or []
    for f in files:
        key = f.get("key")
        if key and is_qda_file(key, qda_exts):
            return True
    return False


def download_record(
    *,
    record: Dict,
    downloads_root: Path,
    qda_exts: List[str],
    session: requests.Session,
    connect_timeout: int,
    read_timeout: int,
    user_agent: str,
    policy,
    run_budget_left_bytes: int,
) -> Tuple[str, List[Tuple[str, str]], int]:
    rec_id = str(record.get("id", "unknown"))
    md = record.get("metadata") or {}
    title = md.get("title") or f"zenodo-{rec_id}"

    slug = safe_slug(title)
    local_dir_rel = f"zenodo/{slug}-{rec_id}"
    local_dir = downloads_root / local_dir_rel
    ensure_dir(local_dir)

    (local_dir / "metadata.json").write_text(json.dumps(record, indent=2), encoding="utf-8")

    files = record.get("files") or []

    candidates = []
    for f in files:
        key = f.get("key")
        links = f.get("links") or {}
        dl_url = links.get("self") or links.get("download")
        if not key or not dl_url:
            continue

        size_bytes = f.get("size")
        if not isinstance(size_bytes, int):
            size_bytes = None

        candidates.append({"name": key, "url": dl_url, "size_bytes": size_bytes})

    selected = policy.select_files(candidates) if hasattr(policy, "select_files") else candidates

    qda_rows: List[Tuple[str, str]] = []
    bytes_used = 0

    for f in selected:
        key = f["name"]
        url = f["url"]
        size_bytes = f.get("size_bytes")

        remaining_run = run_budget_left_bytes - bytes_used
        if remaining_run <= 0:
            break

        max_for_this_file = min(policy.max_bytes_per_file, remaining_run)

        if isinstance(size_bytes, int) and size_bytes > max_for_this_file:
            continue

        out_path = local_dir / key

        ok, nbytes = try_download_file(
            url,
            out_path,
            session=session,
            connect_timeout=connect_timeout,
            read_timeout=read_timeout,
            user_agent=user_agent,
            max_bytes=max_for_this_file,
        )
        if not ok:
            continue

        bytes_used += nbytes

        if is_qda_file(key, qda_exts):
            qda_rows.append((url, key))

    return local_dir_rel, qda_rows, bytes_used