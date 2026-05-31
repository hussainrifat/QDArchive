"""
Part 2 Step 4d — Classification report PDF
For each of 4 distributions (repo × project_type):
  - Histogram of primary ISIC classes (vector, count on bar)
  - Rank-ordered top-20 table
  - Comments
"""

import sqlite3
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.backends.backend_pdf import PdfPages
import textwrap

DB_PATH = Path(__file__).parent.parent / "23025313-sq26-classification.db"
OUT_PATH = Path(__file__).parent.parent / "export" / "23025313-classification-report.pdf"

REPO_LABELS = {"dryad": "Dryad", "fsd": "FSD Finland"}
TYPE_LABELS = {
    "QDA_PROJECT": "QDA Projects",
    "QD_PROJECT":  "QD Projects",
}
DISTRIBUTIONS = [
    ("dryad", "QDA_PROJECT"),
    ("dryad", "QD_PROJECT"),
    ("fsd",   "QDA_PROJECT"),
    ("fsd",   "QD_PROJECT"),
]

COMMENTS = {
    ("dryad", "QDA_PROJECT"): (
        "Dryad hosts only one QDA project in this dataset — a single NVivo (.nvp) project file. "
        "It is classified under Scientific Research and Development (N/72), reflecting the academic "
        "nature of qualitative data analysis projects typically deposited on Dryad."
    ),
    ("dryad", "QD_PROJECT"): (
        "Dryad QD projects are dominated by Scientific Research & Development (N/72), reflecting "
        "the repository's academic focus. Human Health Activities (R/86) ranks second, consistent "
        "with the large number of medical and nursing interview studies found via the qualitative "
        "research search queries. Agriculture (A/01) appears due to Dryad's strong life-sciences "
        "user base."
    ),
    ("fsd", "QDA_PROJECT"): (
        "No QDA projects (files with QDA-specific extensions) were found in the FSD Finland "
        "catalogue. FSD distributes data in DDI-C XML format, which is a metadata standard rather "
        "than a QDA analysis file, so all FSD projects are classified as QD_PROJECT or OTHER."
    ),
    ("fsd", "QD_PROJECT"): (
        "FSD Finland's QD projects are concentrated in Social Work Activities Without Accommodation "
        "(R/88) and Human Health Activities (R/86), reflecting Finland's strong tradition of social "
        "science and welfare research. Education (Q/85) also features prominently. The narrow "
        "distribution compared to Dryad indicates FSD's focused qualitative social science mandate."
    ),
}


def get_distribution(conn, repo_name, project_type):
    rows = conn.execute("""
        SELECT
            p.isic_section_code || p.isic_division_code AS code,
            p.isic_section_code,
            p.isic_division_code,
            p.isic_division_name,
            COUNT(*) AS cnt
        FROM PROJECTS p
        JOIN REPOSITORIES r ON r.id = p.repository_id
        WHERE r.name = ? AND p.type = ?
        GROUP BY code
        ORDER BY cnt DESC
    """, (repo_name, project_type)).fetchall()
    return rows


def make_histogram_page(pdf, repo, ptype, rows):
    if not rows:
        fig, ax = plt.subplots(figsize=(11.7, 8.3))
        ax.text(0.5, 0.5, "No data for this distribution",
                ha="center", va="center", fontsize=16, transform=ax.transAxes)
        ax.axis("off")
        ax.set_title(f"{REPO_LABELS[repo]} — {TYPE_LABELS[ptype]}: Histogram",
                     fontsize=14, fontweight="bold", pad=16)
        pdf.savefig(fig, bbox_inches="tight")
        plt.close(fig)
        return

    labels = [f"{r[1]}{r[2]}\n{textwrap.fill(r[3], 18)}" for r in rows]
    counts = [r[4] for r in rows]

    fig, ax = plt.subplots(figsize=(max(11.7, len(rows) * 1.1), 8.3))

    bars = ax.bar(range(len(counts)), counts, color="#2F5496", edgecolor="white", linewidth=0.5)

    for bar, cnt in zip(bars, counts):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + max(counts) * 0.01,
                str(cnt), ha="center", va="bottom", fontsize=9, fontweight="bold")

    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels, fontsize=8, rotation=0, ha="center")
    ax.set_ylabel("Number of Projects", fontsize=11)
    ax.set_xlabel("ISIC Division", fontsize=11)
    ax.set_title(
        f"{REPO_LABELS[repo]} — {TYPE_LABELS[ptype]}\nISIC Division Distribution",
        fontsize=13, fontweight="bold", pad=14
    )
    ax.set_ylim(0, max(counts) * 1.15)
    ax.grid(axis="y", linestyle="--", alpha=0.4)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    fig.tight_layout(pad=2.0)
    pdf.savefig(fig, bbox_inches="tight")
    plt.close(fig)


