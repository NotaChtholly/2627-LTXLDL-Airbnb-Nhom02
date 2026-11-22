from __future__ import annotations

import json
import logging
import os
import random
import time
from pathlib import Path
from typing import Any, Mapping

import pandas as pd

from src import baseline

LOGGER = logging.getLogger(__name__)

LLM_SAMPLE_PATH = "data/samples/llm_sample_1000.csv"
HAND_LABEL_PATH = "data/samples/hand_labeled_100.csv"

REQUIRED_COLS = ["review_id", "listing_id", "comments"]
HAND_LABEL_COLS = ["sentiment_hand", "aspects_positive_hand", "aspects_negative_hand", "language_hand"]
SENTIMENTS = ("positive", "mixed", "negative")
MAX_CHARS_PER_REVIEW = 1500


def _to_str_ids(ids) -> pd.Index:
    return pd.Index([str(i) for i in ids]).unique()


def extract_llm_samples(df_reviews: pd.DataFrame, assigned_llm_ids, out_path: str | Path = LLM_SAMPLE_PATH) -> pd.DataFrame:
    """Lọc các review được chọn làm Mẫu LLM và lưu ra CSV."""
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
        raise ValueError(f"{len(not_found)} review_id được giao không có trong dữ liệu, ví dụ: {sorted(not_found)[:5]}")
    sample = sample.sort_values("review_id").reset_index(drop=True)
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    sample.to_csv(out_path, index=False, encoding="utf-8")
    LOGGER.info("[llm] Đã lưu %d review mẫu LLM -> %s", len(sample), out_path)
    return sample


def export_hand_labeled_dataset(df_llm_samples: pd.DataFrame, assigned_hand_ids, out_path: str | Path = HAND_LABEL_PATH,
                                overwrite: bool = False) -> pd.DataFrame:
    """Trích các review đánh dấu Nhãn tay (nằm TRONG mẫu LLM) ra file có cột nhãn trống."""
    out_path = Path(out_path)
    if out_path.exists() and not overwrite:
        LOGGER.info("[llm] %s đã tồn tại -> giữ nguyên, không ghi đè nhãn tay", out_path)
        return pd.read_csv(out_path, dtype={"review_id": str, "listing_id": str}, encoding="utf-8-sig")
    df = df_llm_samples.copy()
    df["review_id"] = df["review_id"].astype(str)
    ids = _to_str_ids(assigned_hand_ids)
    hand = df[df["review_id"].isin(ids)]
    not_in_llm = set(ids) - set(hand["review_id"])
    if not_in_llm:
        raise ValueError(f"{len(not_in_llm)} review_id nhãn tay không nằm trong mẫu LLM, ví dụ: {sorted(not_in_llm)[:5]}")
    hand = hand[REQUIRED_COLS].sort_values("review_id").reset_index(drop=True)
    for col in HAND_LABEL_COLS:
        hand[col] = ""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    hand.to_csv(out_path, index=False, encoding="utf-8-sig")
    LOGGER.info("[llm] Đã lưu %d review cần gán nhãn tay -> %s", len(hand), out_path)
    return hand


def response_schema(aspects: list[str]) -> dict:
    aspect_enum = {"type": "string", "enum": list(aspects)}
    return {
        "type": "object",
        "properties": {
            "results": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                        "sentiment": {"type": "string", "enum": list(SENTIMENTS)},
                        "language": {"type": "string", "description": "ISO 639-1 code of the review text, e.g. en, fr, zh"},
                        "aspects_positive": {"type": "array", "items": aspect_enum},
                        "aspects_negative": {"type": "array", "items": aspect_enum},
                    },
                    "required": ["id", "sentiment", "language", "aspects_positive", "aspects_negative"],
                },
            }
        },
        "required": ["results"],
    }


SYSTEM_INSTRUCTION = (
    "You are a careful data annotator for Airbnb guest reviews. For EACH review, return: "
    "sentiment (positive = overall satisfied; negative = overall dissatisfied; mixed = clear praise AND clear complaint), "
    "language (ISO 639-1 code of the review text; if a review is written in two languages, choose the dominant one), "
    "aspects_positive and aspects_negative: the aspects explicitly praised or criticised, chosen ONLY from the allowed list. "
    "Aspect meanings — location: neighbourhood, transport, distance to attractions; cleanliness: dirt, smell, hygiene; "
    "host: communication, check-in, responsiveness; value: price vs what you get; amenities: equipment such as wifi, kitchen, "
    "heating, bed, parking, pool; noise: sound disturbance, quietness; safety: feeling safe/unsafe, security. "
    "Automated 'host cancelled' notices and reviews with no evaluative content are 'positive' with no aspects. "
    "Return one result per input id, in the same order, as JSON only."
)


