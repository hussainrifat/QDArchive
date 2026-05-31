"""
Part 2 Step 4d — Classification Report PDF
Professional A4 portrait report for master's submission.
"""

import sqlite3
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.patches import FancyBboxPatch
import textwrap
import datetime

DB_PATH  = Path(__file__).parent.parent / "23025313-sq26-classification.db"
OUT_PATH = Path(__file__).parent.parent / "export" / "23025313-classification-report.pdf"

# ── Design tokens ────────────────────────────────────────────────────────────
C_NAVY   = "#003865"
C_BLUE   = "#2E75B6"
C_LGOLD  = "#C8A951"
C_LIGHT  = "#F2F6FC"
C_STRIPE = "#DEEAF1"
C_TEXT   = "#1A1A1A"
C_GREY   = "#6B6B6B"

PAGE_W, PAGE_H = 8.27, 11.69   # A4 portrait inches

plt.rcParams.update({
    "font.family":      "DejaVu Sans",
    "font.size":        10,
    "text.color":       C_TEXT,
    "axes.labelcolor":  C_TEXT,
    "xtick.color":      C_TEXT,
    "ytick.color":      C_TEXT,
})

PAGE_NUM = [0]

# ── Helpers ──────────────────────────────────────────────────────────────────

def new_page():
    PAGE_NUM[0] += 1
    fig = plt.figure(figsize=(PAGE_W, PAGE_H))
    return fig


def add_header(fig, section=""):
    """Thin navy top bar + course info."""
    fig.add_axes([0, 0.965, 1, 0.035]).set_axis_off()
    fig.patches.append(FancyBboxPatch(
        (0, 0.965), 1, 0.035,
        boxstyle="square,pad=0", linewidth=0,
        facecolor=C_NAVY, transform=fig.transFigure, zorder=3
    ))
    fig.text(0.015, 0.979, "Seeding QDArchive — Part 2: Data Classification Report",
             fontsize=7.5, color="white", va="center", fontweight="bold")
    fig.text(0.985, 0.979, "Jakir Hussain Rifat · 23025313 · FAU Erlangen",
             fontsize=7, color="#AACCEE", va="center", ha="right")
    if section:
        fig.text(0.015, 0.958, section,
                 fontsize=8, color=C_GREY, va="top", style="italic")


def add_footer(fig):
    """Thin bottom rule + page number."""
    fig.patches.append(FancyBboxPatch(
        (0.05, 0.025), 0.9, 0.001,
        boxstyle="square,pad=0", linewidth=0,
        facecolor="#CCCCCC", transform=fig.transFigure
    ))
    fig.text(0.5, 0.013, f"— {PAGE_NUM[0]} —",
             fontsize=8, color=C_GREY, ha="center", va="center")


def add_section_rule(fig, y, label):
    """Gold rule + section label."""
    fig.patches.append(FancyBboxPatch(
        (0.05, y), 0.9, 0.003,
        boxstyle="square,pad=0", linewidth=0,
        facecolor=C_LGOLD, transform=fig.transFigure
    ))
    fig.text(0.05, y + 0.008, label.upper(),
             fontsize=9, color=C_NAVY, fontweight="bold", va="bottom",
             transform=fig.transFigure)


def para(fig, x, y, text, width=95, fontsize=9.5, color=C_TEXT, line_spacing=0.022):
    """Render a wrapped paragraph, return bottom y."""
    lines = []
    for raw in text.split("\n"):
        lines.extend(textwrap.wrap(raw, width) if raw.strip() else [""])
    cy = y
    for line in lines:
        fig.text(x, cy, line, fontsize=fontsize, color=color, va="top",
                 transform=fig.transFigure)
        cy -= line_spacing
    return cy


