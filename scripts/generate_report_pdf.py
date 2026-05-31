"""
Part 2 Step 4d — Classification Report PDF
Professional A4 portrait, horizontal bar charts, clean academic layout.
"""

import sqlite3
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.patches import FancyBboxPatch
import textwrap, datetime

DB_PATH  = Path(__file__).parent.parent / "23025313-sq26-classification.db"
OUT_PATH = Path(__file__).parent.parent / "export" / "23025313-classification-report.pdf"

# ── Design tokens ─────────────────────────────────────────────────────────────
C_NAVY   = "#003865"
C_BLUE   = "#2E75B6"
C_LGOLD  = "#C8A951"
C_STRIPE = "#EBF3FB"
C_LIGHT  = "#F4F8FC"
C_TEXT   = "#1A1A1A"
C_GREY   = "#777777"
C_LGREY  = "#CCCCCC"

# Section-colour palette for bars (by ISIC section letter)
SECTION_COLORS = {
    "N": "#2E75B6", "R": "#C00000", "A": "#548235",
    "Q": "#7030A0", "P": "#E36C09", "S": "#0070C0",
    "K": "#FF6600", "L": "#595959",
}
DEFAULT_BAR = "#2E75B6"

PAGE_W, PAGE_H = 8.27, 11.69   # A4 portrait
ML, MR = 0.08, 0.92            # left / right margins (figure fraction)
CTOP   = 0.935                 # content top  (below header)
CBOT   = 0.050                 # content bottom (above footer)

plt.rcParams.update({
    "font.family":      "DejaVu Sans",
    "font.size":        10,
    "text.color":       C_TEXT,
    "axes.labelcolor":  C_GREY,
    "xtick.color":      C_GREY,
    "ytick.color":      C_TEXT,
})

PAGE_NUM = [0]


# ── Chrome helpers ────────────────────────────────────────────────────────────

def new_page():
    PAGE_NUM[0] += 1
    return plt.figure(figsize=(PAGE_W, PAGE_H))


def chrome(fig, section=""):
    """Header, footer, optional breadcrumb."""
    # header band
    fig.patches.append(FancyBboxPatch(
        (0, 0.965), 1, 0.035, boxstyle="square,pad=0",
        facecolor=C_NAVY, linewidth=0, transform=fig.transFigure, zorder=3))
    fig.text(0.015, 0.982,
             "Seeding QDArchive — Part 2: Data Classification Report",
             fontsize=7.5, color="white", va="center", fontweight="bold")
    fig.text(0.985, 0.982,
             "Jakir Hussain Rifat · 23025313 · FAU Erlangen",
             fontsize=7, color="#AACCEE", va="center", ha="right")
    if section:
        fig.text(ML, 0.955, section,
                 fontsize=8, color=C_GREY, va="top", style="italic")
    # footer rule + page number
    fig.patches.append(FancyBboxPatch(
        (ML, 0.033), MR - ML, 0.001, boxstyle="square,pad=0",
        facecolor=C_LGREY, linewidth=0, transform=fig.transFigure))
    fig.text(0.5, 0.020, f"— {PAGE_NUM[0]} —",
             fontsize=8, color=C_GREY, ha="center", va="center")


def hrule(fig, y, label=None, gold=True):
    """Horizontal rule, optionally labelled."""
    color = C_LGOLD if gold else C_LGREY
    fig.patches.append(FancyBboxPatch(
        (ML, y), MR - ML, 0.0025, boxstyle="square,pad=0",
        facecolor=color, linewidth=0, transform=fig.transFigure))
    if label:
        fig.text(ML, y + 0.007, label.upper(),
                 fontsize=9, color=C_NAVY, fontweight="bold", va="bottom")


def para(fig, x, y, text, width=99, fs=9.5, color=C_TEXT, ls=0.022):
    """Render a wrapped paragraph; return y below last line."""
    lines = []
    for raw in text.split("\n"):
        lines.extend(textwrap.wrap(raw, width) if raw.strip() else [""])
    for line in lines:
        fig.text(x, y, line, fontsize=fs, color=color, va="top")
        y -= ls
    return y


# ── Data helpers ──────────────────────────────────────────────────────────────

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


# ── Chart helper ──────────────────────────────────────────────────────────────

