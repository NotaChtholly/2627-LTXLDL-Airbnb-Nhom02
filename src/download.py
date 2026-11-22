from __future__ import annotations

import argparse
import gzip
import logging
import shutil
from pathlib import Path
from typing import Any, Mapping

import pandas as pd
import requests
import yaml

LOGGER = logging.getLogger(__name__)
TABLES = ("listings", "calendar", "reviews")
REQUIRED_COLUMNS = {
    "listings": {"id"},
    "calendar": {"listing_id", "date"},
    "reviews": {"id", "listing_id", "date", "comments"},
}
USER_AGENT = "Mozilla/5.0 (compatible; UET-LTXLDL-student-project/1.0; +https://insideairbnb.com)"


def load_config(path: str | Path) -> dict[str, Any]:
    config_path = Path(path).resolve()
    with config_path.open("r", encoding="utf-8-sig") as file:
        config = yaml.safe_load(file)
    if not isinstance(config, dict):
        raise ValueError("File YAML phải chứa một mapping.")
    config["_project_root"] = str(config_path.parent.parent)
    config["snapshots"] = [str(s) for s in config["snapshots"]]
    return config


def _path(config: Mapping[str, Any], value: str | Path) -> Path:
    path = Path(value)
    root = Path(config.get("_project_root", Path.cwd()))
    return path if path.is_absolute() else root / path


def _compression(path: Path) -> str | None:
    with path.open("rb") as file:
        return "gzip" if file.read(2) == b"\x1f\x8b" else None


def _check_csv_file(path: Path, table: str) -> None:
    if not path.is_file() or path.stat().st_size == 0:
        raise ValueError(f"File không tồn tại hoặc rỗng: {path}")
    try:
        columns = set(pd.read_csv(path, compression=_compression(path), nrows=0).columns)
    except Exception as exc:
        raise ValueError(f"File không phải CSV hợp lệ: {path}") from exc
    missing = REQUIRED_COLUMNS[table] - columns
    if missing:
        raise ValueError(f"{path} thiếu cột: {sorted(missing)}")


def _gzip_file(path: Path) -> None:
    compressed = path.with_name(path.name + ".gzip")
    try:
        with path.open("rb") as source, gzip.open(compressed, "wb") as target:
            shutil.copyfileobj(source, target, length=1024 * 1024)
        compressed.replace(path)
    finally:
        if compressed.exists():
            compressed.unlink()


def download_raw_snapshots(
    config: Mapping[str, Any], session: requests.Session | None = None
) -> None:
    raw_root = _path(config, config["paths"]["raw"])
    raw_root.mkdir(parents=True, exist_ok=True)
    http = session or requests.Session()
    http.headers.update({"User-Agent": USER_AGENT})
    close_session = session is None
    base_url = config["source"]["base_url"].rstrip("/")
    data_root = config["data_root"].strip("/")

    try:
        for snapshot in config["snapshots"]:
            snapshot = str(snapshot)
            snapshot_dir = raw_root / snapshot
            snapshot_dir.mkdir(parents=True, exist_ok=True)
            for table in TABLES:
                destination = snapshot_dir / f"{table}.csv.gz"
                if destination.exists():
                    try:
                        _check_csv_file(destination, table)
                    except (OSError, ValueError) as exc:
                        LOGGER.warning("Tải lại file không hợp lệ %s: %s", destination, exc)
                    else:
                        LOGGER.info("Đã có %s, bỏ qua tải", destination)
                        continue

                temporary = destination.with_name(destination.name + ".part")
                response = None
                try:
                    url = f"{base_url}/{data_root}/{snapshot}/data/{table}.csv.gz"
                    LOGGER.info("Tải %s", url)
                    response = http.get(url, stream=True, timeout=(20, 300))
                    if response.status_code == 404:
                        raise ValueError(
                            f"404 — không có bản chụp {snapshot} cho {data_root}. "
                            "Kiểm tra lại ngày mốc trong configs/<city>.yaml."
                        )
                    response.raise_for_status()
                    with temporary.open("wb") as file:
                        for chunk in response.iter_content(1024 * 1024):
                            if chunk:
                                file.write(chunk)
                    _check_csv_file(temporary, table)
                    if _compression(temporary) is None:
                        _gzip_file(temporary)
                    _check_csv_file(temporary, table)
                    temporary.replace(destination)
                    LOGGER.info("Đã tải %s (%.1f MB)", destination, destination.stat().st_size / 1e6)
                finally:
                    if response is not None:
                        response.close()
                    if temporary.exists():
                        temporary.unlink()
    finally:
        if close_session:
            http.close()