def get_distrib(conn, repo, ptype):
    return conn.execute("""
        SELECT p.isic_section_code, p.isic_division_code,
               p.isic_section_name, p.isic_division_name, COUNT(*) AS cnt
        FROM PROJECTS p
        JOIN REPOSITORIES r ON r.id = p.repository_id
        WHERE r.name=? AND p.type=?
        GROUP BY p.isic_section_code, p.isic_division_code
        ORDER BY cnt DESC
    """, (repo, ptype)).fetchall()


def get_repo_summary(conn):
    return conn.execute("""
        SELECT r.name,
               SUM(CASE WHEN p.type='QDA_PROJECT' THEN 1 ELSE 0 END) as qda,
               SUM(CASE WHEN p.type='QD_PROJECT'  THEN 1 ELSE 0 END) as qd,
               SUM(CASE WHEN p.type='OTHER_PROJECT' THEN 1 ELSE 0 END) as other,
               SUM(CASE WHEN p.type='NOT_A_PROJECT' THEN 1 ELSE 0 END) as not_a,
               COUNT(*) as total
        FROM PROJECTS p
        JOIN REPOSITORIES r ON r.id=p.repository_id
        GROUP BY r.name ORDER BY r.name DESC
    """).fetchall()


# ── Pages ────────────────────────────────────────────────────────────────────

def page_title(pdf, conn):
    fig = new_page()

    # top colour band
    fig.patches.append(FancyBboxPatch(
        (0, 0.82), 1, 0.18,
        boxstyle="square,pad=0", linewidth=0,
        facecolor=C_NAVY, transform=fig.transFigure
    ))
    fig.patches.append(FancyBboxPatch(
        (0, 0.805), 1, 0.015,
        boxstyle="square,pad=0", linewidth=0,
        facecolor=C_LGOLD, transform=fig.transFigure
    ))

    fig.text(0.5, 0.935, "Seeding QDArchive",
             fontsize=26, fontweight="bold", color="white",
             ha="center", va="center")
    fig.text(0.5, 0.885, "Part 2: Data Classification Report",
             fontsize=16, color="#AACCEE",
             ha="center", va="center")
    fig.text(0.5, 0.850, "ISIC Rev. 5 Classification of Qualitative Research Projects",
             fontsize=10.5, color="#88AACC", style="italic",
             ha="center", va="center")

    # metadata block
    today = datetime.date.today().strftime("%B %Y")
    meta = [
        ("Student",   "Jakir Hussain Rifat"),
        ("Matric. ID","23025313"),
        ("Course",    "Seeding QDArchive (SQ26) — Applied Software Engineering Project"),
        ("Professor", "Prof. Dr. Dirk Riehle, Professorship for Open-Source Software"),
        ("University","Friedrich-Alexander-Universität Erlangen-Nürnberg (FAU)"),
        ("Date",      today),
        ("Repository","https://github.com/hussainrifat/QDArchive"),
    ]
    ty = 0.78
    for label, value in meta:
        fig.text(0.12, ty, f"{label}:", fontsize=9.5, color=C_GREY,
                 va="top", fontweight="bold")
        fig.text(0.34, ty, value, fontsize=9.5, color=C_TEXT, va="top")
        ty -= 0.042

    # summary table
    summary = get_repo_summary(conn)
    total_all = sum(r[5] for r in summary)

    fig.patches.append(FancyBboxPatch(
        (0.08, 0.28), 0.84, 0.24,
        boxstyle="round,pad=0.01", linewidth=1,
        edgecolor="#BBBBBB", facecolor=C_LIGHT,
        transform=fig.transFigure
    ))

    fig.text(0.5, 0.505, "Dataset Overview",
             fontsize=10, fontweight="bold", color=C_NAVY,
             ha="center", va="top")

    headers = ["Repository", "QDA Projects", "QD Projects", "Other", "Not a Project", "Total"]
    xs = [0.12, 0.30, 0.43, 0.56, 0.67, 0.83]
    y0 = 0.478
    for hdr, x in zip(headers, xs):
        fig.text(x, y0, hdr, fontsize=8.5, color=C_NAVY,
                 fontweight="bold", va="top",
                 ha="right" if x > 0.25 else "left")

    fig.patches.append(FancyBboxPatch(
        (0.09, y0 - 0.005), 0.82, 0.001,
        boxstyle="square,pad=0", linewidth=0,
        facecolor=C_NAVY, transform=fig.transFigure
    ))

    row_labels = {"dryad": "Dryad", "fsd": "FSD Finland"}
    for i, row in enumerate(summary):
        ry = y0 - 0.035 - i * 0.038
        if i % 2 == 0:
            fig.patches.append(FancyBboxPatch(
                (0.09, ry - 0.008), 0.82, 0.032,
                boxstyle="square,pad=0", linewidth=0,
                facecolor=C_STRIPE, transform=fig.transFigure
            ))
        vals = [row_labels.get(row[0], row[0]),
                str(row[1]), str(row[2]), str(row[3]), str(row[4]), str(row[5])]
        for val, x in zip(vals, xs):
            fig.text(x, ry, val, fontsize=9, va="top",
                     ha="right" if x > 0.25 else "left")

    totry = y0 - 0.035 - len(summary) * 0.038
    fig.patches.append(FancyBboxPatch(
        (0.09, totry - 0.008), 0.82, 0.001,
        boxstyle="square,pad=0", linewidth=0,
        facecolor="#AAAAAA", transform=fig.transFigure
    ))
    tot_vals = ["Total", "", "", "", "", str(total_all)]
    for val, x in zip(tot_vals, xs):
        fig.text(x, totry + 0.010, val, fontsize=9, va="top",
                 fontweight="bold", ha="right" if x > 0.25 else "left")

    add_footer(fig)
    pdf.savefig(fig, bbox_inches="tight")
    plt.close(fig)


