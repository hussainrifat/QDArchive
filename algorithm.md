# Data Acquisition Algorithm

This document describes the algorithm used by the Seeding QDArchive pipeline to acquire qualitative research datasets from open repositories.

The pipeline currently supports the following repositories:

- Zenodo
- DataverseNO

The system performs a series of steps to search, filter, download, and store qualitative datasets.

---

# Pipeline Overview

The acquisition pipeline follows this workflow:

1. Load configuration
2. Load known QDA file extensions
3. Query repository APIs
4. Filter datasets
5. Download dataset files
6. Detect QDA project files
7. Store metadata in SQLite
8. Export metadata to CSV

---

# Step 1 – Configuration

The pipeline starts by reading the configuration file:

```
config.json
```

Configuration defines:

- download directory
- database path
- CSV export path
- repository sources
- HTTP settings

Example configuration:

```
downloads_root = my_downloads
sqlite_path = metadata.db
csv_path = metadata.csv
sources = [Zenodo, DataverseNO]
```

---

# Step 2 – Load QDA Extensions

The system loads known QDA project file extensions from:

```
QDA File Extensions Formats.xlsx
```

Examples of QDA file types:

- `.qdpx` (REFI-QDA)
- `.nvpx` (NVivo)
- `.atlasproj` (ATLAS.ti)
- `.mx24` (MAXQDA)

These extensions are used to identify QDA project files inside datasets.

---

# Step 3 – Repository Search

Each repository connector performs a search query using the repository API.

Example queries include terms such as:

- qualitative
- interview
- focus group
- NVivo
- MAXQDA
- Atlas.ti
- qdpx

The API returns a list of dataset records.

---

# Step 4 – Dataset Filtering

Each dataset is inspected before downloading.

The pipeline checks:

1. **License availability**

Datasets without license information are skipped.

2. **Relevant files**

Datasets must contain at least one of the following:

- QDA project files
- primary qualitative data files
- zipped dataset files

Datasets failing these conditions are ignored.

---

# Step 5 – Dataset Download

For valid datasets:

1. A local directory is created:

```
my_downloads/{source}/{dataset-slug}
```

2. The dataset metadata is saved as:

```
metadata.json
```

3. All selected files are downloaded into the dataset directory.

Download limits are applied to prevent extremely large datasets.

---

# Step 6 – QDA File Detection

After downloading files, the pipeline scans them to detect QDA project files.

Detection is performed by matching file extensions against the known QDA extension list.

Example:

```
interview_project.qdpx  → valid QDA file
survey_results.csv      → not a QDA project file
```

Only detected QDA files are recorded in the database.

---

# Step 7 – Store Metadata in SQLite

Each detected QDA file generates one database record.

The record is inserted into the SQLite table:

```
acquisitions
```

Stored fields include:

- QDA file URL
- download timestamp
- local directory
- local filename
- repository source
- license
- uploader information

---

# Step 8 – Export Metadata

After the acquisition process completes, the database is exported to:

```
metadata.csv
```

This file contains all stored metadata and can be used for further analysis.

---

# Deduplication

The system prevents duplicate records using:

```
UNIQUE(qda_file_url)
```

This ensures that the same QDA file is not inserted multiple times.

---

# Result

The final output consists of:

1. Downloaded dataset files
2. A structured SQLite metadata database
3. A CSV export for analysis

Together these outputs form the initial seed data for the QDArchive project.