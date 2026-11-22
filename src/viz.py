from __future__ import annotations
import csv
import logging
from pathlib import Path
from typing import Any, Mapping

import matplotlib as mpl

mpl.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

LOGGER = logging.getLogger(__name__)

VIZ_PALETTE = ("#264653", "#2A9D8F", "#E9C46A", "#F4A261", "#E76F51", "#8AB17D", "#6D597A", "#B56576")
SENT_COLORS = {"positive": "#2A9D8F", "mixed": "#E9C46A", "negative": "#E76F51"}


def setup_viz_theme() -> None:
    """Set consistent defaults for Matplotlib and Seaborn charts."""
    mpl.rcParams.update({
        "figure.figsize": (10, 6), "figure.dpi": 300, "savefig.dpi": 300, "font.family": "DejaVu Sans",
        "axes.grid": True, "grid.alpha": 0.25, "axes.spines.top": False, "axes.spines.right": False,
    })
    sns.set_theme(style="whitegrid", palette=list(VIZ_PALETTE),
                  rc={"figure.figsize": (10, 6), "figure.dpi": 300, "savefig.dpi": 300, "font.family": "DejaVu Sans"})


def init_report_template(reports_dir: str | Path) -> None:
    """Create a reports directory and an empty QA report with column headers (if none exists)."""
    report_path = Path(reports_dir) / "qa_report.csv"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    (report_path.parent / ".gitkeep").touch()
    if not report_path.exists() or report_path.stat().st_size == 0:
        with report_path.open("w", newline="", encoding="utf-8-sig") as report_file:
            writer = csv.writer(report_file)
            writer.writerow(("rule_id", "rule_name", "table", "condition", "reason", "action", "n_rows_before",
                             "n_flagged", "n_rows_after", "kpi_name", "kpi_before", "kpi_after", "note"))


def _save(fig: plt.Figure, out_dir: Path, name: str) -> Path:
    path = out_dir / f"{name}.png"
    fig.tight_layout()
    fig.savefig(path, dpi=300)
    plt.close(fig)
    LOGGER.info("Lưu hình %s", path)
    return path


def fig_map(listings: pd.DataFrame, areas: pd.DataFrame, config: Mapping[str, Any], out: Path) -> None:
    last = config["snapshots"][-1]
    L = listings.loc[(listings["snapshot"] == last) & ~listings["flag_missing_coords"]]
    fig, ax = plt.subplots(figsize=(10, 8))
    for i, (_, b) in enumerate(areas.iterrows()):
        ax.add_patch(plt.Rectangle((b.lon_min, b.lat_min), b.lon_max - b.lon_min, b.lat_max - b.lat_min,
                                   fill=False, lw=1, ls="--", color="grey"))
        ax.text(b.lon_min + 0.005, b.lat_max - 0.012, b.analysis_area, fontsize=9, color="grey")
    for i, (area, g) in enumerate(L.groupby("analysis_area")):
        ax.scatter(g["longitude"], g["latitude"], s=10, alpha=0.7, color=VIZ_PALETTE[i % len(VIZ_PALETTE)], label=f"{area} (n={len(g)})")
    mm = L.loc[L["flag_area_mismatch"]]
    if len(mm):
        ax.scatter(mm["longitude"], mm["latitude"], s=28, facecolors="none", edgecolors="red", label=f"lệch vùng (QA L09, n={len(mm)})")
    pad_x = (areas.lon_max.max() - areas.lon_min.min()) * 0.02
    pad_y = (areas.lat_max.max() - areas.lat_min.min()) * 0.02
    ax.set_xlim(areas.lon_min.min() - pad_x, areas.lon_max.max() + pad_x)
    ax.set_ylim(areas.lat_min.min() - pad_y, areas.lat_max.max() + pad_y)
    ax.set_xlabel("Kinh độ"), ax.set_ylabel("Vĩ độ")
    ax.set_title(f"{config['city'].title()} — vị trí {len(L)} listing theo vùng phân tích (mốc {last})")
    ax.legend(fontsize=8, loc="upper left", bbox_to_anchor=(1.01, 1.0), borderaxespad=0)
    _save(fig, out, "fig_map_listings_by_area")


def fig_area_structure(kpis: Mapping[str, pd.DataFrame], config: Mapping[str, Any], out: Path) -> None:
    last = config["snapshots"][-1]
    area = config["kpi"]["area_col"]
    parts = [("kpi_entire_home_share", "entire_home_share_pct", "Nguyên căn"),
             ("kpi_multi_host_share", "multi_host_share_pct", "Host ≥2 nhà"),
             ("kpi_short_stay_share", "short_stay_share_pct", "Ngắn ngày (≤7 đêm)"),
             ("kpi_active_listings", "active_share_pct", "Đang mở lịch")]
    frames = []
    for k, col, label in parts:
        if k in kpis:
            f = kpis[k].loc[kpis[k]["snapshot"] == last, [area, col]].rename(columns={col: "value"})
            f["chỉ số"] = label
            frames.append(f)
    if not frames:
        return
    df = pd.concat(frames)
    fig, ax = plt.subplots()
    sns.barplot(data=df, x=area, y="value", hue="chỉ số", ax=ax, palette=list(VIZ_PALETTE[:4]))
    ax.set_ylabel("% listing"), ax.set_xlabel("Vùng phân tích")
    ax.set_title(f"Cơ cấu cho thuê ngắn hạn theo vùng — mốc {last}")
    ax.legend(title="", fontsize=8)
    _save(fig, out, "fig_area_structure")


