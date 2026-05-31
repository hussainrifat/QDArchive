"""
Part 2 Step 4d — Classification Report PDF
Professional A4 portrait report for master's submission.
"""

import sqlite3
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.patches import FancyBboxPatch
import textwrap
import datetime

DB_PATH  = Path(__file__).parent.parent / "23025313-sq26-classification.db"
OUT_PATH = Path(__file__).parent.parent / "export" / "23025313-classification-report.pdf"

C_NAVY   = "#003865"
C_BLUE   = "#2E75B6"
C_LGOLD  = "#C8A951"
C_LIGHT  = "#F2F6FC"
C_STRIPE = "#DEEAF1"
C_TEXT   = "#1A1A1A"
C_GREY   = "#6B6B6B"

PAGE_W, PAGE_H = 8.27, 11.69
MARGIN_L, MARGIN_R = 0.08, 0.92   # figure-fraction left/right margins
CONTENT_TOP = 0.93                 # top of usable content area (below header)
CONTENT_BOT = 0.045                # bottom of usable content area (above footer)

plt.rcParams.update({
    "font.family":     "DejaVu Sans",
    "font.size":       10,
    "text.color":      C_TEXT,
    "axes.labelcolor": C_TEXT,
    "xtick.color":     C_TEXT,
    "ytick.color":     C_TEXT,
})

PAGE_NUM = [0]


# ── Page chrome ───────────────────────────────────────────────────────────────

def new_page():
    PAGE_NUM[0] += 1
    return plt.figure(figsize=(PAGE_W, PAGE_H))


def add_header(fig, section=""):
    fig.patches.append(FancyBboxPatch(
        (0, 0.965), 1, 0.035,
        boxstyle="square,pad=0", linewidth=0,
        facecolor=C_NAVY, transform=fig.transFigure, zorder=3
    ))
    fig.text(0.015, 0.982, "Seeding QDArchive — Part 2: Data Classification Report",
             fontsize=7.5, color="white", va="center", fontweight="bold")
    fig.text(0.985, 0.982, "Jakir Hussain Rifat · 23025313 · FAU Erlangen",
             fontsize=7, color="#AACCEE", va="center", ha="right")
    if section:
        fig.text(MARGIN_L, 0.956, section,
                 fontsize=8, color=C_GREY, va="top", style="italic")


def add_footer(fig):
    fig.patches.append(FancyBboxPatch(
        (MARGIN_L, 0.030), MARGIN_R - MARGIN_L, 0.001,
        boxstyle="square,pad=0", linewidth=0,
        facecolor="#CCCCCC", transform=fig.transFigure
    ))
    fig.text(0.5, 0.018, f"— {PAGE_NUM[0]} —",
             fontsize=8, color=C_GREY, ha="center", va="center")


def section_rule(fig, y, label):
    """Gold underline rule with label above it."""
    fig.patches.append(FancyBboxPatch(
        (MARGIN_L, y), MARGIN_R - MARGIN_L, 0.003,
        boxstyle="square,pad=0", linewidth=0,
        facecolor=C_LGOLD, transform=fig.transFigure
    ))
    fig.text(MARGIN_L, y + 0.007, label.upper(),
             fontsize=9, color=C_NAVY, fontweight="bold", va="bottom")


def para(fig, x, y, text, width=98, fontsize=9.5, color=C_TEXT, spacing=0.022):
    """Render wrapped paragraph; return y of the line after last line."""
    lines = []
    for raw in text.split("\n"):
        lines.extend(textwrap.wrap(raw, width) if raw.strip() else [""])
    for line in lines:
        fig.text(x, y, line, fontsize=fontsize, color=color, va="top")
        y -= spacing
    return y


