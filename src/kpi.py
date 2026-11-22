from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any, Mapping

import numpy as np
import pandas as pd

LOGGER = logging.getLogger(__name__)

REQUIRED_COLS = ["snapshot", "id", "price", "room_type", "analysis_area", "host_id",
                 "minimum_nights", "number_of_reviews", "latitude", "longitude"]


def verify_filtered_schema(df: pd.DataFrame) -> bool:
    """Kiểm tra tồn tại cột bắt buộc và kiểu dữ liệu chuẩn của bảng listings (trước/sau QA).

    - id phải là chuỗi (ID Airbnb có thể vượt int64), price là chuỗi tiền tệ gốc hoặc float.
    - Không được xoá/đổi tên cột gốc của Inside Airbnb.
    """
    expected_schema = {
        "id": ["object", "string", "str"],
        "price": ["object", "string", "str", "float64"],
    }
    missing_cols = [col for col in REQUIRED_COLS if col not in df.columns]
    invalid_types = []
    for col, allowed in expected_schema.items():
        if col in df.columns and str(df[col].dtype) not in allowed:
            invalid_types.append((col, str(df[col].dtype)))
    if missing_cols:
        LOGGER.error("[LỖI] Thiếu các cột bắt buộc: %s", missing_cols)
        return False
    if invalid_types:
        LOGGER.error("[LỖI] Sai kiểu dữ liệu (Cột, Kiểu hiện tại): %s", invalid_types)
        return False
    LOGGER.info("[THÀNH CÔNG] Schema listings hợp lệ (%d cột, %d dòng).", df.shape[1], len(df))
    return True


def init_kpi_structures(processed_dir: str | Path = "data/processed", reports_dir: str | Path = "reports") -> None:
    """Tạo sẵn cấu trúc data/processed/ (.gitkeep) và từ điển dữ liệu mẫu trong reports/."""
    processed_dir, reports_dir = Path(processed_dir), Path(reports_dir)
    processed_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)
    (processed_dir / ".gitkeep").touch()
    sample = {
        "dataset": "listings.csv.gz (Inside Airbnb)",
        "columns": {
            "id": "Mã định danh duy nhất cho mỗi listing (chuỗi)",
            "price": "Giá thuê một đêm, chuỗi '$1,234.00' (tiền tệ theo configs)",
            "room_type": "Loại không gian thuê: Entire home/apt, Private room, Shared room, Hotel room",
            "analysis_area": "Vùng phân tích A01..A08 do giảng viên giao (sheet «Vùng»)",
        },
    }
    with open(reports_dir / "data_dictionary_sample.json", "w", encoding="utf-8") as f:
        json.dump(sample, f, ensure_ascii=False, indent=4)
    LOGGER.info("[THÀNH CÔNG] Đã tạo %s và %s.", processed_dir / ".gitkeep", reports_dir / "data_dictionary_sample.json")


