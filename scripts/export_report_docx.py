"""
Export classification report as an editable Word (.docx) document.
Charts are embedded as PNG images. All text is in proper Word styles
so the document can be freely edited and formatted.
"""

import sqlite3, io, datetime
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

from docx import Document
from docx.shared import Inches, Pt, RGBColor, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

DB_PATH  = Path(__file__).parent.parent / "23025313-sq26-classification.db"
OUT_PATH = Path(__file__).parent.parent / "export" / "23025313-classification-report.docx"

# ── Colours ───────────────────────────────────────────────────────────────────
NAVY  = RGBColor(0x00, 0x38, 0x65)
BLUE  = RGBColor(0x2E, 0x75, 0xB6)
GOLD  = RGBColor(0xC8, 0xA9, 0x51)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
GREY  = RGBColor(0x59, 0x59, 0x59)
STRIPE = "DEEAF1"   # hex string for XML shading

SECTION_COLORS = {
    "N": "#2E75B6", "R": "#C00000", "A": "#548235",
    "Q": "#7030A0", "P": "#E36C09", "S": "#0070C0",
    "K": "#FF6600",
}

# ── Document style helpers ────────────────────────────────────────────────────

def set_cell_bg(cell, hex_color):
    tc   = cell._tc
    tcPr = tc.get_or_add_tcPr()
    shd  = OxmlElement("w:shd")
    shd.set(qn("w:val"),   "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"),  hex_color)
    tcPr.append(shd)


def set_cell_border(cell, **kwargs):
    tc   = cell._tc
    tcPr = tc.get_or_add_tcPr()
    tcBorders = OxmlElement("w:tcBorders")
    for edge, color in kwargs.items():
        tag = OxmlElement(f"w:{edge}")
        tag.set(qn("w:val"),   "single")
        tag.set(qn("w:sz"),    "4")
        tag.set(qn("w:color"), color)
        tcBorders.append(tag)
    tcPr.append(tcBorders)


def heading(doc, text, level=1, color=None):
    p = doc.add_heading(text, level=level)
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    for run in p.runs:
        run.font.color.rgb = color or NAVY
        if level == 1:
            run.font.size = Pt(16)
        elif level == 2:
            run.font.size = Pt(13)
        else:
            run.font.size = Pt(11)
    return p


def body(doc, text, space_after=8):
    p = doc.add_paragraph(text)
    p.style = doc.styles["Normal"]
    p.paragraph_format.space_after  = Pt(space_after)
    p.paragraph_format.space_before = Pt(0)
    for run in p.runs:
        run.font.size = Pt(10.5)
    return p


def gold_rule(doc):
    """A thin gold paragraph border used as a section divider."""
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(6)
    p.paragraph_format.space_after  = Pt(6)
    pPr = p._p.get_or_add_pPr()
    pBdr = OxmlElement("w:pBdr")
    bottom = OxmlElement("w:bottom")
    bottom.set(qn("w:val"),   "single")
    bottom.set(qn("w:sz"),    "6")
    bottom.set(qn("w:color"), "C8A951")
    pBdr.append(bottom)
    pPr.append(pBdr)
    return p


def page_break(doc):
    doc.add_page_break()


# ── Data helpers ───────────────────────────────────────────────────────────────

def get_distrib(conn, repo, ptype):
    return conn.execute("""
        SELECT p.isic_section_code, p.isic_division_code,
               p.isic_division_name, COUNT(*) AS cnt
        FROM PROJECTS p JOIN REPOSITORIES r ON r.id=p.repository_id
        WHERE r.name=? AND p.type=?
        GROUP BY p.isic_section_code, p.isic_division_code
        ORDER BY cnt DESC
    """, (repo, ptype)).fetchall()


def get_repo_summary(conn):
    return conn.execute("""
        SELECT r.name,
               SUM(CASE WHEN p.type='QDA_PROJECT'   THEN 1 ELSE 0 END),
               SUM(CASE WHEN p.type='QD_PROJECT'    THEN 1 ELSE 0 END),
               SUM(CASE WHEN p.type='OTHER_PROJECT' THEN 1 ELSE 0 END),
               SUM(CASE WHEN p.type='NOT_A_PROJECT' THEN 1 ELSE 0 END),
               COUNT(*)
        FROM PROJECTS p JOIN REPOSITORIES r ON r.id=p.repository_id
        GROUP BY r.name ORDER BY r.name DESC
    """).fetchall()


# ── Chart generator ────────────────────────────────────────────────────────────

def make_chart_image(rows, title):
    """Render a horizontal bar chart and return PNG bytes."""
    if not rows:
        return None

    n      = len(rows)
    labels = [r[2] for r in rows]
    counts = [r[3] for r in rows]
    colors = [SECTION_COLORS.get(r[0], "#2E75B6") for r in rows]
    codes  = [f"{r[0]}-{r[1]}" for r in rows]

    fig_h = max(2.5, 0.55 + n * 0.42)
    fig, ax = plt.subplots(figsize=(7.0, fig_h))

    ypos  = list(range(n - 1, -1, -1))
    bar_h = min(0.55, 3.5 / max(n, 1))
    bars  = ax.barh(ypos, counts, height=bar_h,
                    color=list(reversed(colors)),
                    edgecolor="white", linewidth=0.6)

    xmax = max(counts)
    for bar, cnt, code in zip(bars, reversed(counts), reversed(codes)):
        ax.text(bar.get_width() + xmax * 0.015,
                bar.get_y() + bar.get_height() / 2,
                f"{cnt}  ({code})",
                va="center", ha="left", fontsize=8.5,
                color="#333333")

    ax.set_yticks(ypos)
    ax.set_yticklabels(list(reversed(labels)), fontsize=9)
    ax.set_ylim(-0.6, n - 0.4)
    ax.set_xlabel("Number of Projects", fontsize=9, color="#777777")
    ax.set_xlim(0, xmax * 1.28)
    ax.xaxis.set_major_locator(mticker.MaxNLocator(integer=True, nbins=6))
    ax.xaxis.grid(True, linestyle="--", alpha=0.4, zorder=0)
    ax.set_axisbelow(True)
    ax.set_title(title, fontsize=10, fontweight="bold",
                 color="#003865", pad=8)
    for sp in ["top", "right"]:
        ax.spines[sp].set_visible(False)
    ax.spines["left"].set_color("#CCCCCC")
    ax.spines["bottom"].set_color("#CCCCCC")
    ax.tick_params(axis="x", colors="#777777", length=3)
    ax.tick_params(axis="y", length=0)

    plt.tight_layout(pad=0.6)
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=180, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf


# ── Ranked table builder ───────────────────────────────────────────────────────

def add_ranked_table(doc, rows, total):
    if not rows:
        body(doc, "No data available for this distribution.")
        return

    top20 = rows[:20]
    tbl = doc.add_table(rows=1, cols=5)
    tbl.alignment = WD_TABLE_ALIGNMENT.LEFT
    tbl.style = "Table Grid"

    # header row
    hdr_cells = tbl.rows[0].cells
    for cell, txt in zip(hdr_cells, ["Rank", "Code", "ISIC Division Name (Full)", "Count", "%"]):
        cell.text = txt
        cell.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
        set_cell_bg(cell, "003865")
        for run in cell.paragraphs[0].runs:
            run.font.bold  = True
            run.font.color.rgb = WHITE
            run.font.size  = Pt(9)

    for i, row in enumerate(top20):
        cells = tbl.add_row().cells
        pct   = f"{row[3] / total * 100:.1f}%" if total else "—"
        code  = f"{row[0]}-{row[1]}"
        for cell, val in zip(cells, [str(i+1), code, row[2], str(row[3]), pct]):
            cell.text = val
            cell.paragraphs[0].alignment = (
                WD_ALIGN_PARAGRAPH.LEFT if val == row[2]
                else WD_ALIGN_PARAGRAPH.CENTER
            )
            for run in cell.paragraphs[0].runs:
                run.font.size = Pt(9)
            if i % 2 == 0:
                set_cell_bg(cell, "EBF3FB")

    # column widths
    widths = [Cm(1.2), Cm(1.5), Cm(8.8), Cm(1.5), Cm(1.5)]
    for row in tbl.rows:
        for cell, w in zip(row.cells, widths):
            cell.width = w

    doc.add_paragraph()


# ── Discussion text ────────────────────────────────────────────────────────────

DISCUSSION = {
    ("dryad", "QDA_PROJECT"): [
        "Only one QDA project was identified across the entire Dryad corpus — a NVivo project "
        "file (.nvp) classified as R-86 (Human Health Activities). This suggests the underlying "
        "qualitative study concerned medical or patient-related research, consistent with the "
        "large body of health-science interview studies observed across the broader Dryad dataset.",

        "The near-total absence of QDA files in Dryad reflects a structural gap in open-data "
        "culture among qualitative researchers. Despite 15 targeted search queries — including "
        "specific QDA extension terms ('qdpx', 'nvp') — researchers deposit interview "
        "transcripts, coded spreadsheets, and final datasets but not the NVivo or MAXQDA project "
        "files that capture the analytical process itself. This is the precise gap that "
        "QDArchive is designed to address.",
    ],
    ("dryad", "QD_PROJECT"): [
        "Dryad's 340 QD projects span nine ISIC divisions, with three divisions accounting for "
        "96.8% of the distribution. N-72 (Scientific Research and Development) dominates at "
        "60.3% (205 projects), followed by R-86 (Human Health Activities) at 27.1% (92 "
        "projects) and A-01 (Crop and Animal Production) at 8.8% (30 projects).",

        "The dominance of N-72 is partly structural: it serves as both the correct "
        "classification for general academic research and the classifier's fallback for "
        "ambiguous descriptions. The R-86 cluster is substantively significant — it corresponds "
        "to the large body of medical and nursing interview studies identified via queries such "
        "as 'semi-structured interview' and 'thematic analysis', which typically deposit "
        "anonymised transcripts (.docx, .txt) and coding sheets (.xlsx).",

        "The A-01 presence (8.8%, 30 projects) reflects Dryad's strong life-sciences base. "
        "Agricultural researchers use 'qualitative' in a scientific rather than social-science "
        "sense (e.g., qualitative assessment of crop traits). These projects — typically "
        "containing .csv, .xlsx, and image files — represent noise from broad keyword matching "
        "and are correctly classified as QD_PROJECT since they contain no QDA analysis files.",
    ],
    ("fsd", "QDA_PROJECT"): [
        "No QDA projects were identified in the FSD Finland corpus. This is a direct consequence "
        "of FSD's access control model: all primary data files — interview transcripts, written "
        "responses, and coding files — require institutional authentication via the Aila Data "
        "Service. Without downloadable files, no project can be assigned the QDA_PROJECT type.",

        "FSD's public catalogue lists 403 English-language qualitative studies, but the only "
        "file consistently available without authentication is the DDI-C 2.5 XML metadata "
        "record. Some of these studies very likely include QDA analysis files accessible to "
        "authenticated users, but this cannot be confirmed from public data. The absence of "
        "FSD QDA projects should be interpreted as an access limitation, not as evidence that "
        "Finnish social science researchers do not produce QDA files.",
    ],
    ("fsd", "QD_PROJECT"): [
        "Only four FSD studies qualified as QD_PROJECT — those with publicly accessible PDF "
        "attachments (typically methodological reports or codebooks) that do not require Aila "
        "login. These four projects span three ISIC divisions: S-91 (Libraries, Archives and "
        "Cultural Activities, 50%), N-72 (Scientific Research, 25%), and Q-85 (Education, 25%).",

        "The disciplinary profile — cultural heritage, research methodology, and education — "
        "is consistent with FSD's institutional mandate as Finland's national social science "
        "data archive, whose holdings are concentrated in sociology, political science, history, "
        "and education research.",

        "The extremely small sample size (n=4) means this distribution cannot be considered "
        "representative of FSD's full 403-study catalogue. A meaningful ISIC classification "
        "of FSD data would require authenticated Aila access to retrieve the primary data "
        "files from at least a representative sample of the archived studies.",
    ],
}


