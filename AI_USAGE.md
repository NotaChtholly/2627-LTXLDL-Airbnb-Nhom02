# Báo cáo minh bạch việc sử dụng AI

- Dự án: Quy trình phân tích thị trường Inside Airbnb Melbourne
- Môn học: Lập trình xử lý dữ liệu (UET.DSE2049), Học kỳ 1, năm học 2026–2027
- Nhóm: UET.DSE2049 4 – Nhóm 2
- Mã dữ liệu: `DSE2049-C04-G02-melbourne`
- Cách làm việc: Làm việc tại nhà, có sử dụng AI và nhóm tự kiểm tra lại kết quả
- Ước tính đóng góp chung: **Con người 55% – AI 45%**

Nhóm tự ước lượng tỷ lệ đóng góp chung là 55% từ các thành viên và 45% từ AI. Con số này không thể tính chính xác cho từng dòng mã, vì mỗi phần có mức độ hỗ trợ khác nhau. AI giúp gợi ý cú pháp và tạo bản nháp ban đầu; sau đó các thành viên xem lại, chạy thử và chỉnh cho phù hợp với dữ liệu cũng như yêu cầu của bài.

## 1. Nhóm đã dùng AI vào những việc nào

- **Hoàng Minh Anh Đức – tích hợp dự án (`run_pipeline.py`):** Nhóm dùng Claude 3.5 Sonnet và ChatGPT (GPT-4o) để tham khảo cấu trúc YAML, khung script chạy pipeline và cách nối các mô-đun. Thành viên thiết kế cấu trúc repository, chia nhánh Git, theo dõi quota và xử lý các lỗi khi ghép mã.
- **Nguyễn Thế Đức – tải, làm sạch và QA (`src/download.py`, `src/qa.py`):** ChatGPT và Gemini được dùng để tham khảo cách tải tệp `.csv.gz` theo luồng, đọc dữ liệu theo `chunksize=100_000`, xử lý giá AUD và viết các cờ QA `flag_*`. Thành viên kiểm tra dữ liệu thô Melbourne, nhận ra cột giá ở một số mốc bị rỗng và chốt các quy tắc QA cần dùng.
- **Trần Minh Đăng – KPI (`src/kpi.py`):** ChatGPT gợi ý cách dùng `groupby()` theo vùng và mốc, tính trung vị và phân vị (P25, P75). Thành viên xác định công thức KPI, chọn ngưỡng host nhiều căn (từ 2 listing trở lên) và kiểm tra lại số liệu. Ước tính: AI 40%, con người 60%.
- **Nguyễn Nhật Minh – trích xuất review bằng LLM (`src/llm.py`):** Nhóm dùng Gemini API (`gemini-3.5-flash-lite`) để trích xuất cảm xúc, 7 khía cạnh khen/chê và ngôn ngữ từ 1.000 review. AI cũng gợi ý JSON schema cho đầu ra (`response_schema`) và cách lưu cache. Thành viên thiết kế prompt, thống nhất danh sách khía cạnh, xử lý giới hạn gọi API và gán nhãn tay.
- **Nguyễn Tiến Nam – baseline và biểu đồ (`src/baseline.py`, `src/viz.py`):** ChatGPT và Claude gợi ý biểu thức chính quy cho baseline, cách cấu hình Seaborn/Matplotlib và một số đoạn mã vẽ biểu đồ. Thành viên chọn màu, sắp xếp bố cục, đối chiếu nhãn thủ công và xem biểu đồ có truyền tải đúng kết quả không. Ước tính: AI 45%, con người 55%.
- **Cả 5 thành viên – gán nhãn và kiểm tra:** Mỗi người tự gán nhãn 20 review trong `hand_labeled_100.csv` để làm bộ đối chiếu. Phần này nhóm thực hiện thủ công, không dùng AI gán nhãn.

Các tỷ lệ theo từng phần chỉ là ước lượng. Khi làm bài, nhóm thấy AI hữu ích nhất lúc cần tìm cú pháp hoặc dựng khung nhanh. Còn việc kiểm tra kết quả có hợp lý với dữ liệu và đề bài không thì nhóm vẫn phải tự làm. Từ đó, nhóm ước tính phần đóng góp chung của các thành viên khoảng 55%, AI khoảng 45%.

## 2. Một số prompt đã sử dụng

Dưới đây là một số prompt nhóm đã dùng để bắt đầu từng phần. Trong lúc làm, nhóm có hỏi lại và sửa prompt khi câu trả lời chưa đúng ý hoặc chưa khớp với dữ liệu.