KPI_CATALOG = [
    {"kpi": "kpi_active_listings", "goal": "Đo quy mô cho thuê ngắn hạn còn 'sống' ở từng vùng, theo dõi theo mốc",
     "formula": "active = has_availability=='t' và availability_365>0; share = n_active / n_listing (theo snapshot, analysis_area)",
     "unit": "listing; %", "dimension": "vùng × thời gian"},
    {"kpi": "kpi_entire_home_share", "goal": "Ước lượng nhà nguyên căn bị rút khỏi thị trường thuê dài hạn",
     "formula": "n(room_type=='Entire home/apt') / n_listing (theo snapshot, analysis_area)", "unit": "%", "dimension": "vùng × thời gian"},
    {"kpi": "kpi_multi_host_share", "goal": "Phát hiện vận hành thương mại (host nhiều nhà) thay vì chia sẻ nhà",
     "formula": "n(calculated_host_listings_count >= 2) / n_listing có host_id (theo snapshot, analysis_area)", "unit": "%", "dimension": "vùng × thời gian"},
    {"kpi": "kpi_short_stay_share", "goal": "Tỉ lệ listing thuộc diện lưu trú ngắn hạn (đối tượng thuế/quy định của Victoria)",
     "formula": "n(minimum_nights <= 7, loại flag_min_nights_outlier) / n_listing (theo snapshot, analysis_area)", "unit": "%", "dimension": "vùng × thời gian"},
    {"kpi": "kpi_occupancy_90d", "goal": "Sức khoẻ cầu du lịch: tỉ lệ ngày đã đặt/đóng trong 90 ngày tới",
     "formula": "n(available=='f', date trong [mốc, mốc+90)) / n_ngày (calendar; theo snapshot, analysis_area)", "unit": "%", "dimension": "vùng × thời gian"},
    {"kpi": "kpi_review_velocity", "goal": "Nhịp khách thực tế (review 12 tháng gần nhất) để so với công suất",
     "formula": "mean(number_of_reviews_ltm) (theo snapshot, analysis_area)", "unit": "review/listing/năm", "dimension": "vùng × thời gian"},
    {"kpi": "kpi_median_price", "goal": "Mặt bằng giá đêm theo vùng và loại phòng cho đối chiếu với giá thuê dài hạn",
     "formula": "median(price_num) với price_usable (mốc cuối, loại thiếu giá & ngoại lai) theo analysis_area × room_type; kèm p25/p75 và giá/người",
     "unit": "AUD/đêm (tiền tệ theo configs.currency)", "dimension": "vùng (chỉ mốc cuối)"},
    {"kpi": "kpi_llm_sentiment", "goal": "Trải nghiệm khách theo vùng từ văn bản review (LLM) và khía cạnh bị chê nhiều nhất",
     "formula": "share_positive = n(sentiment=='positive') / n_review_LLM theo analysis_area; kpi_llm_aspects = đếm khía cạnh khen/chê theo vùng",
     "unit": "%; lượt nhắc", "dimension": "vùng (dùng LLM)"},
]


def _share(num: pd.Series, den: pd.Series) -> pd.Series:
    return (num / den.replace(0, np.nan) * 100).round(2)