def fig_area_price(kpis: Mapping[str, pd.DataFrame], config: Mapping[str, Any], out: Path) -> None:
    if "kpi_median_price" not in kpis:
        return
    area = config["kpi"]["area_col"]
    p = kpis["kpi_median_price"]
    allp = p.loc[p["room_type"] == "ALL"].sort_values(area)
    fig, ax = plt.subplots()
    err = np.vstack([allp["price_median"] - allp["price_p25"], allp["price_p75"] - allp["price_median"]])
    ax.bar(allp[area], allp["price_median"], yerr=err, capsize=4, color=VIZ_PALETTE[1])
    for x, y, n in zip(allp[area], allp["price_median"], allp["n_listing"]):
        ax.text(x, y, f"n={n}", ha="center", va="bottom", fontsize=8)
    ax.set_ylabel(f"Giá đêm ({config['currency']}) — median, thanh = p25–p75")
    ax.set_xlabel("Vùng phân tích")
    ax.set_title(f"Mặt bằng giá theo vùng — chỉ mốc cuối {config['snapshots'][-1]}, sau QA")
    _save(fig, out, "fig_area_median_price")


def fig_time_occupancy(kpis: Mapping[str, pd.DataFrame], config: Mapping[str, Any], out: Path) -> None:
    if "kpi_occupancy_90d" not in kpis:
        return
    area = config["kpi"]["area_col"]
    df = kpis["kpi_occupancy_90d"]
    fig, ax = plt.subplots()
    for i, (a, g) in enumerate(df.groupby(area)):
        ax.plot(g["snapshot"], g["occupancy_pct"], marker="o", label=a, color=VIZ_PALETTE[i % len(VIZ_PALETTE)])
    ax.set_ylabel(f"% ngày đã đặt/đóng trong {config['kpi']['occupancy_window_days']} ngày tới")
    ax.set_xlabel("Mốc chụp")
    ax.set_title("Công suất 90 ngày tới theo vùng và theo mốc")
    ax.legend(title="Vùng", fontsize=8, ncol=4)
    _save(fig, out, "fig_time_occupancy_by_area")


def fig_time_city(kpis: Mapping[str, pd.DataFrame], config: Mapping[str, Any], out: Path) -> None:
    series = [("kpi_active_listings", "n_active", "n_listing", "Đang mở lịch (%)"),
              ("kpi_multi_host_share", "n_multi_host_listing", "n_listing", "Host ≥2 nhà (%)"),
              ("kpi_short_stay_share", "n_short_stay", "n_listing", "Ngắn ngày ≤7 đêm (%)"),
              ("kpi_entire_home_share", "n_entire", "n_listing", "Nguyên căn (%)")]
    fig, ax1 = plt.subplots()
    for i, (k, num, den, label) in enumerate(series):
        if k not in kpis:
            continue
        g = kpis[k].groupby("snapshot")[[num, den]].sum()
        ax1.plot(g.index, g[num] / g[den] * 100, marker="o", label=label, color=VIZ_PALETTE[i])
    ax1.set_ylabel("% listing (toàn mẫu 1.000 listing)")
    ax1.set_xlabel("Mốc chụp")
    if "kpi_review_velocity" in kpis:
        ax2 = ax1.twinx()
        g = kpis["kpi_review_velocity"].groupby("snapshot")["reviews_ltm_mean"].mean()
        ax2.plot(g.index, g.values, marker="s", ls="--", color=VIZ_PALETTE[4], label="Review 12 tháng / listing")
        ax2.set_ylabel("review/listing/năm")
        ax2.grid(False)
        h1, l1 = ax1.get_legend_handles_labels()
        h2, l2 = ax2.get_legend_handles_labels()
        ax1.legend(h1 + h2, l1 + l2, fontsize=8, loc="best")
    else:
        ax1.legend(fontsize=8)
    ax1.set_title(f"{config['city'].title()} — xu hướng toàn thành phố qua 4 mốc")
    _save(fig, out, "fig_time_city_trends")