def hbar_chart(fig, ax_rect, rows, title, subtitle, caption):
    """
    Draw a horizontal bar chart in the given axes rectangle.
    ax_rect = [left, bottom, width, height] in figure fraction.
    Returns the axes object.
    """
    n      = len(rows)
    labels = [textwrap.fill(r[2], 30) for r in rows]
    counts = [r[3] for r in rows]
    codes  = [f"{r[0]}-{r[1]}" for r in rows]
    colors = [SECTION_COLORS.get(r[0], DEFAULT_BAR) for r in rows]
    xmax   = max(counts)

    ax = fig.add_axes(ax_rect)

    # bars (reversed so rank 1 is at top)
    ypos = list(range(n - 1, -1, -1))
    bar_h = min(0.55, 4.0 / max(n, 1))
    bars = ax.barh(ypos, counts, height=bar_h,
                   color=list(reversed(colors)),
                   edgecolor="white", linewidth=0.6, zorder=3)

    # count labels to the right of each bar
    for bar, cnt in zip(bars, reversed(counts)):
        ax.text(bar.get_width() + xmax * 0.015, bar.get_y() + bar.get_height() / 2,
                str(cnt), va="center", ha="left",
                fontsize=9.5, fontweight="bold", color=C_NAVY)

    # ISIC codes as secondary y-labels on the right
    ax2 = ax.twinx()
    ax2.set_ylim(ax.get_ylim())
    ax2.set_yticks(ypos)
    ax2.set_yticklabels(list(reversed(codes)), fontsize=8, color=C_GREY)
    ax2.tick_params(length=0)
    ax2.spines["right"].set_color(C_LGREY)
    for sp in ["top", "left", "bottom"]:
        ax2.spines[sp].set_visible(False)

    # y-axis labels (full division names)
    ax.set_yticks(ypos)
    ax.set_yticklabels(list(reversed(labels)), fontsize=9)
    ax.set_ylim(-0.6, n - 0.4)

    ax.set_xlabel("Number of Projects", fontsize=9, color=C_GREY)
    ax.set_xlim(0, xmax * 1.22)
    ax.xaxis.set_major_locator(mticker.MaxNLocator(integer=True, nbins=6))
    ax.xaxis.grid(True, linestyle="--", alpha=0.4, zorder=0)
    ax.set_axisbelow(True)
    for sp in ["top", "right"]:
        ax.spines[sp].set_visible(False)
    ax.spines["left"].set_color(C_LGREY)
    ax.spines["bottom"].set_color(C_LGREY)
    ax.tick_params(axis="x", colors=C_GREY, length=3)
    ax.tick_params(axis="y", length=0)

    # title + subtitle above axes
    fig.text(ax_rect[0], ax_rect[1] + ax_rect[3] + 0.015,
             title, fontsize=12, fontweight="bold", color=C_NAVY, va="bottom")
    fig.text(ax_rect[0], ax_rect[1] + ax_rect[3] + 0.004,
             subtitle, fontsize=8.5, color=C_GREY, va="bottom", style="italic")

    # caption below axes
    fig.text(0.5, ax_rect[1] - 0.018, caption,
             ha="center", fontsize=7.5, color=C_GREY, style="italic")

    return ax


def draw_table(fig, rows, total, tbl_top):
    """
    Draw the ranked-class table. Returns y-coordinate below last row.
    tbl_top = figure-fraction y of the table header top edge.
    """
    top20   = rows[:20]
    row_h   = 0.030
    col_xs  = [ML + 0.005, ML + 0.060, ML + 0.145, 0.795, 0.865]
    col_hdr = ["Rank", "Code", "ISIC Division Name (Full)", "Count", "%"]
    col_ha  = ["center", "center", "left", "center", "center"]

    # header background
    fig.patches.append(FancyBboxPatch(
        (ML, tbl_top - row_h), MR - ML, row_h,
        boxstyle="square,pad=0", linewidth=0,
        facecolor=C_NAVY, transform=fig.transFigure))
    for hdr, x, ha in zip(col_hdr, col_xs, col_ha):
        fig.text(x, tbl_top - row_h / 2, hdr,
                 fontsize=8.5, color="white", fontweight="bold",
                 va="center", ha=ha)

    for i, row in enumerate(top20):
        ry_top = tbl_top - row_h * (i + 2)
        if i % 2 == 0:
            fig.patches.append(FancyBboxPatch(
                (ML, ry_top), MR - ML, row_h,
                boxstyle="square,pad=0", linewidth=0,
                facecolor=C_STRIPE, transform=fig.transFigure))
        pct  = f"{row[3] / total * 100:.1f}%" if total else "—"
        code = f"{row[0]}-{row[1]}"
        vals = [str(i + 1), code, row[2], str(row[3]), pct]
        for val, x, ha in zip(vals, col_xs, col_ha):
            fig.text(x, ry_top + row_h / 2, val,
                     fontsize=8.5, va="center", ha=ha)

    return tbl_top - row_h * (len(top20) + 2)