- **Khởi tạo cấu hình (`configs/melbourne.yaml`) – Hoàng Minh Anh Đức:** “Tạo khung cấu hình YAML cho Melbourne, dùng AUD, có 4 mốc dữ liệu, 8 vùng A01-A08 và các quota listings, calendar, reviews, room_type, giá thiếu cùng danh sách 7 khía cạnh review.”
- **Tải và lọc dữ liệu (`src/download.py`) – Nguyễn Thế Đức:** “Gợi ý hàm tải các tệp `.csv.gz` bằng requests stream qua tệp tạm `.part`, sau đó lọc listings và reviews theo danh sách được phân công. Thêm kiểm tra quota và báo lỗi nếu số dòng không khớp.”
- **Làm sạch và QA (`src/qa.py`) – Nguyễn Thế Đức:** “Gợi ý cách chuẩn hóa cột price thành số AUD và tạo cờ QA cho giá hoặc review bị thiếu, giá không hợp lệ, ngoại lai theo ngưỡng giá, ID trùng và khóa ngoại không khớp. Xuất dữ liệu sạch và báo cáo QA.”
- **Tính KPI (`src/kpi.py`) – Trần Minh Đăng:** “Gợi ý các hàm tính giá trung vị theo 8 vùng, theo dõi biến động trên các mốc dữ liệu và tính chỉ số về multi-listing hosts.”
- **Trích xuất review (`src/llm.py`) – Nguyễn Nhật Minh:** “Gợi ý JSON schema cho sentiment, khía cạnh tích cực/tiêu cực và ISO language; thêm cache khi gọi Gemini API và cách xử lý khi bị giới hạn số lần gọi.”
- **Baseline (`src/baseline.py`) – Nguyễn Tiến Nam:** “Gợi ý cách dùng từ khóa và regex để phân loại cảm xúc cùng 7 khía cạnh tiếng Anh trên 1.000 review, không gọi LLM.”
- **Biểu đồ (`src/viz.py`) – Nguyễn Tiến Nam:** “Gợi ý cấu hình Seaborn/Matplotlib và hàm vẽ biểu đồ so sánh giá giữa các vùng, cùng tỷ lệ ngày không còn trống theo vùng qua các mốc.”
- **Điều phối pipeline (`run_pipeline.py`) – Hoàng Minh Anh Đức:** “Gợi ý script dùng argparse để chạy lần lượt các bước nạp cấu hình, tải dữ liệu, QA, KPI, trích xuất review và tạo biểu đồ; cho phép bỏ qua một số bước bằng tham số.”

## 3. Một số lỗi AI gợi ý và cách nhóm xử lý

Trong quá trình làm, có lúc mã AI gợi ý trông hợp lý nhưng chạy lên lại không đúng với dữ liệu hoặc cấu trúc dự án của nhóm. Nhóm phải chạy thử, xem lỗi ở đâu rồi tự sửa. Dưới đây là năm trường hợp cụ thể:

- **URL tải dữ liệu bị lặp đường dẫn (`src/download.py`):** Phần ghép `base_url` với `data_root` tạo URL có `data_root` hai lần, dẫn đến lỗi `403 Forbidden`. Trưởng nhóm kiểm tra URL thực tế và sửa logic để không nối lặp.
- **Đọc nhầm tệp gzip (`src/download.py`):** Tệp tạm có đuôi `.part` nên Pandas không tự nhận ra định dạng nén. Lần đầu đọc gây `UnicodeDecodeError`. Nhóm thêm `compression="gzip"` khi đọc.
- **Giả định sai về cột giá năm 2025 (`src/download.py`):** Điều kiện ban đầu yêu cầu các mốc cũ không có giá thiếu. Khi kiểm tra dữ liệu thô, nhóm thấy cột `price` ở các mốc năm 2025 rỗng. Nhóm chỉnh lại để chỉ kiểm tra quota 20 giá thiếu ở mốc cuối theo yêu cầu bài.
- **Chưa lọc đúng nhóm trong tệp phân công (`src/download.py`):** Tệp assignment có dữ liệu của nhiều nhóm. Nếu dùng tất cả, số lượng bản ghi bị tăng lên. Nhóm thêm bước lọc theo mã `DSE2049-C04-G02-melbourne` trước khi lấy ID.
- **Đọc sai tiêu đề và lấy mẫu ngẫu nhiên (`src/download.py`, `run_pipeline.py`):** Một gợi ý giả định CSV không có tiêu đề và dùng `.sample(1000)`. Việc đó có thể lấy sai cột hoặc sai review, trong khi bài đã chỉ định mẫu. Nhóm mở CSV để kiểm tra tiêu đề và lọc theo cờ `Mẫu LLM`, `Nhãn tay`.

## 4. Nhóm đã kiểm tra kết quả ra sao

- **Kiểm tra quota:** Nhóm dùng `validate_quotas` để so số lượng listings, calendar, reviews, tỷ lệ room type, số chỗ ở chưa có đánh giá, giá thiếu ở mốc cuối và số listings mỗi vùng. Nếu số liệu lệch, pipeline báo lỗi để nhóm kiểm tra lại.
- **Tạo nhãn tham chiếu bằng tay:** Cả 5 thành viên gán nhãn 100 review, mỗi người 20 câu theo một bộ hướng dẫn chung. Sau đó nhóm lấy bộ nhãn này để xem kết quả từ Gemini và baseline khớp đến đâu, dựa trên Accuracy, Precision, Recall và F1-score.
- **Chạy lại pipeline:** Trưởng nhóm thử chạy repository trong thư mục mới, tạo môi trường ảo và cài thư viện từ `requirements.txt`. Nhóm dùng lệnh `python run_pipeline.py --config configs/melbourne.yaml --skip-download` để kiểm tra các bước xử lý sau tải dữ liệu và đối chiếu các tệp đầu ra.
- **Chạy thử trên mẫu nhỏ:** Trước khi xử lý toàn bộ 1.000 review, nhóm chạy thử trên 20 câu để xem prompt có khiến mô hình tự thêm khía cạnh hay không. Sau đó nhóm điều chỉnh prompt và lưu kết quả vào cache.
- **Đọc lại mã và chuẩn bị vấn đáp:** Mỗi người đọc lại phần mã mình làm. Chỗ nào chưa chắc thì nhóm tra tài liệu hoặc hỏi nhau, nhất là về cách làm sạch dữ liệu, công thức KPI và phần trích xuất review để còn giải thích được khi vấn đáp.

