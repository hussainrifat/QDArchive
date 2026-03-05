from __future__ import annotations

import json
import zipfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import requests

from download_policy import DownloadPolicy, select_files
from util import ensure_dir, is_qda_file, safe_slug, try_download_file

DATAVERSE_BASE = "https://dataverse.no"
SEARCH_API = f"{DATAVERSE_BASE}/api/search"
DATASET_API = f"{DATAVERSE_BASE}/api/datasets"


def search_dataverse(
    *,
    session: requests.Session,
    timeout: int,
    user_agent: str,
    limit: int
) -> List[Dict]:
    q = '(qualitative OR interview OR transcript OR "focus group" OR NVivo OR MAXQDA OR "Atlas.ti" OR REFI OR QDA OR qdpx OR nvpx OR atlasproj OR mx24 OR mx22 OR mx20)'
    headers = {"User-Agent": user_agent}

    results: List[Dict] = []
    start = 0
    per_page = 50

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

    direct = data.get("termsOfUse") or data.get("license")
    if direct and str(direct).strip():
        return str(direct).strip()

    latest = data.get("latestVersion") or {}
    terms = latest.get("termsOfUse") or latest.get("license")
    if terms and str(terms).strip():
        return str(terms).strip()

    blocks = latest.get("metadataBlocks") or {}
    for block in blocks.values():
        fields = block.get("fields") or []
        for f in fields:
            name = (f.get("typeName") or "").lower()
            value = f.get("value")
            if any(k in name for k in ["license", "terms", "rights", "conditions"]):
                if isinstance(value, str) and value.strip():
                    return value.strip()
                if isinstance(value, list):
                    joined = " ; ".join([str(x).strip() for x in value if str(x).strip()])
                    if joined:
                        return joined

    return None


def dataset_files(dataset_json: Dict) -> List[Dict]:
    data = dataset_json.get("data") or {}
    latest = data.get("latestVersion") or {}
    files = latest.get("files") or []
    return files if isinstance(files, list) else []


def _is_zip(filename: str) -> bool:
    return filename.lower().endswith(".zip")


def qda_files_inside_zip(zip_path: Path, qda_exts: List[str]) -> List[str]:
    found: List[str] = []
    try:
        with zipfile.ZipFile(zip_path, "r") as z:
            for name in z.namelist():
                if name.endswith("/"):
                    continue
                if is_qda_file(name, qda_exts):
                    found.append(name)
    except zipfile.BadZipFile:
        return []
    return found


def record_has_qda_or_zip(dataset_json: Dict, qda_exts: List[str]) -> bool:
    for f in dataset_files(dataset_json):
        df = f.get("dataFile") or {}
        name = df.get("filename")
        if not name:
            continue
        if is_qda_file(name, qda_exts):
            return True
        if _is_zip(name):
            return True
    return False


def download_dataset(
    *,
    dataset_item: Dict,
    dataset_json: Dict,
    downloads_root: Path,
    qda_exts: List[str],
    session: requests.Session,
    connect_timeout: int,
    read_timeout: int,
    user_agent: str,
    policy: DownloadPolicy,
    run_budget_left_bytes: int,
    dataverse_download_primary_only_if_qda_present: bool = True,
) -> Tuple[str, List[Tuple[str, str]], int]:
    title = dataset_item.get("name") or "dataverse-dataset"
    slug = safe_slug(title)

    local_dir_rel = f"dataverseno/{slug}"
    local_dir = downloads_root / local_dir_rel
    ensure_dir(local_dir)

    (local_dir / "metadata.json").write_text(json.dumps(dataset_json, indent=2), encoding="utf-8")

    files = dataset_files(dataset_json)

    qda_present = False
    zip_present = False
    for f in files:
        df = f.get("dataFile") or {}
        name = df.get("filename") or ""
        if is_qda_file(name, qda_exts):
            qda_present = True
        if _is_zip(name):
            zip_present = True

    allow_primary = policy.download_primary_data
    if dataverse_download_primary_only_if_qda_present:
        allow_primary = allow_primary and (qda_present or zip_present)

    candidates: List[Dict] = []
    for f in files:
        df = f.get("dataFile") or {}
        file_id = df.get("id")
        filename = df.get("filename")
        if not file_id or not filename:
            continue

        dl_url = f"{DATAVERSE_BASE}/api/access/datafile/{file_id}"

        size = df.get("filesize")
        size_bytes = int(size) if isinstance(size, int) else None

        ext = Path(filename).suffix.lower().lstrip(".")
        is_qda = is_qda_file(filename, qda_exts)
        is_zip = _is_zip(filename)
        is_primary = allow_primary and (ext in policy.allowed_primary_exts)

        if not (is_qda or is_zip or is_primary):
            continue

        candidates.append({"name": filename, "url": dl_url, "size_bytes": size_bytes})

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
            continue

        if _is_zip(name):
            inner_qdas = qda_files_inside_zip(out_path, qda_exts)
            for inner in inner_qdas:
                qda_rows.append((f"{url}#{inner}", f"{name}::{inner}"))

    return local_dir_rel, qda_rows, run_bytes_used