# ── Pages ──────────────────────────────────────────────────────────────────────

def page_title(pdf, conn):
    fig = new_page()

    # top band
    fig.patches.append(FancyBboxPatch(
        (0, 0.820), 1, 0.180, boxstyle="square,pad=0",
        facecolor=C_NAVY, linewidth=0, transform=fig.transFigure))
    fig.patches.append(FancyBboxPatch(
        (0, 0.808), 1, 0.012, boxstyle="square,pad=0",
        facecolor=C_LGOLD, linewidth=0, transform=fig.transFigure))

    fig.text(0.5, 0.932, "Seeding QDArchive",
             fontsize=28, fontweight="bold", color="white",
             ha="center", va="center")
    fig.text(0.5, 0.878, "Part 2: Data Classification Report",
             fontsize=17, color="#AACCEE", ha="center", va="center")
    fig.text(0.5, 0.845, "ISIC Rev. 5 Classification of Qualitative Research Projects",
             fontsize=10.5, color="#88AACC", style="italic",
             ha="center", va="center")

    # metadata block
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
    ty = 0.792
    for lbl, val in meta:
        fig.text(0.10, ty, f"{lbl}:", fontsize=9.5, color=C_GREY,
                 fontweight="bold", va="top")
        fig.text(0.32, ty, val, fontsize=9.5, color=C_TEXT, va="top")
        ty -= 0.044

    # separator
    fig.patches.append(FancyBboxPatch(
        (ML, ty - 0.010), MR - ML, 0.001, boxstyle="square,pad=0",
        facecolor=C_LGREY, linewidth=0, transform=fig.transFigure))

    # Dataset overview table
    ty -= 0.030
    fig.text(0.5, ty, "Dataset Overview",
             fontsize=11, fontweight="bold", color=C_NAVY,
             ha="center", va="top")

    summary   = get_repo_summary(conn)
    total_all = sum(r[5] for r in summary)
    ty       -= 0.040

    col_xs  = [ML + 0.010, 0.315, 0.430, 0.535, 0.645, 0.835]
    col_hdr = ["Repository", "QDA Projects", "QD Projects", "Other", "Not a Project", "Total"]
    col_ha  = ["left", "center", "center", "center", "center", "center"]
    row_h   = 0.038

    # header
    fig.patches.append(FancyBboxPatch(
        (ML, ty - row_h), MR - ML, row_h, boxstyle="square,pad=0",
        facecolor=C_NAVY, linewidth=0, transform=fig.transFigure))
    for hdr, x, ha in zip(col_hdr, col_xs, col_ha):
        fig.text(x, ty - row_h / 2, hdr,
                 fontsize=8.5, color="white", fontweight="bold",
                 va="center", ha=ha)

    rl = {"dryad": "Dryad", "fsd": "FSD Finland"}
    for i, row in enumerate(summary):
        ry = ty - row_h * (i + 2)
        if i % 2 == 0:
            fig.patches.append(FancyBboxPatch(
                (ML, ry), MR - ML, row_h, boxstyle="square,pad=0",
                facecolor=C_STRIPE, linewidth=0, transform=fig.transFigure))
        vals = [rl.get(row[0], row[0]),
                str(row[1]), str(row[2]), str(row[3]), str(row[4]), str(row[5])]
        for val, x, ha in zip(vals, col_xs, col_ha):
            fig.text(x, ry + row_h / 2, val, fontsize=9.5, va="center", ha=ha)

    # total row
    toty = ty - row_h * (len(summary) + 2)
    fig.patches.append(FancyBboxPatch(
        (ML, toty), MR - ML, row_h, boxstyle="square,pad=0",
        facecolor="#D4DCE8", linewidth=0, transform=fig.transFigure))
    for val, x, ha in zip(["Total", "", "", "", "", str(total_all)], col_xs, col_ha):
        fig.text(x, toty + row_h / 2, val, fontsize=9.5, va="center",
                 ha=ha, fontweight="bold", color=C_NAVY)

    # legend for section colours
    ty2 = toty - 0.038
    fig.text(ML, ty2, "ISIC Section colour key used in charts:",
             fontsize=8, color=C_GREY, va="top")
    lx = ML
    for code, name, col in [
        ("N", "Prof./Scientific", "#2E75B6"),
        ("R", "Health/Social",    "#C00000"),
        ("A", "Agriculture",      "#548235"),
        ("Q", "Education",        "#7030A0"),
        ("P", "Public Admin",     "#E36C09"),
        ("S", "Arts/Culture",     "#0070C0"),
    ]:
        fig.patches.append(FancyBboxPatch(
            (lx, ty2 - 0.042), 0.018, 0.016, boxstyle="square,pad=0",
            facecolor=col, linewidth=0, transform=fig.transFigure))
        fig.text(lx + 0.022, ty2 - 0.034, f"{code} – {name}",
                 fontsize=7.5, color=C_TEXT, va="center")
        lx += 0.130

    chrome(fig)
    pdf.savefig(fig, bbox_inches="tight")
    plt.close(fig)


