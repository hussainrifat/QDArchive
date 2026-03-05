from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import requests

from download_policy import DownloadPolicy, select_files
from util import ensure_dir, is_qda_file, safe_slug, try_download_file

ZENODO_API = "https://zenodo.org/api/records"


def _broad_query(qda_exts: List[str]) -> str:
    ext_terms = [e.lower().lstrip(".") for e in qda_exts]
    ext_terms = list(dict.fromkeys(ext_terms))[:15]
    ext_q = "(" + " OR ".join(ext_terms) + ")"
    qual_q = '(qualitative OR interview OR transcript OR "focus group" OR ethnograph OR coding)'
    return f"({ext_q}) AND {qual_q}"


def search_records_overfetch(
    *,
    qda_exts: List[str],
    session: requests.Session,
    timeout: int,
    user_agent: str,
    overfetch: int
) -> List[Dict]:
    q = _broad_query(qda_exts)
    headers = {"User-Agent": user_agent}

    results: List[Dict] = []
    page = 1
    size = 25

    while len(results) < overfetch:
        params = {"q": q, "page": page, "size": size}
        r = session.get(ZENODO_API, params=params, headers=headers, timeout=timeout)
        r.raise_for_status()
        data = r.json()

        hits = (data.get("hits") or {}).get("hits") or []
        if not hits:
            break

        results.extend(hits)
        page += 1

        if page > 200:
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
    policy: DownloadPolicy,
    run_budget_left_bytes: int
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
    candidates: List[Dict] = []
    for f in files:
        key = f.get("key")
        links = f.get("links") or {}
        dl_url = links.get("self") or links.get("download")
        if not key or not dl_url:
            continue

        size = f.get("size")
        size_bytes = int(size) if isinstance(size, int) else None

        candidates.append({"name": key, "url": dl_url, "size_bytes": size_bytes})

    selected = select_files(candidates, policy)

    qda_rows: List[Tuple[str, str]] = []
    dataset_bytes_used = 0
    run_bytes_used = 0

    for f in selected:
        name = f["name"]
        url = f["url"]
        size_bytes = f.get("size_bytes")

        remaining_dataset = policy.max_total_bytes_per_dataset - dataset_bytes_used
        remaining_run = run_budget_left_bytes - run_bytes_used
        if remaining_dataset <= 0 or remaining_run <= 0:
            break

        max_for_this_file = policy.max_bytes_per_file
        if remaining_dataset < max_for_this_file:
            max_for_this_file = remaining_dataset
        if remaining_run < max_for_this_file:
            max_for_this_file = remaining_run

        if isinstance(size_bytes, int) and size_bytes > max_for_this_file:
            continue

        out_path = local_dir / name
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

        dataset_bytes_used += nbytes
        run_bytes_used += nbytes

        if is_qda_file(name, qda_exts):
            qda_rows.append((url, name))

    return local_dir_rel, qda_rows, run_bytes_used