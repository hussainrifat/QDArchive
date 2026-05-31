"""
Part 2 Step 3 — File-level ISIC classifier
Classifies each primary data file in QDA_PROJECT and QD_PROJECT
using the filename + parent project context.
"""

import os
import sys
import json
import time
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()
import anthropic

sys.path.insert(0, str(Path(__file__).parent.parent))
from db.database import get_connection

PRIMARY_EXTENSIONS = {'txt', 'pdf', 'docx', 'doc', 'rtf', 'odt', 'xlsx', 'csv', 'xls'}

DB_PATH = Path(__file__).parent.parent / "23025313-sq26-classification.db"

ISIC_CONTEXT = """
ISIC Rev. 5 Sections (use these exact codes):
A - Agriculture, forestry and fishing
B - Mining and quarrying
C - Manufacturing
D - Electricity, gas, steam and air conditioning supply
E - Water supply; sewerage, waste management
F - Construction
G - Wholesale and retail trade
H - Transportation and storage
I - Accommodation and food service activities
J - Publishing, broadcasting and content production
K - Telecommunications, computer programming, IT services
L - Financial and insurance activities
M - Real estate activities
N - Professional, scientific and technical activities
O - Administrative and support service activities
P - Public administration and defence
Q - Education
R - Human health and social work activities
S - Arts, entertainment and recreation
T - Other service activities
U - Activities of households as employers
V - Activities of extraterritorial organizations

Key divisions:
72 - Scientific research and development
86 - Human health activities
88 - Social work activities without accommodation
85 - Education
01 - Crop and animal production
90 - Creative, arts and entertainment activities
84 - Public administration and defence
66 - Activities auxiliary to financial services

Guidance:
- Health/medical/nursing/patient data → R/86
- Social science/sociology/anthropology → N/72
- Education/teaching/learning → Q/85
- Environmental/ecology → N/72
- Psychology/mental health → R/86
- Agriculture/farming → A/01
- Business/management → N/72
- Community/social work → R/88
- Arts/culture/media → S/90
- Technology/computer science → K/72 (use N for section if unclear)
- Criminal justice/policing → P/84
- If unclear → N/72
"""

client = anthropic.Anthropic()


def classify_file(file_name: str, file_type: str, project_title: str,
                  project_description: str, project_isic: dict) -> dict:
    prompt = f"""You are an ISIC Rev. 5 classification expert.

Classify this individual research data file into the most appropriate ISIC Section and Division.
The file belongs to a qualitative research project.

{ISIC_CONTEXT}

Parent project:
- Title: {project_title[:150]}
- Description: {(project_description or '')[:300]}
- Project ISIC: {project_isic.get('section_code')}/{project_isic.get('division_code')} ({project_isic.get('division_name')})

File to classify:
- Filename: {file_name}
- File type: .{file_type}

Respond with ONLY a JSON object, no other text:
{{"section_code": "R", "section_name": "Human health and social work activities", "division_code": "86", "division_name": "Human health activities", "confidence": "high"}}

Rules:
- section_code must be a single letter A-V
- division_code must be a 2-digit number as a string
- confidence: high, medium, or low
- Base classification on the filename and project context
- Usually matches parent project; only differ if filename clearly indicates another domain
- If unclear use the parent project's ISIC classification
"""
    try:
        message = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=150,
            messages=[{"role": "user", "content": prompt}]
        )
        text = message.content[0].text.strip()
        text = text.replace("```json", "").replace("```", "").strip()
        return json.loads(text)
    except Exception as e:
        return {
            "section_code": project_isic.get('section_code', 'N'),
            "section_name": project_isic.get('section_name', 'Professional, scientific and technical activities'),
            "division_code": project_isic.get('division_code', '72'),
            "division_name": project_isic.get('division_name', 'Scientific research and development'),
            "confidence": "low"
        }


def add_isic_columns_to_files(conn):
    existing = [r[1] for r in conn.execute('PRAGMA table_info(FILES)').fetchall()]
    cols = [
        ('isic_section_code', 'TEXT'),
        ('isic_section_name', 'TEXT'),
        ('isic_division_code', 'TEXT'),
        ('isic_division_name', 'TEXT'),
        ('isic_confidence', 'TEXT'),
    ]
    for col_name, col_type in cols:
        if col_name not in existing:
            conn.execute(f'ALTER TABLE FILES ADD COLUMN {col_name} {col_type}')
            print(f"  Added column: {col_name}")
    conn.commit()


def run(limit=None):
    import sqlite3
    conn = sqlite3.connect(str(DB_PATH))

    print("Adding ISIC columns to FILES table...")
    add_isic_columns_to_files(conn)

    ext_list = ','.join(f"'{e}'" for e in PRIMARY_EXTENSIONS)
    rows = conn.execute(f"""
        SELECT
            f.id, f.file_name, f.file_type,
            p.title, p.description,
            p.isic_section_code, p.isic_section_name,
            p.isic_division_code, p.isic_division_name
        FROM FILES f
        JOIN PROJECTS p ON f.project_id = p.id
        WHERE p.type IN ('QDA_PROJECT', 'QD_PROJECT')
        AND f.file_type IN ({ext_list})
        AND (f.isic_section_code IS NULL OR f.isic_section_code = '')
        ORDER BY p.id, f.id
    """).fetchall()

    if limit:
        rows = rows[:limit]

    total = len(rows)
    print(f"Classifying {total} primary data files...")
    print()

    for i, row in enumerate(rows, 1):
        (fid, fname, ftype, ptitle, pdesc,
         sec_code, sec_name, div_code, div_name) = row

        project_isic = {
            'section_code': sec_code, 'section_name': sec_name,
            'division_code': div_code, 'division_name': div_name
        }

        result = classify_file(fname, ftype, ptitle or '', pdesc or '', project_isic)

        conn.execute("""
            UPDATE FILES SET
                isic_section_code = ?,
                isic_section_name = ?,
                isic_division_code = ?,
                isic_division_name = ?,
                isic_confidence = ?
            WHERE id = ?
        """, (
            result.get('section_code'),
            result.get('section_name'),
            result.get('division_code'),
            result.get('division_name'),
            result.get('confidence'),
            fid
        ))

        if i % 50 == 0:
            conn.commit()
            print(f"  [{i}/{total}] committed...")
        elif i % 10 == 0:
            print(f"  [{i}/{total}] {result.get('section_code')}-{result.get('division_code')} — {fname[:50]}")

        time.sleep(0.05)

    conn.commit()

    print()
    print("=== FILE CLASSIFICATION SUMMARY ===")
    for r in conn.execute("""
        SELECT f.isic_section_code, f.isic_division_name, COUNT(*)
        FROM FILES f
        JOIN PROJECTS p ON f.project_id = p.id
        WHERE p.type IN ('QDA_PROJECT', 'QD_PROJECT')
        AND f.isic_section_code IS NOT NULL
        GROUP BY f.isic_section_code, f.isic_division_name
        ORDER BY COUNT(*) DESC LIMIT 15
    """).fetchall():
        print(f"  {r[0]}-{r[1]}: {r[2]}")

    conn.close()
    print()
    print("Done.")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--limit', type=int, help='Only classify this many files (for testing)')
    args = parser.parse_args()
    run(limit=args.limit)
