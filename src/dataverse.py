from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import requests

from util import download_file, ensure_dir, is_qda_file, safe_slug

DATAVERSE_BASE = "https://dataverse.no"
SEARCH_API = f"{DATAVERSE_BASE}/api/search"
DATASET_API = f"{DATAVERSE_BASE}/api/datasets"


def search_dataverse(
    *,
    qda_exts: List[str],
    session: requests.Session,
    timeout: int,
    user_agent: str,
    limit: int
) -> List[Dict]:
    terms = list(dict.fromkeys([e.lower().lstrip(".") for e in qda_exts]))[:10]
    q = "(" + " OR ".join(terms) + ")"

    headers = {"User-Agent": user_agent}
    results: List[Dict] = []
    start = 0
    per_page = min(max(limit, 1), 50)

    while len(results) < limit:
        params = {
            "q": q,
            "type": "dataset",
            "start": start,
            "per_page": per_page,
            "sort": "date",
            "order": "desc",
        }
        r = session.get(SEARCH_API, params=params, headers=headers, timeout=timeout)
        r.raise_for_status()
        data = r.json()
        items = (data.get("data") or {}).get("items") or []
        if not items:
            break
        results.extend(items)
        start += per_page
        if start > 2000:
            break

    return results[:limit]


def get_dataset_details(
    *,
    persistent_id: str,
    session: requests.Session,
    timeout: int,
    user_agent: str
) -> Dict:
    headers = {"User-Agent": user_agent}
    url = f"{DATASET_API}/:persistentId/?persistentId={persistent_id}"
    r = session.get(url, headers=headers, timeout=timeout)
    r.raise_for_status()
    return r.json()


def extract_license(dataset_json: Dict) -> Optional[str]:
    data = dataset_json.get("data") or {}
    return data.get("termsOfUse") or data.get("license")


def dataset_files(dataset_json: Dict) -> List[Dict]:
    data = dataset_json.get("data") or {}
    latest = data.get("latestVersion") or {}
    files = latest.get("files") or []
    return files if isinstance(files, list) else []


def record_has_qda(dataset_json: Dict, qda_exts: List[str]) -> bool:
    for f in dataset_files(dataset_json):
        df = f.get("dataFile") or {}
        name = df.get("filename")
        if name and is_qda_file(name, qda_exts):
            return True
    return False


def download_dataset(
    *,
    dataset_item: Dict,
    dataset_json: Dict,
    downloads_root: Path,
    qda_exts: List[str],
    session: requests.Session,
    timeout: int,
    user_agent: str
) -> Tuple[str, List[Tuple[str, str]]]:
    title = dataset_item.get("name") or "dataverse-dataset"
    slug = safe_slug(title)
    local_dir_rel = f"dataverseno/{slug}"
    local_dir = downloads_root / local_dir_rel
    ensure_dir(local_dir)

    (local_dir / "metadata.json").write_text(json.dumps(dataset_json, indent=2), encoding="utf-8")

    qda_rows: List[Tuple[str, str]] = []
    for f in dataset_files(dataset_json):
        df = f.get("dataFile") or {}
        file_id = df.get("id")
        filename = df.get("filename")
        if not file_id or not filename:
            continue

        dl_url = f"{DATAVERSE_BASE}/api/access/datafile/{file_id}"
        out_path = local_dir / filename
        download_file(dl_url, out_path, session=session, timeout=timeout, user_agent=user_agent)

        if is_qda_file(filename, qda_exts):
            qda_rows.append((dl_url, filename))

    return local_dir_rel, qda_rows