def page_introduction(pdf):
    fig = new_page()
    chrome(fig)

    y = CTOP
    hrule(fig, y, "1.  Introduction and Methodology")
    y -= 0.040

    y = para(fig, ML, y, (
        "This report presents the results of Part 2 of the Seeding QDArchive project, conducted "
        "as part of the Applied Software Engineering Project seminar at FAU Erlangen (Winter "
        "2025/26 + Summer 2026) under the supervision of Prof. Dr. Dirk Riehle. The project's "
        "objective is to populate QDArchive — a new repository for qualitative research data — "
        "by acquiring and classifying publicly available qualitative research datasets from two "
        "assigned repositories."
    ))
    y -= 0.018

    hrule(fig, y, "1.1  Scope of Classification")
    y -= 0.034
    y = para(fig, ML, y, (
        "Part 1 acquired 1,256 qualitative research projects from Dryad and the Finnish Social "
        "Science Data Archive (FSD Finland), storing full metadata in a structured SQLite "
        "database. Part 2 classifies these projects across two dimensions: project type (based "
        "on the files contained) and economic sector (using the ISIC Rev. 5 standard)."
    ))
    y -= 0.018

    hrule(fig, y, "1.2  Project Type Classification")
    y -= 0.034
    y = para(fig, ML, y, (
        "Each project was assigned one of four mutually exclusive types based on all file "
        "records, including files that failed to download. Using all file records — rather than "
        "only successfully downloaded files — was a critical methodological decision: 3,342 "
        "Dryad files were rate-limited during acquisition (FAILED_SERVER_UNRESPONSIVE). "
        "Classifying on downloaded files only would have incorrectly labelled these projects as "
        "having no files."
    ))
    y -= 0.010
    bullets = [
        ("QDA_PROJECT",   "project contains at least one QDA analysis file (.qdpx, .nvp, .mx24)"),
        ("QD_PROJECT",    "no QDA file, but contains primary data files (.txt, .pdf, .docx, .doc)"),
        ("OTHER_PROJECT", "no QDA or primary files, but other valid data files present"),
        ("NOT_A_PROJECT", "no file type information can be derived"),
    ]
    for code, desc in bullets:
        fig.text(ML + 0.02, y, code, fontsize=9, color=C_NAVY,
                 fontweight="bold", va="top", family="monospace")
        fig.text(ML + 0.175, y, f"— {desc}", fontsize=9, color=C_TEXT, va="top")
        y -= 0.023
    y -= 0.012

    hrule(fig, y, "1.3  ISIC Rev. 5 Classification")
    y -= 0.034
    y = para(fig, ML, y, (
        "All 1,256 projects were classified into the International Standard Industrial "
        "Classification of All Economic Activities, Revision 5 (ISIC Rev. 5) at two levels: "
        "Section (letter A–V) and Division (two-digit code). The Anthropic Claude API "
        "(claude-haiku-4-5) received each project's title, description, and keywords and "
        "returned the most appropriate Section/Division with a confidence rating. Additionally, "
        "each primary data file (.txt, .pdf, .docx, .doc, .xlsx, .csv, etc.) in QDA and QD "
        "projects was individually classified using its filename and parent project context — "
        "covering 1,764 files in total."
    ))
    y -= 0.018

    hrule(fig, y, "1.4  Report Structure")
    y -= 0.034
    para(fig, ML, y, (
        "Results are presented as four distributions organised by repository and project type: "
        "(1) Dryad × QDA_PROJECT, (2) Dryad × QD_PROJECT, (3) FSD Finland × QDA_PROJECT, and "
        "(4) FSD Finland × QD_PROJECT. Each distribution includes a horizontal bar chart of "
        "identified ISIC divisions, a rank-ordered table of the top classes, and a discussion "
        "of findings. Section 4 provides a comparative analysis across both repositories. "
        "Chart bars are colour-coded by ISIC section as shown in the legend on the title page."
    ))

    pdf.savefig(fig, bbox_inches="tight")
    plt.close(fig)