def build_prompt(batch: list[tuple[str, str]], aspects: list[str]) -> str:
    items = [{"id": rid, "text": (text or "")[:MAX_CHARS_PER_REVIEW]} for rid, text in batch]
    return f"Allowed aspects: {', '.join(aspects)}.\nReviews (JSON): {json.dumps(items, ensure_ascii=False)}"


class GeminiExtractor:
    def __init__(self, config: Mapping[str, Any]):
        from google import genai

        llm = config["llm"]
        env = llm.get("api_key_env", "GEMINI_API_KEY")
        key = os.environ.get(env)
        if not key:
            raise RuntimeError(f"Thiếu khoá API: đặt biến môi trường {env} (xem .env.example) hoặc chạy với --skip-llm.")
        self.client = genai.Client(api_key=key)
        self.model = llm.get("model", "gemini-2.5-flash")
        self.aspects = list(llm["aspects"])
        self.temperature = float(llm.get("temperature", 0.0))
        self.max_retries = int(llm.get("max_retries", 6))
        self.schema = response_schema(self.aspects)

    def extract(self, batch: list[tuple[str, str]]) -> tuple[list[dict], int, int]:
        from google.genai import errors, types

        config = types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION,
            temperature=self.temperature,
            response_mime_type="application/json",
            response_json_schema=self.schema,
        )
        prompt = build_prompt(batch, self.aspects)
        delay = 5.0
        for attempt in range(1, self.max_retries + 1):
            try:
                response = self.client.models.generate_content(model=self.model, contents=prompt, config=config)
                data = json.loads(response.text)
                usage = getattr(response, "usage_metadata", None)
                p_tok = int(getattr(usage, "prompt_token_count", 0) or 0)
                o_tok = int(getattr(usage, "candidates_token_count", 0) or 0)
                return self._validate(data.get("results", []), batch), p_tok, o_tok
            except errors.APIError as exc:
                code = getattr(exc, "code", None)
                if code in (429, 500, 502, 503, 504) and attempt < self.max_retries:
                    LOGGER.warning("Gemini %s (lần %d/%d) -> chờ %.0fs", code, attempt, self.max_retries, delay)
                    time.sleep(delay)
                    delay = min(delay * 2, 90)
                    continue
                raise
            except (json.JSONDecodeError, ValueError) as exc:
                if attempt < self.max_retries:
                    LOGGER.warning("Kết quả không phải JSON hợp lệ (%s) -> thử lại", exc)
                    time.sleep(2)
                    continue
                raise
        raise RuntimeError("Không gọi được Gemini sau nhiều lần thử.")

    def _validate(self, results: list[dict], batch: list[tuple[str, str]]) -> list[dict]:
        by_id = {str(r.get("id")): r for r in results}
        out = []
        for rid, _ in batch:
            r = by_id.get(rid)
            if r is None:
                raise ValueError(f"LLM không trả kết quả cho review {rid}")
            sentiment = str(r.get("sentiment", "")).lower()
            if sentiment not in SENTIMENTS:
                raise ValueError(f"sentiment lạ: {sentiment}")
            ap = [a for a in r.get("aspects_positive", []) if a in self.aspects]
            an = [a for a in r.get("aspects_negative", []) if a in self.aspects]
            out.append({"review_id": rid, "sentiment": sentiment, "language": str(r.get("language", "unknown")).lower()[:5],
                        "aspects_positive": "|".join(sorted(set(ap))), "aspects_negative": "|".join(sorted(set(an)))})
        return out


class MockExtractor:

    def __init__(self, config: Mapping[str, Any]):
        self.aspects = list(config["llm"]["aspects"])
        self.model = "mock-baseline"

    def extract(self, batch: list[tuple[str, str]]) -> tuple[list[dict], int, int]:
        out = []
        for rid, text in batch:
            r = baseline.label_review(text, self.aspects)
            r["review_id"] = rid
            out.append(r)
        p_tok = sum(len((t or "")[:MAX_CHARS_PER_REVIEW]) for _, t in batch) // 4 + 60 * len(batch)
        return out, p_tok, 35 * len(batch)


def _read_cache(path: Path) -> dict[str, dict]:
    cache: dict[str, dict] = {}
    if path.exists():
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    r = json.loads(line)
                    cache[str(r["review_id"])] = r
    return cache


