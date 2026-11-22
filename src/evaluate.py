from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any, Mapping

import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, cohen_kappa_score, confusion_matrix, f1_score

LOGGER = logging.getLogger(__name__)
LABELS = ["positive", "mixed", "negative"]
_SPLIT = re.compile(r"[|,;/\s]+")


def _norm_sent(s: Any) -> str:
    s = str(s or "").strip().lower()
    aliases = {"pos": "positive", "neg": "negative", "mix": "mixed", "neutral": "mixed", "tích cực": "positive",
               "tiêu cực": "negative", "hỗn hợp": "mixed", "trung lập": "mixed"}
    return aliases.get(s, s)


def _norm_lang(s: Any) -> str:
    s = str(s or "").strip().lower()
    return s.split("-")[0][:2] if s else ""


def _aspect_set(s: Any, aspects: list[str]) -> set[str]:
    return {a for a in _SPLIT.split(str(s or "").strip().lower()) if a in aspects}


def load_hand_labels(path: Path, aspects: list[str]) -> pd.DataFrame | None:
    if not path.exists():
        LOGGER.warning("[eval] chưa có %s", path)
        return None
    df = pd.read_csv(path, dtype=str, encoding="utf-8-sig").fillna("")
    df["review_id"] = df["review_id"].astype(str).str.strip()
    df["sentiment_hand"] = df["sentiment_hand"].map(_norm_sent)
    filled = df.loc[df["sentiment_hand"].isin(LABELS)].copy()
    if filled.empty:
        LOGGER.warning("[eval] %s chưa có nhãn sentiment_hand hợp lệ (%s) -> bỏ qua chấm.", path, "/".join(LABELS))
        return None
    bad = df.loc[~df["sentiment_hand"].isin(LABELS) & (df["sentiment_hand"] != ""), "sentiment_hand"].unique()
    if len(bad):
        LOGGER.warning("[eval] nhãn sentiment_hand lạ bị bỏ qua: %s", list(bad)[:10])
    filled["language_hand"] = filled["language_hand"].map(_norm_lang)
    filled["ap_hand"] = filled["aspects_positive_hand"].map(lambda s: _aspect_set(s, aspects))
    filled["an_hand"] = filled["aspects_negative_hand"].map(lambda s: _aspect_set(s, aspects))
    LOGGER.info("[eval] %d/%d review có nhãn tay hợp lệ", len(filled), len(df))
    return filled


def _pairs(ap: set[str], an: set[str]) -> set[str]:
    return {f"{a}+" for a in ap} | {f"{a}-" for a in an}


def _aspect_metrics(hand: pd.DataFrame, pred: pd.DataFrame, aspects: list[str]) -> tuple[dict[str, float], pd.DataFrame]:
    tp = fp = fn = 0
    per = {a: [0, 0, 0] for a in aspects}
    for _, h in hand.iterrows():
        p = pred.loc[pred["review_id"] == h["review_id"]]
        if p.empty:
            continue
        truth = _pairs(h["ap_hand"], h["an_hand"])
        guess = _pairs(_aspect_set(p.iloc[0]["aspects_positive"], aspects), _aspect_set(p.iloc[0]["aspects_negative"], aspects))
        tp += len(truth & guess)
        fp += len(guess - truth)
        fn += len(truth - guess)
        for a in aspects:
            t = {x for x in truth if x[:-1] == a}
            g = {x for x in guess if x[:-1] == a}
            per[a][0] += len(t & g)
            per[a][1] += len(g - t)
            per[a][2] += len(t - g)
    prec = tp / (tp + fp) if tp + fp else 0.0
    rec = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0.0
    rows = []
    for a, (t, p_, n) in per.items():
        pr = t / (t + p_) if t + p_ else 0.0
        rc = t / (t + n) if t + n else 0.0
        rows.append({"aspect": a, "tp": t, "fp": p_, "fn": n, "precision": round(pr, 3), "recall": round(rc, 3),
                     "f1": round(2 * pr * rc / (pr + rc), 3) if pr + rc else 0.0})
    return {"aspect_precision_micro": prec, "aspect_recall_micro": rec, "aspect_f1_micro": f1}, pd.DataFrame(rows)