# ── Document assembly ──────────────────────────────────────────────────────────

def build(conn):
    doc = Document()

    # ── Page margins ──────────────────────────────────────────────────────────
    for section in doc.sections:
        section.top_margin    = Cm(2.5)
        section.bottom_margin = Cm(2.5)
        section.left_margin   = Cm(3.0)
        section.right_margin  = Cm(2.5)

    # ── Title page ────────────────────────────────────────────────────────────
    tp = doc.add_paragraph()
    tp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    tp.paragraph_format.space_before = Pt(60)
    r = tp.add_run("Seeding QDArchive")
    r.font.size  = Pt(28)
    r.font.bold  = True
    r.font.color.rgb = NAVY

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run("Part 2: Data Classification Report")
    r.font.size  = Pt(18)
    r.font.color.rgb = BLUE

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run("ISIC Rev. 5 Classification of Qualitative Research Projects")
    r.font.size   = Pt(11)
    r.font.italic = True
    r.font.color.rgb = GREY

    doc.add_paragraph()
    gold_rule(doc)
    doc.add_paragraph()

    today = datetime.date.today().strftime("%B %Y")
    meta  = [
        ("Student",    "Jakir Hussain Rifat"),
        ("Matric. ID", "23025313"),
        ("Course",     "Seeding QDArchive (SQ26) — Applied Software Engineering Project"),
        ("Professor",  "Prof. Dr. Dirk Riehle, Professorship for Open-Source Software"),
        ("University", "Friedrich-Alexander-Universität Erlangen-Nürnberg (FAU)"),
        ("Date",       today),
        ("Repository", "https://github.com/hussainrifat/QDArchive"),
    ]
    tbl = doc.add_table(rows=len(meta), cols=2)
    tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, (lbl, val) in enumerate(meta):
        c0, c1 = tbl.rows[i].cells
        c0.text = lbl
        c1.text = val
        c0.paragraphs[0].runs[0].font.bold  = True
        c0.paragraphs[0].runs[0].font.color.rgb = GREY
        c0.paragraphs[0].runs[0].font.size  = Pt(10)
        c1.paragraphs[0].runs[0].font.size  = Pt(10)
        c0.width = Cm(3.5)
        c1.width = Cm(10.0)

    doc.add_paragraph()
    gold_rule(doc)
    doc.add_paragraph()

    # Dataset overview table on title page
    p = doc.add_paragraph("Dataset Overview")
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.runs[0].font.bold = True
    p.runs[0].font.size = Pt(12)
    p.runs[0].font.color.rgb = NAVY

    summary   = get_repo_summary(conn)
    total_all = sum(r[5] for r in summary)
    ov_hdrs   = ["Repository", "QDA Projects", "QD Projects", "Other", "Not a Project", "Total"]
    ov_tbl    = doc.add_table(rows=1, cols=6)
    ov_tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    ov_tbl.style     = "Table Grid"

    for cell, hdr in zip(ov_tbl.rows[0].cells, ov_hdrs):
        cell.text = hdr
        cell.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
        set_cell_bg(cell, "003865")
        run = cell.paragraphs[0].runs[0]
        run.font.bold = True
        run.font.color.rgb = WHITE
        run.font.size = Pt(9)

    rl = {"dryad": "Dryad", "fsd": "FSD Finland"}
    for i, row in enumerate(summary):
        cells = ov_tbl.add_row().cells
        vals  = [rl.get(row[0], row[0]),
                 str(row[1]), str(row[2]), str(row[3]), str(row[4]), str(row[5])]
        for cell, val in zip(cells, vals):
            cell.text = val
            cell.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
            cell.paragraphs[0].runs[0].font.size = Pt(9.5)
            if i % 2 == 0:
                set_cell_bg(cell, "EBF3FB")

    tot_cells = ov_tbl.add_row().cells
    for cell, val in zip(tot_cells, ["Total", "", "", "", "", str(total_all)]):
        cell.text = val
        cell.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
        set_cell_bg(cell, "D4DCE8")
        run = cell.paragraphs[0].runs[0]
        run.font.bold = True
        run.font.size = Pt(9.5)
        run.font.color.rgb = NAVY

    page_break(doc)

    # ── Section 1: Introduction ───────────────────────────────────────────────
    heading(doc, "1.  Introduction and Methodology", level=1)
    gold_rule(doc)
    body(doc, (
        "This report presents the results of Part 2 of the Seeding QDArchive project, conducted "
        "as part of the Applied Software Engineering Project seminar at FAU Erlangen (Winter "
        "2025/26 + Summer 2026) under the supervision of Prof. Dr. Dirk Riehle. The project's "
        "objective is to populate QDArchive — a new repository for qualitative research data — "
        "by acquiring and classifying publicly available qualitative research datasets from two "
        "assigned repositories."
    ))

    heading(doc, "1.1  Scope of Classification", level=2)
    gold_rule(doc)
    body(doc, (
        "Part 1 of this project acquired 1,256 qualitative research projects from Dryad and the "
        "Finnish Social Science Data Archive (FSD Finland), storing full metadata in a structured "
        "SQLite database. Part 2 classifies these projects across two dimensions: project type "
        "(based on the files contained) and economic sector (using the ISIC Rev. 5 standard)."
    ))

    heading(doc, "1.2  Project Type Classification", level=2)
    gold_rule(doc)
    body(doc, (
        "Each project was assigned one of four mutually exclusive types based on all file "
        "records, including files that failed to download. Using all file records — rather than "
        "only successfully downloaded files — was a critical methodological decision: 3,342 "
        "Dryad files were rate-limited during acquisition (FAILED_SERVER_UNRESPONSIVE). "
        "Classifying on downloaded files only would have incorrectly labelled these projects "
        "as having no files."
    ))

    bt = doc.add_table(rows=4, cols=2)
    bt.style = "Table Grid"
    for (code, desc), row in zip([
        ("QDA_PROJECT",   "Project contains at least one QDA analysis file (.qdpx, .nvp, .mx24)"),
        ("QD_PROJECT",    "No QDA file, but contains primary data files (.txt, .pdf, .docx, .doc)"),
        ("OTHER_PROJECT", "No QDA or primary files, but other valid data files present"),
        ("NOT_A_PROJECT", "No file type information can be derived"),
    ], bt.rows):
        row.cells[0].text = code
        row.cells[1].text = desc
        row.cells[0].paragraphs[0].runs[0].font.bold = True
        row.cells[0].paragraphs[0].runs[0].font.color.rgb = NAVY
        for cell in row.cells:
            cell.paragraphs[0].runs[0].font.size = Pt(9.5)
        row.cells[0].width = Cm(3.5)
        row.cells[1].width = Cm(10.0)
    doc.add_paragraph()

    heading(doc, "1.3  ISIC Rev. 5 Classification", level=2)
    gold_rule(doc)
    body(doc, (
        "All 1,256 projects were classified into the International Standard Industrial "
        "Classification of All Economic Activities, Revision 5 (ISIC Rev. 5) at two hierarchical "
        "levels: Section (single letter, A–V) and Division (two-digit numeric code). "
        "Classification was performed using the Anthropic Claude API (claude-haiku-4-5), which "
        "received each project's title, description, and keywords and returned the most "
        "appropriate Section and Division along with a confidence rating (high, medium, or low)."
    ))
    body(doc, (
        "In addition to project-level classification, each primary data file (.txt, .pdf, .docx, "
        ".doc, .xlsx, .csv, etc.) belonging to QDA_PROJECT and QD_PROJECT types was individually "
        "classified using its filename and parent project context — covering 1,764 files in total."
    ))

    heading(doc, "1.4  Report Structure", level=2)
    gold_rule(doc)
    body(doc, (
        "Results are presented as four distributions organised by repository and project type: "
        "(1) Dryad × QDA_PROJECT, (2) Dryad × QD_PROJECT, (3) FSD Finland × QDA_PROJECT, and "
        "(4) FSD Finland × QD_PROJECT. Each distribution includes a bar chart of identified ISIC "
        "classes, a rank-ordered table of the top classes, and a discussion of findings. "
        "Section 4 provides a comparative analysis across both repositories."
    ))

    page_break(doc)

    # ── Sections 2 & 3: Distributions ────────────────────────────────────────
    rlabels = {"dryad": "Dryad", "fsd": "FSD Finland"}
    tlabels = {"QDA_PROJECT": "QDA Projects", "QD_PROJECT": "QD Projects"}
    section_hdrs = {
        "dryad": "2.  Repository 1: Dryad",
        "fsd":   "3.  Repository 2: FSD Finland",
    }
    dist_labels = {
        ("dryad", "QDA_PROJECT"): "1",
        ("dryad", "QD_PROJECT"):  "2",
        ("fsd",   "QDA_PROJECT"): "3",
        ("fsd",   "QD_PROJECT"):  "4",
    }
    last_repo = None

    for repo, ptype in [("dryad","QDA_PROJECT"),("dryad","QD_PROJECT"),
                        ("fsd","QDA_PROJECT"),  ("fsd","QD_PROJECT")]:
        rows  = get_distrib(conn, repo, ptype)
        dl    = dist_labels[(repo, ptype)]
        total = sum(r[3] for r in rows)
        disc  = DISCUSSION[(repo, ptype)]

        if repo != last_repo:
            heading(doc, section_hdrs[repo], level=1)
            gold_rule(doc)
            last_repo = repo

        sub_title = f"Distribution {dl}: {rlabels[repo]} — {tlabels[ptype]}"
        heading(doc, sub_title, level=2)
        gold_rule(doc)

        # subtitle line
        p = doc.add_paragraph()
        r = p.add_run(f"{total} project{'s' if total != 1 else ''}  ·  "
                      f"{len(rows)} distinct ISIC division{'s' if len(rows) != 1 else ''}")
        r.font.italic = True
        r.font.size   = Pt(9.5)
        r.font.color.rgb = GREY
        p.paragraph_format.space_after = Pt(6)

        # chart image
        chart_title = f"{rlabels[repo]} — {tlabels[ptype]}: ISIC Division Distribution"
        img_buf = make_chart_image(rows, chart_title)
        if img_buf:
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            run = p.add_run()
            chart_w = min(Inches(5.5), Inches(0.5 + len(rows) * 0.5))
            run.add_picture(img_buf, width=Inches(5.8))
            cap = doc.add_paragraph(
                f"Figure {dl}: ISIC Rev. 5 division distribution for Distribution {dl}. "
                "Counts and ISIC codes shown to the right of each bar. "
                "Bars are colour-coded by ISIC section.")
            cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
            cap.runs[0].font.italic = True
            cap.runs[0].font.size   = Pt(8.5)
            cap.runs[0].font.color.rgb = GREY
            cap.paragraph_format.space_after = Pt(12)
        else:
            p = doc.add_paragraph(
                "No projects of this type were identified in this repository. "
                "See findings below for an explanation.")
            p.runs[0].font.italic = True
            p.runs[0].font.color.rgb = GREY

        # ranked table
        p = doc.add_paragraph("Table: Rank-ordered ISIC classes")
        p.runs[0].font.bold = True
        p.runs[0].font.size = Pt(10)
        p.runs[0].font.color.rgb = NAVY
        p.paragraph_format.space_after = Pt(4)
        add_ranked_table(doc, rows, total)

        # findings
        p = doc.add_paragraph("Findings and Discussion")
        p.runs[0].font.bold = True
        p.runs[0].font.size = Pt(10)
        p.runs[0].font.color.rgb = NAVY
        gold_rule(doc)
        for paragraph in disc:
            body(doc, paragraph)

        page_break(doc)

    # ── Section 4: Comparative analysis ──────────────────────────────────────
    dq  = conn.execute("""SELECT COUNT(*) FROM PROJECTS p
        JOIN REPOSITORIES r ON r.id=p.repository_id
        WHERE r.name='dryad' AND p.type='QD_PROJECT'""").fetchone()[0]
    fq  = conn.execute("""SELECT COUNT(*) FROM PROJECTS p
        JOIN REPOSITORIES r ON r.id=p.repository_id
        WHERE r.name='fsd' AND p.type='QD_PROJECT'""").fetchone()[0]
    qda = conn.execute(
        "SELECT COUNT(*) FROM PROJECTS WHERE type='QDA_PROJECT'").fetchone()[0]

    heading(doc, "4.  Comparative Analysis and Conclusion", level=1)
    gold_rule(doc)

    heading(doc, "4.1  Cross-Repository Observations", level=2)
    gold_rule(doc)
    body(doc, (
        f"The two repositories exhibit markedly different profiles in terms of both scale and "
        f"disciplinary coverage. Dryad contributed {dq} QD projects across nine ISIC divisions, "
        f"while FSD Finland contributed only {fq} publicly accessible QD projects across three "
        f"divisions. This disparity does not reflect FSD's actual holdings — FSD catalogues 403 "
        f"qualitative studies in its English-language archive — but is a direct consequence of "
        f"the archive's requirement for institutional authentication via the Aila Data Service."
    ))
    body(doc, (
        "Both repositories are dominated by N-72 (Scientific Research and Development), the "
        "expected outcome for academic research collections. The second-ranked division differs "
        "sharply: Dryad ranks R-86 (Human Health Activities) second at 27.1%, reflecting its "
        "strong life-sciences and clinical research base. FSD's small QD sample shows no R-86 "
        "representation; instead S-91 (Libraries, Archives and Cultural Activities) and Q-85 "
        "(Education) appear, consistent with Finland's social-science and cultural heritage "
        "research tradition."
    ))

    heading(doc, "4.2  QDA File Availability", level=2)
    gold_rule(doc)
    body(doc, (
        f"Across both repositories, only {qda} QDA analysis file was identified — a single "
        "NVivo (.nvp) project deposited on Dryad, classified as R-86 (Human Health Activities). "
        "This confirms the core challenge motivating QDArchive: researchers who conduct "
        "qualitative data analysis with NVivo, MAXQDA, or QDAcity rarely deposit the resulting "
        "analysis files in open repositories. Interview transcripts and coded datasets are "
        "deposited, but the structured analysis files that capture the analytical process itself "
        "remain largely inaccessible. QDArchive therefore cannot be seeded purely by harvesting "
        "existing repositories — it must rely on targeted outreach and deposit incentives."
    ))

    heading(doc, "4.3  Classification Confidence and Limitations", level=2)
    gold_rule(doc)
    body(doc, (
        "The AI-assisted ISIC classification produces reliable results for projects with "
        "descriptive titles, rich abstracts, and multiple keywords. Quality is lower for FSD "
        "projects, where only the DDI-C 2.5 XML title and abstract were available — no file "
        "content could be read. The large N-72 share also partly reflects the classifier's "
        "fallback behaviour: projects with generic or absent descriptions are assigned N-72 "
        "rather than a more specific division. A manual review of a sample of N-72 assignments "
        "would be required to quantify this effect precisely."
    ))

    heading(doc, "4.4  Conclusion", level=2)
    gold_rule(doc)
    body(doc, (
        "This classification provides a structured, ISIC-aligned view of 1,256 qualitative "
        "research projects acquired from Dryad and FSD Finland. The data confirms that "
        "qualitative research in the social, health, and agricultural sciences is well "
        "represented in open repositories — but that the QDA analysis files that are "
        "QDArchive's primary target are almost entirely absent from open deposit. The "
        "classification infrastructure developed here — the ISIC classifier, file-level "
        "annotation pipeline, and structured SQLite schema — provides a reusable foundation "
        "for classifying future acquisitions as QDArchive grows."
    ))

    return doc


def run():
    conn = sqlite3.connect(str(DB_PATH))
    OUT_PATH.parent.mkdir(exist_ok=True)
    doc = build(conn)
    conn.close()
    doc.save(OUT_PATH)
    print(f"Saved: {OUT_PATH}")


if __name__ == "__main__":
    run()