def page_introduction(pdf):
    fig = new_page()
    add_header(fig)
    add_footer(fig)

    add_section_rule(fig, 0.895, "1.  Introduction and Methodology")

    y = 0.870

    y = para(fig, 0.07, y, (
        "This report presents the results of Part 2 of the Seeding QDArchive project, conducted "
        "as part of the Applied Software Engineering Project seminar at FAU Erlangen (Winter 2025/26 "
        "+ Summer 2026) under the supervision of Prof. Dr. Dirk Riehle. The project's objective is "
        "to populate QDArchive — a new repository for qualitative research data — by acquiring and "
        "classifying publicly available qualitative research datasets from two assigned repositories."
    ), width=100)

    y -= 0.018
    add_section_rule(fig, y, "1.1  Scope of Classification")
    y -= 0.030

    y = para(fig, 0.07, y, (
        "Part 1 of this project acquired 1,256 qualitative research projects from Dryad and the "
        "Finnish Social Science Data Archive (FSD Finland), storing full metadata in a structured "
        "SQLite database. Part 2 classifies these projects across two dimensions: project type "
        "(based on the files contained) and economic sector (using the ISIC Rev. 5 standard)."
    ), width=100)

    y -= 0.018
    add_section_rule(fig, y, "1.2  Project Type Classification")
    y -= 0.030

    y = para(fig, 0.07, y, (
        "Each project was assigned one of four mutually exclusive types based on all file records "
        "associated with that project, including files that failed to download. Using all file "
        "records — rather than only successfully downloaded files — was an important methodological "
        "decision: 3,342 Dryad files were rate-limited during acquisition and recorded as "
        "FAILED_SERVER_UNRESPONSIVE. Classifying on downloaded files only would have incorrectly "
        "treated these projects as having no files.\n"
        "\n"
        "   QDA_PROJECT   — project contains at least one QDA analysis file (.qdpx, .nvp, .mx24)\n"
        "   QD_PROJECT    — no QDA file, but contains primary data files (.txt, .pdf, .docx, .doc)\n"
        "   OTHER_PROJECT — no QDA or primary files, but other data files present\n"
        "   NOT_A_PROJECT — no file type information available"
    ), width=100, fontsize=9)

    y -= 0.018
    add_section_rule(fig, y, "1.3  ISIC Rev. 5 Classification")
    y -= 0.030

    y = para(fig, 0.07, y, (
        "All 1,256 projects were classified into the International Standard Industrial "
        "Classification of All Economic Activities, Revision 5 (ISIC Rev. 5) at two hierarchical "
        "levels: Section (single letter, A–V) and Division (two-digit numeric code). Classification "
        "was performed using the Anthropic Claude API, which received each project's title, "
        "description, and keywords and returned the most appropriate Section and Division along with "
        "a confidence rating (high, medium, or low)."
        "\n\n"
        "In addition to project-level classification, each primary data file belonging to "
        "QDA_PROJECT and QD_PROJECT types was individually classified using its filename and parent "
        "project context. This file-level classification covers 1,764 primary data files across "
        "both repositories."
    ), width=100)

    y -= 0.018
    add_section_rule(fig, y, "1.4  Report Structure")
    y -= 0.030

    y = para(fig, 0.07, y, (
        "This report presents classification results in the form of four distributions, organised "
        "by repository and project type: (1) Dryad × QDA_PROJECT, (2) Dryad × QD_PROJECT, "
        "(3) FSD Finland × QDA_PROJECT, and (4) FSD Finland × QD_PROJECT. For each distribution, "
        "a histogram of identified ISIC classes and a rank-ordered table of the top classes are "
        "provided, followed by a discussion of notable findings. Section 4 provides a comparative "
        "analysis across both repositories."
    ), width=100)

    pdf.savefig(fig, bbox_inches="tight")
    plt.close(fig)