# ── Data helpers ──────────────────────────────────────────────────────────────

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
               SUM(CASE WHEN p.type='QDA_PROJECT'   THEN 1 ELSE 0 END),
               SUM(CASE WHEN p.type='QD_PROJECT'    THEN 1 ELSE 0 END),
               SUM(CASE WHEN p.type='OTHER_PROJECT' THEN 1 ELSE 0 END),
               SUM(CASE WHEN p.type='NOT_A_PROJECT' THEN 1 ELSE 0 END),
               COUNT(*)
        FROM PROJECTS p
        JOIN REPOSITORIES r ON r.id=p.repository_id
        GROUP BY r.name ORDER BY r.name DESC
    """).fetchall()


# ── Pages ──────────────────────────────────────────────────────────────────────

def page_title(pdf, conn):
    fig = new_page()

    # header band
    fig.patches.append(FancyBboxPatch(
        (0, 0.82), 1, 0.18,
        boxstyle="square,pad=0", linewidth=0,
        facecolor=C_NAVY, transform=fig.transFigure
    ))
    fig.patches.append(FancyBboxPatch(
        (0, 0.808), 1, 0.012,
        boxstyle="square,pad=0", linewidth=0,
        facecolor=C_LGOLD, transform=fig.transFigure
    ))
    fig.text(0.5, 0.930, "Seeding QDArchive",
             fontsize=28, fontweight="bold", color="white", ha="center", va="center")
    fig.text(0.5, 0.878, "Part 2: Data Classification Report",
             fontsize=17, color="#AACCEE", ha="center", va="center")
    fig.text(0.5, 0.845, "ISIC Rev. 5 Classification of Qualitative Research Projects",
             fontsize=10.5, color="#88AACC", style="italic", ha="center", va="center")

    # metadata table
    today = datetime.date.today().strftime("%B %Y")
    meta = [
        ("Student",    "Jakir Hussain Rifat"),
        ("Matric. ID", "23025313"),
        ("Course",     "Seeding QDArchive (SQ26) — Applied Software Engineering Project"),
        ("Professor",  "Prof. Dr. Dirk Riehle, Professorship for Open-Source Software"),
        ("University", "Friedrich-Alexander-Universität Erlangen-Nürnberg (FAU)"),
        ("Date",       today),
        ("Repository", "https://github.com/hussainrifat/QDArchive"),
    ]
    ty = 0.790
    for label, value in meta:
        fig.text(0.10, ty, f"{label}:", fontsize=9.5, color=C_GREY,
                 va="top", fontweight="bold")
        fig.text(0.32, ty, value, fontsize=9.5, color=C_TEXT, va="top")
        ty -= 0.043

    # separator rule
    fig.patches.append(FancyBboxPatch(
        (MARGIN_L, ty - 0.010), MARGIN_R - MARGIN_L, 0.001,
        boxstyle="square,pad=0", linewidth=0,
        facecolor="#CCCCCC", transform=fig.transFigure
    ))

    # dataset overview table
    ty -= 0.030
    fig.text(0.5, ty, "Dataset Overview",
             fontsize=11, fontweight="bold", color=C_NAVY, ha="center", va="top")

    summary = get_repo_summary(conn)
    total_all = sum(r[5] for r in summary)

    ty -= 0.038
    headers = ["Repository", "QDA Projects", "QD Projects", "Other", "Not a Project", "Total"]
    col_xs  = [0.10, 0.30, 0.43, 0.56, 0.67, 0.84]
    col_ha  = ["left", "center", "center", "center", "center", "center"]

    # header row background
    fig.patches.append(FancyBboxPatch(
        (MARGIN_L, ty - 0.006), MARGIN_R - MARGIN_L, 0.030,
        boxstyle="square,pad=0", linewidth=0,
        facecolor=C_NAVY, transform=fig.transFigure
    ))
    for hdr, x, ha in zip(headers, col_xs, col_ha):
        fig.text(x, ty + 0.008, hdr, fontsize=8.5, color="white",
                 fontweight="bold", va="center", ha=ha)

    row_labels = {"dryad": "Dryad", "fsd": "FSD Finland"}
    for i, row in enumerate(summary):
        ry = ty - 0.034 * (i + 1)
        if i % 2 == 0:
            fig.patches.append(FancyBboxPatch(
                (MARGIN_L, ry - 0.006), MARGIN_R - MARGIN_L, 0.030,
                boxstyle="square,pad=0", linewidth=0,
                facecolor=C_STRIPE, transform=fig.transFigure
            ))
        vals = [row_labels.get(row[0], row[0]),
                str(row[1]), str(row[2]), str(row[3]), str(row[4]), str(row[5])]
        for val, x, ha in zip(vals, col_xs, col_ha):
            fig.text(x, ry + 0.008, val, fontsize=9, va="center", ha=ha)

    # total row
    toty = ty - 0.034 * (len(summary) + 1)
    fig.patches.append(FancyBboxPatch(
        (MARGIN_L, toty - 0.006), MARGIN_R - MARGIN_L, 0.030,
        boxstyle="square,pad=0", linewidth=0,
        facecolor="#D0D8E8", transform=fig.transFigure
    ))
    for val, x, ha in zip(["Total", "", "", "", "", str(total_all)], col_xs, col_ha):
        fig.text(x, toty + 0.008, val, fontsize=9, va="center",
                 ha=ha, fontweight="bold", color=C_NAVY)

    add_footer(fig)
    pdf.savefig(fig, bbox_inches="tight")
    plt.close(fig)


def page_introduction(pdf):
    fig = new_page()
    add_header(fig)
    add_footer(fig)

    y = CONTENT_TOP - 0.010
    section_rule(fig, y, "1.  Introduction and Methodology")
    y -= 0.035

    y = para(fig, MARGIN_L, y, (
        "This report presents the results of Part 2 of the Seeding QDArchive project, conducted "
        "as part of the Applied Software Engineering Project seminar at FAU Erlangen (Winter "
        "2025/26 + Summer 2026) under the supervision of Prof. Dr. Dirk Riehle. The project's "
        "objective is to populate QDArchive — a new repository for qualitative research data — by "
        "acquiring and classifying publicly available qualitative research datasets from two "
        "assigned repositories."
    ))
    y -= 0.016

    section_rule(fig, y, "1.1  Scope of Classification")
    y -= 0.032

    y = para(fig, MARGIN_L, y, (
        "Part 1 of this project acquired 1,256 qualitative research projects from Dryad and the "
        "Finnish Social Science Data Archive (FSD Finland), storing full metadata in a structured "
        "SQLite database. Part 2 classifies these projects across two dimensions: project type "
        "(based on the files contained) and economic sector (using the ISIC Rev. 5 standard)."
    ))
    y -= 0.016

    section_rule(fig, y, "1.2  Project Type Classification")
    y -= 0.032

    y = para(fig, MARGIN_L, y, (
        "Each project was assigned one of four mutually exclusive types based on all file records "
        "associated with that project, including files that failed to download. Using all file "
        "records — rather than only successfully downloaded files — was a critical methodological "
        "decision: 3,342 Dryad files were rate-limited during acquisition and recorded as "
        "FAILED_SERVER_UNRESPONSIVE. Classifying on downloaded files only would have incorrectly "
        "treated these projects as having no files."
    ))
    y -= 0.010
    bullet_items = [
        ("QDA_PROJECT",   "project contains at least one QDA analysis file (.qdpx, .nvp, .mx24)"),
        ("QD_PROJECT",    "no QDA file, but contains primary data files (.txt, .pdf, .docx, .doc)"),
        ("OTHER_PROJECT", "no QDA or primary files, but other data files present"),
        ("NOT_A_PROJECT", "no file type information available"),
    ]
    for code, desc in bullet_items:
        fig.text(MARGIN_L + 0.02, y, f"{code}", fontsize=9, color=C_NAVY,
                 fontweight="bold", va="top", family="monospace")
        fig.text(MARGIN_L + 0.17, y, f"— {desc}", fontsize=9, color=C_TEXT, va="top")
        y -= 0.022
    y -= 0.010

    section_rule(fig, y, "1.3  ISIC Rev. 5 Classification")
    y -= 0.032

    y = para(fig, MARGIN_L, y, (
        "All 1,256 projects were classified into the International Standard Industrial "
        "Classification of All Economic Activities, Revision 5 (ISIC Rev. 5) at two hierarchical "
        "levels: Section (single letter, A–V) and Division (two-digit numeric code). "
        "Classification was performed using the Anthropic Claude API (claude-haiku-4-5), which "
        "received each project's title, description, and keywords and returned the most "
        "appropriate Section and Division along with a confidence rating (high, medium, or low)."
        "\n\n"
        "In addition to project-level classification, each primary data file (.txt, .pdf, .docx, "
        ".doc, .xlsx, .csv, etc.) belonging to QDA_PROJECT and QD_PROJECT types was individually "
        "classified using its filename and parent project context, covering 1,764 files."
    ))
    y -= 0.016

    section_rule(fig, y, "1.4  Report Structure")
    y -= 0.032

    para(fig, MARGIN_L, y, (
        "Results are presented as four distributions organised by repository and project type: "
        "(1) Dryad × QDA_PROJECT, (2) Dryad × QD_PROJECT, (3) FSD Finland × QDA_PROJECT, and "
        "(4) FSD Finland × QD_PROJECT. Each distribution includes a histogram of identified ISIC "
        "classes with counts, a rank-ordered table of the top classes, and a discussion of "
        "findings. Section 4 provides a comparative analysis across both repositories."
    ))

    pdf.savefig(fig, bbox_inches="tight")
    plt.close(fig)


def page_histogram(pdf, repo, ptype, rows, section_label, dlabel):
    rlabels = {"dryad": "Dryad", "fsd": "FSD Finland"}
    tlabels = {"QDA_PROJECT": "QDA Projects", "QD_PROJECT": "QD Projects"}

    fig = new_page()
    add_header(fig, section_label)
    add_footer(fig)

    total = sum(r[4] for r in rows) if rows else 0
    title = f"{rlabels[repo]} — {tlabels[ptype]}: ISIC Division Distribution"
    fig.text(MARGIN_L, CONTENT_TOP, title,
             fontsize=13, fontweight="bold", color=C_NAVY, va="top")
    fig.text(MARGIN_L, CONTENT_TOP - 0.035,
             f"Distribution {dlabel}  ·  {total} project{'s' if total != 1 else ''}  ·  "
             f"{len(rows)} distinct ISIC division{'s' if len(rows) != 1 else ''}",
             fontsize=9, color=C_GREY, va="top", style="italic")

    # plot area: leave room for title (top) and caption (bottom)
    ax = fig.add_axes([MARGIN_L, CONTENT_BOT + 0.08, MARGIN_R - MARGIN_L, 0.76])

    if not rows:
        ax.axis("off")
        ax.text(0.5, 0.5, "No projects of this type were found in this repository.",
                ha="center", va="center", fontsize=11, color=C_GREY, style="italic",
                transform=ax.transAxes)
        fig.text(0.5, CONTENT_BOT + 0.040,
                 "No data available for this distribution — see Findings page for explanation.",
                 ha="center", fontsize=8, color=C_GREY, style="italic")
        pdf.savefig(fig, bbox_inches="tight")
        plt.close(fig)
        return

    n = len(rows)
    # Narrow bars when there are only a few — avoid bars that fill the entire axis
    bar_w = 0.35 if n == 1 else (0.45 if n <= 3 else 0.65)
    labels = [textwrap.fill(r[3], 20) for r in rows]
    counts = [r[4] for r in rows]
    codes  = [f"{r[0]}-{r[1]}" for r in rows]
    ymax   = max(counts)

    bars = ax.bar(range(n), counts, width=bar_w,
                  color=C_BLUE, edgecolor="white", linewidth=0.8, zorder=3)

    for bar, cnt in zip(bars, counts):
        ax.text(bar.get_x() + bar.get_width() / 2,
                bar.get_height() + ymax * 0.02,
                str(cnt), ha="center", va="bottom",
                fontsize=10, fontweight="bold", color=C_NAVY)

    ax.set_xticks(range(n))
    ax.set_xticklabels(labels, fontsize=9, rotation=30, ha="right")
    ax.set_ylabel("Number of Projects", fontsize=10, color=C_GREY)
    ax.set_xlim(-0.6, n - 0.4)
    ax.set_ylim(0, ymax * 1.20)
    ax.yaxis.set_major_locator(ticker.MaxNLocator(integer=True))
    ax.yaxis.grid(True, linestyle="--", alpha=0.45, zorder=0)
    ax.set_axisbelow(True)
    for spine in ["top", "right"]:
        ax.spines[spine].set_visible(False)
    ax.spines["left"].set_color("#CCCCCC")
    ax.spines["bottom"].set_color("#CCCCCC")
    ax.tick_params(colors=C_GREY, length=3)

    # ISIC codes as secondary x labels
    ax2 = ax.twiny()
    ax2.set_xlim(ax.get_xlim())
    ax2.set_xticks(range(n))
    ax2.set_xticklabels(codes, fontsize=8, color=C_GREY)
    ax2.tick_params(length=0)
    ax2.spines["top"].set_visible(False)

    fig.text(0.5, CONTENT_BOT + 0.020,
             "Figure: ISIC Rev. 5 divisions identified in this distribution. "
             "Counts shown above bars. ISIC codes shown on top axis.",
             ha="center", fontsize=8, color=C_GREY, style="italic")

    pdf.savefig(fig, bbox_inches="tight")
    plt.close(fig)


def page_table_and_discussion(pdf, repo, ptype, rows, section_label,
                               dlabel, discussion_paragraphs):
    rlabels = {"dryad": "Dryad", "fsd": "FSD Finland"}
    tlabels = {"QDA_PROJECT": "QDA Projects", "QD_PROJECT": "QD Projects"}
    top20 = rows[:20]
    total = sum(r[4] for r in rows)

    fig = new_page()
    add_header(fig, section_label)
    add_footer(fig)

    title = f"{rlabels[repo]} — {tlabels[ptype]}: Ranked Class Table and Findings"
    fig.text(MARGIN_L, CONTENT_TOP, title,
             fontsize=13, fontweight="bold", color=C_NAVY, va="top")
    n_shown = min(20, len(top20))
    fig.text(MARGIN_L, CONTENT_TOP - 0.033,
             f"Distribution {dlabel}  ·  {total} project{'s' if total != 1 else ''}  ·  "
             f"top {n_shown} of {len(rows)} class{'es' if len(rows) != 1 else ''} shown",
             fontsize=9, color=C_GREY, va="top", style="italic")

    # ── Table ──────────────────────────────────────────────────────────────────
    # Table starts below title block
    tbl_top  = CONTENT_TOP - 0.062     # y of the top of the header row
    row_h    = 0.031
    col_xs   = [MARGIN_L, MARGIN_L + 0.055, MARGIN_L + 0.135, 0.80, 0.87]
    col_hdrs = ["Rank", "Code", "ISIC Division Name (Full)", "Count", "%"]
    col_ha   = ["center", "center", "left", "center", "center"]

    if top20:
        # header row
        fig.patches.append(FancyBboxPatch(
            (MARGIN_L, tbl_top - row_h + 0.005), MARGIN_R - MARGIN_L, row_h,
            boxstyle="square,pad=0", linewidth=0,
            facecolor=C_NAVY, transform=fig.transFigure
        ))
        for hdr, x, ha in zip(col_hdrs, col_xs, col_ha):
            fig.text(x, tbl_top - row_h / 2 + 0.005, hdr,
                     fontsize=8.5, color="white", fontweight="bold",
                     va="center", ha=ha)

        for i, row in enumerate(top20):
            ry = tbl_top - row_h * (i + 2) + 0.005
            if i % 2 == 1:
                fig.patches.append(FancyBboxPatch(
                    (MARGIN_L, ry), MARGIN_R - MARGIN_L, row_h,
                    boxstyle="square,pad=0", linewidth=0,
                    facecolor=C_STRIPE, transform=fig.transFigure
                ))
            pct  = f"{row[4] / total * 100:.1f}%" if total else "—"
            code = f"{row[0]}-{row[1]}"
            vals = [str(i + 1), code, row[3], str(row[4]), pct]
            for val, x, ha in zip(vals, col_xs, col_ha):
                fig.text(x, ry + row_h / 2, val,
                         fontsize=8.5, va="center", ha=ha)

        table_bottom = tbl_top - row_h * (len(top20) + 2) + 0.005
    else:
        table_bottom = tbl_top

    # ── Findings ───────────────────────────────────────────────────────────────
    y = table_bottom - 0.022
    section_rule(fig, y, "Findings and Discussion")
    y -= 0.032

    for p in discussion_paragraphs:
        y = para(fig, MARGIN_L, y, p)
        y -= 0.014
        if y < CONTENT_BOT + 0.015:
            break

    pdf.savefig(fig, bbox_inches="tight")
    plt.close(fig)


def page_fsd_qda_findings(pdf, discussion_paragraphs):
    """Single combined page for FSD QDA — no data so no histogram needed."""
    fig = new_page()
    add_header(fig, "3.  Repository 2: FSD Finland")
    add_footer(fig)

    title = "FSD Finland — QDA Projects: Distribution 3"
    fig.text(MARGIN_L, CONTENT_TOP, title,
             fontsize=13, fontweight="bold", color=C_NAVY, va="top")
    fig.text(MARGIN_L, CONTENT_TOP - 0.033,
             "Distribution 3  ·  0 projects  ·  0 distinct ISIC divisions",
             fontsize=9, color=C_GREY, va="top", style="italic")

    # shaded note box
    y_box = CONTENT_TOP - 0.075
    fig.patches.append(FancyBboxPatch(
        (MARGIN_L, y_box - 0.045), MARGIN_R - MARGIN_L, 0.055,
        boxstyle="round,pad=0.01", linewidth=1,
        edgecolor="#BBBBBB", facecolor="#FFF8E8",
        transform=fig.transFigure
    ))
    fig.text(0.5, y_box - 0.015,
             "No QDA projects were identified in this repository for this distribution.",
             ha="center", fontsize=10, color="#774400",
             style="italic", va="center")

    y = y_box - 0.075
    section_rule(fig, y, "Findings and Discussion")
    y -= 0.032

    for p in discussion_paragraphs:
        y = para(fig, MARGIN_L, y, p)
        y -= 0.014

    pdf.savefig(fig, bbox_inches="tight")
    plt.close(fig)


def page_comparative(pdf, conn):
    fig = new_page()
    add_header(fig)
    add_footer(fig)

    y = CONTENT_TOP - 0.010
    section_rule(fig, y, "4.  Comparative Analysis and Conclusion")
    y -= 0.035

    dryad_qd = conn.execute("""
        SELECT COUNT(*) FROM PROJECTS p JOIN REPOSITORIES r ON r.id=p.repository_id
        WHERE r.name='dryad' AND p.type='QD_PROJECT'""").fetchone()[0]
    fsd_qd = conn.execute("""
        SELECT COUNT(*) FROM PROJECTS p JOIN REPOSITORIES r ON r.id=p.repository_id
        WHERE r.name='fsd' AND p.type='QD_PROJECT'""").fetchone()[0]
    total_qda = conn.execute(
        "SELECT COUNT(*) FROM PROJECTS WHERE type='QDA_PROJECT'").fetchone()[0]

    section_rule(fig, y, "4.1  Cross-Repository Observations")
    y -= 0.032
    y = para(fig, MARGIN_L, y, (
        f"The two repositories exhibit markedly different profiles in terms of both scale and "
        f"disciplinary coverage. Dryad contributed {dryad_qd} QD projects across nine ISIC "
        f"divisions, while FSD Finland contributed only {fsd_qd} publicly accessible QD projects "
        f"across three divisions. This disparity does not reflect FSD's actual holdings — FSD "
        f"catalogues 403 qualitative studies in its English-language archive — but is a direct "
        f"consequence of the archive's requirement for institutional authentication via the Aila "
        f"Data Service. Only studies with publicly accessible PDF attachments qualified as "
        f"QD_PROJECT."
    ))
    y -= 0.013
    y = para(fig, MARGIN_L, y, (
        "Both repositories are dominated by N-72 (Scientific Research and Development), the "
        "expected outcome for academic research collections. The second-ranked division differs "
        "sharply: Dryad ranks R-86 (Human Health Activities) second at 27.1%, reflecting its "
        "strong life-sciences and clinical research base. FSD's small QD sample shows no R-86 "
        "representation; instead S-91 (Libraries, Archives and Cultural Activities) and Q-85 "
        "(Education) appear, consistent with Finland's social-science and cultural heritage "
        "research tradition."
    ))
    y -= 0.016

    section_rule(fig, y, "4.2  QDA File Availability")
    y -= 0.032
    y = para(fig, MARGIN_L, y, (
        f"Across both repositories, only {total_qda} QDA analysis file was identified — a single "
        "NVivo (.nvp) project deposited on Dryad and classified as R-86 (Human Health "
        "Activities). This confirms the core challenge motivating QDArchive: researchers who "
        "conduct qualitative data analysis with NVivo, MAXQDA, or QDAcity rarely deposit the "
        "resulting analysis files in open repositories. Interview transcripts and coded datasets "
        "are deposited, but the structured analysis files that capture the analytical process "
        "itself remain largely inaccessible. QDArchive therefore cannot be seeded purely by "
        "harvesting existing repositories — it must rely on targeted outreach and deposit "
        "incentives to build a meaningful QDA file collection."
    ))
    y -= 0.016

    section_rule(fig, y, "4.3  Classification Confidence and Limitations")
    y -= 0.032
    y = para(fig, MARGIN_L, y, (
        "The AI-assisted ISIC classification produces reliable results for projects with "
        "descriptive titles, rich abstracts, and multiple keywords. Quality is lower for FSD "
        "projects, where only the DDI-C 2.5 XML title and abstract were available — no file "
        "content could be read. The large N-72 share also partly reflects the classifier's "
        "fallback behaviour: projects with generic or absent descriptions are assigned N-72 "
        "rather than a more specific division. A manual review of a sample of N-72 assignments "
        "would be required to quantify this effect."
    ))
    y -= 0.016

    section_rule(fig, y, "4.4  Conclusion")
    y -= 0.032
    para(fig, MARGIN_L, y, (
        "This classification provides a structured, ISIC-aligned view of 1,256 qualitative "
        "research projects from Dryad and FSD Finland. The data confirms that qualitative "
        "research in the social, health, and agricultural sciences is represented in open "
        "repositories — but that QDA analysis files, QDArchive's primary target, are almost "
        "entirely absent from open deposit. The classification infrastructure built here — "
        "the ISIC classifier, file-level annotation pipeline, and structured SQLite schema — "
        "provides a reusable foundation for classifying future acquisitions as QDArchive grows."
    ))

    pdf.savefig(fig, bbox_inches="tight")
    plt.close(fig)


# ── Discussion text ────────────────────────────────────────────────────────────

DISCUSSION = {
    ("dryad", "QDA_PROJECT"): [
        "Only one QDA project was identified across the entire Dryad corpus — a NVivo project "
        "file (.nvp) classified as R-86 (Human Health Activities). This assignment suggests the "
        "underlying qualitative study concerned medical or patient-related research, which is "
        "consistent with the large body of health-science interview studies observed in the "
        "broader Dryad QD dataset.",

        "The near-total absence of QDA files in Dryad reflects a structural gap in open-data "
        "culture among qualitative researchers. Despite 15 targeted search queries including "
        "specific QDA file extension terms ('qdpx', 'nvp'), researchers appear to deposit "
        "interview transcripts, coded spreadsheets, and final datasets — but not the NVivo or "
        "MAXQDA project files that capture the analytical process itself. This is the precise "
        "gap that QDArchive is designed to address.",
    ],
    ("dryad", "QD_PROJECT"): [
        "Dryad's 340 QD projects span nine ISIC divisions, with three divisions accounting for "
        "96.8% of the distribution. N-72 (Scientific Research and Development) dominates at "
        "60.3% (205 projects), followed by R-86 (Human Health Activities) at 27.1% (92 "
        "projects) and A-01 (Crop and Animal Production) at 8.8% (30 projects).",

        "The dominance of N-72 is partly structural: it serves as both the correct "
        "classification for general academic research and the classifier's default for "
        "ambiguous descriptions. The R-86 cluster is substantively significant — it corresponds "
        "to the large body of medical and nursing interview studies identified via queries such "
        "as 'semi-structured interview' and 'thematic analysis', which typically deposit "
        "anonymised transcripts (.docx, .txt) and coding sheets (.xlsx).",

        "The A-01 presence (8.8%) reflects Dryad's strong life-sciences base. Agricultural "
        "researchers use 'qualitative' in a scientific rather than social-science sense (e.g., "
        "qualitative assessment of crop traits). These projects — typically containing .csv, "
        ".xlsx, and image files — represent noise from broad keyword matching. They are "
        "correctly classified as QD_PROJECT rather than QDA_PROJECT since they contain no "
        "qualitative data analysis files.",
    ],
    ("fsd", "QDA_PROJECT"): [
        "No QDA projects were identified in the FSD Finland corpus. This is a direct consequence "
        "of FSD's access control model: all primary data files — interview transcripts, written "
        "responses, and coding files — require institutional authentication via the Aila Data "
        "Service. Without downloadable files, no project can be assigned the QDA_PROJECT type.",

        "FSD's public catalogue lists 403 English-language qualitative studies, but the only "
        "file consistently available without authentication is the DDI-C 2.5 XML metadata "
        "record. Some of these studies very likely include QDA analysis files accessible to "
        "authenticated users, but this cannot be determined from public data alone. The absence "
        "of FSD QDA projects should therefore be interpreted as an access limitation, not as "
        "evidence that Finnish social science researchers do not produce QDA files.",
    ],
    ("fsd", "QD_PROJECT"): [
        "Only four FSD studies qualified as QD_PROJECT — those with publicly accessible PDF "
        "attachments (typically methodological reports or codebooks) not requiring Aila login. "
        "These four projects span three divisions: S-91 (Libraries, Archives and Cultural "
        "Activities, 50%), N-72 (Scientific Research, 25%), and Q-85 (Education, 25%).",

        "The disciplinary profile — cultural heritage, research methodology, and education — "
        "is consistent with FSD's institutional mandate as Finland's national social science "
        "data archive, whose holdings are concentrated in sociology, political science, history, "
        "and education research.",

        "The extremely small sample size (n=4) means this distribution cannot be considered "
        "representative of FSD's full 403-study catalogue. A meaningful ISIC classification of "
        "FSD data would require authenticated Aila access to retrieve the actual primary data "
        "files from at least a representative sample of the archived studies.",
    ],
}


# ── Entry point ────────────────────────────────────────────────────────────────

def run():
    conn = sqlite3.connect(str(DB_PATH))
    OUT_PATH.parent.mkdir(exist_ok=True)

    dlabels  = {("dryad","QDA_PROJECT"):"1", ("dryad","QD_PROJECT"):"2",
                ("fsd","QDA_PROJECT"):"3",   ("fsd","QD_PROJECT"):"4"}
    slabels  = {("dryad","QDA_PROJECT"):"2.  Repository 1: Dryad",
                ("dryad","QD_PROJECT") :"2.  Repository 1: Dryad",
                ("fsd","QDA_PROJECT")  :"3.  Repository 2: FSD Finland",
                ("fsd","QD_PROJECT")   :"3.  Repository 2: FSD Finland"}

    with PdfPages(OUT_PATH) as pdf:
        page_title(pdf, conn)
        page_introduction(pdf)

        for repo, ptype in [("dryad","QDA_PROJECT"), ("dryad","QD_PROJECT"),
                             ("fsd","QDA_PROJECT"),   ("fsd","QD_PROJECT")]:
            rows  = get_distrib(conn, repo, ptype)
            dl    = dlabels[(repo, ptype)]
            sl    = slabels[(repo, ptype)]
            disc  = DISCUSSION[(repo, ptype)]
            total = sum(r[4] for r in rows)
            print(f"  Distribution {dl}: {repo}/{ptype} — {len(rows)} classes, {total} projects")

            if repo == "fsd" and ptype == "QDA_PROJECT":
                # No data — single combined page, skip separate histogram
                page_fsd_qda_findings(pdf, disc)
            else:
                page_histogram(pdf, repo, ptype, rows, sl, dl)
                page_table_and_discussion(pdf, repo, ptype, rows, sl, dl, disc)

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
