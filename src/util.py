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


def _sleep_backoff(attempt: int) -> None:
    # 0 -> 0.5s, 1 -> 1s, 2 -> 2s, 3 -> 4s ...
    time.sleep(min(8.0, 0.5 * (2 ** attempt)))


def get_json_with_retries(
    url: str,
    *,
    session: requests.Session,
    headers: dict,
    params: dict | None,
    connect_timeout: int,
    read_timeout: int,
    max_retries: int = 4,
) -> dict:
    last_err: Exception | None = None
    for attempt in range(max_retries + 1):
        try:
            r = session.get(
                url,
                params=params,
                headers=headers,
                timeout=(connect_timeout, read_timeout),
            )
            r.raise_for_status()
            return r.json()
        except (requests.RequestException, ValueError) as e:
            last_err = e
            if attempt >= max_retries:
                break
            _sleep_backoff(attempt)
    raise RuntimeError(f"GET JSON failed after retries: {url} ({last_err})")


def download_file(
    url: str,
    out_path: Path,
    *,
    session: requests.Session,
    connect_timeout: int,
    read_timeout: int,
    user_agent: str,
    max_bytes: int | None = None
) -> int:
    """
    Downloads url to out_path.
    If max_bytes is set, aborts when exceeded.
    Returns number of bytes written.
    """
    headers = {"User-Agent": user_agent}
    ensure_dir(out_path.parent)

    tmp_path = out_path.with_suffix(out_path.suffix + ".partial")
    written = 0

    with session.get(url, stream=True, timeout=(connect_timeout, read_timeout), headers=headers) as r:
        r.raise_for_status()
        with tmp_path.open("wb") as f:
            for chunk in r.iter_content(chunk_size=1024 * 256):
                if not chunk:
                    continue
                written += len(chunk)
                if max_bytes is not None and written > max_bytes:
                    f.close()
                    try:
                        tmp_path.unlink(missing_ok=True)
                    except Exception:
                        pass
                    raise ValueError(f"File too large: exceeded {max_bytes} bytes")
                f.write(chunk)

    tmp_path.replace(out_path)
    return written


def try_download_file(
    url: str,
    out_path: Path,
    *,
    session: requests.Session,
    connect_timeout: int,
    read_timeout: int,
    user_agent: str,
    max_bytes: int | None = None
) -> tuple[bool, int]:
    """
    Safe download wrapper.
    Returns (ok, bytes_written).
    ok False for HTTP errors or size abort.
    """
    try:
        n = download_file(
            url,
            out_path,
            session=session,
            connect_timeout=connect_timeout,
            read_timeout=read_timeout,
            user_agent=user_agent,
            max_bytes=max_bytes,
        )
        return True, n
    except (requests.RequestException, ValueError):
        return False, 0