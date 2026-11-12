# Inside Airbnb: Phân tích thị trường Melbourne
-Dự án bài tập lớn môn Lập trình xử lý dữ liệu (UET.DSE2049) học kỳ 1 năm học 2026–2027 của **Nhóm 02**.
-Mục tiêu của dự án là xây dựng quy trình có thể tái chạy để thu thập và phân tích dữ liệu Airbnb tại Melbourne, theo các khu vực và mốc thời gian. Thành phố, tiền tệ và các mốc snapshot được khai báo trong [`configs/melbourne.yaml`](configs/melbourne.yaml).
## Dữ liệu
-Dữ liệu được lấy từ [Inside Airbnb](https://insideairbnb.com/) theo giấy phép CC BY 4.0. Repo sử dụng bốn snapshot của Melbourne:
      | Snapshot | Ngày |

      | 1 | 2025-09-12 |
      | 2 | 2025-12-12 |
      | 3 | 2026-03-21 |
      | 4 | 2026-06-16 |
-Mỗi snapshot gồm `listings.csv.gz`, `calendar.csv.gz` và `reviews.csv.gz`. Quy trình sử dụng các tệp phân công trong `data/samples/` để lọc listing/review cần phân tích; `analysis_area` được gắn từ bảng phân công listing.
-Dữ liệu gốc được tải vào `data/raw/` và đã được loại khỏi Git bằng `.gitignore`. Vì vậy, lần chạy đầu tiên cần kết nối mạng để tải dữ liệu. Không commit dữ liệu thô lên repository. Khi sử dụng dữ liệu trong báo cáo, ghi rõ nguồn và ngày snapshot tương ứng.
## Yêu cầu môi trường
- Python 3.12.9 (theo `.python-version`)
- Git
- Kết nối Internet khi cần tải snapshot lần đầu
Các thư viện Python đã được ghim phiên bản trong [`requirements.txt`](requirements.txt).
## Cài đặt
```bash
git clone https://github.com/NotaChtholly/2627-LTXLDL-Airbnb-Nhom02.git
cd 2627-LTXLDL-Airbnb-Nhom02
```
Tạo môi trường ảo và cài thư viện:
**Windows PowerShell**
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```
**macOS / Linux**
```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```
## Chạy quy trình
-Từ thư mục gốc của repository, chạy toàn bộ các bước hiện có:
```bash
python run_pipeline.py --config configs/melbourne.yaml
```
-Lệnh trên tải các snapshot còn thiếu hoặc không hợp lệ, lọc dữ liệu theo các ID được phân công, kiểm tra quota và schema listing, sau đó tạo mẫu review LLM và tệp review để gán nhãn tay.
-Nếu các tệp dữ liệu gốc đã có trong `data/raw/`, có thể bỏ qua tải xuống:
```bash
python run_pipeline.py --config configs/melbourne.yaml --skip-download
```
-Có thể bỏ qua kiểm tra quota khi cần chạy riêng các bước còn lại:
```bash
python run_pipeline.py --config configs/melbourne.yaml --skip-validation
```
-Hai cờ `--skip-download` và `--skip-validation` có thể dùng đồng thời.
## Đầu ra hiện tại
- `data/raw/<ngày-snapshot>/`: dữ liệu Inside Airbnb đã tải; không được commit.
- `data/samples/llm_sample_1000.csv`: review nằm trong danh sách ID được phân công cho mẫu LLM.
- `data/samples/hand_labeled_100.csv`: mẫu review và các cột trống để ghi nhãn cảm xúc, khía cạnh và ngôn ngữ. Nếu tệp đã tồn tại, chương trình giữ nguyên để tránh ghi đè nhãn.
- `reports/qa_report.csv`: khung báo cáo QA có hàng tiêu đề.
- `docs/data_dictionary_sample.json`: từ điển dữ liệu mẫu được khởi tạo khi chạy pipeline.
## Cấu trúc repository
```text
.
├── configs/
│   └── melbourne.yaml          # Thành phố, snapshot, đường dẫn và tham số
├── data/
│   ├── raw/                    # Dữ liệu tải xuống; Git bỏ qua thư mục này
│   ├── processed/              # Dành cho dữ liệu đã xử lý
│   └── samples/                # ID được phân công và mẫu review
├── docs/
│   └── data_dictionary_sample.json
├── figures/                    # Nơi lưu biểu đồ
├── reports/                    # Báo cáo và qa_report.csv
├── src/
│   ├── download.py             # Tải snapshot, lọc theo ID, kiểm tra quota
│   ├── kpi.py                  # Kiểm tra schema và khởi tạo tài liệu dữ liệu
│   ├── llm.py                  # Trích mẫu review và tạo tệp gán nhãn
│   ├── qa.py                   # Dành cho các quy tắc QA
│   ├── baseline.py             # Dành cho phương pháp đối chứng
│   ├── evaluate.py             # Dành cho đánh giá kết quả
│   └── viz.py                  # Thiết lập giao diện biểu đồ và khung báo cáo
├── run_pipeline.py             # Điểm chạy pipeline
├── requirements.txt
├── .python-version
├── .env.example
└── AI_USAGE.md
```
## Phạm vi triển khai và các bước tiếp theo
-Ở bản hiên tại, pipeline đã có tải và kiểm tra tệp nguồn, lọc dữ liệu theo phân công, kiểm tra quota và schema, cùng bước chuẩn bị mẫu review. Cấu hình đã khai báo các nhóm KPI không gian và thời gian.
-Các bước theo yêu cầu bài tập cần tiếp tục hoàn thiện: áp dụng quy tắc QA và ghi tác động vào báo cáo, tính và xuất KPI; gọi LLM để phân tích review, xây dựng baseline và đánh giá trên nhãn tay, sinh biểu đồ và báo cáo PDF. `src/llm.py` hiện chỉ chuẩn bị dữ liệu mẫu, chưa gọi Gemini hay dịch vụ LLM khác. Chương trình cũng chưa tải hoặc xử lý tệp ranh giới GeoJSON. Do đó, lệnh chạy hiện tại chưa tạo các tệp KPI, biểu đồ hoặc báo cáo cuối cùng. Các đầu ra đó cần được bổ sung về sau.
## API key
-`.env.example` nêu tên biến `GEMINI_API_KEY` để dùng khi tích hợp Gemini. Mã nguồn hiện tại chưa đọc biến này và chưa gửi yêu cầu tới API, nên chưa cần API key để chạy pipeline đang có.
## Tham khảo
- [Đề bài lớn: Inside Airbnb](https://courses.iaidev.com/programming-for-data-processing/2627-1/projects/project_airbnb.html)
- [Inside Airbnb](https://insideairbnb.com/)
