from __future__ import annotations

from dataclasses import dataclass

from util import ext_lower, is_qda_file


@dataclass
class DownloadPolicy:
    max_files_per_dataset: int
    max_total_bytes_per_dataset: int
    max_bytes_per_file: int
    max_total_bytes_per_run: int

    download_primary_data: bool
    allowed_primary_exts: set[str]
    skip_exts: set[str]

    qda_exts: list[str]


def policy_from_config(cfg: dict, qda_exts: list[str]) -> DownloadPolicy:
    dp = cfg.get("download_policy") or {}

    def mb_to_bytes(mb: int) -> int:
        return int(mb) * 1024 * 1024

    return DownloadPolicy(
        max_files_per_dataset=int(dp.get("max_files_per_dataset", 25)),
        max_total_bytes_per_dataset=mb_to_bytes(int(dp.get("max_total_mb_per_dataset", 800))),
        max_bytes_per_file=mb_to_bytes(int(dp.get("max_mb_per_file", 250))),
        max_total_bytes_per_run=mb_to_bytes(int(dp.get("max_total_mb_per_run", 5000))),
        download_primary_data=bool(dp.get("download_primary_data", True)),
        allowed_primary_exts=set([str(x).lower().lstrip(".") for x in dp.get("allowed_primary_exts", [])]),
        skip_exts=set([str(x).lower().lstrip(".") for x in dp.get("skip_exts", [])]),
        qda_exts=qda_exts,
    )


def is_allowed(filename: str, policy: DownloadPolicy) -> tuple[bool, str]:
    ext = ext_lower(filename)

    if ext in policy.skip_exts:
        return False, f"skip_ext:{ext}"

    if is_qda_file(filename, policy.qda_exts):
        return True, f"qda_ext:{ext}"

    if policy.download_primary_data and ext in policy.allowed_primary_exts:
        return True, f"primary_ext:{ext}"

    return False, f"not_allowed_ext:{ext}"


def select_files(files: list[dict], policy: DownloadPolicy) -> list[dict]:
    """
    Each file dict must contain:
      name: str
      url: str
      size_bytes: int | None
    This returns selected files enriched with:
      reason: str
      is_qda: bool
    """

    enriched: list[dict] = []
    for f in files:
        name = f.get("name") or ""
        ok, reason = is_allowed(name, policy)
        if not ok:
            continue
        f2 = dict(f)
        f2["reason"] = reason
        f2["is_qda"] = is_qda_file(name, policy.qda_exts)
        enriched.append(f2)

    enriched.sort(key=lambda x: (0 if x.get("is_qda") else 1))

    chosen: list[dict] = []
    total = 0

    for f in enriched:
        if len(chosen) >= policy.max_files_per_dataset:
            break

        size = f.get("size_bytes")
        if isinstance(size, int) and size > policy.max_bytes_per_file:
            continue

        if isinstance(size, int) and (total + size) > policy.max_total_bytes_per_dataset:
            continue

        chosen.append(f)
        if isinstance(size, int):
            total += size

    return chosen