def page_combined_small(pdf, repo, ptype, rows, section_label, dlabel, disc):
    """Single page: small chart + table + findings (for distributions with ≤ 5 classes)."""
    rlabels = {"dryad": "Dryad", "fsd": "FSD Finland"}
    tlabels = {"QDA_PROJECT": "QDA Projects", "QD_PROJECT": "QD Projects"}

    fig = new_page()
    chrome(fig, section_label)

    n     = len(rows)
    total = sum(r[3] for r in rows) if rows else 0

    dist_line = (f"Distribution {dlabel}  ·  {total} project{'s' if total != 1 else ''}  ·  "
                 f"{n} distinct ISIC division{'s' if n != 1 else ''}")

    if n > 0:
        # chart occupies upper portion
        chart_h   = 0.06 + n * 0.065
        chart_top = CTOP - 0.010
        ax_rect   = [ML, chart_top - chart_h, MR - ML - 0.05, chart_h]
        hbar_chart(
            fig, ax_rect, rows,
            title    = f"{rlabels[repo]} — {tlabels[ptype]}: ISIC Division Distribution",
            subtitle = dist_line,
            caption  = ("Figure: ISIC Rev. 5 divisions. Counts shown to the right of bars. "
                        "ISIC codes on the right axis. Bars colour-coded by ISIC section.")
        )
        tbl_top = chart_top - chart_h - 0.055
    else:
        # no chart — findings-only layout
        fig.text(ML, CTOP, f"{rlabels[repo]} — {tlabels[ptype]}: Distribution {dlabel}",
                 fontsize=13, fontweight="bold", color=C_NAVY, va="top")
        fig.text(ML, CTOP - 0.035, dist_line,
                 fontsize=9, color=C_GREY, va="top", style="italic")
        fig.patches.append(FancyBboxPatch(
            (ML, CTOP - 0.110), MR - ML, 0.060,
            boxstyle="round,pad=0.01", linewidth=1,
            edgecolor="#BBBBBB", facecolor="#FFF8E8",
            transform=fig.transFigure))
        fig.text(0.5, CTOP - 0.080,
                 "No projects of this type were identified in this repository.",
                 ha="center", fontsize=10, color="#774400",
                 style="italic", va="center")
        tbl_top = CTOP - 0.130

    # ranked table
    if rows:
        hrule(fig, tbl_top, "Ranked Class Table", gold=False)
        tbl_top -= 0.028
        fig.text(ML, tbl_top,
                 f"Top {min(20, n)} of {n} class{'es' if n != 1 else ''}  ·  "
                 f"Total: {total} project{'s' if total != 1 else ''}",
                 fontsize=8, color=C_GREY, va="top", style="italic")
        tbl_top -= 0.022
        tbl_bot = draw_table(fig, rows, total, tbl_top)
    else:
        tbl_bot = tbl_top

    # findings
    y = tbl_bot - 0.022
    hrule(fig, y, "Findings and Discussion")
    y -= 0.032
    for p in disc:
        y = para(fig, ML, y, p)
        y -= 0.014
        if y < CBOT + 0.015:
            break

    pdf.savefig(fig, bbox_inches="tight")
    plt.close(fig)


