from __future__ import annotations

from typing import Dict, List

import requests

from src import db as dbmod
from src.util import utc_now_iso
from src.download_policy import DownloadPolicy
from src.dataverse import (
    search_dataverse,
    get_dataset_details,
    extract_license as dv_license,
    record_has_qda_or_zip as dv_has_qda_or_zip,
    download_dataset as dv_download,
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

    dp = cfg.get("download_policy") or {}
    only_if_qda = bool(dp.get("dataverse_download_primary_only_if_qda_present", True))

    items = search_dataverse(
        session=session,
        timeout=timeout,
        user_agent=user_agent,
        limit=max(limit * 15, 150),
    )

    for item in items:
        if downloaded_datasets >= limit:
            break
        if bytes_used >= run_budget_left_bytes:
            break

        scanned += 1

        pid = item.get("global_id") or item.get("globalId")
        if not pid:
            continue

        ds_json = get_dataset_details(
            persistent_id=pid,
            session=session,
            timeout=timeout,
            user_agent=user_agent,
        )

        lic = dv_license(ds_json)
        if not lic:
            skipped_no_license += 1
            continue

        if not dv_has_qda_or_zip(ds_json, qda_exts):
            skipped_no_qda += 1
            continue

        local_dir_rel, qda_rows, used = dv_download(
            dataset_item=item,
            dataset_json=ds_json,
            downloads_root=downloads_root,
            qda_exts=qda_exts,
            session=session,
            connect_timeout=connect_timeout,
            read_timeout=read_timeout,
            user_agent=user_agent,
            policy=policy,
            run_budget_left_bytes=(run_budget_left_bytes - bytes_used),
            dataverse_download_primary_only_if_qda_present=only_if_qda,
        )

        bytes_used += used

        if not qda_rows:
            continue

        downloaded_datasets += 1
        ts = utc_now_iso()

        for qda_url, qda_filename in qda_rows:
            dbmod.insert_acquisition(
                conn,
                qda_file_url=qda_url,
                download_timestamp=ts,
                local_dir=local_dir_rel,
                local_qda_filename=qda_filename,
                context_repository="DataverseNO",
                license_str=str(lic),
                uploader_name=None,
                uploader_email=None,
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
