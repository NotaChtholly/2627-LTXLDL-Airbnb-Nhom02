from __future__ import annotations
import argparse
import logging
from pathlib import Path
from typing import Any
import pandas as pd
import yaml
from src.download import (
    download_raw_snapshots,
    filter_assigned_data,
    validate_quotas,
)
from src.kpi import init_kpi_structures, verify_filtered_schema
from src.llm import export_hand_labeled_dataset, extract_llm_samples
from src.viz import init_report_template, setup_viz_theme
LOGGER = logging.getLogger(__name__)
def load_config(path: str | Path) -> dict[str, Any]:
    config_path = Path(path).resolve()
    with config_path.open("r", encoding="utf-8-sig") as f:
        config = yaml.safe_load(f)
    if not isinstance(config, dict):
        raise ValueError(f"Tệp cấu hình không hợp lệ: {config_path}")
    return config
def _get_llm_and_hand_ids(config: dict[str, Any]) -> tuple[list[str], list[str]]:    
    assign_cfg = config.get("assigned_ids") or config.get("assignments", {})
    rev_path = Path(assign_cfg.get("reviews_file") or assign_cfg.get("reviews"))
    df_rev = pd.read_csv(rev_path, dtype="string", encoding="utf-8-sig")
    required_cols = {"review_id", "Mẫu LLM", "Nhãn tay"}
    if not required_cols.issubset(df_rev.columns):
        raise ValueError(f"Tệp {rev_path} thiếu các cột bắt buộc: {sorted(required_cols)}")
    llm_mask = df_rev["Mẫu LLM"].str.strip().str.lower().eq("x")
    hand_mask = df_rev["Nhãn tay"].str.strip().str.lower().eq("x")
    llm_ids = df_rev.loc[llm_mask, "review_id"].str.strip().dropna().tolist()
    hand_ids = df_rev.loc[hand_mask, "review_id"].str.strip().dropna().tolist()
    return llm_ids, hand_ids
def main() -> None:
    parser = argparse.ArgumentParser(
        description="Chạy quy trình xử lý dữ liệu Inside Airbnb."
    )
    parser.add_argument(
        "--config",
        required=True,
        help="Đường dẫn tới file cấu hình YAML (ví dụ: configs/melbourne.yaml)",
    )
    parser.add_argument(
        "--skip-download",
        action="store_true",
        help="Bỏ qua bước tải file thô nếu đã có sẵn trong data/raw/",
    )
    parser.add_argument(
        "--skip-validation",
        action="store_true",
        help="Bỏ qua bước kiểm tra Quotas",
    )
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
    config = load_config(args.config)
    paths = config.get("paths", {})
    processed_dir = paths.get("processed_dir", paths.get("processed", "data/processed"))
    reports_dir = paths.get("reports_dir", paths.get("reports", "reports"))
    samples_dir = Path(paths.get("samples_dir", paths.get("samples", "data/samples")))
    setup_viz_theme()
    init_kpi_structures(processed_dir=processed_dir)
    init_report_template(reports_dir=reports_dir)
    if not args.skip_download:
        download_raw_snapshots(config)
    data_dict = filter_assigned_data(config)
    if not args.skip_validation:
        validate_quotas(data_dict, config)
    df_listings = data_dict["listings"]
    df_reviews = data_dict["reviews"]
    if not verify_filtered_schema(df_listings):
        raise RuntimeError("Dữ liệu listings vi phạm Hợp đồng Dữ liệu")
    llm_ids, hand_ids = _get_llm_and_hand_ids(config)
    df_llm_samples = extract_llm_samples(
        df_reviews,
        llm_ids,
        out_path=str(samples_dir / "llm_sample_1000.csv"),
    )
    export_hand_labeled_dataset(
        df_llm_samples,
        hand_ids,
        out_path=str(samples_dir / "hand_labeled_100.csv"),
    )
if __name__ == "__main__":
    main()