def page_histogram_full(pdf, repo, ptype, rows, section_label, dlabel):
    """Full page histogram for larger distributions."""
    rlabels = {"dryad": "Dryad", "fsd": "FSD Finland"}
    tlabels = {"QDA_PROJECT": "QDA Projects", "QD_PROJECT": "QD Projects"}

    fig = new_page()
    chrome(fig, section_label)

    n     = len(rows)
    total = sum(r[3] for r in rows)

    chart_h = min(0.78, 0.060 + n * 0.072)
    caption = ("Figure: ISIC Rev. 5 divisions for this distribution. "
               "Counts to the right of bars. ISIC codes on the right axis. "
               "Bars colour-coded by ISIC section (see title page legend).")
    hbar_chart(
        fig,
        ax_rect  = [ML, CBOT + 0.065, MR - ML - 0.05, chart_h],
        rows     = rows,
        title    = f"{rlabels[repo]} — {tlabels[ptype]}: ISIC Division Distribution",
        subtitle = (f"Distribution {dlabel}  ·  {total} projects  ·  "
                    f"{n} distinct ISIC divisions"),
        caption  = caption
    )

    pdf.savefig(fig, bbox_inches="tight")
    plt.close(fig)


def page_table_full(pdf, repo, ptype, rows, section_label, dlabel, disc):
    """Table + findings page for larger distributions."""
    rlabels = {"dryad": "Dryad", "fsd": "FSD Finland"}
    tlabels = {"QDA_PROJECT": "QDA Projects", "QD_PROJECT": "QD Projects"}
    total   = sum(r[3] for r in rows)
    n       = len(rows)

    fig = new_page()
    chrome(fig, section_label)

    fig.text(ML, CTOP,
             f"{rlabels[repo]} — {tlabels[ptype]}: Ranked Class Table and Findings",
             fontsize=13, fontweight="bold", color=C_NAVY, va="top")
    fig.text(ML, CTOP - 0.033,
             f"Distribution {dlabel}  ·  {total} projects  ·  "
             f"top {min(20, n)} of {n} classes shown",
             fontsize=9, color=C_GREY, va="top", style="italic")

    tbl_top = CTOP - 0.068
    tbl_bot = draw_table(fig, rows, total, tbl_top)

    y = tbl_bot - 0.025
    hrule(fig, y, "Findings and Discussion")
    y -= 0.032
    for p in disc:
        y = para(fig, ML, y, p)
        y -= 0.014
        if y < CBOT + 0.015:
            break

    pdf.savefig(fig, bbox_inches="tight")
    plt.close(fig)


