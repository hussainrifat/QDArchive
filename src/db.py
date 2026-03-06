from __future__ import annotations

import csv
import sqlite3
from pathlib import Path
from typing import Optional

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS acquisitions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  qda_file_url TEXT NOT NULL,
  download_timestamp TEXT NOT NULL,
  local_dir TEXT NOT NULL,
  local_qda_filename TEXT NOT NULL,
  context_repository TEXT,
  license TEXT,
  uploader_name TEXT,
  uploader_email TEXT
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_acq_qda_file_url ON acquisitions(qda_file_url);
CREATE INDEX IF NOT EXISTS idx_acq_local_dir ON acquisitions(local_dir);
"""

def connect(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn

def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA_SQL)
    conn.commit()

def insert_acquisition(
    conn: sqlite3.Connection,
    *,
    qda_file_url: str,
    download_timestamp: str,
    local_dir: str,
    local_qda_filename: str,
    context_repository: Optional[str] = None,
    license_str: Optional[str] = None,
    uploader_name: Optional[str] = None,
    uploader_email: Optional[str] = None,
) -> None:
    conn.execute(
        """
        INSERT OR IGNORE INTO acquisitions
        (qda_file_url, download_timestamp, local_dir, local_qda_filename,
         context_repository, license, uploader_name, uploader_email)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            qda_file_url,
            download_timestamp,
            local_dir,
            local_qda_filename,
            context_repository,
            license_str,
            uploader_name,
            uploader_email,
        ),
    )
    conn.commit()

def export_csv(conn: sqlite3.Connection, out_csv: Path) -> None:
    rows = conn.execute(
        """
        SELECT
          qda_file_url AS url,
          download_timestamp AS download_timestamp,
          local_dir AS local_directory,
          local_qda_filename AS filename,
          context_repository AS source,
          license AS license,
          uploader_name AS uploader_name,
          uploader_email AS uploader_email,
          (local_dir || '/' || local_qda_filename) AS local_path,
          lower(substr(local_qda_filename, instr(local_qda_filename, '.') + 1)) AS file_ext
        FROM acquisitions
        ORDER BY id ASC
        """
    ).fetchall()

    out_csv.parent.mkdir(parents=True, exist_ok=True)
    with out_csv.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(
            [
                "url",
                "download_timestamp",
                "local_directory",
                "filename",
                "source",
                "license",
                "uploader_name",
                "uploader_email",
                "local_path",
                "file_ext",
            ]
        )
        w.writerows(rows)