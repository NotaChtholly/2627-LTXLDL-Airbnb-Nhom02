# Báo cáo kỹ thuật — Thị trường Airbnb Melbourne (bản nháp tự sinh)

Môn Lập trình xử lý dữ liệu (UET.DSE2049) · Nhóm DSE2049-C04-G02-melbourne · mã commit: `d09471f`

## 1. Bối cảnh và bên đặt hàng

**Bên đặt hàng: Chính quyền thành phố Melbourne.** Câu hỏi đặt ra: cho thuê ngắn hạn tập trung ở đâu, bao nhiêu phần là nhà nguyên căn và host thương mại (nhiều nhà), xu hướng công suất và giá qua 4 quý, và khách phàn nàn điều gì (từ review). Nhóm chọn chính quyền thành phố vì đây là bên chịu tác động trực tiếp của lưu trú ngắn hạn đối với nhà ở và cộng đồng trong địa bàn, đồng thời cần căn cứ dữ liệu để kiến nghị hoặc thực thi các quy định liên quan (như quy định và thuế lưu trú ngắn hạn của bang Victoria được nhắc ở KPI mục 4). Mối quan tâm của họ khớp với những gì dữ liệu Inside Airbnb đo được: loại phòng, số nhà do cùng một host vận hành, công suất qua lịch đặt phòng và phản hồi của khách trong review. Chủ nhà hay nền tảng thường chỉ cần tối ưu từng listing, còn chính quyền cần nhìn cả thành phố theo từng vùng và theo thời gian để quyết định nơi nào cần giám sát, điều mà 4 mốc chụp cho phép làm. Bên đặt hàng này cũng cần số liệu có thể kiểm chứng, nên nhóm ghi lại từng quy tắc QA và định nghĩa từng KPI ở các mục sau để truy ra được mỗi con số đến từ đâu.

## 2. Dữ liệu

