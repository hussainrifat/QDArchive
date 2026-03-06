from __future__ import annotations

from typing import Dict, List

import requests

from src import db as dbmod
from src.util import utc_now_iso
from src.download_policy import DownloadPolicy
from src.zenodo import (
    search_records_overfetch as zen_search_overfetch,
    extract_license as zen_license,
    extract_uploader as zen_uploader,
    record_has_qda_file as zen_has_qda,
    download_record as zen_download,
)


def acquire(
    *,
    conn,
    qda_exts: List[str],
    session: requests.Session,
    timeout: int,
    user_agent: str,
    downloads_root,
    limit: int,
    policy: DownloadPolicy,
    run_budget_left_bytes: int,
    connect_timeout: int,
    read_timeout: int,
    cfg: dict,
) -> Dict:
    scanned = skipped_no_license = skipped_no_qda = downloaded_datasets = inserted_rows = 0
    bytes_used = 0

    overfetch = max(limit * 10, 100)

    candidates = zen_search_overfetch(
        qda_exts=qda_exts,
        session=session,
        connect_timeout=connect_timeout,
        read_timeout=read_timeout,
        user_agent=user_agent,
        overfetch=overfetch,
    )

    for rec in candidates:
        if downloaded_datasets >= limit:
            break
        if bytes_used >= run_budget_left_bytes:
            break

        scanned += 1

        lic = zen_license(rec)
        if not lic:
            skipped_no_license += 1
            continue

        if not zen_has_qda(rec, qda_exts):
            skipped_no_qda += 1
            continue

        uploader_name, uploader_email = zen_uploader(rec)

        local_dir_rel, qda_rows, used = zen_download(
            record=rec,
            downloads_root=downloads_root,
            qda_exts=qda_exts,
            session=session,
            connect_timeout=connect_timeout,
            read_timeout=read_timeout,
            user_agent=user_agent,
            policy=policy,
            run_budget_left_bytes=(run_budget_left_bytes - bytes_used),
        )

        bytes_used += used
        downloaded_datasets += 1
        ts = utc_now_iso()

        for qda_url, qda_filename in qda_rows:
            dbmod.insert_acquisition(
                conn,
                qda_file_url=qda_url,
                download_timestamp=ts,
                local_dir=local_dir_rel,
                local_qda_filename=qda_filename,
                context_repository="Zenodo",
                license_str=lic,
                uploader_name=uploader_name,
                uploader_email=uploader_email,
            )
            inserted_rows += 1

    return {
        "scanned": scanned,
        "skipped_no_license": skipped_no_license,
        "skipped_no_qda": skipped_no_qda,
        "downloaded_datasets": downloaded_datasets,
        "inserted_rows": inserted_rows,
        "bytes_used": bytes_used,
    }