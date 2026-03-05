from __future__ import annotations

import argparse
import importlib
import json
from pathlib import Path
from typing import Dict, List

import requests

from src import db as dbmod
from src.download_policy import policy_from_config
from src.qda_exts import load_qda_extensions
from src.util import ensure_dir


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
    csv_path = Path(cfg.get("csv_path", "metadata.csv"))
    qda_xlsx = Path(cfg.get("qda_extensions_xlsx", "QDA File Extensions Formats.xlsx"))

    connect_timeout = int(cfg.get("http_connect_timeout_sec", 15))
    read_timeout = int(cfg.get("http_read_timeout_sec", 30))

    api_timeout = int(cfg.get("http_timeout_sec", max(connect_timeout, read_timeout)))
    user_agent = str(cfg.get("user_agent", "SeedingQDArchive/Part1"))

    sources: List[str] = list(cfg.get("sources") or [])

    ensure_dir(downloads_root)

    qda_exts = load_qda_extensions(qda_xlsx)
    print("Loaded QDA extensions:", len(qda_exts))

    policy = policy_from_config(cfg, qda_exts)
    run_bytes_used = 0

    conn = dbmod.connect(sqlite_path)
    dbmod.init_db(conn)

    with requests.Session() as session:
        for src in sources:
            print()
            print("Running source:", src)

            budget_left = policy.max_total_bytes_per_run - run_bytes_used
            if budget_left <= 0:
                print("Run budget reached, stopping.")
                break

            try:
                mod = importlib.import_module(src)
            except ModuleNotFoundError:
                # fallback if someone configured sources as "src.sources.x"
                mod = importlib.import_module(f"src.{src}")

            stats: Dict = mod.acquire(
                conn=conn,
                qda_exts=qda_exts,
                session=session,
                timeout=api_timeout,
                user_agent=user_agent,
                downloads_root=downloads_root,
                limit=args.limit,
                policy=policy,
                run_budget_left_bytes=budget_left,
                connect_timeout=connect_timeout,
                read_timeout=read_timeout,
                cfg=cfg,
            )

            used = int(stats.get("bytes_used") or 0)
            run_bytes_used += used

            print(f"{src}_scanned:", stats.get("scanned", 0))
            print(f"{src}_skipped_no_license:", stats.get("skipped_no_license", 0))
            print(f"{src}_skipped_no_qda:", stats.get("skipped_no_qda", 0))
            print(f"{src}_downloaded_datasets:", stats.get("downloaded_datasets", 0))
            print(f"{src}_inserted_qda_rows:", stats.get("inserted_rows", 0))
            print(f"{src}_bytes_used:", used)

    dbmod.export_csv(conn, csv_path)

    print()
    print("Done.")
    print("Downloads folder:", downloads_root.resolve())
    print("SQLite DB:", sqlite_path.resolve())
    print("CSV export:", csv_path.resolve())
    print("Run downloaded bytes:", run_bytes_used)


if __name__ == "__main__":
    main()