- Nguồn: CC BY 4.0 — Inside Airbnb (https://insideairbnb.com/get-the-data/). Đường dẫn: `https://data.insideairbnb.com/australia/vic/melbourne/<mốc>/data/`
- Bốn mốc chụp: 2025-09-12, 2025-12-12, 2026-03-21, 2026-06-16. Tiền tệ: AUD.
- Phần dữ liệu của nhóm (lọc theo danh sách ID được giao): 1000 listing × 4 mốc = 4000 dòng listings; 1460000 dòng calendar; 20000 dòng reviews (5000 review duy nhất).
- Cấu trúc tệp và kiểu dữ liệu: xem `reports/data_dictionary.md`. Điểm lạ của từng bản chụp: xem cột `note`/`n_flagged` trong QA.

## 3. QA (tên → điều kiện → lý do → hành động) và tác động

| rule_id | rule_name | table | n_flagged | n_rows_before | n_rows_after | kpi_name | kpi_before | kpi_after |
|---|---|---|---|---|---|---|---|---|
| L01 | type_cast_numeric_dates | listings | 0 | 4000 | 4000 | n_ô_không_ép_được | 0 | 0 |
| L02 | duplicate_within_snapshot | listings | 0 | 4000 | 4000 | n_listing_mốc_cuối | 1000 | 1000 |
| L03 | listing_missing_across_snapshots | listings | 0 | 4000 | 4000 | n_id_thiếu_mốc | 0 | 0 |
| L04 | missing_price_last_snapshot | listings | 20 | 4000 | 4000 | median_price_mốc_cuối | 266.0 | 266.0 |
| L05 | price_outlier | listings | 2 | 4000 | 4000 | mean_price_mốc_cuối | 336.6156 | 317.8279 |
| L06 | min_nights_outlier | listings | 0 | 4000 | 4000 | tỉ_lệ_listing_ngắn_ngày | 0.99 | 0.99 |
| L07 | accommodates_outlier | listings | 0 | 4000 | 4000 |  |  |  |
| L08 | missing_coordinates | listings | 0 | 4000 | 4000 |  |  |  |
| L09 | coords_outside_assigned_area | listings | 0 | 4000 | 4000 | n_listing_A01_mốc_cuối | 120 | 120 |
| L10 | room_type_unknown | listings | 0 | 4000 | 4000 |  |  |  |
| L11 | neighbourhood_changed_across_snapshots | listings | 0 | 4000 | 4000 |  |  |  |
| L12 | missing_host_id | listings | 0 | 4000 | 4000 |  |  |  |
| C01 | unparseable_date | calendar | 0 | 1460000 | 1460000 |  |  |  |
| C02 | available_not_t_f | calendar | 0 | 1460000 | 1460000 |  |  |  |
| C03 | duplicate_listing_day | calendar | 0 | 1460000 | 1460000 | tỉ_lệ_ngày_không_trống | 0.4191 | 0.4191 |
| C04 | date_outside_365_window | calendar | 312 | 1460000 | 1460000 |  |  |  |
| C05 | missing_calendar_price | calendar | 1460000 | 1460000 | 1460000 |  |  |  |
| R01 | type_cast_date_text | reviews | 0 | 20000 | 20000 |  |  |  |
| R02 | duplicate_within_snapshot | reviews | 0 | 20000 | 20000 |  |  |  |
| R03 | duplicate_across_snapshots | reviews | 20000 | 20000 | 20000 | n_review_để_phân_tích | 20000 | 5000 |
| R04 | empty_or_too_short_comment | reviews_unique | 0 | 5000 | 5000 |  |  |  |
| R05 | review_listing_not_assigned | reviews_unique | 0 | 5000 | 5000 |  |  |  |
| R06 | review_date_after_snapshot | reviews_unique | 0 | 5000 | 5000 |  |  |  |

Nhận xét: không quy tắc nào làm thay đổi số dòng và 18/23 quy tắc không bắt được dòng nào, nên dữ liệu nguồn khá sạch và tác động của QA thể hiện chủ yếu ở KPI chứ không ở số dòng. Bốn quy tắc có tác động lớn nhất (theo thứ tự tên → điều kiện → lý do → hành động → tác động):

- **R03 `duplicate_across_snapshots` (reviews).** Điều kiện: cùng `id` review xuất hiện ở nhiều mốc. Lý do: đề thiết kế 5000 review lặp lại ở 4 mốc, nếu đếm theo mốc sẽ nhân 4 và phải gọi LLM 4 lần cho cùng một review. Hành động: giữ bảng theo mốc, tạo thêm `reviews_unique` (1 bản/id, lấy mốc mới nhất) cho LLM và KPI văn bản. Tác động: lớn nhất, cả 20000 dòng bị gắn cờ và số review cần phân tích giảm từ 20000 xuống 5000 (−75%).
- **C05 `missing_calendar_price` (calendar).** Điều kiện: `price` rỗng. Lý do: giá theo ngày dùng để tham chiếu mùa vụ, thiếu thì không đưa vào trung bình giá theo ngày. Hành động: gắn cờ, không xoá, vẫn tính công suất. Tác động: 1460000/1460000 dòng (100%) thiếu giá, nên calendar không dùng được để xem giá theo mùa vụ; công suất không bị ảnh hưởng, còn các KPI giá phải lấy từ cột `price` của listings ở mốc cuối (xem L04, L05).
- **L05 `price_outlier` (listings).** Điều kiện: `price_num` < 10 hoặc > 5000 AUD/đêm ở mốc cuối. Lý do: giá nhập nhầm kéo lệch giá trung bình. Hành động: gắn cờ, loại khỏi KPI giá. Tác động: chỉ 2 listing bị gắn cờ nhưng giá trung bình mốc cuối giảm từ 336.6156 xuống 317.8279 (−5.6%), trong khi trung vị gần như không đổi (266.0 → 265.75); vì vậy KPI giá dùng trung vị kèm p25/p75 thay cho trung bình.
- **L04 `missing_price_last_snapshot` (listings).** Điều kiện: snapshot là 2026-06-16 và `price` rỗng. Lý do: KPI giá chỉ dùng mốc cuối, listing thiếu giá không vào mẫu giá. Hành động: gắn cờ, loại khỏi KPI giá nhưng giữ trong KPI đếm. Tác động: 20 listing (2% mẫu mốc cuối) bị loại; cùng với L05, mẫu giá còn 978/1000 listing. Trung vị không đổi (266.0 → 266.0), nên tác động chính là thu hẹp cỡ mẫu chứ không làm lệch mức giá.

Các quy tắc còn lại có tác động nhỏ (ví dụ C04 chỉ gắn cờ 312/1460000 dòng calendar nằm ngoài cửa sổ 365 ngày, khoảng 0.02%). Chi tiết điều kiện/lý do/hành động của cả 23 quy tắc nằm trong `reports/qa_report.csv`.

## 4. KPI (tính sau QA)

| kpi | goal | formula | unit | dimension |
|---|---|---|---|---|
| kpi_active_listings | Đo quy mô cho thuê ngắn hạn còn 'sống' ở từng vùng, theo dõi theo mốc | active = has_availability=='t' và availability_365>0; share = n_active / n_listing (theo snapshot, analysis_area) | listing; % | vùng × thời gian |
| kpi_entire_home_share | Ước lượng nhà nguyên căn bị rút khỏi thị trường thuê dài hạn | n(room_type=='Entire home/apt') / n_listing (theo snapshot, analysis_area) | % | vùng × thời gian |
| kpi_multi_host_share | Phát hiện vận hành thương mại (host nhiều nhà) thay vì chia sẻ nhà | n(calculated_host_listings_count >= 2) / n_listing có host_id (theo snapshot, analysis_area) | % | vùng × thời gian |
| kpi_short_stay_share | Tỉ lệ listing thuộc diện lưu trú ngắn hạn (đối tượng thuế/quy định của Victoria) | n(minimum_nights <= 7, loại flag_min_nights_outlier) / n_listing (theo snapshot, analysis_area) | % | vùng × thời gian |
| kpi_occupancy_90d | Sức khoẻ cầu du lịch: tỉ lệ ngày đã đặt/đóng trong 90 ngày tới | n(available=='f', date trong [mốc, mốc+90)) / n_ngày (calendar; theo snapshot, analysis_area) | % | vùng × thời gian |
| kpi_review_velocity | Nhịp khách thực tế (review 12 tháng gần nhất) để so với công suất | mean(number_of_reviews_ltm) (theo snapshot, analysis_area) | review/listing/năm | vùng × thời gian |
| kpi_median_price | Mặt bằng giá đêm theo vùng và loại phòng cho đối chiếu với giá thuê dài hạn | median(price_num) với price_usable (mốc cuối, loại thiếu giá & ngoại lai) theo analysis_area × room_type; kèm p25/p75 và giá/người | AUD/đêm (tiền tệ theo configs.currency) | vùng (chỉ mốc cuối) |
| kpi_llm_sentiment | Trải nghiệm khách theo vùng từ văn bản review (LLM) và khía cạnh bị chê nhiều nhất | share_positive = n(sentiment=='positive') / n_review_LLM theo analysis_area; kpi_llm_aspects = đếm khía cạnh khen/chê theo vùng | %; lượt nhắc | vùng (dùng LLM) |

### kpi_active_listings

| snapshot | analysis_area | n_listing | n_active | active_share_pct |
|---|---|---|---|---|
| 2025-09-12 | A01 | 120 | 119 | 99.17 |
| 2025-09-12 | A02 | 120 | 113 | 94.17 |
| 2025-09-12 | A03 | 127 | 125 | 98.43 |
| 2025-09-12 | A04 | 130 | 126 | 96.92 |
| 2025-09-12 | A05 | 130 | 126 | 96.92 |
| 2025-09-12 | A06 | 120 | 120 | 100.0 |
| 2025-09-12 | A07 | 130 | 125 | 96.15 |
| 2025-09-12 | A08 | 123 | 122 | 99.19 |
| 2025-12-12 | A01 | 120 | 120 | 100.0 |
| 2025-12-12 | A02 | 120 | 117 | 97.5 |
| 2025-12-12 | A03 | 127 | 124 | 97.64 |
| 2025-12-12 | A04 | 130 | 129 | 99.23 |
| 2025-12-12 | A05 | 130 | 130 | 100.0 |
| 2025-12-12 | A06 | 120 | 120 | 100.0 |
| 2025-12-12 | A07 | 130 | 127 | 97.69 |
| 2025-12-12 | A08 | 123 | 120 | 97.56 |
| 2026-03-21 | A01 | 120 | 120 | 100.0 |
| 2026-03-21 | A02 | 120 | 119 | 99.17 |
| 2026-03-21 | A03 | 127 | 127 | 100.0 |
| 2026-03-21 | A04 | 130 | 130 | 100.0 |
| 2026-03-21 | A05 | 130 | 130 | 100.0 |
| 2026-03-21 | A06 | 120 | 120 | 100.0 |
| 2026-03-21 | A07 | 130 | 130 | 100.0 |
| 2026-03-21 | A08 | 123 | 123 | 100.0 |
| … (8 dòng nữa) |

### kpi_entire_home_share

| snapshot | analysis_area | n_listing | n_entire | entire_home_share_pct |
|---|---|---|---|---|
| 2025-09-12 | A01 | 120 | 107 | 89.17 |
| 2025-09-12 | A02 | 120 | 115 | 95.83 |
| 2025-09-12 | A03 | 127 | 99 | 77.95 |
| 2025-09-12 | A04 | 130 | 115 | 88.46 |
| 2025-09-12 | A05 | 130 | 126 | 96.92 |
| 2025-09-12 | A06 | 120 | 99 | 82.5 |
| 2025-09-12 | A07 | 130 | 117 | 90.0 |
| 2025-09-12 | A08 | 123 | 97 | 78.86 |
| 2025-12-12 | A01 | 120 | 107 | 89.17 |
| 2025-12-12 | A02 | 120 | 115 | 95.83 |
| 2025-12-12 | A03 | 127 | 99 | 77.95 |
| 2025-12-12 | A04 | 130 | 115 | 88.46 |
| 2025-12-12 | A05 | 130 | 126 | 96.92 |
| 2025-12-12 | A06 | 120 | 99 | 82.5 |
| 2025-12-12 | A07 | 130 | 117 | 90.0 |
| 2025-12-12 | A08 | 123 | 97 | 78.86 |
| 2026-03-21 | A01 | 120 | 107 | 89.17 |
| 2026-03-21 | A02 | 120 | 115 | 95.83 |
| 2026-03-21 | A03 | 127 | 99 | 77.95 |
| 2026-03-21 | A04 | 130 | 115 | 88.46 |
| 2026-03-21 | A05 | 130 | 126 | 96.92 |
| 2026-03-21 | A06 | 120 | 99 | 82.5 |
| 2026-03-21 | A07 | 130 | 117 | 90.0 |
| 2026-03-21 | A08 | 123 | 97 | 78.86 |
| … (8 dòng nữa) |

### kpi_multi_host_share

| snapshot | analysis_area | n_listing | n_multi_host_listing | n_host | multi_host_share_pct |
|---|---|---|---|---|---|
| 2025-09-12 | A01 | 120 | 96 | 100 | 80.0 |
| 2025-09-12 | A02 | 120 | 88 | 104 | 73.33 |
| 2025-09-12 | A03 | 127 | 71 | 116 | 55.91 |
| 2025-09-12 | A04 | 130 | 106 | 76 | 81.54 |
| 2025-09-12 | A05 | 130 | 79 | 120 | 60.77 |
| 2025-09-12 | A06 | 120 | 72 | 110 | 60.0 |
| 2025-09-12 | A07 | 130 | 77 | 116 | 59.23 |
| 2025-09-12 | A08 | 123 | 50 | 115 | 40.65 |
| 2025-12-12 | A01 | 120 | 100 | 99 | 83.33 |
| 2025-12-12 | A02 | 120 | 89 | 104 | 74.17 |
| 2025-12-12 | A03 | 127 | 73 | 116 | 57.48 |
| 2025-12-12 | A04 | 130 | 106 | 76 | 81.54 |
| 2025-12-12 | A05 | 130 | 80 | 120 | 61.54 |
| 2025-12-12 | A06 | 120 | 71 | 110 | 59.17 |
| 2025-12-12 | A07 | 130 | 75 | 116 | 57.69 |
| 2025-12-12 | A08 | 123 | 51 | 115 | 41.46 |
| 2026-03-21 | A01 | 120 | 99 | 99 | 82.5 |
| 2026-03-21 | A02 | 120 | 86 | 104 | 71.67 |
| 2026-03-21 | A03 | 127 | 72 | 116 | 56.69 |
| 2026-03-21 | A04 | 130 | 106 | 77 | 81.54 |
| 2026-03-21 | A05 | 130 | 76 | 120 | 58.46 |
| 2026-03-21 | A06 | 120 | 72 | 110 | 60.0 |
| 2026-03-21 | A07 | 130 | 74 | 116 | 56.92 |
| 2026-03-21 | A08 | 123 | 49 | 115 | 39.84 |
| … (8 dòng nữa) |

### kpi_short_stay_share

| snapshot | analysis_area | n_listing | n_short_stay | short_stay_share_pct |
|---|---|---|---|---|
| 2025-09-12 | A01 | 120 | 118 | 98.33 |
| 2025-09-12 | A02 | 120 | 117 | 97.5 |
| 2025-09-12 | A03 | 127 | 124 | 97.64 |
| 2025-09-12 | A04 | 130 | 130 | 100.0 |
| 2025-09-12 | A05 | 130 | 129 | 99.23 |
| 2025-09-12 | A06 | 120 | 114 | 95.0 |
| 2025-09-12 | A07 | 130 | 127 | 97.69 |
| 2025-09-12 | A08 | 123 | 123 | 100.0 |
| 2025-12-12 | A01 | 120 | 118 | 98.33 |
| 2025-12-12 | A02 | 120 | 118 | 98.33 |
| 2025-12-12 | A03 | 127 | 125 | 98.43 |
| 2025-12-12 | A04 | 130 | 130 | 100.0 |
| 2025-12-12 | A05 | 130 | 128 | 98.46 |
| 2025-12-12 | A06 | 120 | 115 | 95.83 |
| 2025-12-12 | A07 | 130 | 128 | 98.46 |
| 2025-12-12 | A08 | 123 | 123 | 100.0 |
| 2026-03-21 | A01 | 120 | 120 | 100.0 |
| 2026-03-21 | A02 | 120 | 120 | 100.0 |
| 2026-03-21 | A03 | 127 | 127 | 100.0 |
| 2026-03-21 | A04 | 130 | 130 | 100.0 |
| 2026-03-21 | A05 | 130 | 130 | 100.0 |
| 2026-03-21 | A06 | 120 | 120 | 100.0 |
| 2026-03-21 | A07 | 130 | 130 | 100.0 |
| 2026-03-21 | A08 | 123 | 123 | 100.0 |
| … (8 dòng nữa) |

### kpi_occupancy_90d

| snapshot | analysis_area | n_days | n_booked | n_listing | occupancy_pct |
|---|---|---|---|---|---|
| 2025-09-12 | A01 | 10800 | 4035 | 120 | 37.36 |
| 2025-09-12 | A02 | 10800 | 4902 | 120 | 45.39 |
| 2025-09-12 | A03 | 11430 | 4456 | 127 | 38.99 |
| 2025-09-12 | A04 | 11700 | 4421 | 130 | 37.79 |
| 2025-09-12 | A05 | 11700 | 5010 | 130 | 42.82 |
| 2025-09-12 | A06 | 10800 | 3286 | 120 | 30.43 |
| 2025-09-12 | A07 | 11700 | 5443 | 130 | 46.52 |
| 2025-09-12 | A08 | 11070 | 3770 | 123 | 34.06 |
| 2025-12-12 | A01 | 10731 | 4095 | 120 | 38.16 |
| 2025-12-12 | A02 | 10700 | 4821 | 120 | 45.06 |
| 2025-12-12 | A03 | 11404 | 5216 | 127 | 45.74 |
| 2025-12-12 | A04 | 11588 | 4809 | 130 | 41.5 |
| 2025-12-12 | A05 | 11661 | 5849 | 130 | 50.16 |
| 2025-12-12 | A06 | 10794 | 4284 | 120 | 39.69 |
| 2025-12-12 | A07 | 11662 | 6289 | 130 | 53.93 |
| 2025-12-12 | A08 | 11066 | 4583 | 123 | 41.42 |
| 2026-03-21 | A01 | 10800 | 3190 | 120 | 29.54 |
| 2026-03-21 | A02 | 10800 | 4137 | 120 | 38.31 |
| 2026-03-21 | A03 | 11430 | 4100 | 127 | 35.87 |
| 2026-03-21 | A04 | 11700 | 3242 | 130 | 27.71 |
| 2026-03-21 | A05 | 11700 | 3764 | 130 | 32.17 |
| 2026-03-21 | A06 | 10800 | 3342 | 120 | 30.94 |
| 2026-03-21 | A07 | 11700 | 4398 | 130 | 37.59 |
| 2026-03-21 | A08 | 11070 | 3309 | 123 | 29.89 |
| … (8 dòng nữa) |

### kpi_review_velocity

| snapshot | analysis_area | n_listing | reviews_ltm_mean | reviews_ltm_median | share_with_review_pct |
|---|---|---|---|---|---|
| 2025-09-12 | A01 | 120 | 20.85 | 12.5 | 93.33 |
| 2025-09-12 | A02 | 120 | 26.48 | 17.0 | 96.67 |
| 2025-09-12 | A03 | 127 | 17.35 | 9.0 | 92.13 |
| 2025-09-12 | A04 | 130 | 20.12 | 13.0 | 94.62 |
| 2025-09-12 | A05 | 130 | 13.2 | 9.0 | 94.62 |
| 2025-09-12 | A06 | 120 | 11.04 | 7.0 | 95.83 |
| 2025-09-12 | A07 | 130 | 18.22 | 12.0 | 97.69 |
| 2025-09-12 | A08 | 123 | 13.44 | 10.0 | 95.12 |
| 2025-12-12 | A01 | 120 | 21.12 | 15.0 | 99.17 |
| 2025-12-12 | A02 | 120 | 27.42 | 16.5 | 97.5 |
| 2025-12-12 | A03 | 127 | 18.94 | 10.0 | 92.91 |
| 2025-12-12 | A04 | 130 | 20.78 | 14.5 | 96.92 |
| 2025-12-12 | A05 | 130 | 13.31 | 10.0 | 96.15 |
| 2025-12-12 | A06 | 120 | 11.78 | 7.0 | 99.17 |
| 2025-12-12 | A07 | 130 | 18.52 | 13.0 | 97.69 |
| 2025-12-12 | A08 | 123 | 14.15 | 10.0 | 96.75 |
| 2026-03-21 | A01 | 120 | 21.58 | 14.0 | 99.17 |
| 2026-03-21 | A02 | 120 | 28.38 | 18.5 | 98.33 |
| 2026-03-21 | A03 | 127 | 19.78 | 10.0 | 94.49 |
| 2026-03-21 | A04 | 130 | 21.15 | 15.0 | 97.69 |
| 2026-03-21 | A05 | 130 | 13.25 | 9.5 | 96.92 |
| 2026-03-21 | A06 | 120 | 11.78 | 8.0 | 99.17 |
| 2026-03-21 | A07 | 130 | 19.14 | 14.5 | 97.69 |
| 2026-03-21 | A08 | 123 | 14.33 | 11.0 | 96.75 |
| … (8 dòng nữa) |

### kpi_median_price

| snapshot | analysis_area | room_type | n_listing | price_median | price_p25 | price_p75 | price_per_person_median | currency |
|---|---|---|---|---|---|---|---|---|
| 2026-06-16 | A01 | Entire home/apt | 106 | 277.52 | 232.01 | 345.0 | 68.0 | AUD |
| 2026-06-16 | A01 | Private room | 13 | 115.9 | 76.08 | 162.0 | 63.0 | AUD |
| 2026-06-16 | A02 | Entire home/apt | 110 | 305.15 | 231.31 | 400.62 | 74.71 | AUD |
| 2026-06-16 | A02 | Private room | 5 | 108.5 | 105.0 | 122.0 | 105.0 | AUD |
| 2026-06-16 | A03 | Entire home/apt | 95 | 278.67 | 185.5 | 380.5 | 61.48 | AUD |
| 2026-06-16 | A03 | Private room | 28 | 87.84 | 74.0 | 138.0 | 50.25 | AUD |
| 2026-06-16 | A04 | Entire home/apt | 115 | 228.0 | 177.38 | 308.0 | 63.5 | AUD |
| 2026-06-16 | A04 | Private room | 15 | 119.0 | 99.03 | 135.25 | 78.0 | AUD |
| 2026-06-16 | A05 | Entire home/apt | 120 | 282.75 | 229.0 | 411.38 | 83.96 | AUD |
| 2026-06-16 | A05 | Private room | 4 | 86.14 | 77.38 | 148.62 | 62.76 | AUD |
| 2026-06-16 | A06 | Entire home/apt | 95 | 313.0 | 244.5 | 392.14 | 69.0 | AUD |
| 2026-06-16 | A06 | Private room | 21 | 116.0 | 92.0 | 160.0 | 65.75 | AUD |
| 2026-06-16 | A07 | Entire home/apt | 116 | 286.0 | 203.12 | 380.53 | 84.88 | AUD |
| 2026-06-16 | A07 | Private room | 13 | 111.33 | 82.0 | 122.67 | 61.34 | AUD |
| 2026-06-16 | A08 | Entire home/apt | 96 | 294.0 | 230.83 | 475.5 | 71.33 | AUD |
| 2026-06-16 | A08 | Private room | 26 | 112.65 | 82.0 | 144.5 | 68.33 | AUD |
| 2026-06-16 | A01 | ALL | 119 | 269.0 | 212.16 | 337.93 | 68.0 | AUD |
| 2026-06-16 | A02 | ALL | 115 | 298.0 | 219.06 | 400.25 | 76.08 | AUD |
| 2026-06-16 | A03 | ALL | 123 | 217.19 | 158.6 | 339.05 | 60.62 | AUD |
| 2026-06-16 | A04 | ALL | 130 | 217.36 | 156.0 | 295.15 | 64.84 | AUD |
| 2026-06-16 | A05 | ALL | 124 | 278.66 | 227.62 | 405.25 | 82.34 | AUD |
| 2026-06-16 | A06 | ALL | 116 | 285.44 | 198.38 | 375.3 | 68.97 | AUD |
| 2026-06-16 | A07 | ALL | 129 | 251.5 | 184.5 | 354.5 | 80.0 | AUD |
| 2026-06-16 | A08 | ALL | 122 | 262.0 | 169.95 | 390.62 | 71.08 | AUD |

### kpi_llm_sentiment

| snapshot | analysis_area | n_review_llm | n_positive | n_mixed | n_negative | positive_share_pct | negative_share_pct |
|---|---|---|---|---|---|---|---|
| 2026-06-16 | A01 | 107 | 87 | 16 | 4 | 81.31 | 3.74 |
| 2026-06-16 | A02 | 166 | 134 | 30 | 2 | 80.72 | 1.2 |
| 2026-06-16 | A03 | 89 | 81 | 7 | 1 | 91.01 | 1.12 |
| 2026-06-16 | A04 | 125 | 107 | 17 | 1 | 85.6 | 0.8 |
| 2026-06-16 | A05 | 119 | 110 | 9 | 0 | 92.44 | 0.0 |
| 2026-06-16 | A06 | 92 | 84 | 8 | 0 | 91.3 | 0.0 |
| 2026-06-16 | A07 | 175 | 160 | 15 | 0 | 91.43 | 0.0 |
| 2026-06-16 | A08 | 127 | 119 | 8 | 0 | 93.7 | 0.0 |

### kpi_llm_aspects

| snapshot | analysis_area | aspect | polarity | mentions |
|---|---|---|---|---|
| 2026-06-16 | A01 | amenities | negative | 18 |
| 2026-06-16 | A01 | amenities | positive | 65 |
| 2026-06-16 | A01 | cleanliness | negative | 7 |
| 2026-06-16 | A01 | cleanliness | positive | 42 |
| 2026-06-16 | A01 | host | negative | 3 |
| 2026-06-16 | A01 | host | positive | 58 |
| 2026-06-16 | A01 | location | positive | 75 |
| 2026-06-16 | A01 | noise | negative | 1 |
| 2026-06-16 | A01 | noise | positive | 7 |
| 2026-06-16 | A01 | safety | negative | 1 |
| 2026-06-16 | A01 | safety | positive | 1 |
| 2026-06-16 | A01 | value | negative | 2 |
| 2026-06-16 | A01 | value | positive | 6 |
| 2026-06-16 | A02 | amenities | negative | 15 |
| 2026-06-16 | A02 | amenities | positive | 118 |
| 2026-06-16 | A02 | cleanliness | negative | 14 |
| 2026-06-16 | A02 | cleanliness | positive | 52 |
| 2026-06-16 | A02 | host | negative | 3 |
| 2026-06-16 | A02 | host | positive | 106 |
| 2026-06-16 | A02 | location | negative | 3 |
| 2026-06-16 | A02 | location | positive | 135 |
| 2026-06-16 | A02 | noise | negative | 14 |
| 2026-06-16 | A02 | noise | positive | 11 |
| 2026-06-16 | A02 | safety | negative | 1 |
| … (77 dòng nữa) |

## 5. Phân tích review bằng LLM

- Mô hình: `gemini-3.5-flash-lite` (provider gemini), 20 review/lần gọi, temperature 0.0, đầu ra JSON theo schema (sentiment, language, aspects_positive/negative).
- Mẫu: 1.000 review «Mẫu LLM» do giảng viên chỉ định; 100 review «Nhãn tay» nằm trong mẫu. Mỗi người gán lần lượt 20 nhãn tay chia đều.
- Đối chứng không LLM: VADER + từ khoá khía cạnh + langdetect (`src/baseline.py`).

### Kết quả chấm trên nhãn tay

| method | task | metric | value | n |
|---|---|---|---|---|
| llm_vs_baseline | sentiment | agreement | 0.888 | 1000 |
| llm_vs_baseline | sentiment | cohen_kappa | 0.1481 | 1000 |

Phân tích lỗi: `reports/llm_evaluation.md`, `reports/llm_errors.csv`.

### Ước tính chi phí xử lý toàn bộ review của thành phố

| model | n_reviews_sample | n_reviews_city | prompt_tokens_per_review | output_tokens_per_review | usd_per_1m_input | usd_per_1m_output | cost_usd_sample | cost_usd_city | cost_usd_city_free_tier | model_used_in_run |
|---|---|---|---|---|---|---|---|---|---|---|
| gemini-3.5-flash-lite | 1000 | 1026690 | 95.7 | 76.2 | 0.3 | 2.5 | 0.2192 | 225.02 | 0.0 | gemini-3.5-flash-lite |
| gemini-2.5-flash-lite | 1000 | 1026690 | 95.7 | 76.2 | 0.1 | 0.4 | 0.04 | 41.11 | 0.0 | gemini-3.5-flash-lite |

## 6. Hình

- `figures\fig_area_median_price.png`
- `figures\fig_area_structure.png`
- `figures\fig_calendar_seasonality.png`
- `figures\fig_llm_aspects.png`
- `figures\fig_llm_sentiment_by_area.png`
- `figures\fig_map_listings_by_area.png`
- `figures\fig_time_city_trends.png`
- `figures\fig_time_occupancy_by_area.png`

## 7. Kết luận cho bên đặt hàng

- **Theo vùng, cơ cấu cho thuê:** nhà nguyên căn chiếm 87.5% mẫu và ở vùng nào cũng cao (từ 77.95% ở A03 đến 96.92% ở A05). Mức độ vận hành thương mại khác biệt rõ hơn: tỉ lệ listing của host nhiều nhà cao nhất ở A04 (81.54%), A01 (80.0–83.33%) và A02 (71.67–74.17%), thấp nhất ở A08 (39.84–41.46%). A04 có 130 listing nhưng chỉ 76–77 host, tức là vùng gom nhiều nhà về ít host nhất trong mẫu. Nếu cần ưu tiên giám sát, nên xem A04, A01 và A02 trước.
- **Theo vùng, giá đêm (mốc cuối 2026-06-16):** trung vị toàn mẫu khoảng 266 AUD/đêm. Nhà nguyên căn dao động từ 228 (A04) đến 313 AUD (A06), phòng riêng chỉ 86–119 AUD. A03 và A04 có trung vị chung thấp nhất (khoảng 217 AUD); ở A03 chủ yếu do cơ cấu (28/123 listing là phòng riêng, còn nguyên căn vẫn 278.67 AUD), còn ở A04 giá nguyên căn thực sự thấp hơn các vùng khác. Tính theo giá mỗi người, A05 (82.34) và A07 (80.0) đắt nhất, A03 (60.62) rẻ nhất.
- **Theo thời gian, công suất có dấu hiệu mùa vụ:** trong ba mốc đầu (2025-09-12 đến 2026-03-21), công suất 90 ngày tới của toàn mẫu là 39.2%, tăng lên 44.6% ở mốc 2025-12-12 (cửa sổ 90 ngày chủ yếu rơi vào mùa hè) rồi giảm còn 32.8% ở mốc 2026-03-21. Mốc tháng 12 cao hơn mốc tháng 9 ở 7/8 vùng (trừ A02), mạnh nhất ở A06 (+9.26 điểm %). Đến tháng 3, cả 8 vùng đều thấp hơn mốc tháng 12, giảm mạnh nhất ở A05 (−17.99 điểm %), A07 (−16.34) và A04 (−13.79); 7/8 vùng còn thấp hơn cả mốc tháng 9 (trừ A06).
- **Theo thời gian, cơ cấu gần như không đổi:** trong cùng ba mốc, tỉ lệ nhà nguyên căn không đổi ở bất kỳ vùng nào, tỉ lệ listing của host nhiều nhà toàn mẫu chỉ dao động 63.4–64.5% (mỗi vùng biến động không quá 3.33 điểm %), còn số review 12 tháng gần nhất tăng nhẹ ở cả 8 vùng (trung bình từ khoảng 17.6 lên 18.6 review/listing/năm, rõ nhất ở A03 +2.43 và A02 +1.90). Tỉ lệ listing active tăng từ 97.6% lên 99.9% và tỉ lệ ngắn ngày gần 100%, nên hai chỉ số này ít phân biệt được giữa các vùng và giữa các mốc.
- **Từ review, cảm xúc:** trong 1000 review phân tích bằng LLM, 88.2% tích cực, 11.0% lẫn lộn (mixed) và chỉ 0.8% (8 review) tiêu cực. Tỉ lệ tích cực thấp nhất ở A02 (80.72%), A01 (81.31%) và A04 (85.6%), trong khi 5 vùng còn lại đạt 91.01–93.7%. Đây cũng chính là ba vùng có tỉ lệ host nhiều nhà cao nhất; mối liên hệ này đáng chú ý nhưng mới dựa trên 8 vùng nên chưa đủ để kết luận về nguyên nhân.
- **Từ review, khía cạnh được khen và bị chê:** trong phần bảng khía cạnh hiển thị ở mục 4 (A01 và A02), vị trí, tiện nghi và chủ nhà được khen nhiều nhất (ở A02 lần lượt 135, 118 và 106 lượt). Tiện nghi cũng là khía cạnh bị chê nhiều nhất ở cả hai vùng (18 lượt ở A01, 15 ở A02); ở A02 vệ sinh và tiếng ồn bị chê 14 lượt mỗi loại, và riêng tiếng ồn có lượt chê (14) nhiều hơn lượt khen (11).
- **Hạn chế, dữ liệu và mẫu:** (1) mẫu là cùng 1000 listing được giao, chia gần đều 120–130 listing mỗi vùng, nên số listing theo vùng không cho biết vùng nào tập trung cho thuê nhiều hơn (chỉ so sánh được tỉ lệ) và KPI theo thời gian không bắt được listing mới hay listing rời thị trường; (2) giá chỉ tính ở mốc cuối vì giá trong calendar trống hoàn toàn (C05), nên chưa có xu hướng giá qua 4 quý như bên đặt hàng quan tâm; (3) công suất tính từ `available == 'f'` gộp cả ngày đã đặt lẫn ngày chủ nhà tự chặn lịch, nên có thể cao hơn công suất thực; (4) dữ liệu không có giá thuê dài hạn, nên tỉ lệ nhà nguyên căn chỉ là chỉ báo gián tiếp cho việc nhà bị rút khỏi thị trường thuê dài hạn.
- **Hạn chế, phân tích review bằng LLM:** mẫu LLM do giảng viên chỉ định gồm 1000 trên 1026690 review của thành phố (khoảng 0.1%) nên chưa chắc đại diện cho toàn thành phố, và kết quả lệch mạnh về tích cực nên tỉ lệ tiêu cực theo vùng (0–3.74%) chỉ dựa trên tối đa 4 review mỗi vùng. Độ đồng thuận giữa LLM và baseline là 0.888 nhưng Cohen's kappa chỉ 0.1481: mức đồng thuận cao một phần do nhóm tích cực chiếm áp đảo, còn sau khi loại phần trùng hợp ngẫu nhiên thì hai phương pháp đồng thuận thấp, nên điểm cảm xúc chỉ nên xem là chỉ báo tham khảo (xem phân tích lỗi ở `reports/llm_evaluation.md`). Chạy toàn bộ review của thành phố ước tính tốn khoảng 41.11 đến 225.02 USD tuỳ mô hình, nên việc mở rộng là khả thi.