def page_histogram(pdf, repo, ptype, rows, section_label, page_label):
    repo_labels = {"dryad": "Dryad", "fsd": "FSD Finland"}
    type_labels  = {"QDA_PROJECT": "QDA Projects", "QD_PROJECT": "QD Projects"}

    fig = new_page()
    add_header(fig, section_label)
    add_footer(fig)

    title = f"{repo_labels[repo]} — {type_labels[ptype]}: ISIC Division Distribution"
    fig.text(0.07, 0.925, title,
             fontsize=13, fontweight="bold", color=C_NAVY, va="top")
    fig.text(0.07, 0.905,
             f"Distribution {page_label}  ·  {sum(r[4] for r in rows) if rows else 0} projects  ·  "
             f"{len(rows)} distinct ISIC division{'s' if len(rows)!=1 else ''}",
             fontsize=9, color=C_GREY, va="top", style="italic")

    if not rows:
        fig.text(0.5, 0.55,
                 "No projects of this type were found in this repository.",
                 fontsize=12, color=C_GREY, ha="center", va="center",
                 style="italic")
        pdf.savefig(fig, bbox_inches="tight")
        plt.close(fig)
        return

    ax = fig.add_axes([0.08, 0.22, 0.88, 0.66])

    # Full division names as required by the professor
    labels = [textwrap.fill(r[3], 22) for r in rows]
    counts = [r[4] for r in rows]
    codes  = [f"{r[0]}-{r[1]}" for r in rows]

    bars = ax.bar(range(len(counts)), counts,
                  color=C_BLUE, edgecolor="white", linewidth=0.8, zorder=3)

    # Count on top of each bar
    ymax = max(counts)
    for bar, cnt in zip(bars, counts):
        ax.text(bar.get_x() + bar.get_width() / 2,
                bar.get_height() + ymax * 0.015,
                str(cnt), ha="center", va="bottom",
                fontsize=9.5, fontweight="bold", color=C_NAVY)

    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels, fontsize=8.5, rotation=30, ha="right")
    ax.set_ylabel("Number of Projects", fontsize=10, color=C_GREY)
    ax.set_ylim(0, ymax * 1.18)
    ax.yaxis.grid(True, linestyle="--", alpha=0.5, zorder=0)
    ax.set_axisbelow(True)
    for spine in ["top", "right"]:
        ax.spines[spine].set_visible(False)
    ax.spines["left"].set_color("#CCCCCC")
    ax.spines["bottom"].set_color("#CCCCCC")
    ax.tick_params(axis="both", colors=C_GREY, length=3)

    # ISIC code annotations below each bar
    for i, code in enumerate(codes):
        ax.text(i, -ymax * 0.06, code,
                ha="center", va="top", fontsize=7.5,
                color=C_GREY, style="italic")

    ax.text(0.5, -0.18,
            "Figure: Histogram of ISIC Rev. 5 divisions identified in this distribution. "
            "Counts shown above bars; ISIC codes in italics below.",
            ha="center", va="top", fontsize=7.5, color=C_GREY,
            transform=ax.transAxes, style="italic")

    pdf.savefig(fig, bbox_inches="tight")
    plt.close(fig)


