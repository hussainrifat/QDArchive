import csv
from pathlib import Path
from db.database import get_connection

EXPORT_PATH = Path(__file__).parent.parent / "export" / "metadata.csv"


def export_to_csv():
    EXPORT_PATH.parent.mkdir(exist_ok=True)
    conn = get_connection()
    rows = conn.execute("""
        SELECT
            p.id, p.title, p.description, p.project_url, p.doi,
            p.language, p.upload_date, p.download_date,
            p.download_repository_folder, p.download_project_folder,
            p.download_method, p.query_string,
            r.name AS repository_name, r.url AS repository_url
        FROM PROJECTS p
        JOIN REPOSITORIES r ON r.id = p.repository_id
        ORDER BY p.id
    """).fetchall()
    conn.close()

    with open(EXPORT_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "id", "title", "description", "project_url", "doi",
            "language", "upload_date", "download_date",
            "repository_folder", "project_folder",
            "download_method", "query_string",
            "repository_name", "repository_url"
        ])
        writer.writerows(rows)

    print(f"Exported {len(rows)} projects to {EXPORT_PATH}")