def _append_cache(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def run_llm(reviews_unique: pd.DataFrame, config: Mapping[str, Any], skip_llm: bool = False) -> pd.DataFrame:
    llm = config["llm"]
    root = Path(config.get("_project_root", Path.cwd()))
    cache_path = root / llm["cache"]
    results_path = root / llm["results"]
    aspects = list(llm["aspects"])

    sample = reviews_unique.loc[reviews_unique["llm_sample"].astype(int) == 1].copy()
    sample["review_id"] = sample["id"].astype(str)
    sample = sample.sort_values("review_id").reset_index(drop=True)
    cache = _read_cache(cache_path)
    todo = sample.loc[~sample["review_id"].isin(cache.keys())]
    LOGGER.info("[llm] mẫu LLM: %d review, đã có cache: %d, cần gọi: %d", len(sample), len(sample) - len(todo), len(todo))

    if len(todo) and not skip_llm:
        provider = llm.get("provider", "gemini")
        extractor = MockExtractor(config) if provider == "mock" else GeminiExtractor(config)
        if provider == "mock":
            LOGGER.warning("[llm] provider=mock: KHÔNG phải LLM thật, chỉ dùng để test luồng.")
        bs = int(llm.get("batch_size", 20))
        pairs = list(zip(todo["review_id"], todo["comments"].fillna("").astype(str)))
        for start in range(0, len(pairs), bs):
            batch = pairs[start:start + bs]
            rows, p_tok, o_tok = extractor.extract(batch)
            stamp = {"model": extractor.model, "prompt_tokens": round(p_tok / len(batch), 2),
                     "output_tokens": round(o_tok / len(batch), 2), "batch_size": len(batch)}
            rows = [{**r, **stamp} for r in rows]
            _append_cache(cache_path, rows)
            for r in rows:
                cache[r["review_id"]] = r
            LOGGER.info("[llm] %d/%d review xong (lô %d, tokens %d+%d)", min(start + bs, len(pairs)), len(pairs), start // bs + 1, p_tok, o_tok)
    elif len(todo):
        LOGGER.warning("[llm] --skip-llm: %d review chưa có trong cache sẽ không có nhãn LLM.", len(todo))

    have = [cache[r] for r in sample["review_id"] if r in cache]
    results = pd.DataFrame(have, columns=["review_id", "sentiment", "language", "aspects_positive", "aspects_negative",
                                          "model", "prompt_tokens", "output_tokens", "batch_size"])
    results_path.parent.mkdir(parents=True, exist_ok=True)
    results.to_csv(results_path, index=False, encoding="utf-8-sig")
    LOGGER.info("[llm] lưu %d kết quả -> %s", len(results), results_path)
    return results


def count_city_reviews(config: Mapping[str, Any]) -> int:
    root = Path(config.get("_project_root", Path.cwd()))
    path = root / config["paths"]["raw"] / config["snapshots"][-1] / "reviews.csv.gz"
    if not path.exists():
        return 0
    n = 0
    for chunk in pd.read_csv(path, usecols=["id"], chunksize=200_000):
        n += len(chunk)
    return n


def estimate_cost(results: pd.DataFrame, n_reviews_city: int, config: Mapping[str, Any]) -> pd.DataFrame:
    llm = config["llm"]
    n = len(results)
    if n == 0:
        return pd.DataFrame()
    p_avg = float(results["prompt_tokens"].astype(float).mean())
    o_avg = float(results["output_tokens"].astype(float).mean())
    rows = []
    for model, price in llm.get("prices_usd_per_1m", {}).items():
        cost_sample = (p_avg * n * price["input"] + o_avg * n * price["output"]) / 1e6
        cost_city = (p_avg * n_reviews_city * price["input"] + o_avg * n_reviews_city * price["output"]) / 1e6
        rows.append({"model": model, "n_reviews_sample": n, "n_reviews_city": n_reviews_city,
                     "prompt_tokens_per_review": round(p_avg, 1), "output_tokens_per_review": round(o_avg, 1),
                     "usd_per_1m_input": price["input"], "usd_per_1m_output": price["output"],
                     "cost_usd_sample": round(cost_sample, 4), "cost_usd_city": round(cost_city, 2),
                     "cost_usd_city_free_tier": 0.0, "model_used_in_run": results["model"].iloc[0]})
    df = pd.DataFrame(rows)
    root = Path(config.get("_project_root", Path.cwd()))
    path = root / config["paths"]["reports"] / "llm_cost_estimate.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, encoding="utf-8-sig")
    LOGGER.info("[llm] lưu ước tính chi phí -> %s", path)
    return df
