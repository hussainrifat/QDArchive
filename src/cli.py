from __future__ import annotations

import argparse
import json
from pathlib import Path

import requests

import db as dbmod
from qda_exts import load_qda_extensions
from util import ensure_dir, utc_now_iso

from zenodo import (
    search_records as zen_search,
    extract_license as zen_license,
    extract_uploader as zen_uploader,
    record_has_qda_file as zen_has_qda,
    download_record as zen_download,
)

from dataverse import (
    search_dataverse,
    get_dataset_details,
    extract_license as dv_license,
    record_has_qda as dv_has_qda,
    download_dataset as dv_download,
)


def load_config(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="config.json")
    ap.add_argument("--limit", type=int, default=10)
    args = ap.parse_args()

    cfg = load_config(Path(args.config))
    downloads_root = Path(cfg["downloads_root"])
    sqlite_path = Path(cfg["sqlite_path"])
    qda_xlsx = Path(cfg.get("qda_extensions_xlsx", "QDA File Extensions Formats.xlsx"))
    timeout = int(cfg.get("http_timeout_sec", 60))
    user_agent = str(cfg.get("user_agent", "SeedingQDArchive/Part1"))

    ensure_dir(downloads_root)

    qda_exts = load_qda_extensions(qda_xlsx)

    conn = dbmod.connect(sqlite_path)
    dbmod.init_db(conn)

    # counters so you can verify it’s working
    zen_scanned = zen_skip_no_license = zen_skip_no_qda = zen_downloaded = zen_rows = 0
    dv_scanned = dv_skip_no_license = dv_skip_no_qda = dv_downloaded = dv_rows = 0

    with requests.Session() as session:
        # -------------------
        # Zenodo acquisition
        # -------------------
        zen_records = zen_search(
            qda_exts=qda_exts,
            session=session,
            timeout=timeout,
            user_agent=user_agent,
            limit=args.limit,
        )

        for rec in zen_records:
            zen_scanned += 1

            lic = zen_license(rec)
            if not lic:
                zen_skip_no_license += 1
                continue

            if not zen_has_qda(rec, qda_exts):
                zen_skip_no_qda += 1
                continue

            uploader_name, uploader_email = zen_uploader(rec)

            local_dir_rel, qda_rows = zen_download(
                record=rec,
                downloads_root=downloads_root,
                qda_exts=qda_exts,
                session=session,
                timeout=timeout,
                user_agent=user_agent,
            )

            zen_downloaded += 1
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
                zen_rows += 1

        # -----------------------
        # DataverseNO acquisition
        # -----------------------
        dv_items = search_dataverse(
            qda_exts=qda_exts,
            session=session,
            timeout=timeout,
            user_agent=user_agent,
            limit=args.limit,
        )

        for item in dv_items:
            dv_scanned += 1
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
                dv_skip_no_license += 1
                continue

            if not dv_has_qda(ds_json, qda_exts):
                dv_skip_no_qda += 1
                continue

            local_dir_rel, qda_rows = dv_download(
                dataset_item=item,
                dataset_json=ds_json,
                downloads_root=downloads_root,
                qda_exts=qda_exts,
                session=session,
                timeout=timeout,
                user_agent=user_agent,
            )

            dv_downloaded += 1
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
                dv_rows += 1

    dbmod.export_csv(conn, Path("metadata.csv"))

    print("Done.")
    print("Zenodo scanned:", zen_scanned)
    print("Zenodo skipped (no license):", zen_skip_no_license)
    print("Zenodo skipped (no QDA file detected):", zen_skip_no_qda)
    print("Zenodo downloaded datasets:", zen_downloaded)
    print("Zenodo inserted QDA rows:", zen_rows)
    print("DataverseNO scanned:", dv_scanned)
    print("DataverseNO skipped (no license):", dv_skip_no_license)
    print("DataverseNO skipped (no QDA file detected):", dv_skip_no_qda)
    print("DataverseNO downloaded datasets:", dv_downloaded)
    print("DataverseNO inserted QDA rows:", dv_rows)
    print("Downloads folder:", downloads_root.resolve())
    print("SQLite DB:", sqlite_path.resolve())
    print("CSV export:", Path("metadata.csv").resolve())


if __name__ == "__main__":
    main()