def page_table_and_discussion(pdf, repo, ptype, rows, section_label,
                               page_label, discussion_paragraphs):
    repo_labels = {"dryad": "Dryad", "fsd": "FSD Finland"}
    type_labels  = {"QDA_PROJECT": "QDA Projects", "QD_PROJECT": "QD Projects"}
    top20 = rows[:20]

    fig = new_page()
    add_header(fig, section_label)
    add_footer(fig)

    title = f"{repo_labels[repo]} — {type_labels[ptype]}: Ranked Class Table and Findings"
    fig.text(0.07, 0.925, title,
             fontsize=13, fontweight="bold", color=C_NAVY, va="top")
    total = sum(r[4] for r in rows)
    fig.text(0.07, 0.905,
             f"Distribution {page_label}  ·  {total} projects  ·  top {min(20,len(top20))} of {len(rows)} class{'es' if len(rows)!=1 else ''} shown",
             fontsize=9, color=C_GREY, va="top", style="italic")

    if not top20:
        y = 0.860
        add_section_rule(fig, y, "Findings")
        y -= 0.030
        for p in discussion_paragraphs:
            y = para(fig, 0.07, y, p, width=100)
            y -= 0.015
        pdf.savefig(fig, bbox_inches="tight")
        plt.close(fig)
        return

    # ── Table ──────────────────────────────────────────────────────────────
    table_top    = 0.890
    row_h        = 0.030
    col_xs       = [0.07, 0.13, 0.21, 0.80, 0.89]
    col_headers  = ["Rank", "Code", "ISIC Division Name (Full)", "Count", "%"]
    col_ha       = ["center","center","left","center","center"]

    # header row
    fig.patches.append(FancyBboxPatch(
        (0.065, table_top - 0.005), 0.87, row_h + 0.004,
        boxstyle="square,pad=0", linewidth=0,
        facecolor=C_NAVY, transform=fig.transFigure
    ))
    for hdr, x, ha in zip(col_headers, col_xs, col_ha):
        fig.text(x, table_top + 0.010, hdr,
                 fontsize=8.5, color="white", fontweight="bold",
                 va="center", ha=ha, transform=fig.transFigure)

    for i, row in enumerate(top20):
        ry = table_top - row_h * (i + 1) - 0.005
        if i % 2 == 1:
            fig.patches.append(FancyBboxPatch(
                (0.065, ry - 0.003), 0.87, row_h,
                boxstyle="square,pad=0", linewidth=0,
                facecolor=C_STRIPE, transform=fig.transFigure
            ))
        pct = f"{row[4]/total*100:.1f}%" if total else "—"
        code = f"{row[0]}-{row[1]}"
        vals = [str(i + 1), code, row[3], str(row[4]), pct]
        for val, x, ha in zip(vals, col_xs, col_ha):
            fig.text(x, ry + 0.010, val,
                     fontsize=8.5, va="center", ha=ha,
                     transform=fig.transFigure)

    table_bottom = table_top - row_h * (len(top20) + 1) - 0.010

    # ── Findings ────────────────────────────────────────────────────────────
    y = table_bottom - 0.025
    add_section_rule(fig, y, "Findings and Discussion")
    y -= 0.030

    for p in discussion_paragraphs:
        y = para(fig, 0.07, y, p, width=100)
        y -= 0.014
        if y < 0.055:
            break

    pdf.savefig(fig, bbox_inches="tight")
    plt.close(fig)


