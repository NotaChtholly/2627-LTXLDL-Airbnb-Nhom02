import csv
from pathlib import Path
import matplotlib as mpl
import seaborn as sns
VIZ_PALETTE = (
    "#264653",
    "#2A9D8F",
    "#E9C46A",
    "#F4A261",
    "#E76F51",
)
def setup_viz_theme() -> None:
    mpl.rcParams.update(
        {
            "figure.figsize": (10, 6),
            "figure.dpi": 300,
            "savefig.dpi": 300,
            "font.family": "DejaVu Sans",
            "axes.grid": True,
            "grid.alpha": 0.25,
            "axes.spines.top": False,
            "axes.spines.right": False,
        }
    )
    sns.set_theme(
        style="whitegrid",
        palette=VIZ_PALETTE,
        rc={
            "figure.figsize": (10, 6),
            "figure.dpi": 300,
            "savefig.dpi": 300,
            "font.family": "DejaVu Sans",
        },
    )
def init_report_template(reports_dir: str = "reports", figures_dir: str = "figures") -> None:
    fig_keep = Path(figures_dir) / ".gitkeep"
    fig_keep.parent.mkdir(parents=True, exist_ok=True)
    fig_keep.touch(exist_ok=True)
    rep_keep = Path(reports_dir) / ".gitkeep"
    rep_keep.parent.mkdir(parents=True, exist_ok=True)
    rep_keep.touch(exist_ok=True)
    report_path = Path(reports_dir) / "qa_report.csv"
    if not report_path.exists() or report_path.stat().st_size == 0:
        with report_path.open("w", newline="", encoding="utf-8") as report_file:
            writer = csv.writer(report_file)
            writer.writerow(
                (
                    "rule_name",
                    "condition",
                    "reason",
                    "action",
                    "rows_affected",
                    "kpi_impact_price_diff",
                )
            )