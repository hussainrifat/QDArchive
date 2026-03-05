from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import requests

from util import download_file, ensure_dir, is_qda_file, safe_slug


ZENODO_API = "https://zenodo.org/api/records"


def _broad_query(qda_exts: List[str]) -> str:
    # Broad keyword query, then we filter by real QDA extensions in the file list.
    terms = [e.lower().lstrip(".") for e in qda_exts]
    terms = list(dict.fromkeys(terms))[:20]
    return "(" + " OR ".join(terms) + ")"


def search_records(
    *,
    qda_exts: List[str],
    session: requests.Session,
    timeout: int,
    user_agent: str,
    limit: int
) -> List[Dict]:
    q = _broad_query(qda_exts)

    headers = {"User-Agent": user_agent}
    page = 1
    size = min(max(limit, 1), 25)

    results: List[Dict] = []
    while len(results) < limit:
        params = {"q": q, "page": page, "size": size}
        r = session.get(ZENODO_API, params=params, headers=headers, timeout=timeout)
        r.raise_for_status()
        data = r.json()

        hits = (data.get("hits") or {}).get("hits") or []
        if not hits:
            break

        results.extend(hits)

        total = (data.get("hits") or {}).get("total") or 0
        if len(results) >= total:
            break

        page += 1
        if page > 200:
            break

    return results[:limit]


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
    timeout: int,
    user_agent: str
) -> Tuple[str, List[Tuple[str, str]]]:
    rec_id = str(record.get("id", "unknown"))
    md = record.get("metadata") or {}
    title = md.get("title") or f"zenodo-{rec_id}"

    slug = safe_slug(title)
    local_dir_rel = f"zenodo/{slug}-{rec_id}"
    local_dir = downloads_root / local_dir_rel
    ensure_dir(local_dir)

    (local_dir / "metadata.json").write_text(json.dumps(record, indent=2), encoding="utf-8")

    files = record.get("files") or []
    qda_rows: List[Tuple[str, str]] = []

    for f in files:
        key = f.get("key")
        links = f.get("links") or {}
        dl_url = links.get("self") or links.get("download")
        if not key or not dl_url:
            continue

        out_path = local_dir / key
        download_file(dl_url, out_path, session=session, timeout=timeout, user_agent=user_agent)

        if is_qda_file(key, qda_exts):
            qda_rows.append((dl_url, key))

    return local_dir_rel, qda_rows