def make_table_page(pdf, repo, ptype, rows, comment):
    top20 = rows[:20]

    fig = plt.figure(figsize=(11.7, 8.3))
    ax = fig.add_subplot(111)
    ax.axis("off")

    ax.set_title(
        f"{REPO_LABELS[repo]} — {TYPE_LABELS[ptype]}\nTop Classes (Rank-Ordered)",
        fontsize=13, fontweight="bold", pad=18, loc="left", x=0.02
    )

    if not top20:
        ax.text(0.5, 0.5, "No data for this distribution.",
                ha="center", va="center", fontsize=14, transform=ax.transAxes)
        # still add comment
        wrapped = textwrap.fill(comment, 120)
        fig.text(0.04, 0.06, f"Comments:\n{wrapped}",
                 fontsize=9, va="bottom",
                 bbox=dict(boxstyle="round,pad=0.5", fc="#f0f0f0", ec="gray", lw=0.8))
        pdf.savefig(fig, bbox_inches="tight")
        plt.close(fig)
        return

    table_data = [["Rank", "Code", "ISIC Division Name", "Count"]]
    total = sum(r[4] for r in rows)
    for rank, r in enumerate(top20, 1):
        code = f"{r[1]}{r[2]}"
        table_data.append([str(rank), code, r[3], str(r[4])])

    col_widths = [0.06, 0.08, 0.62, 0.08]
    table = ax.table(
        cellText=table_data[1:],
        colLabels=table_data[0],
        colWidths=col_widths,
        loc="upper center",
        bbox=[0.02, 0.22, 0.96, 0.72]
    )
    table.auto_set_font_size(False)
    table.set_fontsize(9)

    for (row_idx, col_idx), cell in table.get_celld().items():
        if row_idx == 0:
            cell.set_facecolor("#2F5496")
            cell.set_text_props(color="white", fontweight="bold")
        elif row_idx % 2 == 0:
            cell.set_facecolor("#EEF2FF")
        cell.set_edgecolor("white")
        if col_idx in (0, 1, 3):
            cell.get_text().set_ha("center")

    # summary line
    fig.text(0.02, 0.20,
             f"Total projects in this distribution: {total}  |  Distinct classes: {len(rows)}",
             fontsize=9, color="#444444")

    # comments box
    wrapped = textwrap.fill(comment, 125)
    fig.text(0.02, 0.02, f"Comments:\n{wrapped}",
             fontsize=8.5, va="bottom",
             bbox=dict(boxstyle="round,pad=0.5", fc="#fffbe6", ec="#ccaa00", lw=0.8))

    pdf.savefig(fig, bbox_inches="tight")
    plt.close(fig)


def make_cover_page(pdf, conn):
    fig = plt.figure(figsize=(11.7, 8.3))
    ax = fig.add_subplot(111)
    ax.axis("off")

    ax.text(0.5, 0.78, "Seeding QDArchive", ha="center", fontsize=28,
            fontweight="bold", transform=ax.transAxes, color="#1a3a6b")
    ax.text(0.5, 0.68, "Part 2: Data Classification Report",
            ha="center", fontsize=20, transform=ax.transAxes, color="#2F5496")
    ax.text(0.5, 0.60, "ISIC Rev. 5 Classification of Qualitative Research Projects",
            ha="center", fontsize=13, transform=ax.transAxes, color="#555555")

    # summary stats
    stats = conn.execute("""
        SELECT r.name, p.type, COUNT(*)
        FROM PROJECTS p JOIN REPOSITORIES r ON r.id=p.repository_id
        GROUP BY r.name, p.type ORDER BY r.name, p.type
    """).fetchall()

    lines = ["Repository", "Project Type", "Count"]
    summary_text = f"{'Repository':<12} {'Project Type':<22} {'Count':>6}\n"
    summary_text += "-" * 44 + "\n"
    for repo, ptype, cnt in stats:
        summary_text += f"{repo:<12} {ptype:<22} {cnt:>6}\n"

    total = conn.execute("SELECT COUNT(*) FROM PROJECTS").fetchone()[0]
    summary_text += "-" * 44 + "\n"
    summary_text += f"{'TOTAL':<12} {'':<22} {total:>6}"

    ax.text(0.5, 0.35, summary_text, ha="center", va="center",
            fontsize=10, transform=ax.transAxes,
            fontfamily="monospace",
            bbox=dict(boxstyle="round,pad=0.8", fc="#f4f7fb", ec="#2F5496", lw=1.2))

    ax.text(0.5, 0.12, "Student: Jakir Hussain Rifat (23025313)\nFAU Erlangen — Seeding QDArchive SQ26",
            ha="center", fontsize=10, transform=ax.transAxes, color="#666666")

    ax.axhline(y=0.55, xmin=0.1, xmax=0.9, color="#2F5496", linewidth=1.5)

    pdf.savefig(fig, bbox_inches="tight")
    plt.close(fig)


def run():
    conn = sqlite3.connect(str(DB_PATH))

    OUT_PATH.parent.mkdir(exist_ok=True)

    with PdfPages(OUT_PATH) as pdf:
        # cover
        make_cover_page(pdf, conn)

        for repo, ptype in DISTRIBUTIONS:
            rows = get_distribution(conn, repo, ptype)
            comment = COMMENTS.get((repo, ptype), "")
            print(f"  {repo}/{ptype}: {len(rows)} classes, {sum(r[4] for r in rows)} projects")

            make_histogram_page(pdf, repo, ptype, rows)
            make_table_page(pdf, repo, ptype, rows, comment)

        d = pdf.infodict()
        d["Title"] = "QDArchive Part 2 Classification Report"
        d["Author"] = "Jakir Hussain Rifat (23025313)"
        d["Subject"] = "ISIC Rev. 5 Classification of Qualitative Research Projects"

    conn.close()
    print(f"\nSaved: {OUT_PATH}")


if __name__ == "__main__":
    run()