def page_comparative(pdf, conn):
    fig = new_page()
    add_header(fig)
    add_footer(fig)

    add_section_rule(fig, 0.895, "4.  Comparative Analysis and Conclusion")
    y = 0.865

    add_section_rule(fig, y, "4.1  Cross-Repository Observations")
    y -= 0.030

    dryad_qd = conn.execute("""
        SELECT COUNT(*) FROM PROJECTS p JOIN REPOSITORIES r ON r.id=p.repository_id
        WHERE r.name='dryad' AND p.type='QD_PROJECT'""").fetchone()[0]
    fsd_qd   = conn.execute("""
        SELECT COUNT(*) FROM PROJECTS p JOIN REPOSITORIES r ON r.id=p.repository_id
        WHERE r.name='fsd' AND p.type='QD_PROJECT'""").fetchone()[0]
    total_qda = conn.execute("""
        SELECT COUNT(*) FROM PROJECTS WHERE type='QDA_PROJECT'""").fetchone()[0]

    y = para(fig, 0.07, y, (
        f"The two repositories exhibit markedly different profiles in terms of both scale and "
        f"disciplinary coverage. Dryad contributed {dryad_qd} QD projects across nine ISIC "
        f"divisions, while FSD Finland contributed only {fsd_qd} publicly accessible QD projects "
        f"across three divisions. This disparity is not indicative of FSD's actual holdings — FSD "
        f"lists 403 qualitative studies in its English-language catalogue — but reflects the "
        f"archive's requirement for institutional authentication via the Aila Data Service. "
        f"Consequently, FSD's contribution to this dataset is limited to the subset of studies "
        f"with publicly accessible attachments."
    ), width=100)

    y -= 0.018
    y = para(fig, 0.07, y, (
        "Both repositories are dominated by the N-72 division (Scientific Research and "
        "Development), which is the expected outcome when classifying academic research projects. "
        "However, the second-ranked division differs sharply: Dryad's QD projects rank R-86 "
        "(Human Health Activities) second with 27.1% of projects, reflecting its strong "
        "life-sciences and medical research user base. FSD's small QD sample, by contrast, shows "
        "no R-86 representation, with S-91 (Libraries, Archives and Cultural Activities) "
        "appearing most frequently alongside Q-85 (Education), consistent with Finland's "
        "social-science and cultural heritage research tradition."
    ), width=100)

    y -= 0.018
    add_section_rule(fig, y, "4.2  QDA File Availability")
    y -= 0.030

    y = para(fig, 0.07, y, (
        f"Across both repositories, only {total_qda} QDA analysis file was identified — a single "
        "NVivo (.nvp) project deposited on Dryad. This finding confirms the core challenge that "
        "motivates the QDArchive project: researchers who conduct qualitative data analysis using "
        "tools such as NVivo, MAXQDA, or QDAcity rarely deposit the resulting analysis files in "
        "open repositories. They may deposit interview transcripts or coded datasets, but the "
        "structured analysis files that capture the analytical process itself remain largely "
        "inaccessible. The practical implication is that QDArchive must rely on outreach and "
        "incentive structures — not just harvesting existing open repositories — to build a "
        "meaningful QDA file collection."
    ), width=100)

    y -= 0.018
    add_section_rule(fig, y, "4.3  Classification Confidence and Limitations")
    y -= 0.030

    y = para(fig, 0.07, y, (
        "The AI-assisted ISIC classification approach produces accurate results for projects with "
        "descriptive titles, rich abstracts, and multiple keywords. Classification quality is "
        "lower for FSD projects, where only the DDI-C 2.5 XML title and abstract were available "
        "as input — no file content could be analysed. The large proportion of N-72 "
        "(Scientific Research and Development) classifications also reflects the classifier's "
        "default fallback behaviour for ambiguous inputs: projects with generic descriptions "
        "tend to be assigned to N-72 rather than a more specific division. A manual review of a "
        "sample of N-72 assignments would be needed to quantify this effect precisely."
    ), width=100)

    y -= 0.018
    add_section_rule(fig, y, "4.4  Conclusion")
    y -= 0.030

    y = para(fig, 0.07, y, (
        "This classification provides a structured, ISIC-aligned view of 1,256 qualitative "
        "research projects acquired from Dryad and FSD Finland. The data confirms that "
        "qualitative research in the social, health, and agricultural sciences is well represented "
        "in open repositories — but that the QDA analysis files, which are QDArchive's primary "
        "target, are almost entirely absent from open deposit. The classification infrastructure "
        "built here — including the ISIC classifier, file-level annotation pipeline, and "
        "structured SQLite schema — provides a reusable foundation for classifying future "
        "acquisitions as QDArchive grows."
    ), width=100)

    pdf.savefig(fig, bbox_inches="tight")
    plt.close(fig)