def _read_assignments(config: Mapping[str, Any]) -> tuple[pd.DataFrame, pd.DataFrame]:
    assigned_listings = pd.read_csv(
        _path(config, config["assignments"]["listings"]), dtype="string", encoding="utf-8-sig"
    )
    assigned_reviews = pd.read_csv(
        _path(config, config["assignments"]["reviews"]), dtype="string", encoding="utf-8-sig"
    )
    if not {"listing_id", "analysis_area"}.issubset(assigned_listings.columns):
        raise ValueError("assigned_listings.csv cần có cột listing_id và analysis_area.")
    if not {"review_id", "listing_id", "llm_sample", "hand_label"}.issubset(assigned_reviews.columns):
        raise ValueError("assigned_reviews.csv cần có cột review_id, listing_id, llm_sample, hand_label.")
    for frame, cols in ((assigned_listings, ["listing_id", "analysis_area"]),
                        (assigned_reviews, ["review_id", "listing_id"])):
        for col in cols:
            frame[col] = frame[col].str.strip()
    return assigned_listings, assigned_reviews


def _ids(series: pd.Series) -> set[str]:
    values = series.astype("string").str.strip().dropna()
    return set(values[values.ne("")])


def _read_matching_rows(path: Path, key: str, ids: set[str], usecols: list[str] | None = None) -> pd.DataFrame:
    chunks = []
    for chunk in pd.read_csv(
        path,
        compression=_compression(path),
        dtype={"id": "string", "listing_id": "string"},
        usecols=usecols,
        low_memory=False,
        chunksize=100_000,
    ):
        if key not in chunk.columns:
            raise ValueError(f"{path} thiếu cột {key}.")
        matches = chunk.loc[chunk[key].astype("string").str.strip().isin(ids)]
        if not matches.empty:
            chunks.append(matches)
    return (
        pd.concat(chunks, ignore_index=True)
        if chunks
        else pd.read_csv(path, compression=_compression(path), nrows=0)
    )


def filter_assigned_data(config: Mapping[str, Any]) -> dict[str, dict[str, pd.DataFrame]]:
    raw_root = _path(config, config["paths"]["raw"])
    assigned_listings, assigned_reviews = _read_assignments(config)
    listing_ids = _ids(assigned_listings["listing_id"])
    review_ids = _ids(assigned_reviews["review_id"])
    area_by_listing = assigned_listings.set_index("listing_id")["analysis_area"]
    flags = assigned_reviews.set_index("review_id")[["llm_sample", "hand_label"]].astype(int)
    filtered: dict[str, dict[str, pd.DataFrame]] = {}

    for value in config["snapshots"]:
        snapshot = str(value)
        folder = raw_root / snapshot
        paths = {table: folder / f"{table}.csv.gz" for table in TABLES}
        for table, path in paths.items():
            _check_csv_file(path, table)

        listings = _read_matching_rows(paths["listings"], "id", listing_ids)
        listings["analysis_area"] = listings["id"].str.strip().map(area_by_listing)
        calendar = _read_matching_rows(paths["calendar"], "listing_id", listing_ids)
        reviews = _read_matching_rows(paths["reviews"], "id", review_ids)
        reviews = reviews.join(flags, on="id")
        for frame in (listings, calendar, reviews):
            frame.insert(0, "snapshot", snapshot)
        filtered[snapshot] = {"listings": listings, "calendar": calendar, "reviews": reviews}
        LOGGER.info("%s: listings=%d calendar=%d reviews=%d", snapshot, len(listings), len(calendar), len(reviews))
    return filtered


def concat_snapshots(
    filtered_dict: Mapping[str, Mapping[str, pd.DataFrame]],
) -> dict[str, pd.DataFrame]:
    if not filtered_dict:
        raise ValueError("Không có snapshot để nối.")
    return {
        table: pd.concat(
            [filtered_dict[snapshot][table] for snapshot in filtered_dict],
            ignore_index=True,
        )
        for table in TABLES
    }


def save_filtered(combined: Mapping[str, pd.DataFrame], config: Mapping[str, Any]) -> dict[str, Path]:
    processed = _path(config, config["paths"]["processed"])
    processed.mkdir(parents=True, exist_ok=True)
    out = {}
    for table, frame in combined.items():
        path = processed / f"filtered_{table}.csv.gz"
        frame.to_csv(path, index=False, compression="gzip")
        out[table] = path
        LOGGER.info("Lưu %s (%d dòng)", path, len(frame))
    return out


