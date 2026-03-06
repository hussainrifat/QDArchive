# Seeding QDArchive – Part 1 (Acquisition)

This project implements a **data acquisition pipeline** for the QDArchive project.

The pipeline automatically:

- searches **Zenodo** and **DataverseNO** for datasets likely containing QDA files  
- filters locally for real **QDA file extensions**  
- skips datasets **without license information**  
- downloads dataset files into a structured folder  
- records downloaded QDA files in **SQLite**  
- exports the database to **metadata.csv**

The goal is to automatically collect **open qualitative research datasets** and store them in a structured archive.

---

# Overview

The pipeline performs the following workflow:

1. Query open repositories for qualitative datasets  
2. Inspect dataset metadata  
3. Detect QDA project files using known extensions  
4. Download dataset files and metadata  
5. Store metadata in a local SQLite database  
6. Export results to CSV for analysis

---

# Supported Sources

| Source | Status |
|------|------|
| Zenodo | Implemented |
| DataverseNO | Implemented |

Additional repositories can easily be added later.

---

# Setup

Create a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

---

# Run the Pipeline

Execute the acquisition pipeline:

```bash
PYTHONPATH=src python3 run.py --limit 10
```

This will:

- search repositories  
- download datasets  
- store metadata in SQLite  
- export metadata to CSV

---

# Output Files

The pipeline produces three outputs.

## 1. Downloaded datasets

```
my_downloads/
    zenodo/
        dataset-slug/
            metadata.json
            files...
    dataverseno/
        dataset-slug/
            metadata.json
            files...
```

Each dataset is stored in its own directory.

---

## 2. SQLite database

```
metadata.db
```

Table:

```
acquisitions
```

Fields stored:

| Field | Description |
|------|------|
| qda_file_url | URL of the QDA file |
| download_timestamp | Timestamp of download |
| local_dir | Local dataset directory |
| local_qda_filename | Name of downloaded QDA file |
| context_repository | Repository source |
| license | Dataset license |
| uploader_name | Uploader name if available |
| uploader_email | Uploader email if available |

---

## 3. CSV export

```
metadata.csv
```

This file is exported from the SQLite database and contains the same metadata.

---

# Project Structure

```
QDArchive
│
├── run.py
├── config.json
├── requirements.txt
│
├── src
│   ├── db.py
│   ├── util.py
│   ├── zenodo.py
│   ├── dataverse.py
│   └── sources
│       ├── zenodo_source.py
│       └── dataverse_source.py
│
├── metadata.db
├── metadata.csv
└── my_downloads
```

---

# Reset Pipeline

To remove all downloaded data and start again:

```bash
rm -rf my_downloads
rm -f metadata.db metadata.csv
```

Then run the pipeline again.

---

# Notes

Not all qualitative datasets contain QDA project files.

Some datasets only include **primary qualitative data**, such as:

- interview transcripts  
- PDFs  
- CSV data tables  
- research documentation

These datasets may still be downloaded even if they do not produce entries in the acquisitions table.