from __future__ import annotations
import logging
from pathlib import Path
from typing import Any
import pandas as pd
import requests
LOGGER = logging.getLogger(__name__)
TABLES = ("listings", "calendar", "reviews")
REQUIRED_COLUMNS = {
    "listings": {"id", "price", "room_type", "number_of_reviews"},
    "calendar": {"listing_id", "date"},
    "reviews": {"id", "listing_id", "date", "comments"},
}
def _check_csv_file(path: Path, table: str) -> None:
    if not path.is_file() or path.stat().st_size == 0:
        raise ValueError(f"File không tồn tại hoặc rỗng: {path}")
    try:
        columns = set(pd.read_csv(path, compression="gzip", nrows=0).columns)
    except Exception:
        columns = set(pd.read_csv(path, nrows=0).columns)
    missing = REQUIRED_COLUMNS[table] - columns
    if missing:
        raise ValueError(f"{path} thiếu các cột bắt buộc: {sorted(missing)}")
def _build_snapshot_url(config: dict[str, Any], snapshot: str, table: str) -> str:
    base_url = config["source"]["base_url"].rstrip("/")
    data_root = config["data_root"].strip("/")
    if base_url.endswith(data_root):
        return f"{base_url}/{snapshot}/data/{table}.csv.gz"
    return f"{base_url}/{data_root}/{snapshot}/data/{table}.csv.gz"
def download_raw_snapshots(config: dict[str, Any]) -> None:
    raw_dir = Path(config["paths"].get("raw_dir", config["paths"].get("raw", "data/raw")))
    with requests.Session() as session:
        for snapshot in map(str, config["snapshots"]):
            snapshot_dir = raw_dir / snapshot
            snapshot_dir.mkdir(parents=True, exist_ok=True)
            for table in TABLES:
                dest = snapshot_dir / f"{table}.csv.gz"
                if dest.exists():
                    try:
                        _check_csv_file(dest, table)
                        continue
                    except Exception as exc:
                        LOGGER.warning("Tải lại file lỗi %s: %s", dest, exc)
                url = _build_snapshot_url(config, snapshot, table)
                temp_file = dest.with_suffix(".csv.gz.part")
                try:
                    with session.get(url, stream=True, timeout=(20, 180)) as resp:
                        resp.raise_for_status()
                        with temp_file.open("wb") as f:
                            for chunk in resp.iter_content(chunk_size=1024 * 1024):
                                if chunk:
                                    f.write(chunk)
                    _check_csv_file(temp_file, table)
                    temp_file.replace(dest)
                    LOGGER.info("Đã tải thành công: %s", dest)
                finally:
                    if temp_file.exists():
                        temp_file.unlink()
def _read_matching_chunks(path: Path, key: str, valid_ids: set[str]) -> pd.DataFrame:
    chunks = []
    for chunk in pd.read_csv(
        path, dtype={"id": "string", "listing_id": "string"}, low_memory=False, chunksize=100_000
    ):
        matched = chunk.loc[chunk[key].str.strip().isin(valid_ids)]
        if not matched.empty:
            chunks.append(matched)
    if not chunks:
        return pd.read_csv(path, nrows=0)
    return pd.concat(chunks, ignore_index=True)
def filter_assigned_data(config: dict[str, Any]) -> dict[str, pd.DataFrame]:
    raw_dir = Path(config["paths"].get("raw_dir", config["paths"].get("raw", "data/raw")))
    assign_cfg = config.get("assigned_ids") or config.get("assignments")
    listings_path = Path(assign_cfg.get("listings_file") or assign_cfg.get("listings"))
    reviews_path = Path(assign_cfg.get("reviews_file") or assign_cfg.get("reviews"))
    df_assign_listings = pd.read_csv(listings_path, dtype="string", encoding="utf-8-sig")
    df_assign_reviews = pd.read_csv(reviews_path, dtype="string", encoding="utf-8-sig")
    listing_ids = set(df_assign_listings["listing_id"].str.strip().dropna())
    review_ids = set(df_assign_reviews["review_id"].str.strip().dropna())
    area_map = df_assign_listings.set_index(df_assign_listings["listing_id"].str.strip())[
        "analysis_area"
    ].str.strip()
    all_tables: dict[str, list[pd.DataFrame]] = {t: [] for t in TABLES}
    for snapshot in map(str, config["snapshots"]):
        snap_dir = raw_dir / snapshot
        df_l = _read_matching_chunks(snap_dir / "listings.csv.gz", "id", listing_ids)
        df_l["analysis_area"] = df_l["id"].str.strip().map(area_map)
        df_c = _read_matching_chunks(snap_dir / "calendar.csv.gz", "listing_id", listing_ids)
        df_r = _read_matching_chunks(snap_dir / "reviews.csv.gz", "id", review_ids)
        for name, df in zip(TABLES, (df_l, df_c, df_r)):
            df.insert(0, "snapshot", snapshot)
            all_tables[name].append(df)
    return {table: pd.concat(frames, ignore_index=True) for table, frames in all_tables.items()}
def validate_quotas(data_dict: dict[str, pd.DataFrame], config: dict[str, Any]) -> bool:
    errors: list[str] = []
    snapshots = [str(s) for s in config["snapshots"]]
    expected_no_reviews = {"2025-09-12": 50, "2025-12-12": 30, "2026-03-21": 25, "2026-06-16": 25}
    for snap in snapshots:
        df_l = data_dict["listings"].loc[data_dict["listings"]["snapshot"] == snap]
        df_c = data_dict["calendar"].loc[data_dict["calendar"]["snapshot"] == snap]
        df_r = data_dict["reviews"].loc[data_dict["reviews"]["snapshot"] == snap]
        if len(df_l) != 1000:
            errors.append(f"{snap}: listings cần 1000 dòng, thực tế {len(df_l)}")
        if len(df_c) != 365000:
            errors.append(f"{snap}: calendar cần 365000 dòng, thực tế {len(df_c)}")
        if len(df_r) != 5000:
            errors.append(f"{snap}: reviews cần 5000 dòng, thực tế {len(df_r)}")
        room_counts = df_l["room_type"].value_counts()
        if room_counts.get("Entire home/apt", 0) != 875 or room_counts.get("Private room", 0) != 125:
            errors.append(f"{snap}: sai tỷ lệ loại phòng 875/125.")
        no_rev = int((pd.to_numeric(df_l["number_of_reviews"], errors="coerce") == 0).sum())
        if snap in expected_no_reviews and no_rev != expected_no_reviews[snap]:
            errors.append(f"{snap}: số phòng 0 review cần {expected_no_reviews[snap]}, có {no_rev}")
        if snap == snapshots[-1]:
            missing_price = int(df_l["price"].isna().sum())
            if missing_price != 20:
                errors.append(f"{snap}: thiếu giá ở mốc cuối cần 20, thực tế {missing_price}")
        area_counts = df_l["analysis_area"].value_counts()
        if not ((area_counts >= 120) & (area_counts <= 130)).all():
            errors.append(f"{snap}: số listing mỗi vùng analysis_area nằm ngoài khoảng 120-130.")
    if errors:
        raise ValueError("Kiểm tra Quota thất bại:\n" + "\n".join(errors))
    return True