def evaluate(hand: pd.DataFrame | None, llm: pd.DataFrame, base: pd.DataFrame, reviews: pd.DataFrame,
             config: Mapping[str, Any]) -> tuple[pd.DataFrame, pd.DataFrame, str]:
    aspects = list(config["llm"]["aspects"])
    methods = {"llm": llm, "baseline": base}
    metric_rows: list[dict] = []
    head: list[str] = [f"# Đánh giá LLM vs baseline — {config['city'].title()}", ""]
    agree_md: list[str] = []
    md: list[str] = []
    errors = pd.DataFrame()

    both = llm.merge(base, on="review_id", suffixes=("_llm", "_base"))
    if len(both):
        agree = float((both["sentiment_llm"] == both["sentiment_base"]).mean())
        kappa = float(cohen_kappa_score(both["sentiment_llm"], both["sentiment_base"]))
        metric_rows += [{"method": "llm_vs_baseline", "task": "sentiment", "metric": "agreement", "value": round(agree, 4), "n": len(both)},
                        {"method": "llm_vs_baseline", "task": "sentiment", "metric": "cohen_kappa", "value": round(kappa, 4), "n": len(both)}]
        agree_md += [f"## Đồng thuận LLM – baseline trên {len(both)} review mẫu", "",
                     f"- Tỉ lệ trùng nhãn sentiment: **{agree:.1%}**, Cohen's κ = {kappa:.3f}",
                     f"- Phân bố sentiment LLM: {llm['sentiment'].value_counts().to_dict()}",
                     f"- Phân bố sentiment baseline: {base['sentiment'].value_counts().to_dict()}",
                     f"- Ngôn ngữ (LLM) top: {llm['language'].value_counts().head(6).to_dict()}", ""]

    if hand is None:
        md += ["## Nhãn tay", "", "Chưa có nhãn tay hợp lệ trong `data/samples/hand_labeled_100.csv`. "
               "Điền đủ 100 dòng theo `data/samples/HUONG_DAN_GAN_NHAN.md` rồi chạy lại pipeline để có accuracy/F1.", ""]
        return pd.DataFrame(metric_rows), errors, "\n".join(head + agree_md + md)

    summary_table = [f"## Kết quả trên {len(hand)} review nhãn tay", "",
                     "| Phương pháp | Sent. accuracy | Sent. macro-F1 | F1 pos | F1 mixed | F1 neg | Lang. acc | Aspect P | Aspect R | Aspect F1 |",
                     "|---|---|---|---|---|---|---|---|---|---|"]
    err_rows = []
    text_by_id = reviews.set_index(reviews["id"].astype(str))["comments"].astype(str).to_dict()
    for name, pred in methods.items():
        m = hand.merge(pred, on="review_id", how="inner")
        if m.empty:
            LOGGER.warning("[eval] %s không khớp review nào với nhãn tay", name)
            continue
        y, yhat = m["sentiment_hand"], m["sentiment"].map(_norm_sent)
        acc = accuracy_score(y, yhat)
        f1m = f1_score(y, yhat, labels=LABELS, average="macro", zero_division=0)
        f1c = f1_score(y, yhat, labels=LABELS, average=None, zero_division=0)
        lang_mask = m["language_hand"] != ""
        lang_acc = float((m.loc[lang_mask, "language"].map(_norm_lang) == m.loc[lang_mask, "language_hand"]).mean()) if lang_mask.any() else np.nan
        am, per_aspect = _aspect_metrics(hand, pred, aspects)
        rows = {"sentiment_accuracy": acc, "sentiment_macro_f1": f1m, "f1_positive": f1c[0], "f1_mixed": f1c[1],
                "f1_negative": f1c[2], "language_accuracy": lang_acc, **am}
        metric_rows += [{"method": name, "task": k.split("_")[0], "metric": k, "value": round(float(v), 4), "n": len(m)} for k, v in rows.items()]
        summary_table.append(f"| {name} | {acc:.3f} | {f1m:.3f} | {f1c[0]:.3f} | {f1c[1]:.3f} | {f1c[2]:.3f} | "
                             f"{lang_acc:.3f} | {am['aspect_precision_micro']:.3f} | {am['aspect_recall_micro']:.3f} | {am['aspect_f1_micro']:.3f} |")
        cm = confusion_matrix(y, yhat, labels=LABELS)
        md_cm = [f"### Ma trận nhầm lẫn sentiment — {name} (hàng = nhãn tay, cột = dự đoán)", "",
                 "| | " + " | ".join(LABELS) + " |", "|---|" + "---|" * len(LABELS)]
        md_cm += [f"| **{LABELS[i]}** | " + " | ".join(str(int(x)) for x in cm[i]) + " |" for i in range(len(LABELS))]
        md += md_cm + ["", f"F1 theo khía cạnh ({name}):", "", "| aspect | tp | fp | fn | P | R | F1 |", "|---|---|---|---|---|---|---|"]
        md += [f"| {r.aspect} | {r.tp} | {r.fp} | {r.fn} | {r.precision} | {r.recall} | {r.f1} |" for r in per_aspect.itertuples()]
        md.append("")
        for _, r in m.iterrows():
            gp = _aspect_set(r["aspects_positive"], aspects)
            gn = _aspect_set(r["aspects_negative"], aspects)
            sent_err = _norm_sent(r["sentiment"]) != r["sentiment_hand"]
            asp_err = _pairs(gp, gn) != _pairs(r["ap_hand"], r["an_hand"])
            lang_err = bool(r["language_hand"]) and _norm_lang(r["language"]) != r["language_hand"]
            if sent_err or asp_err or lang_err:
                err_rows.append({"method": name, "review_id": r["review_id"],
                                 "error_type": "+".join(t for t, e in (("sentiment", sent_err), ("aspects", asp_err), ("language", lang_err)) if e),
                                 "hand_sentiment": r["sentiment_hand"], "pred_sentiment": _norm_sent(r["sentiment"]),
                                 "hand_aspects": "|".join(sorted(_pairs(r["ap_hand"], r["an_hand"]))),
                                 "pred_aspects": "|".join(sorted(_pairs(gp, gn))),
                                 "hand_language": r["language_hand"], "pred_language": _norm_lang(r["language"]),
                                 "text": text_by_id.get(str(r["review_id"]), "")[:300].replace("\n", " ")})
    md = head + summary_table + [""] + agree_md + md
    errors = pd.DataFrame(err_rows)
    if len(errors):
        md += ["## Phân tích lỗi", ""]
        for name in methods:
            e = errors.loc[errors["method"] == name]
            if e.empty:
                continue
            kinds = e["error_type"].str.split("+").explode().value_counts().to_dict()
            md.append(f"- **{name}**: {len(e)} review sai ở ít nhất một nhiệm vụ; theo loại: {kinds}.")
            s = e.loc[e["error_type"].str.contains("sentiment")]
            if len(s):
                pairs = (s["hand_sentiment"] + "→" + s["pred_sentiment"]).value_counts().head(5).to_dict()
                md.append(f"  - Cặp nhầm sentiment hay gặp (nhãn tay→dự đoán): {pairs}")
        md += ["", "Chi tiết từng review sai: `reports/llm_errors.csv`. Nhóm đọc 10–15 lỗi đầu và ghi nhận xét vào báo cáo "
               "(vd: LLM gán 'mixed' khi khách chỉ góp ý nhẹ; baseline không hiểu tiếng ngoài tiếng Anh).", ""]
    return pd.DataFrame(metric_rows), errors, "\n".join(md)