# ── Discussion text per distribution ─────────────────────────────────────────

DISCUSSION = {
    ("dryad", "QDA_PROJECT"): [
        "Only one QDA project was identified across the entire Dryad corpus — a NVivo project "
        "file (.nvp) classified under N-72 (Scientific Research and Development). This is the "
        "expected ISIC assignment for an academic qualitative data analysis project with no "
        "further domain-specific context.",

        "The near-total absence of QDA files in Dryad reflects a structural gap in open-data "
        "culture among qualitative researchers. Despite 15 targeted search queries, researchers "
        "appear to deposit interview transcripts, coded spreadsheets, and final datasets — but "
        "not the NVivo or MAXQDA project files that capture the analytical process. This is "
        "the precise gap that QDArchive is designed to address by providing a dedicated, "
        "researcher-friendly repository for this file type.",
    ],
    ("dryad", "QD_PROJECT"): [
        "Dryad's 340 QD projects span nine ISIC divisions, with three divisions accounting for "
        "97% of the distribution. N-72 (Scientific Research and Development) dominates at 60.3% "
        "(205 projects), followed by R-86 (Human Health Activities) at 27.1% (92 projects) and "
        "A-01 (Crop and Animal Production) at 8.8% (30 projects).",

        "The dominance of N-72 is partly structural: it serves as both the correct classification "
        "for generic academic research and the classifier's fallback for ambiguous descriptions. "
        "The R-86 cluster is substantively significant — it corresponds to the large body of "
        "medical and nursing interview studies identified via queries such as 'semi-structured "
        "interview' and 'thematic analysis'. These studies typically deposit anonymised "
        "transcripts (.docx, .txt) and coding sheets (.xlsx), consistent with the file "
        "composition observed in this dataset.",

        "The A-01 presence (8.8%) is attributable to Dryad's strong life-sciences user base. "
        "Agricultural researchers use 'qualitative' in a scientific rather than social-science "
        "sense (e.g., qualitative assessment of crop traits). These projects — which typically "
        "contain .csv, .xlsx, and image files — represent the noise introduced by broad keyword "
        "matching and are correctly classified as QD_PROJECT rather than QDA_PROJECT, since "
        "they contain no qualitative data analysis files.",
    ],
    ("fsd", "QDA_PROJECT"): [
        "No QDA projects were identified in the FSD Finland corpus. This outcome is a direct "
        "consequence of FSD's access control model: all primary data files — interview "
        "transcripts, written responses, and coding files — require institutional authentication "
        "via the Aila Data Service. Without downloadable files, no project can be classified as "
        "QDA_PROJECT.",

        "FSD's public-facing catalogue lists 403 English-language qualitative studies, but the "
        "only file consistently available without authentication is the DDI-C 2.5 XML metadata "
        "record. It is likely that some of these studies include QDA analysis files accessible "
        "to authenticated users, but this cannot be determined from the public dataset. The "
        "absence of FSD QDA projects should therefore be interpreted as an access limitation, "
        "not as evidence that Finnish social science researchers do not produce QDA files.",
    ],
    ("fsd", "QD_PROJECT"): [
        "Only four FSD studies qualified as QD_PROJECT — those with publicly accessible PDF "
        "attachments (typically methodological reports or codebooks) that do not require Aila "
        "login. These four projects span three ISIC divisions: S-91 (Libraries, Archives, "
        "Museums and Cultural Activities, 50%), N-72 (Scientific Research, 25%), and Q-85 "
        "(Education, 25%).",

        "The disciplinary profile of this small sample — cultural heritage, research methodology, "
        "and education — is consistent with FSD's institutional mandate as Finland's national "
        "social science data archive. FSD holdings are concentrated in sociology, political "
        "science, history, and education research, which aligns with the S-91 and Q-85 "
        "classifications observed here.",

        "The extremely small sample size (n=4) means that these distributions cannot be "
        "considered representative of FSD's full holdings. A meaningful classification of FSD "
        "data would require authenticated access to the Aila platform to retrieve the actual "
        "primary data files for at least a sample of the 403 archived studies.",
    ],
}


