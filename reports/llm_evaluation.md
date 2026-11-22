# Đánh giá LLM vs baseline — Melbourne

## Kết quả trên 100 review nhãn tay

| Phương pháp | Sent. accuracy | Sent. macro-F1 | F1 pos | F1 mixed | F1 neg | Lang. acc | Aspect P | Aspect R | Aspect F1 |
|---|---|---|---|---|---|---|---|---|---|
| llm | 0.970 | 0.882 | 0.989 | 0.857 | 0.800 | 1.000 | 0.875 | 0.948 | 0.910 |
| baseline | 0.900 | 0.582 | 0.946 | 0.000 | 0.800 | 1.000 | 0.856 | 0.737 | 0.792 |

## Đồng thuận LLM – baseline trên 1000 review mẫu

- Tỉ lệ trùng nhãn sentiment: **88.8%**, Cohen's κ = 0.148
- Phân bố sentiment LLM: {'positive': 882, 'mixed': 110, 'negative': 8}
- Phân bố sentiment baseline: {'positive': 984, 'negative': 11, 'mixed': 5}
- Ngôn ngữ (LLM) top: {'en': 999, 'zh': 1}

### Ma trận nhầm lẫn sentiment — llm (hàng = nhãn tay, cột = dự đoán)

| | positive | mixed | negative |
|---|---|---|---|
| **positive** | 86 | 2 | 0 |
| **mixed** | 0 | 9 | 0 |
| **negative** | 0 | 1 | 2 |

F1 theo khía cạnh (llm):

| aspect | tp | fp | fn | P | R | F1 |
|---|---|---|---|---|---|---|
| location | 68 | 1 | 3 | 0.986 | 0.958 | 0.971 |
| cleanliness | 31 | 3 | 1 | 0.912 | 0.969 | 0.939 |
| host | 56 | 6 | 2 | 0.903 | 0.966 | 0.933 |
| value | 5 | 2 | 0 | 0.714 | 1.0 | 0.833 |
| amenities | 60 | 17 | 5 | 0.779 | 0.923 | 0.845 |
| noise | 17 | 4 | 2 | 0.81 | 0.895 | 0.85 |
| safety | 1 | 1 | 0 | 0.5 | 1.0 | 0.667 |

### Ma trận nhầm lẫn sentiment — baseline (hàng = nhãn tay, cột = dự đoán)

| | positive | mixed | negative |
|---|---|---|---|
| **positive** | 88 | 0 | 0 |
| **mixed** | 9 | 0 | 0 |
| **negative** | 1 | 0 | 2 |

F1 theo khía cạnh (baseline):

| aspect | tp | fp | fn | P | R | F1 |
|---|---|---|---|---|---|---|
| location | 60 | 5 | 11 | 0.923 | 0.845 | 0.882 |
| cleanliness | 29 | 2 | 3 | 0.935 | 0.906 | 0.921 |
| host | 45 | 6 | 13 | 0.882 | 0.776 | 0.826 |
| value | 4 | 3 | 1 | 0.571 | 0.8 | 0.667 |
| amenities | 33 | 6 | 32 | 0.846 | 0.508 | 0.635 |
| noise | 13 | 7 | 6 | 0.65 | 0.684 | 0.667 |
| safety | 1 | 2 | 0 | 0.333 | 1.0 | 0.5 |

## Phân tích lỗi

- **llm**: 44 review sai ở ít nhất một nhiệm vụ; theo loại: {'aspects': 42, 'sentiment': 3}.
  - Cặp nhầm sentiment hay gặp (nhãn tay→dự đoán): {'positive→mixed': 2, 'negative→mixed': 1}
- **baseline**: 65 review sai ở ít nhất một nhiệm vụ; theo loại: {'aspects': 62, 'sentiment': 10}.
  - Cặp nhầm sentiment hay gặp (nhãn tay→dự đoán): {'mixed→positive': 9, 'negative→positive': 1}

Chi tiết từng review sai: `reports/llm_errors.csv`. Nhóm đọc 10–15 lỗi đầu và ghi nhận xét vào báo cáo (vd: LLM gán 'mixed' khi khách chỉ góp ý nhẹ; baseline không hiểu tiếng ngoài tiếng Anh).