def page_comparative(pdf, conn):
    fig = new_page()
    chrome(fig)

    dq  = conn.execute("""SELECT COUNT(*) FROM PROJECTS p
        JOIN REPOSITORIES r ON r.id=p.repository_id
        WHERE r.name='dryad' AND p.type='QD_PROJECT'""").fetchone()[0]
    fq  = conn.execute("""SELECT COUNT(*) FROM PROJECTS p
        JOIN REPOSITORIES r ON r.id=p.repository_id
        WHERE r.name='fsd' AND p.type='QD_PROJECT'""").fetchone()[0]
    qda = conn.execute(
        "SELECT COUNT(*) FROM PROJECTS WHERE type='QDA_PROJECT'").fetchone()[0]

    y = CTOP
    hrule(fig, y, "4.  Comparative Analysis and Conclusion")
    y -= 0.040

    hrule(fig, y, "4.1  Cross-Repository Observations", gold=False)
    y -= 0.034
    y = para(fig, ML, y, (
        f"The two repositories exhibit markedly different profiles in terms of both scale and "
        f"disciplinary coverage. Dryad contributed {dq} QD projects across nine ISIC divisions, "
        f"while FSD Finland contributed only {fq} publicly accessible QD projects across three "
        f"divisions. This disparity does not reflect FSD's actual holdings — FSD catalogues 403 "
        f"qualitative studies in its English-language archive — but is a direct consequence of "
        f"the archive's requirement for institutional authentication via the Aila Data Service. "
        f"Only studies with publicly accessible PDF attachments qualified as QD_PROJECT."
    ))
    y -= 0.012
    y = para(fig, ML, y, (
        "Both repositories are dominated by N-72 (Scientific Research and Development), the "
        "expected outcome for academic research collections. The second-ranked division differs "
        "sharply: Dryad ranks R-86 (Human Health Activities) second at 27.1%, reflecting its "
        "strong life-sciences and clinical research base. FSD's small QD sample shows no R-86 "
        "representation; instead S-91 (Libraries, Archives and Cultural Activities) and Q-85 "
        "(Education) appear, consistent with Finland's social-science and cultural heritage "
        "research tradition."
    ))
    y -= 0.018

    hrule(fig, y, "4.2  QDA File Availability", gold=False)
    y -= 0.034
    y = para(fig, ML, y, (
        f"Across both repositories, only {qda} QDA analysis file was identified — a single "
        "NVivo (.nvp) project deposited on Dryad, classified as R-86 (Human Health Activities). "
        "This confirms the core challenge motivating QDArchive: researchers who conduct "
        "qualitative data analysis with NVivo, MAXQDA, or QDAcity rarely deposit the resulting "
        "analysis files in open repositories. Interview transcripts and coded datasets are "
        "deposited, but the structured analysis files that capture the analytical process itself "
        "remain largely inaccessible. QDArchive therefore cannot be seeded purely by harvesting "
        "existing repositories — it must rely on targeted outreach and deposit incentives to "
        "build a meaningful QDA file collection."
    ))
    y -= 0.018

    hrule(fig, y, "4.3  Classification Confidence and Limitations", gold=False)
    y -= 0.034
    y = para(fig, ML, y, (
        "The AI-assisted ISIC classification produces reliable results for projects with "
        "descriptive titles, rich abstracts, and multiple keywords. Quality is lower for FSD "
        "projects, where only the DDI-C 2.5 XML title and abstract were available — no file "
        "content could be read. The large N-72 share also partly reflects the classifier's "
        "default fallback behaviour: projects with generic or absent descriptions are assigned "
        "N-72 (Scientific Research and Development) rather than a more specific division. A "
        "manual review of a sample of N-72 assignments would be required to quantify this effect."
    ))
    y -= 0.018

    hrule(fig, y, "4.4  Conclusion", gold=False)
    y -= 0.034
    para(fig, ML, y, (
        "This classification provides a structured, ISIC-aligned view of 1,256 qualitative "
        "research projects acquired from Dryad and FSD Finland. The data confirms that "
        "qualitative research in the social, health, and agricultural sciences is well "
        "represented in open repositories — but that the QDA analysis files that are "
        "QDArchive's primary target are almost entirely absent from open deposit. The "
        "classification infrastructure developed here — the ISIC classifier, file-level "
        "annotation pipeline, and structured SQLite schema — provides a reusable foundation "
        "for classifying future acquisitions as QDArchive grows."
    ))

    pdf.savefig(fig, bbox_inches="tight")
    plt.close(fig)


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


# ── Entry point ────────────────────────────────────────────────────────────────

REPO_SECTION = {
    ("dryad", "QDA_PROJECT"): "2.  Repository 1: Dryad",
    ("dryad", "QD_PROJECT"):  "2.  Repository 1: Dryad",
    ("fsd",   "QDA_PROJECT"): "3.  Repository 2: FSD Finland",
    ("fsd",   "QD_PROJECT"):  "3.  Repository 2: FSD Finland",
}
DIST_LABEL = {
    ("dryad", "QDA_PROJECT"): "1",
    ("dryad", "QD_PROJECT"):  "2",
    ("fsd",   "QDA_PROJECT"): "3",
    ("fsd",   "QD_PROJECT"):  "4",
}


def run():
    conn = sqlite3.connect(str(DB_PATH))
    OUT_PATH.parent.mkdir(exist_ok=True)

    with PdfPages(OUT_PATH) as pdf:
        page_title(pdf, conn)
        page_introduction(pdf)

        for repo, ptype in [("dryad", "QDA_PROJECT"), ("dryad", "QD_PROJECT"),
                             ("fsd",   "QDA_PROJECT"), ("fsd",   "QD_PROJECT")]:
            rows  = get_distrib(conn, repo, ptype)
            dl    = DIST_LABEL[(repo, ptype)]
            sl    = REPO_SECTION[(repo, ptype)]
            disc  = DISCUSSION[(repo, ptype)]
            total = sum(r[3] for r in rows)
            print(f"  Distribution {dl}: {repo}/{ptype} — {len(rows)} classes, {total} projects")

            if len(rows) <= 5:
                # small dataset: everything on one page
                page_combined_small(pdf, repo, ptype, rows, sl, dl, disc)
            else:
                # larger dataset: separate histogram + table pages
                page_histogram_full(pdf, repo, ptype, rows, sl, dl)
                page_table_full(pdf, repo, ptype, rows, sl, dl, disc)

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
