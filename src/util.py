from __future__ import annotations

import re
import time
from pathlib import Path
from typing import Iterable, Set

import requests


def utc_now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def safe_slug(text: str, max_len: int = 80) -> str:
    text = (text or "").strip().lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = re.sub(r"-{2,}", "-", text).strip("-")
    if not text:
        text = "dataset"
    return text[:max_len].strip("-")


def ext_lower(filename: str) -> str:
    return Path(filename).suffix.lower().lstrip(".")


def is_qda_file(filename: str, qda_exts: Iterable[str]) -> bool:
    e = ext_lower(filename)
    s: Set[str] = {x.lower().lstrip(".") for x in qda_exts}
    return e in s


def download_file(
    url: str,
    out_path: Path,
    *,
    session: requests.Session,
    timeout: int,
    user_agent: str
) -> None:
    headers = {"User-Agent": user_agent}
    ensure_dir(out_path.parent)
    with session.get(url, stream=True, timeout=timeout, headers=headers) as r:
        r.raise_for_status()
        with out_path.open("wb") as f:
            for chunk in r.iter_content(chunk_size=1024 * 256):
                if chunk:
                    f.write(chunk)