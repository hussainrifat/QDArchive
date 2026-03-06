# Database Documentation

The acquisition pipeline stores metadata about downloaded QDA files in a SQLite database.

Database file:

```
metadata.db
```

The database contains a single table:

```
acquisitions
```

This document describes the database schema and how metadata is stored.

---

# Schema

Table: **acquisitions**

| Column | Type | Required | Description |
|------|------|------|------|
| id | INTEGER | auto | Auto-increment primary key |
| qda_file_url | TEXT | yes | URL of the downloaded QDA file |
| download_timestamp | TEXT | yes | Timestamp when the file was downloaded |
| local_dir | TEXT | yes | Local dataset directory inside `my_downloads` |
| local_qda_filename | TEXT | yes | Name of the downloaded QDA file |
| context_repository | TEXT | no | Repository source (e.g. Zenodo, DataverseNO) |
| license | TEXT | no | License associated with the dataset |
| uploader_name | TEXT | no | Name of the uploader if available |
| uploader_email | TEXT | no | Email of the uploader if available |

---

# Example Record

Example row stored in the database:

| Field | Example |
|------|------|
| qda_file_url | https://zenodo.org/record/12345/files/project.qdpx |
| download_timestamp | 2026-03-05T21:10:22Z |
| local_dir | zenodo/interview-study-2024 |
| local_qda_filename | project.qdpx |
| context_repository | Zenodo |
| license | CC-BY-4.0 |
| uploader_name | John Doe |
| uploader_email | john@example.com |

---

# Data Flow

Metadata is collected during the acquisition pipeline.

The workflow:

1. Repository is queried for datasets
2. Dataset metadata is retrieved via API
3. Files are downloaded locally
4. QDA files are detected using known extensions
5. Metadata is inserted into the SQLite database
6. The database is exported to CSV

---

# CSV Export

After the pipeline finishes, the database is exported to:

```
metadata.csv
```

This file contains the same columns as the database table.

Example CSV structure:

```
qda_file_url,download_timestamp,local_dir,local_qda_filename,context_repository,license,uploader_name,uploader_email
```

---

# Viewing the Database

You can inspect the database using SQLite.

Open the database:

```
sqlite3 metadata.db
```

Example query:

```
SELECT * FROM acquisitions;
```

Count records:

```
SELECT COUNT(*) FROM acquisitions;
```

Group by repository:

```
SELECT context_repository, COUNT(*) 
FROM acquisitions 
GROUP BY context_repository;
```

---

# Notes

The database only stores **QDA project files**.  

Other dataset files such as:

- PDF
- TXT
- CSV
- DOCX

may be downloaded but are not recorded in the `acquisitions` table unless they contain QDA project formats.

---

# Future Improvements

Possible extensions include:

- storing dataset titles and descriptions
- storing dataset DOIs
- recording file sizes
- storing dataset authors
- detecting QDA software automatically