def run_evaluation(llm: pd.DataFrame, base: pd.DataFrame, reviews_unique: pd.DataFrame, config: Mapping[str, Any]) -> pd.DataFrame:
    root = Path(config.get("_project_root", Path.cwd()))
    reports = root / config["paths"]["reports"]
    reports.mkdir(parents=True, exist_ok=True)
    aspects = list(config["llm"]["aspects"])
    hand = load_hand_labels(root / config["paths"]["samples"] / "hand_labeled_100.csv", aspects)
    if llm is None or llm.empty:
        LOGGER.warning("[eval] chưa có kết quả LLM -> chỉ chấm baseline.")
        llm = pd.DataFrame(columns=["review_id", "sentiment", "language", "aspects_positive", "aspects_negative"])
    metrics, errors, md = evaluate(hand, llm, base, reviews_unique, config)
    metrics.to_csv(reports / "llm_evaluation.csv", index=False, encoding="utf-8-sig")
    errors.to_csv(reports / "llm_errors.csv", index=False, encoding="utf-8-sig")
    (reports / "llm_evaluation.md").write_text(md, encoding="utf-8")
    LOGGER.info("[eval] lưu %s, %s, %s", reports / "llm_evaluation.csv", reports / "llm_errors.csv", reports / "llm_evaluation.md")
    return metrics
