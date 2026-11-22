from __future__ import annotations

import logging
import subprocess
from pathlib import Path
from typing import Any, Mapping

import pandas as pd

LOGGER = logging.getLogger(__name__)


def _git_commit(root: Path) -> str:
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=root, capture_output=True, text=True, timeout=5).stdout.strip() or "(chưa commit)"
    except Exception:
        return "(không có git)"


def _table(df: pd.DataFrame, max_rows: int = 40) -> str:
    if df is None or df.empty:
        return "_(trống)_"
    d = df.head(max_rows)
    cols = list(d.columns)
    lines = ["| " + " | ".join(str(c) for c in cols) + " |", "|" + "---|" * len(cols)]
    for _, r in d.iterrows():
        lines.append("| " + " | ".join("" if pd.isna(v) else str(v) for v in r.tolist()) + " |")
    if len(df) > max_rows:
        lines.append(f"| … ({len(df) - max_rows} dòng nữa) |")
    return "\n".join(lines)


def write_report_draft(clean: Mapping[str, pd.DataFrame], qa_report: pd.DataFrame, kpis: Mapping[str, pd.DataFrame],
                       metrics: pd.DataFrame | None, cost: pd.DataFrame | None, figures: list[Path],
                       config: Mapping[str, Any]) -> Path:
    root = Path(config.get("_project_root", Path.cwd()))
    reports = root / config["paths"]["reports"]
    reports.mkdir(parents=True, exist_ok=True)
    snaps = config["snapshots"]
    L = clean["listings"]
    city = config["city"].title()

    md = [f"# Báo cáo kỹ thuật — Thị trường Airbnb {city} (bản nháp tự sinh)", "",
          f"Môn Lập trình xử lý dữ liệu (UET.DSE2049) · Nhóm {config.get('data_code', '')} · mã commit: `{_git_commit(root)}`", "",
          "## 1. Bối cảnh và bên đặt hàng", "",
          f"**Bên đặt hàng: Chính quyền thành phố {city}.** Câu hỏi đặt ra: cho thuê ngắn hạn tập trung ở đâu, "
          "bao nhiêu phần là nhà nguyên căn và host thương mại (nhiều nhà), xu hướng công suất và giá qua 4 quý, "
          "và khách phàn nàn điều gì (từ review). _(Nhóm viết thêm 3–5 câu về lý do chọn bên đặt hàng.)_", "",
          "## 2. Dữ liệu", "",
          f"- Nguồn: {config['source']['license']}. Đường dẫn: `{config['source']['base_url']}/{config['data_root']}/<mốc>/data/`",
          f"- Bốn mốc chụp: {', '.join(snaps)}. Tiền tệ: {config['currency']}.",
          f"- Phần dữ liệu của nhóm (lọc theo danh sách ID được giao): {L['id'].nunique()} listing × {len(snaps)} mốc = {len(L)} dòng listings; "
          f"{len(clean['calendar'])} dòng calendar; {len(clean['reviews'])} dòng reviews ({len(clean['reviews_unique'])} review duy nhất).",
          "- Cấu trúc tệp và kiểu dữ liệu: xem `reports/data_dictionary.md`. Điểm lạ của từng bản chụp: xem cột `note`/`n_flagged` trong QA.", "",
          "## 3. QA (tên → điều kiện → lý do → hành động) và tác động", "",
          _table(qa_report[["rule_id", "rule_name", "table", "n_flagged", "n_rows_before", "n_rows_after", "kpi_name", "kpi_before", "kpi_after"]]), "",
          "_(Nhóm nhận xét 3–4 quy tắc có tác động lớn nhất; chi tiết điều kiện/lý do/hành động trong `reports/qa_report.csv`.)_", "",
          "## 4. KPI (tính sau QA)", ""]
    if (root / config["paths"]["processed"] / "kpi_catalog.csv").exists():
        md += [_table(pd.read_csv(root / config["paths"]["processed"] / "kpi_catalog.csv")), ""]
    for name, df in kpis.items():
        md += [f"### {name}", "", _table(df, 24), ""]
    md += ["## 5. Phân tích review bằng LLM", "",
           f"- Mô hình: `{config['llm'].get('model')}` (provider {config['llm'].get('provider')}), {config['llm'].get('batch_size')} review/lần gọi, temperature {config['llm'].get('temperature')}, "
           "đầu ra JSON theo schema (sentiment, language, aspects_positive/negative).",
           "- Mẫu: 1.000 review «Mẫu LLM» do giảng viên chỉ định; 100 review «Nhãn tay» nằm trong mẫu. "
           "_(Nhóm ghi cách 5 người chia nhau gán nhãn, cách giải quyết bất đồng.)_",
           "- Đối chứng không LLM: VADER + từ khoá khía cạnh + langdetect (`src/baseline.py`).", ""]
    if metrics is not None and not metrics.empty:
        md += ["### Kết quả chấm trên nhãn tay", "", _table(metrics), "", "Phân tích lỗi: `reports/llm_evaluation.md`, `reports/llm_errors.csv`.", ""]
    if cost is not None and not cost.empty:
        md += ["### Ước tính chi phí xử lý toàn bộ review của thành phố", "", _table(cost), ""]
    md += ["## 6. Hình", ""]
    md += [f"- `{p.relative_to(root) if p.is_relative_to(root) else p}`" for p in figures]
    md += ["", "## 7. Kết luận cho bên đặt hàng", "", "_(Nhóm viết 5–8 gạch đầu dòng: phát hiện chính theo vùng, theo thời gian, từ review; hạn chế của dữ liệu/mẫu.)_", ""]
    path = reports / "report_draft.md"
    path.write_text("\n".join(md), encoding="utf-8")
    LOGGER.info("Lưu bản nháp báo cáo -> %s", path)
    return path
