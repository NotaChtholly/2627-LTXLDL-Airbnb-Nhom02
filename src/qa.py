from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping

import numpy as np
import pandas as pd
LOGGER = logging.getLogger(__name__)
def parse_money(series: pd.Series) -> pd.Series:
    text = series.astype("string").str.replace(r"[^0-9.\-]", "", regex=True)
    return pd.to_numeric(text, errors="coerce").astype(float)


def _path(config: Mapping[str, Any], value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else Path(config.get("_project_root", Path.cwd())) / path


@dataclass
class QALog:
    rows: list[dict[str, Any]] = field(default_factory=list)

    def add(self, rule_id: str, name: str, table: str, condition: str, reason: str, action: str,
            n_before: int, n_flagged: int, n_after: int,
            kpi_name: str = "", kpi_before: Any = "", kpi_after: Any = "", note: str = "") -> None:
        self.rows.append({
            "rule_id": rule_id, "rule_name": name, "table": table, "condition": condition,
            "reason": reason, "action": action, "n_rows_before": int(n_before),
            "n_flagged": int(n_flagged), "n_rows_after": int(n_after), "kpi_name": kpi_name,
            "kpi_before": _fmt(kpi_before), "kpi_after": _fmt(kpi_after), "note": note,
        })
        LOGGER.info("QA %s %-28s %-9s flagged=%-6d rows %d->%d %s", rule_id, name, table, n_flagged, n_before, n_after,
                    f"{kpi_name}: {_fmt(kpi_before)} -> {_fmt(kpi_after)}" if kpi_name else "")

    def frame(self) -> pd.DataFrame:
        return pd.DataFrame(self.rows)


def _fmt(value: Any) -> Any:
    if isinstance(value, (float, np.floating)):
        return "" if np.isnan(value) else round(float(value), 4)
    return value


def _median(series: pd.Series) -> float:
    return float(series.median()) if series.notna().any() else float("nan")


def qa_listings(listings: pd.DataFrame, config: Mapping[str, Any], areas: pd.DataFrame, log: QALog) -> pd.DataFrame:
    qa = config["qa"]
    snapshots = config["snapshots"]
    last = snapshots[-1]
    df = listings.copy()
    n0 = len(df)

    numeric_cols = ["accommodates", "bedrooms", "beds", "minimum_nights", "maximum_nights", "availability_30",
                    "availability_60", "availability_90", "availability_365", "number_of_reviews",
                    "number_of_reviews_ltm", "number_of_reviews_l30d", "calculated_host_listings_count",
                    "review_scores_rating", "review_scores_cleanliness", "review_scores_location",
                    "review_scores_value", "reviews_per_month", "latitude", "longitude", "estimated_occupancy_l365d"]
    bad_type = 0
    for col in numeric_cols:
        if col in df.columns:
            raw = df[col]
            df[col] = pd.to_numeric(raw, errors="coerce")
            bad_type += int((df[col].isna() & raw.notna() & (raw.astype("string").str.strip() != "")).sum())
    for col in ["last_scraped", "first_review", "last_review", "host_since"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")
    price_col = qa.get("price_column", "price")
    df["price_num"] = parse_money(df[price_col]) if price_col in df.columns else np.nan
    log.add("L01", "type_cast_numeric_dates", "listings",
            "cột số/ngày không ở kiểu số/datetime; price dạng '$1,234.00'",
            "KPI cần số thực; chuỗi tiền tệ không tính toán được",
            "ép kiểu (to_numeric/to_datetime, errors=coerce); thêm cột price_num",
            n0, bad_type, len(df), "n_ô_không_ép_được", bad_type, 0)

    keys = qa.get("dedupe_keys_listings", ["snapshot", "id"])
    dup = df.duplicated(subset=keys, keep="first")
    df = df.loc[~dup].copy()
    log.add("L02", "duplicate_within_snapshot", "listings", f"trùng khoá {keys}",
            "một listing đếm 2 lần làm sai mọi KPI đếm", "xoá bản trùng, giữ dòng đầu",
            n0, int(dup.sum()), len(df), "n_listing_mốc_cuối", int((listings["snapshot"] == last).sum()),
            int((df["snapshot"] == last).sum()))

    per_id = df.groupby("id")["snapshot"].nunique()
    df["flag_missing_in_some_snapshot"] = df["id"].map(per_id < len(snapshots)).fillna(False).astype(bool)
    log.add("L03", "listing_missing_across_snapshots", "listings",
            "id không có mặt ở đủ các mốc", "KPI theo thời gian so sánh cùng tập listing; thiếu mốc gây lệch",
            "gắn cờ flag_missing_in_some_snapshot; KPI theo thời gian ghi chú số listing thực có",
            len(df), int(df["flag_missing_in_some_snapshot"].sum()), len(df),
            "n_id_thiếu_mốc", int((per_id < len(snapshots)).sum()), int((per_id < len(snapshots)).sum()))

    last_mask = df["snapshot"] == last
    df["flag_missing_price"] = last_mask & df["price_num"].isna()
    log.add("L04", "missing_price_last_snapshot", "listings", f"snapshot=={last} và price rỗng",
            "KPI giá chỉ dùng mốc cuối (hướng dẫn); listing thiếu giá không vào mẫu giá",
            "gắn cờ flag_missing_price; loại khỏi các KPI về giá, giữ trong KPI đếm",
            len(df), int(df["flag_missing_price"].sum()), len(df),
            "median_price_mốc_cuối", _median(df.loc[last_mask, "price_num"]),
            _median(df.loc[last_mask & ~df["flag_missing_price"], "price_num"]))

    lo, hi = float(qa.get("price_min", 0)), float(qa.get("price_max", np.inf))
    before = _median(df.loc[last_mask & ~df["flag_missing_price"], "price_num"])
    df["flag_price_outlier"] = last_mask & df["price_num"].notna() & ((df["price_num"] < lo) | (df["price_num"] > hi))
    price_ok = last_mask & ~df["flag_missing_price"] & ~df["flag_price_outlier"]
    log.add("L05", "price_outlier", "listings", f"price_num < {lo} hoặc > {hi} ({config['currency']}/đêm) ở mốc cuối",
            "giá nhập nhầm (vd 10.000/đêm, 0) kéo lệch trung bình; median ít nhạy nhưng p90/mean thì có",
            "gắn cờ flag_price_outlier; loại khỏi KPI giá", len(df), int(df["flag_price_outlier"].sum()), len(df),
            "mean_price_mốc_cuối", float(df.loc[last_mask & ~df["flag_missing_price"], "price_num"].mean()),
            float(df.loc[price_ok, "price_num"].mean()) if price_ok.any() else np.nan,
            note=f"median trước/sau: {_fmt(before)} / {_fmt(_median(df.loc[price_ok, 'price_num']))}")

    cap = int(qa.get("min_nights_cap", 365))
    short_max = int(config["kpi"].get("short_stay_max_nights", 7))
    share_before = float((df["minimum_nights"] <= short_max).mean()) if "minimum_nights" in df else np.nan
    df["flag_min_nights_outlier"] = df["minimum_nights"].gt(cap).fillna(False) if "minimum_nights" in df else False
    df["minimum_nights_capped"] = df["minimum_nights"].clip(upper=cap) if "minimum_nights" in df else np.nan
    share_after = float((df.loc[~df["flag_min_nights_outlier"], "minimum_nights"] <= short_max).mean())
    log.add("L06", "min_nights_outlier", "listings", f"minimum_nights > {cap}",
            "giá trị 1000+ đêm là chặn lịch, không phải chính sách thuê; làm méo phân loại ngắn/dài hạn",
            f"gắn cờ flag_min_nights_outlier; thêm minimum_nights_capped (clip {cap}); loại khỏi KPI ngắn ngày",
            len(df), int(df["flag_min_nights_outlier"].sum()), len(df),
            "tỉ_lệ_listing_ngắn_ngày", share_before, share_after)

    acc_max = int(qa.get("accommodates_max", 16))
    df["flag_accommodates_outlier"] = df["accommodates"].gt(acc_max).fillna(False) if "accommodates" in df else False
    log.add("L07", "accommodates_outlier", "listings", f"accommodates > {acc_max}",
            "sức chứa bất thường thường là nhập sai hoặc dạng ký túc; KPI giá/người sẽ lệch",
            "gắn cờ flag_accommodates_outlier", len(df), int(df["flag_accommodates_outlier"].sum()), len(df))

    df["flag_missing_coords"] = df["latitude"].isna() | df["longitude"].isna()
    log.add("L08", "missing_coordinates", "listings", "latitude hoặc longitude rỗng",
            "không vẽ được bản đồ, không kiểm được vùng", "gắn cờ flag_missing_coords; loại khỏi hình không gian",
            len(df), int(df["flag_missing_coords"].sum()), len(df))

    box = areas.set_index("analysis_area")
    inside = pd.Series(False, index=df.index)
    for area, b in box.iterrows():
        m = df["analysis_area"] == area
        inside |= m & df["longitude"].between(b.lon_min, b.lon_max) & df["latitude"].between(b.lat_min, b.lat_max)
    df["flag_area_mismatch"] = ~df["flag_missing_coords"] & ~inside
    log.add("L09", "coords_outside_assigned_area", "listings",
            "(lon, lat) nằm ngoài hình chữ nhật của analysis_area trong sheet «Vùng»",
            "analysis_area là nhãn được giao; toạ độ lệch (Airbnb làm mờ vị trí) làm sai KPI theo vùng nếu tự gán lại",
            "gắn cờ flag_area_mismatch; GIỮ analysis_area theo phân công, không gán lại",
            len(df), int(df["flag_area_mismatch"].sum()), len(df),
            "n_listing_A01_mốc_cuối", int((last_mask & (df["analysis_area"] == box.index[0])).sum()),
            int((last_mask & (df["analysis_area"] == box.index[0])).sum()))

    known = set(qa.get("known_room_types", []))
    df["flag_room_type_unknown"] = ~df["room_type"].isin(known) if known else False
    log.add("L10", "room_type_unknown", "listings", f"room_type không thuộc {sorted(known)}",
            "giá trị mới/lỗi chính tả làm KPI theo loại phòng thiếu nhóm", "gắn cờ flag_room_type_unknown",
            len(df), int(df["flag_room_type_unknown"].sum()), len(df))
    if "neighbourhood_cleansed" in df.columns:
        n_nb = df.groupby("id")["neighbourhood_cleansed"].nunique()
        df["flag_neighbourhood_changed"] = df["id"].map(n_nb > 1).fillna(False).astype(bool)
        log.add("L11", "neighbourhood_changed_across_snapshots", "listings",
                "cùng id nhưng neighbourhood_cleansed khác nhau giữa các mốc",
                "ranh giới hành chính của Inside Airbnb có thể đổi; KPI theo khu vực hành chính sẽ nhảy",
                "gắn cờ flag_neighbourhood_changed; KPI theo vùng dùng analysis_area (ổn định) thay vì neighbourhood_cleansed",
                len(df), int(df["flag_neighbourhood_changed"].sum()), len(df))

    df["flag_missing_host"] = df["host_id"].isna() if "host_id" in df.columns else False
    log.add("L12", "missing_host_id", "listings", "host_id rỗng", "KPI host nhiều nhà cần host_id",
            "gắn cờ flag_missing_host; loại khỏi KPI host", len(df), int(df["flag_missing_host"].sum()), len(df))

    df["price_usable"] = price_ok
    return df


def qa_calendar(calendar: pd.DataFrame, config: Mapping[str, Any], log: QALog) -> pd.DataFrame:
    qa = config["qa"]
    df = calendar.copy()
    n0 = len(df)

    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    bad_date = int(df["date"].isna().sum())
    df = df.loc[df["date"].notna()].copy()
    log.add("C01", "unparseable_date", "calendar", "date không đọc được thành ngày",
            "không xác định được ngày -> không tính công suất", "xoá dòng", n0, bad_date, len(df))

    if "price" in df.columns:
        df["price_num"] = parse_money(df["price"])
    df["available"] = df["available"].astype("string").str.strip().str.lower()
    bad_avail = ~df["available"].isin(["t", "f"])
    log.add("C02", "available_not_t_f", "calendar", "available không phải 't'/'f'",
            "công suất = tỉ lệ ngày 'f'; giá trị lạ làm sai mẫu số", "gắn cờ flag_bad_available; loại khỏi KPI công suất",
            len(df), int(bad_avail.sum()), len(df))
    df["flag_bad_available"] = bad_avail.fillna(True).astype(bool)

    keys = qa.get("dedupe_keys_calendar", ["snapshot", "listing_id", "date"])
    occ_before = float((df["available"] == "f").mean())
    dup = df.duplicated(subset=keys, keep="first")
    df = df.loc[~dup].copy()
    log.add("C03", "duplicate_listing_day", "calendar", f"trùng khoá {keys}",
            "một ngày đếm 2 lần làm sai công suất", "xoá bản trùng", len(df) + int(dup.sum()), int(dup.sum()), len(df),
            "tỉ_lệ_ngày_không_trống", occ_before, float((df["available"] == "f").mean()))

    snap = pd.to_datetime(df["snapshot"])
    outside = (df["date"] < snap) | (df["date"] >= snap + pd.Timedelta(days=366))
    df["flag_date_outside_window"] = outside
    log.add("C04", "date_outside_365_window", "calendar", "date < mốc chụp hoặc > mốc + 365 ngày",
            "calendar chuẩn có đúng 365 ngày kể từ ngày chụp; ngoài cửa sổ là dữ liệu lệch mốc",
            "gắn cờ flag_date_outside_window; loại khỏi KPI công suất", len(df), int(outside.sum()), len(df))

    miss = df["price_num"].isna() if "price_num" in df.columns else pd.Series(False, index=df.index)
    df["flag_missing_price"] = miss
    log.add("C05", "missing_calendar_price", "calendar", "price rỗng",
            "giá ngày dùng để tham chiếu mùa vụ; thiếu thì bỏ khỏi trung bình giá theo ngày",
            "gắn cờ flag_missing_price (không xoá; vẫn tính công suất)", len(df), int(miss.sum()), len(df))
    return df


def qa_reviews(reviews: pd.DataFrame, config: Mapping[str, Any], listings: pd.DataFrame, log: QALog) -> tuple[pd.DataFrame, pd.DataFrame]:
    qa = config["qa"]
    df = reviews.copy()
    n0 = len(df)

    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["comments"] = df["comments"].astype("string")
    bad_date = int(df["date"].isna().sum())
    log.add("R01", "type_cast_date_text", "reviews", "date không đọc được; comments không phải chuỗi",
            "cần ngày để vẽ theo thời gian, chuỗi để đưa vào LLM", "ép kiểu; gắn cờ flag_bad_date (giữ dòng)",
            n0, bad_date, len(df))
    df["flag_bad_date"] = df["date"].isna()

    keys = qa.get("dedupe_keys_reviews", ["snapshot", "id"])
    dup = df.duplicated(subset=keys, keep="first")
    df = df.loc[~dup].copy()
    log.add("R02", "duplicate_within_snapshot", "reviews", f"trùng khoá {keys}", "review đếm 2 lần",
            "xoá bản trùng", n0, int(dup.sum()), len(df))

    per_id = df.groupby("id")["snapshot"].nunique()
    unique = df.sort_values("snapshot").drop_duplicates(subset="id", keep="last").copy()
    log.add("R03", "duplicate_across_snapshots", "reviews", "cùng id xuất hiện ở nhiều mốc",
            "đề thiết kế 5.000 review lặp lại ở 4 mốc; nếu đếm theo mốc sẽ nhân 4 và gọi LLM 4 lần",
            "giữ nguyên bảng theo mốc; tạo thêm reviews_unique (1 bản/id, lấy mốc mới nhất) cho LLM & KPI văn bản",
            len(df), int(df["id"].map(per_id > 1).sum()), len(df),
            "n_review_để_phân_tích", len(df), len(unique))

    min_chars = int(qa.get("review_min_chars", 3))
    text = unique["comments"].fillna("").str.strip()
    empty = text.str.len() < min_chars
    unique["flag_empty_comment"] = empty
    log.add("R04", "empty_or_too_short_comment", "reviews_unique", f"len(comments.strip()) < {min_chars}",
            "LLM/baseline không có gì để phân tích; '.' hay rỗng cho nhãn ngẫu nhiên",
            "gắn cờ flag_empty_comment; loại khỏi mẫu LLM nếu không thuộc nhãn tay",
            len(unique), int(empty.sum()), len(unique))

    assigned = set(listings["id"].astype(str))
    stray = ~unique["listing_id"].astype(str).isin(assigned)
    unique["flag_listing_not_assigned"] = stray
    log.add("R05", "review_listing_not_assigned", "reviews_unique", "listing_id không thuộc 1.000 listing được giao",
            "review phải gắn được vào listing/vùng để tính KPI theo vùng", "gắn cờ flag_listing_not_assigned",
            len(unique), int(stray.sum()), len(unique))

    snap = pd.to_datetime(unique["snapshot"])
    future = unique["date"].notna() & (unique["date"] > snap)
    unique["flag_future_date"] = future
    log.add("R06", "review_date_after_snapshot", "reviews_unique", "date > ngày chụp",
            "review không thể có sau ngày chụp; dấu hiệu lỗi dữ liệu", "gắn cờ flag_future_date",
            len(unique), int(future.sum()), len(unique))

    area = listings.drop_duplicates("id").set_index("id")["analysis_area"]
    unique["analysis_area"] = unique["listing_id"].astype(str).map(area)
    df["analysis_area"] = df["listing_id"].astype(str).map(area)
    return df, unique.reset_index(drop=True)


def run_qa(combined: Mapping[str, pd.DataFrame], config: Mapping[str, Any]) -> tuple[dict[str, pd.DataFrame], pd.DataFrame]:
    log = QALog()
    areas = pd.read_csv(_path(config, config["assignments"]["areas"]))
    listings = qa_listings(combined["listings"], config, areas, log)
    calendar = qa_calendar(combined["calendar"], config, log)
    reviews, reviews_unique = qa_reviews(combined["reviews"], config, listings, log)
    return {"listings": listings, "calendar": calendar, "reviews": reviews, "reviews_unique": reviews_unique}, log.frame()


def save_clean(clean: Mapping[str, pd.DataFrame], config: Mapping[str, Any]) -> dict[str, Path]:
    processed = _path(config, config["paths"]["processed"])
    processed.mkdir(parents=True, exist_ok=True)
    out = {}
    for name, frame in clean.items():
        path = processed / (f"clean_{name}.csv.gz" if name == "calendar" else f"clean_{name}.csv")
        frame.to_csv(path, index=False, compression="gzip" if name == "calendar" else None)
        out[name] = path
        LOGGER.info("Lưu %s (%d dòng)", path, len(frame))
    return out


def write_qa_report(report: pd.DataFrame, config: Mapping[str, Any]) -> Path:
    reports = _path(config, config["paths"]["reports"])
    reports.mkdir(parents=True, exist_ok=True)
    path = reports / "qa_report.csv"
    report.to_csv(path, index=False, encoding="utf-8-sig")
    LOGGER.info("Lưu %s (%d quy tắc)", path, len(report))
    return path
