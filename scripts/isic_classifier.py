"""
Part 2 Step 2 — ISIC Rev. 5 Classifier
Classifies each project into ISIC Section + Division using Claude API
"""

import os
import time
import json
import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

import anthropic

sys.path.insert(0, str(Path(__file__).parent.parent))
from db.database import get_connection

ISIC_CONTEXT = """
ISIC Rev. 5 Sections (use these exact codes):
A - Agriculture, forestry and fishing
B - Mining and quarrying
C - Manufacturing
D - Electricity, gas, steam and air conditioning supply
E - Water supply; sewerage, waste management and remediation activities
F - Construction
G - Wholesale and retail trade; repair of motor vehicles and motorcycles
H - Transportation and storage
I - Accommodation and food service activities
J - Publishing, broadcasting, and content production and distribution activities
K - Telecommunications, computer programming, consultancy, computing infrastructure and other information service activities
L - Financial and insurance activities
M - Real estate activities
N - Professional, scientific and technical activities
O - Administrative and support service activities
P - Public administration and defence; compulsory social security
Q - Education
R - Human health and social work activities
S - Arts, entertainment and recreation
T - Other service activities
U - Activities of households as employers
V - Activities of extraterritorial organizations and bodies

Key divisions relevant to qualitative research:
01 - Crop and animal production (agriculture studies)
86 - Human health activities (medical/nursing/patient research)
87 - Residential care activities
88 - Social work activities without accommodation
85 - Education (teaching, learning, schools, universities)
72 - Scientific research and development (general academic research)
73 - Advertising and market research (consumer studies)
90 - Creative, arts and entertainment activities
91 - Libraries, archives, museums and other cultural activities
94 - Activities of membership organizations (community, NGO research)
84 - Public administration and defence
66 - Activities auxiliary to financial services

Guidance:
- Health/medical/nursing/patient research → Section R, division 86
- Social science/sociology/anthropology research → Section N, division 72
- Education/teaching/learning research → Section Q, division 85
- Environmental/ecology research → Section N, division 72
- Psychology/mental health research → Section R, division 86
- Agriculture/farming research → Section A, division 01
- Business/management/organization research → Section N, division 72
- Community/social work research → Section R, division 88
- Arts/culture/media research → Section S, division 90
- Technology/computer science research → Section K, division 72
- Criminal justice/policing research → Section P, division 84
- If unclear → Section N, division 72
"""

client = anthropic.Anthropic()


def classify_project(title: str, description: str, keywords: list) -> dict:
    """Use Claude to classify a project into ISIC Rev. 5 Section + Division."""

    kw_str = ", ".join(keywords[:10]) if keywords else "none"

    prompt = f"""You are an expert in the ISIC Rev. 5 (International Standard Industrial Classification) taxonomy.

Classify this qualitative research project into the most appropriate ISIC Rev. 5 Section and Division.

{ISIC_CONTEXT}

Project to classify:
Title: {title[:200]}
Description: {description[:500]}
Keywords: {kw_str}

Respond with ONLY a JSON object in this exact format, no other text:
{{"section_code": "R", "section_name": "Human health and social work activities", "division_code": "86", "division_name": "Human health activities", "confidence": "high"}}

Rules:
- section_code must be a single letter A-V
- division_code must be a 2-digit number as a string
- confidence must be: high, medium, or low
- Choose based on the RESEARCH TOPIC not the research method
- If unclear use section N division 72
"""

    try:
        message = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=200,
            messages=[{"role": "user", "content": prompt}]
        )

        text = message.content[0].text.strip()
        text = text.replace("```json", "").replace("```", "").strip()
        result = json.loads(text)
        return result

    except Exception as e:
        print(f"    [ERROR] Classification failed: {e}")
        return {
            "section_code": "N",
            "section_name": "Professional, scientific and technical activities",
            "division_code": "72",
            "division_name": "Scientific research and development",
            "confidence": "low"
        }


def add_isic_columns():
    """Add ISIC columns to PROJECTS table if they don't exist."""
    conn = get_connection()
    existing = [r[1] for r in conn.execute('PRAGMA table_info(PROJECTS)').fetchall()]

    columns_to_add = [
        ('isic_section_code', 'TEXT'),
        ('isic_section_name', 'TEXT'),
        ('isic_division_code', 'TEXT'),
        ('isic_division_name', 'TEXT'),
        ('isic_confidence', 'TEXT'),
    ]

    for col_name, col_type in columns_to_add:
        if col_name not in existing:
            conn.execute(f'ALTER TABLE PROJECTS ADD COLUMN {col_name} {col_type}')
            print(f'Added column: {col_name}')

    conn.commit()
    conn.close()


def run_classifier(limit: int = None, only_unclassified: bool = True):
    """Run ISIC classification on all projects."""

    add_isic_columns()
    conn = get_connection()

    if only_unclassified:
        query = """
            SELECT p.id, p.title, p.description, p.type
            FROM PROJECTS p
            WHERE p.isic_section_code IS NULL
            ORDER BY p.type, p.id
        """
    else:
        query = """
            SELECT p.id, p.title, p.description, p.type
            FROM PROJECTS p
            ORDER BY p.type, p.id
        """

    projects = conn.execute(query).fetchall()

    if limit:
        projects = projects[:limit]

    total = len(projects)
    print(f"Classifying {total} projects...")
    print()

    for i, (project_id, title, description, project_type) in enumerate(projects, 1):
        keywords = [r[0] for r in conn.execute(
            'SELECT keyword FROM KEYWORDS WHERE project_id=? LIMIT 10',
            (project_id,)
        ).fetchall()]

        result = classify_project(
            title or "Unknown",
            description or "",
            keywords
        )

        conn.execute("""
            UPDATE PROJECTS SET
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
            project_id
        ))

        if i % 10 == 0:
            conn.commit()

        print(f"  [{i}/{total}] {result.get('section_code')}-{result.get('division_code')} "
              f"({result.get('confidence')}) — {(title or '')[:60]}")

        time.sleep(0.1)

    conn.commit()

    print()
    print("=== ISIC CLASSIFICATION RESULTS BY SECTION ===")
    for r in conn.execute("""
        SELECT isic_section_code, isic_section_name, COUNT(*)
        FROM PROJECTS
        WHERE isic_section_code IS NOT NULL
        GROUP BY isic_section_code, isic_section_name
        ORDER BY COUNT(*) DESC
    """).fetchall():
        print(f"  {r[0]} — {r[1]}: {r[2]}")

    print()
    print("=== BY REPO AND PROJECT TYPE ===")
    for r in conn.execute("""
        SELECT r.name, p.type, p.isic_section_code, COUNT(*)
        FROM PROJECTS p
        JOIN REPOSITORIES r ON r.id=p.repository_id
        WHERE p.isic_section_code IS NOT NULL
        GROUP BY r.name, p.type, p.isic_section_code
        ORDER BY r.name, p.type, COUNT(*) DESC
    """).fetchall():
        print(f"  {r[0]:<8} {r[1]:<20} {r[2]} {r[3]}")

    conn.close()
    print()
    print("Done.")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--limit', type=int, help='Only classify this many projects (for testing)')
    parser.add_argument('--all', action='store_true', help='Re-classify already classified projects')
    args = parser.parse_args()

    run_classifier(
        limit=args.limit,
        only_unclassified=not args.all
    )