# ── Main ─────────────────────────────────────────────────────────────────────

def run():
    conn = sqlite3.connect(str(DB_PATH))
    OUT_PATH.parent.mkdir(exist_ok=True)

    dist_labels = {
        ("dryad", "QDA_PROJECT"): "1",
        ("dryad", "QD_PROJECT"):  "2",
        ("fsd",   "QDA_PROJECT"): "3",
        ("fsd",   "QD_PROJECT"):  "4",
    }
    section_labels = {
        ("dryad", "QDA_PROJECT"): "2.  Repository 1: Dryad",
        ("dryad", "QD_PROJECT"):  "2.  Repository 1: Dryad",
        ("fsd",   "QDA_PROJECT"): "3.  Repository 2: FSD Finland",
        ("fsd",   "QD_PROJECT"):  "3.  Repository 2: FSD Finland",
    }

    with PdfPages(OUT_PATH) as pdf:
        page_title(pdf, conn)
        page_introduction(pdf)

        for repo, ptype in [
            ("dryad", "QDA_PROJECT"),
            ("dryad", "QD_PROJECT"),
            ("fsd",   "QDA_PROJECT"),
            ("fsd",   "QD_PROJECT"),
        ]:
            rows   = get_distrib(conn, repo, ptype)
            dlabel = dist_labels[(repo, ptype)]
            slabel = section_labels[(repo, ptype)]
            disc   = DISCUSSION[(repo, ptype)]
            total  = sum(r[4] for r in rows)
            print(f"  Distribution {dlabel}: {repo}/{ptype} — {len(rows)} classes, {total} projects")

            page_histogram(pdf, repo, ptype, rows, slabel, dlabel)
            page_table_and_discussion(pdf, repo, ptype, rows, slabel, dlabel, disc)

        page_comparative(pdf, conn)

        d = pdf.infodict()
        d["Title"]   = "Seeding QDArchive — Part 2: Data Classification Report"
        d["Author"]  = "Jakir Hussain Rifat (23025313)"
        d["Subject"] = "ISIC Rev. 5 Classification of Qualitative Research Projects"
        d["Creator"] = "QDArchive Classification Pipeline"

    conn.close()
    print(f"\nSaved: {OUT_PATH}  ({PAGE_NUM[0]} pages)")


if __name__ == "__main__":
    run()
