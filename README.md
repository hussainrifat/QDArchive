# Seeding QDArchive – Part 1 (Acquisition)

This pipeline automatically:
- searches Zenodo + DataverseNO for datasets likely containing QDA files
- filters locally for real QDA file extensions
- skips datasets without license info
- downloads all dataset files into a structured folder
- records each downloaded QDA file in SQLite
- exports SQLite to metadata.csv

## Setup
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt