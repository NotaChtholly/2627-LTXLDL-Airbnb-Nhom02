from __future__ import annotations

import re
from typing import Iterable

import pandas as pd
from langdetect import DetectorFactory, LangDetectException, detect
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

DetectorFactory.seed = 0
_VADER = SentimentIntensityAnalyzer()

ASPECT_KEYWORDS: dict[str, list[str]] = {
    "location": ["location", "located", "close to", "walking distance", "central", "cbd", "tram", "train", "station",
                 "neighbourhood", "neighborhood", "area", "nearby", "convenient", "emplacement", "ubicación", "位置", "vị trí", "lage"],
    "cleanliness": ["clean", "spotless", "dirty", "dust", "smell", "stain", "sticky", "mould", "mold", "hygien", "tidy",
                    "propre", "sale ", "sauber", "干净", "脏", "sạch", "bẩn", "limpio", "sucio"],
    "host": ["host", "owner", "responsive", "communication", "check-in", "check in", "checkin", "welcoming", "helpful",
             "friendly", "hôte", "gastgeber", "房东", "chủ nhà", "anfitrión", "replied", "answered", "messages"],
    "value": ["value", "price", "expensive", "cheap", "worth", "overpriced", "affordable", "money", "cost",
              "giá", "đáng tiền", "precio", "preis", "价格", "cher"],
    "amenities": ["kitchen", "wifi", "wi-fi", "internet", "heater", "heating", "air con", "aircon", "air conditioning",
                  "pool", "gym", "parking", "washer", "dryer", "tv", "bed", "shower", "towel", "equipped", "amenit",
                  "máy lạnh", "piscina", "cuisine", "厨房", "设施"],
    "noise": ["noise", "noisy", "loud", "quiet", "construction", "traffic", "bruyant", "calme", "吵", "ồn", "ruido", "laut", "sleep"],
    "safety": ["safe", "unsafe", "secure", "security", "sketchy", "dangerous", "scary", "lock", "seguro", "sicher", "安全", "an toàn"],
}
_CLAUSE_SPLIT = re.compile(r"[.!?;\n]+|\s+(?:but|however|although|though|mais|pero|aber|nhưng|但是|但)\s+", re.IGNORECASE)


def detect_language(text: str) -> str:
    text = (text or "").strip()
    if len(text) < 3:
        return "unknown"
    try:
        return detect(text)
    except LangDetectException:
        return "unknown"


def vader_sentiment(text: str) -> str:
    s = _VADER.polarity_scores(text or "")
    if s["pos"] >= 0.12 and s["neg"] >= 0.12:
        return "mixed"
    if s["compound"] <= -0.05:
        return "negative"
    return "positive"


def keyword_aspects(text: str, aspects: Iterable[str], overall: str) -> tuple[list[str], list[str]]:
    for clause in _CLAUSE_SPLIT.split(text or ""):
        clause = clause.strip()
        if not clause:
            continue
        low = clause.lower()
        found = [a for a in aspects if any(k in low for k in ASPECT_KEYWORDS.get(a, []))]
        if not found:
            continue
        c = _VADER.polarity_scores(clause)["compound"]
        polarity = "positive" if c >= 0.05 else "negative" if c <= -0.05 else ("negative" if overall == "negative" else "positive")
        (pos if polarity == "positive" else neg).update(found)
    return sorted(pos), sorted(neg)


def label_review(text: str, aspects: Iterable[str]) -> dict:
    sentiment = vader_sentiment(text)
    ap, an = keyword_aspects(text, aspects, sentiment)
    return {"sentiment": sentiment, "language": detect_language(text),
            "aspects_positive": "|".join(ap), "aspects_negative": "|".join(an)}


def run_baseline(reviews: pd.DataFrame, aspects: Iterable[str], text_col: str = "comments", id_col: str = "id") -> pd.DataFrame:
    aspects = list(aspects)
    rows = []
    for rid, text in zip(reviews[id_col].astype(str), reviews[text_col].fillna("").astype(str)):
        r = label_review(text, aspects)
        r["review_id"] = rid
        rows.append(r)
    out = pd.DataFrame(rows, columns=["review_id", "sentiment", "language", "aspects_positive", "aspects_negative"])
    out["model"] = "baseline-vader-keyword"
    return out