def _missing_price_count(series: pd.Series) -> int:
    text = series.astype("string").str.strip().str.lower()
    return int((series.isna() | text.isin({"", "nan", "none", "null", "na", "n/a"})).sum())


def validate_quotas(
    filtered_dict: Mapping[str, Mapping[str, pd.DataFrame]],
    config: Mapping[str, Any],
) -> bool:
    quota = config["quota"]
    qa = config["qa"]
    snapshots = [str(value) for value in config["snapshots"]]
    enforce = {str(s) for s in quota.get("enforce_for", snapshots)}
    no_review_counts = {str(k): int(v) for k, v in quota.get("no_review_counts", {}).items()}
    missing_price_counts = {str(k): int(v) for k, v in quota.get("missing_price_counts", {}).items()}

    errors: list[str] = []
    warnings: list[str] = []
    expected_rows = {
        "listings": int(quota["listings_per_snapshot"]),
        "calendar": int(quota["calendar_rows_per_snapshot"]),
        "reviews": int(quota["reviews_per_snapshot"]),
    }
    for snapshot in snapshots:
        if snapshot not in filtered_dict:
            errors.append(f"Thiếu snapshot {snapshot}.")
            continue
        report = errors if snapshot in enforce else warnings
        frames = filtered_dict[snapshot]
        listings = frames["listings"]
        for table, expected in expected_rows.items():
            actual = len(frames[table])
            if actual != expected:
                report.append(f"{snapshot}: {table} cần {expected} dòng, có {actual}")

        if "room_type" in listings:
            counts = listings["room_type"].value_counts()
            for room_type, expected in quota["room_type_counts"].items():
                actual = int(counts.get(room_type, 0))
                if actual != int(expected):
                    report.append(f"{snapshot}: {room_type} cần {expected}, có {actual}")
        else:
            errors.append(f"{snapshot}: thiếu cột room_type.")

        if "number_of_reviews" not in listings:
            errors.append(f"{snapshot}: thiếu cột number_of_reviews.")
        elif snapshot in no_review_counts:
            no_review = int((pd.to_numeric(listings["number_of_reviews"], errors="coerce") == 0).sum())
            if no_review != no_review_counts[snapshot]:
                report.append(f"{snapshot}: no_review cần {no_review_counts[snapshot]}, có {no_review}")
        else:
            warnings.append(f"{snapshot}: không có quota no_review cho mốc này, bỏ qua.")

        price_column = qa.get("price_column", "price")
        if price_column not in listings:
            errors.append(f"{snapshot}: thiếu cột {price_column}.")
        elif snapshot in missing_price_counts:
            missing_price = _missing_price_count(listings[price_column])
            if missing_price != missing_price_counts[snapshot]:
                report.append(f"{snapshot}: missing_price cần {missing_price_counts[snapshot]}, có {missing_price}")

        area_column = "analysis_area" if "analysis_area" in listings else qa.get("area_column", "neighbourhood_cleansed")
        area_quota = quota.get("neighbourhood_listings")
        if area_quota:
            counts = listings[area_column].fillna("<missing>").value_counts()
            lower, upper = int(area_quota["min"]), int(area_quota["max"])
            for area, count in counts.items():
                if not lower <= int(count) <= upper:
                    report.append(f"{snapshot}: {area_column}={area} có {count} listings, ngoài khoảng {lower}-{upper}")

    for w in warnings:
        LOGGER.warning("Quota (mốc ngoài danh sách bắt buộc): %s", w)
    if errors:
        raise ValueError("Kiểm tra quota thất bại:\n- " + "\n- ".join(errors))
    LOGGER.info("Quota OK cho %d mốc (bắt buộc: %s)", len(snapshots), ", ".join(sorted(enforce & set(snapshots))))
    return True


def main() -> None:
    parser = argparse.ArgumentParser(description="Tải và lọc dữ liệu Inside Airbnb.")
    parser.add_argument("--config", required=True)
    parser.add_argument("--download-only", action="store_true")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    config = load_config(args.config)
    download_raw_snapshots(config)
    if not args.download_only:
        filtered = filter_assigned_data(config)
        validate_quotas(filtered, config)
        combined = concat_snapshots(filtered)
        save_filtered(combined, config)
        for table, frame in combined.items():
            LOGGER.info("%s: %d dòng qua %d snapshot", table, len(frame), len(filtered))


if __name__ == "__main__":
    main()
