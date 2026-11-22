# 2627-LTXLDL-Airbnb-Melbourne

Bài tập lớn **Inside Airbnb** — môn Lập trình xử lý dữ liệu (UET.DSE2049), HK1 2026-2027.
Lớp UET.DSE2049 4 · Nhóm 2 · mã dữ liệu `DSE2049-C04-G02-melbourne` · **Melbourne, Australia (AUD)**.
Bên đặt hàng: **Chính quyền thành phố Melbourne** (cơ cấu cho thuê ngắn hạn theo vùng, xu hướng 4 quý, trải nghiệm khách).

Nguồn dữ liệu: [Inside Airbnb](https://insideairbnb.com/get-the-data/), giấy phép CC BY 4.0.
Bốn mốc chụp: `2025-09-12`, `2025-12-12`, `2026-03-21`, `2026-06-16`.

## 1. Cài đặt (máy sạch)

Python đúng phiên bản trong `.python-version` (đã chạy thử với **3.13.18**; 3.11–3.13 đều chạy được).

```bash
git clone <repo> && cd 2627-LTXLDL-Airbnb-Melbourne
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Khoá API cho bước LLM — đọc từ biến môi trường **`GEMINI_API_KEY`** (tên đặt tại `llm.api_key_env` trong configs):

```bash
export GEMINI_API_KEY=...
```

## 2. Chạy toàn bộ quy trình bằng một lệnh

```bash
python run_pipeline.py --config configs/melbourne.yaml
```

Lệnh này lần lượt: **tải** 12 tệp thô → **lọc** đúng 1.000 listing / 365.000 dòng calendar / 5.000 review mỗi mốc theo
danh sách ID được giao và **tự kiểm quota** → **QA** → trích **mẫu LLM** (1.000) và tệp **nhãn tay** (100) → **baseline**
→ gọi **Gemini** (có cache) → **đánh giá** trên nhãn tay → **ước tính chi phí** → **KPI** → **hình** → bản nháp báo cáo.

Tuỳ chọn:

| Cờ | Tác dụng |
|---|---|
| `--skip-llm` | không gọi API; dùng `data/processed/llm_cache.jsonl` sẵn có (đã commit) |
| `--skip-download` | không tải, dùng tệp đã có trong `data/raw/` |
| `--overwrite-hand-labels` | ghi lại `data/samples/hand_labeled_100.csv` — **mất nhãn đã điền**, chỉ dùng khi cần |
| `-v` | log chi tiết |

Đổi mốc/thành phố: chỉ sửa `configs/<city>.yaml` (mục `snapshots`, `data_root`, `quota`…), không sửa mã.
Tệp cấu hình mẫu cho thành phố khác: sao chép `configs/melbourne.yaml`, thay 4 mốc, tiền tệ, `data_root`, và hai tệp
phân công trong `data/samples/`.

### Smoke test không cần mạng / không cần khoá (≈ 5 giây)

```bash
python tests/make_fixtures.py --small              
python run_pipeline.py --config configs/_smoke_fixtures.yaml
```

Đầu ra của smoke test nằm trong `data/samples/fixtures/_out/` (gitignore). Bước LLM ở đây dùng `provider: mock`
(gán nhãn bằng baseline) — **không phải LLM thật**, chỉ để kiểm tra luồng chạy.

## 3. Tệp kết quả để đối chiếu

| Tệp | Nội dung |
|---|---|
| `data/processed/filtered_{listings,calendar,reviews}.csv.gz` | đúng phần dữ liệu của nhóm, 4 mốc, chưa QA |
| `data/processed/clean_listings.csv`, `clean_calendar.csv.gz`, `clean_reviews.csv`, `clean_reviews_unique.csv` | sau QA, có cột `flag_*`, `price_num`, `price_usable` |
| `reports/qa_report.csv` | mỗi quy tắc QA: tên → điều kiện → lý do → hành động, số dòng và KPI trước/sau |
| `data/processed/kpi_*.csv` + `kpi_catalog.csv` | 8 KPI (tên → mục tiêu → công thức → đơn vị) |
| `data/samples/llm_sample_1000.csv` | 1.000 review mẫu LLM (ID do giảng viên giao) |
| `data/samples/hand_labeled_100.csv` | 100 review nhãn tay (nhóm điền; xem `HUONG_DAN_GAN_NHAN.md`) |
| `data/processed/llm_results.csv`, `llm_cache.jsonl` | kết quả LLM có cấu trúc (sentiment, language, aspects ±) |
| `data/processed/baseline_results.csv` | đối chứng không LLM (VADER + từ khoá + langdetect) |
| `reports/llm_evaluation.{csv,md}`, `llm_errors.csv` | accuracy/F1 của LLM và baseline trên nhãn tay, ma trận nhầm lẫn, lỗi |
| `reports/llm_cost_estimate.csv` | chi phí nếu chạy hết review của thành phố |
| `figures/fig_*.png` | 9 hình: không gian (3), thời gian (3), LLM (3) |
| `reports/data_dictionary.md` | từ điển dữ liệu |
| `reports/report_draft.md` → `reports/report.pdf` | bản nháp tự sinh có số liệu → báo cáo kỹ thuật ≤ 10 trang |

## 4. Cấu trúc repo

```
configs/melbourne.yaml        # thành phố, 4 mốc, quota, tham số QA/KPI/LLM (không ghi cứng trong mã)
configs/_smoke_fixtures.yaml  # cấu hình smoke test trên dữ liệu giả
data/raw/                     # thô — KHÔNG commit (script tải sinh ra)
data/processed/               # sạch, kpi_*.csv, kết quả LLM (commit, < 50 MB)
data/samples/                 # assigned_listings.csv, assigned_reviews.csv, analysis_areas.csv,
                              # llm_sample_1000.csv, hand_labeled_100.csv, fixtures/ (dữ liệu giả)
src/download.py               # tải + lọc + kiểm quota             (Nguyễn Thế Đức)
src/qa.py                     # 23 quy tắc QA, qa_report.csv
src/kpi.py                    # hợp đồng dữ liệu + 8 KPI            (Trần Minh Đăng)
src/llm.py                    # mẫu LLM, nhãn tay, gọi Gemini, cache, chi phí (Nguyễn Nhật Minh)
src/baseline.py               # đối chứng không LLM
src/evaluate.py               # LLM vs baseline trên nhãn tay
src/viz.py                    # theme + 9 hình                       (Nguyễn Tiến Nam)
src/report.py                 # bản nháp báo cáo từ số liệu
tests/make_fixtures.py        # sinh dữ liệu giả để test
run_pipeline.py               # một lệnh chạy tất cả
AI_USAGE.md · .python-version · .env.example · requirements.txt
```

## 5. Bước LLM
- Mô hình mặc định `gemini-2.5-flash` (đổi ở `llm.model`), 20 review/lần gọi, JSON theo schema, temperature 0.
- Mỗi review xử lý xong được ghi ngay vào `data/processed/llm_cache.jsonl`; chạy lại chỉ gọi phần còn thiếu.
  Để **chạy lại thật từ đầu** với khoá khác: xoá `llm_cache.jsonl` (hoặc đổi `llm.cache` trong configs) rồi chạy không có `--skip-llm`.
- Gói miễn phí giới hạn số lần gọi/phút: mã tự chờ và thử lại khi gặp 429/5xx (`llm.max_retries`).
- 1.000 review ≈ 50 lần gọi; thời gian vài phút.
## 6. Sự cố thường gặp

| Hiện tượng | Xử lý |
|---|---|
| `404 — không có bản chụp …` | sai ngày mốc trong configs; đối chiếu sheet «Phân công» |
| `403` khi tải | Inside Airbnb chặn tạm; thử lại sau vài phút hoặc tải tay tệp vào `data/raw/<mốc>/` rồi chạy `--skip-download` |
| `Kiểm tra quota thất bại` | đọc danh sách lỗi: thường do tệp phân công sai nhóm, hoặc mốc tải nhầm |
| `Thiếu khoá API` | `export GEMINI_API_KEY=...` hoặc chạy `--skip-llm` |
| `429` lặp lại | hạ `llm.batch_size`, tăng `max_retries`, hoặc dùng `gemini-2.5-flash-lite` |
