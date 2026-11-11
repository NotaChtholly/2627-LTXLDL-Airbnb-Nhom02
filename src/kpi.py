import os
import json
import pandas as pd
def verify_filtered_schema(df):
    required_cols = [
        "snapshot",
        "id",
        "price",
        "room_type",
        "analysis_area",
        "host_id",
        "minimum_nights",
        "number_of_reviews",
    ]
    expected_schema = {
        'id': ['object', 'string', 'str'],
        'price': ['object', 'string', 'str', 'float64']
    }
    missing_cols = [col for col in required_cols if col not in df.columns]
    invalid_types = []
    for col, allowed_types in expected_schema.items():
        if col in df.columns:
            current_type = str(df[col].dtype)
            if current_type not in allowed_types:
                invalid_types.append((col, current_type))
    if missing_cols:
        print(f"Thiếu các cột bắt buộc: {missing_cols}")
        return False
    if invalid_types:
        print(f"Sai kiểu dữ liệu (Cột, Kiểu hiện tại): {invalid_types}")
        return False
    print("Schema hợp lệ.")
    return True
def init_kpi_structures(processed_dir="data/processed"):
    os.makedirs(processed_dir, exist_ok=True)
    gitkeep_path = os.path.join(processed_dir, ".gitkeep")
    with open(gitkeep_path, "w"):
        pass
    data_dictionary = {
        "dataset": "listings.csv",
        "columns": {
            "id": "Mã định danh duy nhất cho mỗi danh sách",
            "price": "Giá thuê tính theo một đêm",
            "room_type": "Phân loại không gian thuê (Entire home/apt, Private room, Shared room)",
        },
    }
    docs_dir = "docs"
    os.makedirs(docs_dir, exist_ok=True)
    dict_path = os.path.join(docs_dir, "data_dictionary_sample.json")
    with open(dict_path, "w", encoding="utf-8") as f:
        json.dump(data_dictionary, f, ensure_ascii=False, indent=4)
    print(f" Đã tạo {gitkeep_path} và {dict_path}.")