def compute_kpis(clean: Mapping[str, pd.DataFrame], llm_results: pd.DataFrame | None, config: Mapping[str, Any]) -> dict[str, pd.DataFrame]:
    kcfg = config["kpi"]
    area = kcfg.get("area_col", "analysis_area")
    snapshots = config["snapshots"]
    last = snapshots[-1]
    L = clean["listings"]
    C = clean["calendar"]
    R = clean["reviews_unique"]
    keys = ["snapshot", area]
    out: dict[str, pd.DataFrame] = {}

    has_av = L["has_availability"].astype("string").str.strip().str.lower().eq("t").fillna(False).astype(bool) \
        if "has_availability" in L.columns else pd.Series(True, index=L.index)
    g = L.assign(active=has_av & L["availability_365"].gt(0).fillna(False)) \
         .groupby(keys).agg(n_listing=("id", "size"), n_active=("active", "sum")).reset_index()
    g["active_share_pct"] = _share(g["n_active"], g["n_listing"])
    out["kpi_active_listings"] = g

    g = L.assign(entire=L["room_type"] == "Entire home/apt").groupby(keys).agg(n_listing=("id", "size"), n_entire=("entire", "sum")).reset_index()
    g["entire_home_share_pct"] = _share(g["n_entire"], g["n_listing"])
    out["kpi_entire_home_share"] = g

    thr = int(kcfg.get("multi_host_threshold", 2))
    H = L.loc[~L["flag_missing_host"]]
    g = H.assign(multi=H["calculated_host_listings_count"] >= thr).groupby(keys).agg(
        n_listing=("id", "size"), n_multi_host_listing=("multi", "sum"), n_host=("host_id", "nunique")).reset_index()
    g["multi_host_share_pct"] = _share(g["n_multi_host_listing"], g["n_listing"])
    out["kpi_multi_host_share"] = g

    short_max = int(kcfg.get("short_stay_max_nights", 7))
    S = L.loc[~L["flag_min_nights_outlier"]]
    g = S.assign(short=S["minimum_nights"] <= short_max).groupby(keys).agg(n_listing=("id", "size"), n_short_stay=("short", "sum")).reset_index()
    g["short_stay_share_pct"] = _share(g["n_short_stay"], g["n_listing"])
    out["kpi_short_stay_share"] = g

    win = int(kcfg.get("occupancy_window_days", 90))
    Cw = C.loc[~C["flag_bad_available"] & ~C["flag_date_outside_window"]].copy()
    snap = pd.to_datetime(Cw["snapshot"])
    Cw = Cw.loc[(Cw["date"] >= snap) & (Cw["date"] < snap + pd.Timedelta(days=win))]
    area_map = L.drop_duplicates("id").set_index("id")[area]
    Cw[area] = Cw["listing_id"].astype(str).map(area_map)
    g = Cw.assign(booked=Cw["available"] == "f").groupby(keys).agg(n_days=("date", "size"), n_booked=("booked", "sum"),
                                                                  n_listing=("listing_id", "nunique")).reset_index()
    g["occupancy_pct"] = _share(g["n_booked"], g["n_days"])
    out["kpi_occupancy_90d"] = g

    g = L.groupby(keys).agg(n_listing=("id", "size"), reviews_ltm_mean=("number_of_reviews_ltm", "mean"),
                           reviews_ltm_median=("number_of_reviews_ltm", "median"),
                           share_with_review_pct=("number_of_reviews", lambda s: round(float((s > 0).mean() * 100), 2))).reset_index()
    g["reviews_ltm_mean"] = g["reviews_ltm_mean"].round(2)
    out["kpi_review_velocity"] = g

    P = L.loc[(L["snapshot"] == last) & L["price_usable"]].copy()
    P["price_per_person"] = P["price_num"] / P["accommodates"].replace(0, np.nan)
    g = P.groupby([area, "room_type"]).agg(n_listing=("id", "size"), price_median=("price_num", "median"),
                                           price_p25=("price_num", lambda s: s.quantile(0.25)),
                                           price_p75=("price_num", lambda s: s.quantile(0.75)),
                                           price_per_person_median=("price_per_person", "median")).reset_index()
    total = P.groupby(area).agg(n_listing=("id", "size"), price_median=("price_num", "median"),
                                price_p25=("price_num", lambda s: s.quantile(0.25)),
                                price_p75=("price_num", lambda s: s.quantile(0.75)),
                                price_per_person_median=("price_per_person", "median")).reset_index()
    total["room_type"] = "ALL"
    g = pd.concat([g, total], ignore_index=True)
    g.insert(0, "snapshot", last)
    g["currency"] = config["currency"]
    for c in ["price_median", "price_p25", "price_p75", "price_per_person_median"]:
        g[c] = g[c].round(2)
    out["kpi_median_price"] = g

    if llm_results is not None and len(llm_results):
        M = R.merge(llm_results, left_on="id", right_on="review_id", how="inner", suffixes=("", "_llm"))
        g = M.groupby(area).agg(n_review_llm=("review_id", "size"),
                                n_positive=("sentiment", lambda s: int((s == "positive").sum())),
                                n_mixed=("sentiment", lambda s: int((s == "mixed").sum())),
                                n_negative=("sentiment", lambda s: int((s == "negative").sum()))).reset_index()
        g["positive_share_pct"] = _share(g["n_positive"], g["n_review_llm"])
        g["negative_share_pct"] = _share(g["n_negative"], g["n_review_llm"])
        g.insert(0, "snapshot", last)
        out["kpi_llm_sentiment"] = g
        rows = []
        for _, r in M.iterrows():
            for asp in str(r.get("aspects_positive", "") or "").split("|"):
                if asp:
                    rows.append({area: r[area], "aspect": asp, "polarity": "positive"})
            for asp in str(r.get("aspects_negative", "") or "").split("|"):
                if asp:
                    rows.append({area: r[area], "aspect": asp, "polarity": "negative"})
        A = pd.DataFrame(rows, columns=[area, "aspect", "polarity"])
        g = A.groupby([area, "aspect", "polarity"]).size().rename("mentions").reset_index()
        g.insert(0, "snapshot", last)
        out["kpi_llm_aspects"] = g
    else:
        LOGGER.warning("Chưa có kết quả LLM -> bỏ qua kpi_llm_sentiment / kpi_llm_aspects (chạy lại không có --skip-llm).")
    return out


