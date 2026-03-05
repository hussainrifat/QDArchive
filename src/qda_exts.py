from __future__ import annotations

from pathlib import Path
from typing import List, Set

import openpyxl


DEFAULT_QDA_EXTS = [
    # REFI-QDA
    "qdpx",
    "qdc",

    # NVivo
    "nvpx",
    "nvp",

    # ATLAS.ti
    "atlasproj",
    "hpr7",

    # MAXQDA (common)
    "mqda",
    "mx24",
    "mx24bac",
    "mx22",
    "mx20",
    "mx18",
    "mx12",
    "mx11",
    "mx5",
    "mx4",
    "mx3",
    "mx2",
    "m2k",
]


def load_qda_extensions(xlsx_path: Path) -> List[str]:
    if not xlsx_path.exists():
        return sorted(set(DEFAULT_QDA_EXTS))

    wb = openpyxl.load_workbook(str(xlsx_path))
    ws = wb.active

    exts: Set[str] = set()
    for row in ws.iter_rows(values_only=True):
        for v in row:
            if not v:
                continue
            s = str(v).strip().lower().lstrip(".")
            if 2 <= len(s) <= 30 and all(ch.isalnum() or ch in {"_", "-"} for ch in s):
                exts.add(s)

    # Always include our safe defaults
    exts.update(DEFAULT_QDA_EXTS)

    # Remove known bad extension for qualitative QDA search
    exts.discard("qdp")

    return sorted(exts)