def fig_seasonality(calendar: pd.DataFrame, config: Mapping[str, Any], out: Path) -> None:
    last = config["snapshots"][-1]
    C = calendar.loc[(calendar["snapshot"] == last) & ~calendar["flag_bad_available"] & ~calendar["flag_date_outside_window"]]
    if C.empty:
        return
    week = C["date"].dt.to_period("W").dt.start_time
    g = C.assign(week=week, booked=C["available"] == "f").groupby("week").agg(
        booked_pct=("booked", lambda s: s.mean() * 100), price_median=("price_num", "median"))
    fig, ax1 = plt.subplots()
    ax1.plot(g.index, g["booked_pct"], color=VIZ_PALETTE[0], label="% ngày đã đặt/đóng")
    ax1.set_ylabel("% ngày đã đặt/đóng (theo tuần)")
    ax1.set_xlabel("Tuần (365 ngày kể từ mốc chụp)")
    ax2 = ax1.twinx()
    ax2.plot(g.index, g["price_median"], color=VIZ_PALETTE[4], ls="--", label=f"Giá đêm median ({config['currency']})")
    ax2.set_ylabel(f"Giá đêm median ({config['currency']})")
    ax2.grid(False)
    h1, l1 = ax1.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax1.legend(h1 + h2, l1 + l2, fontsize=8, loc="upper right")
    ax1.set_title(f"Mùa vụ 12 tháng tới từ calendar mốc {last}")
    fig.autofmt_xdate()
    _save(fig, out, "fig_calendar_seasonality")


def fig_llm_sentiment(kpis: Mapping[str, pd.DataFrame], config: Mapping[str, Any], out: Path) -> None:
    if "kpi_llm_sentiment" not in kpis:
        return
    area = config["kpi"]["area_col"]
    df = kpis["kpi_llm_sentiment"].sort_values(area)
    fig, ax = plt.subplots()
    bottom = np.zeros(len(df))
    for s in ("positive", "mixed", "negative"):
        vals = df[f"n_{s}"] / df["n_review_llm"] * 100
        ax.bar(df[area], vals, bottom=bottom, color=SENT_COLORS[s], label=s)
        bottom += vals.values
    for x, n in zip(df[area], df["n_review_llm"]):
        ax.text(x, 101, f"n={n}", ha="center", fontsize=8)
    ax.set_ylim(0, 118), ax.set_ylabel("% review"), ax.set_xlabel("Vùng phân tích")
    ax.set_title(f"Cảm xúc review theo vùng (LLM, {int(df['n_review_llm'].sum())} review mẫu)")
    ax.legend(ncol=3, fontsize=8, loc="upper center")
    _save(fig, out, "fig_llm_sentiment_by_area")


def fig_llm_aspects(kpis: Mapping[str, pd.DataFrame], config: Mapping[str, Any], out: Path) -> None:
    if "kpi_llm_aspects" not in kpis:
        return
    df = kpis["kpi_llm_aspects"].groupby(["aspect", "polarity"])["mentions"].sum().unstack(fill_value=0)
    for col in ("positive", "negative"):
        if col not in df:
            df[col] = 0
    df = df.sort_values("positive")
    fig, ax = plt.subplots()
    y = np.arange(len(df))
    ax.barh(y, df["positive"], color=SENT_COLORS["positive"], label="được khen")
    ax.barh(y, -df["negative"], color=SENT_COLORS["negative"], label="bị chê")
    ax.set_yticks(y, df.index)
    ax.axvline(0, color="black", lw=0.8)
    ax.set_xlabel("Số lượt nhắc (trái: chê, phải: khen)")
    ax.set_title("Khía cạnh được khen / bị chê trong review (LLM)")
    ax.legend(fontsize=8)
    _save(fig, out, "fig_llm_aspects")


def fig_llm_eval(metrics: pd.DataFrame | None, out: Path) -> None:
    if metrics is None or metrics.empty:
        return
    m = metrics.loc[metrics["method"].isin(["llm", "baseline"]) & metrics["metric"].isin(
        ["sentiment_accuracy", "sentiment_macro_f1", "language_accuracy", "aspect_f1_micro"])]
    if m.empty:
        return
    fig, ax = plt.subplots()
    sns.barplot(data=m, x="metric", y="value", hue="method", ax=ax, palette=[VIZ_PALETTE[1], VIZ_PALETTE[3]])
    ax.set_ylim(0, 1), ax.set_ylabel("giá trị (0–1)"), ax.set_xlabel("")
    ax.set_title(f"LLM vs baseline trên {int(m['n'].iloc[0])} review nhãn tay")
    for c in ax.containers:
        ax.bar_label(c, fmt="%.2f", fontsize=8)
    _save(fig, out, "fig_llm_vs_baseline")


def make_figures(clean: Mapping[str, pd.DataFrame], kpis: Mapping[str, pd.DataFrame], metrics: pd.DataFrame | None,
                 config: Mapping[str, Any]) -> list[Path]:
    setup_viz_theme()
    root = Path(config.get("_project_root", Path.cwd()))
    out = root / config["paths"]["figures"]
    out.mkdir(parents=True, exist_ok=True)
    areas = pd.read_csv(root / config["assignments"]["areas"])
    fig_map(clean["listings"], areas, config, out)
    fig_area_structure(kpis, config, out)
    fig_area_price(kpis, config, out)
    fig_time_occupancy(kpis, config, out)
    fig_time_city(kpis, config, out)
    fig_seasonality(clean["calendar"], config, out)
    fig_llm_sentiment(kpis, config, out)
    fig_llm_aspects(kpis, config, out)
    fig_llm_eval(metrics, out)
    return sorted(out.glob("fig_*.png"))
