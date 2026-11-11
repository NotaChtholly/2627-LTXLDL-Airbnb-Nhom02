import os
import pandas as pd
LLM_SAMPLE_PATH = "data/samples/llm_sample_1000.csv"
HAND_LABEL_PATH = "data/samples/hand_labeled_100.csv"
REQUIRED_COLS = ["review_id", "listing_id", "comments"]
HAND_LABEL_COLS = ["sentiment_hand", "aspects_hand", "language_hand"]
def _to_str_ids(ids):
    return pd.Index([str(i) for i in ids]).unique()
def extract_llm_samples(df_reviews, assigned_llm_ids, out_path=LLM_SAMPLE_PATH):
    df = df_reviews.copy()
    if "review_id" not in df.columns and "id" in df.columns:
        df = df.rename(columns={"id": "review_id"})
    missing = set(REQUIRED_COLS) - set(df.columns)
    if missing:
        raise ValueError(f"df_reviews thiếu cột bắt buộc: {sorted(missing)}")
    df["review_id"] = df["review_id"].astype(str)
    df = df.drop_duplicates(subset="review_id")
    ids = _to_str_ids(assigned_llm_ids)
    sample = df[df["review_id"].isin(ids)]
    not_found = set(ids) - set(sample["review_id"])
    if not_found:
        raise ValueError(
            f"{len(not_found)} review_id được giao không có trong dữ liệu, "
            f"ví dụ: {sorted(not_found)[:5]}"
        )
    sample = sample.sort_values("review_id").reset_index(drop=True)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    sample.to_csv(out_path, index=False, encoding="utf-8")
    print(f"[llm] Đã lưu {len(sample)} review mẫu LLM -> {out_path}")
    return sample
def export_hand_labeled_dataset(
    df_llm_samples, assigned_hand_ids, out_path=HAND_LABEL_PATH, overwrite=False
):
    if os.path.exists(out_path) and not overwrite:
        print(f"[llm] {out_path} đã tồn tại -> giữ nguyên, không ghi đè nhãn tay")
        return pd.read_csv(out_path, dtype={"review_id": str}, encoding="utf-8-sig")
    df = df_llm_samples.copy()
    df["review_id"] = df["review_id"].astype(str)
    ids = _to_str_ids(assigned_hand_ids)
    hand = df[df["review_id"].isin(ids)]
    not_in_llm = set(ids) - set(hand["review_id"])
    if not_in_llm:
        raise ValueError(
            f"{len(not_in_llm)} review_id nhãn tay không nằm trong mẫu LLM, "
            f"ví dụ: {sorted(not_in_llm)[:5]}"
        )
    hand = hand[REQUIRED_COLS].sort_values("review_id").reset_index(drop=True)
    for col in HAND_LABEL_COLS:
        hand[col] = ""
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    hand.to_csv(out_path, index=False, encoding="utf-8-sig")
    print(f"[llm] Đã lưu {len(hand)} review cần gán nhãn tay -> {out_path}")
    return hand