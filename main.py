#!/usr/bin/env python3
"""
QDArchive Part 1 — Data Acquisition
Usage:
    python3 main.py                    # run all scrapers
    python3 main.py --source dryad     # Dryad only
    python3 main.py --source fsd       # FSD only
    python3 main.py --export           # export DB to CSV only
    python3 main.py --stats            # show download statistics
"""
import argparse
from pathlib import Path
from db.database import init_db, get_project_count, get_file_status_summary
from scrapers import dryad_scraper, fsd_scraper
from export.csv_exporter import export_to_csv

DATA_ROOT = Path(__file__).parent / "data"


def main():
    parser = argparse.ArgumentParser(description="QDArchive data acquisition pipeline")
    parser.add_argument("--source", choices=["dryad", "fsd", "all"], default="all")
    parser.add_argument("--export", action="store_true", help="Export DB to CSV only")
    parser.add_argument("--stats",  action="store_true", help="Show download stats")
    args = parser.parse_args()

    print("Initializing database...")
    init_db()

    if args.stats:
        print(f"\nTotal projects: {get_project_count()}")
        print("\nFile download status summary:")
        for status, count in sorted(get_file_status_summary().items()):
            print(f"  {status:<40} {count}")
        return

    if args.export:
        export_to_csv()
        return

    if args.source in ("dryad", "all"):
        dryad_scraper.run(DATA_ROOT)

    if args.source in ("fsd", "all"):
        fsd_scraper.run(DATA_ROOT)

    print("\nExporting metadata to CSV...")
    export_to_csv()

    print("\nDownload statistics:")
    for status, count in sorted(get_file_status_summary().items()):
        print(f"  {status:<40} {count}")

    print("\nDone.")


if __name__ == "__main__":
    main()