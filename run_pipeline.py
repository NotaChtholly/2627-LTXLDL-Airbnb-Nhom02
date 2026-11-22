from __future__ import annotations

import argparse
import logging
import sys
import time
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from src import baseline, download, evaluate, kpi, llm, qa, report, viz

LOGGER = logging.getLogger("pipeline")


def step(name: str):
    LOGGER.info("=" * 70)
    LOGGER.info("BƯỚC %s", name)
    LOGGER.info("=" * 70)


def main() -> int:
    parser = argparse.ArgumentParser(description="Quy trình phân tích Inside Airbnb (một lệnh).")
    parser.add_argument("--config", required=True, help="configs/<city>.yaml")
    parser.add_argument("--skip-llm", action="store_true", help="không gọi API; chỉ dùng cache LLM nếu có")
    parser.add_argument("--skip-download", action="store_true", help="không tải; dùng tệp sẵn có trong data/raw")
    parser.add_argument("--overwrite-hand-labels", action="store_true", help="ghi đè data/samples/hand_labeled_100.csv (MẤT nhãn đã điền!)")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s",
                        datefmt="%H:%M:%S")
    for noisy in ("matplotlib", "PIL", "httpx", "google_genai"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
    t0 = time.time()

    config = download.load_config(args.config)
    root = Path(config["_project_root"])
    processed = root / config["paths"]["processed"]
    samples = root / config["paths"]["samples"]
    reports = root / config["paths"]["reports"]
    LOGGER.info("Thành phố: %s | mốc: %s | tiền tệ: %s", config["city"], config["snapshots"], config["currency"])

    step("0/10 khởi tạo thư mục & biểu mẫu")
    kpi.init_kpi_structures(processed, reports)
    viz.init_report_template(reports)
    kpi.write_data_dictionary(config)

    step("1/10 tải dữ liệu thô")
    if args.skip_download:
        LOGGER.info("--skip-download: dùng tệp sẵn có")
    else:
        download.download_raw_snapshots(config)

    step("2/10 lọc theo ID được giao + kiểm quota")
    filtered = download.filter_assigned_data(config)
    download.validate_quotas(filtered, config)
    combined = download.concat_snapshots(filtered)
    download.save_filtered(combined, config)
    if not kpi.verify_filtered_schema(combined["listings"]):
        raise SystemExit("Hợp đồng dữ liệu listings không thoả — dừng.")

    step("3/10 QA")
    clean, qa_report = qa.run_qa(combined, config)
    qa.save_clean(clean, config)
    qa.write_qa_report(qa_report, config)

    step("4/10 mẫu LLM (1.000) và tệp nhãn tay (100)")
    RU = clean["reviews_unique"]
    llm_ids = RU.loc[RU["llm_sample"].astype(int) == 1, "id"]
    hand_ids = RU.loc[RU["hand_label"].astype(int) == 1, "id"]
    sample = llm.extract_llm_samples(RU.rename(columns={"id": "review_id"}), llm_ids, samples / "llm_sample_1000.csv")
    llm.export_hand_labeled_dataset(sample, hand_ids, samples / "hand_labeled_100.csv", overwrite=args.overwrite_hand_labels)

    step("5/10 baseline (không LLM)")
    base = baseline.run_baseline(sample, config["llm"]["aspects"], text_col="comments", id_col="review_id")
    base.to_csv(processed / "baseline_results.csv", index=False, encoding="utf-8-sig")
    LOGGER.info("baseline: %d review -> %s", len(base), processed / "baseline_results.csv")

    step("6/10 LLM" + (" (--skip-llm: chỉ cache)" if args.skip_llm else ""))
    llm_results = llm.run_llm(RU, config, skip_llm=args.skip_llm)

    step("7/10 đánh giá LLM vs baseline trên nhãn tay")
    metrics = evaluate.run_evaluation(llm_results, base, RU, config)

    step("8/10 ước tính chi phí")
    cost = llm.estimate_cost(llm_results, llm.count_city_reviews(config), config) if len(llm_results) else pd.DataFrame()

    step("9/10 KPI")
    kpis = kpi.compute_kpis(clean, llm_results if len(llm_results) else None, config)
    kpi.save_kpis(kpis, config)

    step("10/10 hình + bản nháp báo cáo")
    figures = viz.make_figures(clean, kpis, metrics, config)
    report.write_report_draft(clean, qa_report, kpis, metrics, cost, figures, config)

    LOGGER.info("XONG trong %.0fs. Đầu ra: %s, %s, %s", time.time() - t0, processed, reports, root / config["paths"]["figures"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