def save_kpis(kpis: Mapping[str, pd.DataFrame], config: Mapping[str, Any]) -> dict[str, Path]:
    root = Path(config.get("_project_root", Path.cwd()))
    processed = root / config["paths"]["processed"]
    processed.mkdir(parents=True, exist_ok=True)
    out = {}
    for name, frame in kpis.items():
        path = processed / f"{name}.csv"
        frame.to_csv(path, index=False, encoding="utf-8-sig")
        out[name] = path
        LOGGER.info("Lưu %s (%d dòng)", path, len(frame))
    catalog = processed / "kpi_catalog.csv"
    pd.DataFrame(KPI_CATALOG).to_csv(catalog, index=False, encoding="utf-8-sig")
    out["kpi_catalog"] = catalog
    return out


DATA_DICTIONARY = {
    "clean_listings.csv": {
        "snapshot": "Ngày chụp (YYYY-MM-DD) — thêm bởi pipeline",
        "id": "Mã listing (chuỗi) — khoá chính Inside Airbnb",
        "analysis_area": "Vùng A01..A08 theo sheet «Vùng» (gắn từ phân công, không gán lại)",
        "room_type": "Entire home/apt | Private room | Shared room | Hotel room",
        "price": "Giá gốc dạng chuỗi '$1,234.00'",
        "price_num": "Giá đã ép sang số (AUD/đêm); NaN nếu thiếu",
        "price_usable": "True nếu ở mốc cuối, có giá và không ngoại lai -> dùng cho KPI giá",
        "minimum_nights / minimum_nights_capped": "Số đêm tối thiểu gốc / đã chặn ở 365",
        "calculated_host_listings_count": "Số listing của host trong toàn thành phố (Inside Airbnb tính)",
        "number_of_reviews, number_of_reviews_ltm": "Tổng review / review 12 tháng gần nhất",
        "availability_365, has_availability": "Số ngày còn trống trong 365 ngày tới; có mở lịch hay không",
        "flag_*": "Cờ QA (xem reports/qa_report.csv). True = dòng bị quy tắc tương ứng đánh dấu",
    },
    "clean_calendar.csv.gz": {
        "snapshot, listing_id, date": "Mốc, listing, ngày (365 ngày kể từ mốc)",
        "available": "'t' còn trống, 'f' đã đặt hoặc chủ đóng lịch",
        "price_num": "Giá ngày đã ép số", "flag_*": "Cờ QA",
    },
    "clean_reviews.csv / clean_reviews_unique.csv": {
        "id": "Mã review", "listing_id": "Listing được review", "date": "Ngày review", "comments": "Văn bản review",
        "llm_sample": "1 nếu thuộc 1.000 review mẫu LLM (phân công)", "hand_label": "1 nếu thuộc 100 review gán nhãn tay",
        "analysis_area": "Vùng của listing", "flag_*": "Cờ QA",
        "(unique)": "Mỗi id một dòng (lấy mốc mới nhất) — đầu vào bước LLM",
    },
    "llm_results.csv": {
        "review_id": "Mã review", "sentiment": "positive | mixed | negative", "language": "mã ISO 639-1 (en, fr, zh, ...)",
        "aspects_positive / aspects_negative": "các khía cạnh khen / chê, nối bằng '|' (location, cleanliness, host, value, amenities, noise, safety)",
        "model": "tên mô hình đã dùng", "prompt_tokens / output_tokens": "token dùng cho lô chứa review này (chia đều theo lô)",
    },
    "kpi_*.csv": {k["kpi"]: f"{k['goal']} — {k['formula']} — đơn vị: {k['unit']}" for k in KPI_CATALOG},
}


def write_data_dictionary(config: Mapping[str, Any]) -> Path:
    root = Path(config.get("_project_root", Path.cwd()))
    reports = root / config["paths"]["reports"]
    reports.mkdir(parents=True, exist_ok=True)
    path = reports / "data_dictionary.md"
    lines = [f"# Từ điển dữ liệu — {config['city'].title()} ({config['currency']})", "",
             f"Nguồn: {config['source']['license']}. Mốc chụp: {', '.join(config['snapshots'])}.", ""]
    for file, cols in DATA_DICTIONARY.items():
        lines += [f"## `{file}`", "", "| Cột | Ý nghĩa |", "|---|---|"]
        lines += [f"| `{c}` | {d} |" for c, d in cols.items()]
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")
    with open(reports / "data_dictionary.json", "w", encoding="utf-8") as f:
        json.dump(DATA_DICTIONARY, f, ensure_ascii=False, indent=2)
    LOGGER.info("Lưu %s", path)
    return path
