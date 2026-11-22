# Từ điển dữ liệu — Melbourne (AUD)

Nguồn: CC BY 4.0 — Inside Airbnb (https://insideairbnb.com/get-the-data/). Mốc chụp: 2025-09-12, 2025-12-12, 2026-03-21, 2026-06-16.

## `clean_listings.csv`

| Cột | Ý nghĩa |
|---|---|
| `snapshot` | Ngày chụp (YYYY-MM-DD) — thêm bởi pipeline |
| `id` | Mã listing (chuỗi) — khoá chính Inside Airbnb |
| `analysis_area` | Vùng A01..A08 theo sheet «Vùng» (gắn từ phân công, không gán lại) |
| `room_type` | Entire home/apt | Private room | Shared room | Hotel room |
| `price` | Giá gốc dạng chuỗi '$1,234.00' |
| `price_num` | Giá đã ép sang số (AUD/đêm); NaN nếu thiếu |
| `price_usable` | True nếu ở mốc cuối, có giá và không ngoại lai -> dùng cho KPI giá |
| `minimum_nights / minimum_nights_capped` | Số đêm tối thiểu gốc / đã chặn ở 365 |
| `calculated_host_listings_count` | Số listing của host trong toàn thành phố (Inside Airbnb tính) |
| `number_of_reviews, number_of_reviews_ltm` | Tổng review / review 12 tháng gần nhất |
| `availability_365, has_availability` | Số ngày còn trống trong 365 ngày tới; có mở lịch hay không |
| `flag_*` | Cờ QA (xem reports/qa_report.csv). True = dòng bị quy tắc tương ứng đánh dấu |

## `clean_calendar.csv.gz`

| Cột | Ý nghĩa |
|---|---|
| `snapshot, listing_id, date` | Mốc, listing, ngày (365 ngày kể từ mốc) |
| `available` | 't' còn trống, 'f' đã đặt hoặc chủ đóng lịch |
| `price_num` | Giá ngày đã ép số |
| `flag_*` | Cờ QA |

## `clean_reviews.csv / clean_reviews_unique.csv`

| Cột | Ý nghĩa |
|---|---|
| `id` | Mã review |
| `listing_id` | Listing được review |
| `date` | Ngày review |
| `comments` | Văn bản review |
| `llm_sample` | 1 nếu thuộc 1.000 review mẫu LLM (phân công) |
| `hand_label` | 1 nếu thuộc 100 review gán nhãn tay |
| `analysis_area` | Vùng của listing |
| `flag_*` | Cờ QA |
| `(unique)` | Mỗi id một dòng (lấy mốc mới nhất) — đầu vào bước LLM |

## `llm_results.csv`

| Cột | Ý nghĩa |
|---|---|
| `review_id` | Mã review |
| `sentiment` | positive | mixed | negative |
| `language` | mã ISO 639-1 (en, fr, zh, ...) |
| `aspects_positive / aspects_negative` | các khía cạnh khen / chê, nối bằng '|' (location, cleanliness, host, value, amenities, noise, safety) |
| `model` | tên mô hình đã dùng |
| `prompt_tokens / output_tokens` | token dùng cho lô chứa review này (chia đều theo lô) |

## `kpi_*.csv`

| Cột | Ý nghĩa |
|---|---|
| `kpi_active_listings` | Đo quy mô cho thuê ngắn hạn còn 'sống' ở từng vùng, theo dõi theo mốc — active = has_availability=='t' và availability_365>0; share = n_active / n_listing (theo snapshot, analysis_area) — đơn vị: listing; % |
| `kpi_entire_home_share` | Ước lượng nhà nguyên căn bị rút khỏi thị trường thuê dài hạn — n(room_type=='Entire home/apt') / n_listing (theo snapshot, analysis_area) — đơn vị: % |
| `kpi_multi_host_share` | Phát hiện vận hành thương mại (host nhiều nhà) thay vì chia sẻ nhà — n(calculated_host_listings_count >= 2) / n_listing có host_id (theo snapshot, analysis_area) — đơn vị: % |
| `kpi_short_stay_share` | Tỉ lệ listing thuộc diện lưu trú ngắn hạn (đối tượng thuế/quy định của Victoria) — n(minimum_nights <= 7, loại flag_min_nights_outlier) / n_listing (theo snapshot, analysis_area) — đơn vị: % |
| `kpi_occupancy_90d` | Sức khoẻ cầu du lịch: tỉ lệ ngày đã đặt/đóng trong 90 ngày tới — n(available=='f', date trong [mốc, mốc+90)) / n_ngày (calendar; theo snapshot, analysis_area) — đơn vị: % |
| `kpi_review_velocity` | Nhịp khách thực tế (review 12 tháng gần nhất) để so với công suất — mean(number_of_reviews_ltm) (theo snapshot, analysis_area) — đơn vị: review/listing/năm |
| `kpi_median_price` | Mặt bằng giá đêm theo vùng và loại phòng cho đối chiếu với giá thuê dài hạn — median(price_num) với price_usable (mốc cuối, loại thiếu giá & ngoại lai) theo analysis_area × room_type; kèm p25/p75 và giá/người — đơn vị: AUD/đêm (tiền tệ theo configs.currency) |
| `kpi_llm_sentiment` | Trải nghiệm khách theo vùng từ văn bản review (LLM) và khía cạnh bị chê nhiều nhất — share_positive = n(sentiment=='positive') / n_review_LLM theo analysis_area; kpi_llm_aspects = đếm khía cạnh khen/chê theo vùng — đơn vị: %; lượt nhắc |
