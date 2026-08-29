"""
STEP 1 — Data Audit
STEP 2 — Leakage Prevention (duplicate / near-duplicate detection)
"""
import pandas as pd
import numpy as np
import re
import os
import json
from collections import Counter
from difflib import SequenceMatcher
from src.config import (
    DATASET_PATH, SHEET_NAME, COL_MESSAGE, COL_LANGUAGE,
    COL_CATEGORY, COL_LABEL, REPORT_DIR,
)


# ──────────────────────────────────────────────────────────────────────────────
def load_dataset() -> pd.DataFrame:
    """Load the Excel workbook and return a DataFrame."""
    df = pd.read_excel(DATASET_PATH, sheet_name=SHEET_NAME)
    return df


# ──────────────────────────────────────────────────────────────────────────────
def audit(df: pd.DataFrame) -> dict:
    """Comprehensive data-quality audit."""
    report = {}

    # Basic shape
    report["rows"] = len(df)
    report["columns"] = list(df.columns)
    report["dtypes"] = {c: str(df[c].dtype) for c in df.columns}

    # Missing values
    report["missing_values"] = {c: int(df[c].isna().sum()) for c in df.columns}

    # Exact duplicate rows
    exact_dup = int(df.duplicated().sum())
    report["exact_duplicate_rows"] = exact_dup

    # Duplicate message content
    dup_msg = int(df[COL_MESSAGE].duplicated(keep=False).sum())
    report["duplicate_message_count"] = dup_msg
    dup_messages = df[df[COL_MESSAGE].duplicated(keep=False)]
    report["duplicate_messages"] = (
        dup_messages[[COL_MESSAGE, COL_LABEL]].drop_duplicates().to_dict(orient="records")
    )

    # Conflicting duplicates — same text, different label
    conflicts = []
    for msg, grp in df.groupby(COL_MESSAGE):
        labels = grp[COL_LABEL].unique()
        if len(labels) > 1:
            conflicts.append({"message": msg, "labels": labels.tolist()})
    report["conflicting_duplicates"] = conflicts

    # Class distribution
    report["label_distribution"] = df[COL_LABEL].value_counts().to_dict()

    # Language distribution
    report["language_distribution"] = df[COL_LANGUAGE].value_counts().to_dict()

    # Category distribution
    report["category_distribution"] = df[COL_CATEGORY].value_counts().to_dict()

    # Cross-tabulation: label × language
    report["label_by_language"] = (
        pd.crosstab(df[COL_LABEL], df[COL_LANGUAGE]).to_dict()
    )

    # Message-length statistics
    lengths = df[COL_MESSAGE].astype(str).str.len()
    report["message_length_stats"] = {
        "mean": round(float(lengths.mean()), 2),
        "median": round(float(lengths.median()), 2),
        "std": round(float(lengths.std()), 2),
        "min": int(lengths.min()),
        "max": int(lengths.max()),
        "q25": int(lengths.quantile(0.25)),
        "q75": int(lengths.quantile(0.75)),
    }

    # Very short messages (< 15 chars)
    short_mask = lengths < 15
    report["very_short_messages"] = int(short_mask.sum())
    if short_mask.sum() > 0:
        report["short_message_examples"] = (
            df.loc[short_mask, [COL_MESSAGE, COL_LABEL]]
            .head(10)
            .to_dict(orient="records")
        )

    # Empty / whitespace-only
    empty_mask = df[COL_MESSAGE].astype(str).str.strip().str.len() == 0
    report["empty_messages"] = int(empty_mask.sum())

    # Unusual characters check (non-printable or control chars)
    unusual = df[COL_MESSAGE].astype(str).apply(
        lambda x: bool(re.search(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", x))
    )
    report["messages_with_control_chars"] = int(unusual.sum())

    # URL count
    url_count = df[COL_MESSAGE].astype(str).apply(
        lambda x: len(re.findall(r"https?://\S+", x))
    )
    report["messages_with_urls"] = int((url_count > 0).sum())

    # Currency patterns
    currency_count = df[COL_MESSAGE].astype(str).apply(
        lambda x: len(re.findall(r"Rs\.?\s*\d+|₨\s*\d+|\$\s*\d+|£\s*\d+", x, re.IGNORECASE))
    )
    report["messages_with_currency"] = int((currency_count > 0).sum())

    return report


# ──────────────────────────────────────────────────────────────────────────────
def detect_near_duplicates(df: pd.DataFrame, threshold: float = 0.90) -> list:
    """
    Detect near-duplicate message pairs using SequenceMatcher.
    Only compare within the same length bucket for efficiency.
    """
    messages = df[COL_MESSAGE].astype(str).tolist()
    labels = df[COL_LABEL].tolist()
    near_dups = []

    # Bucket by approximate length (±20 chars)
    buckets = {}
    for i, msg in enumerate(messages):
        bucket = len(msg) // 20
        for b in [bucket - 1, bucket, bucket + 1]:
            buckets.setdefault(b, []).append(i)

    seen_pairs = set()
    for bucket_indices in buckets.values():
        for a in range(len(bucket_indices)):
            for b in range(a + 1, len(bucket_indices)):
                i, j = bucket_indices[a], bucket_indices[b]
                if i == j:
                    continue
                pair = (min(i, j), max(i, j))
                if pair in seen_pairs:
                    continue
                seen_pairs.add(pair)

                ratio = SequenceMatcher(None, messages[i], messages[j]).ratio()
                if ratio >= threshold:
                    near_dups.append({
                        "idx_a": i,
                        "idx_b": j,
                        "similarity": round(ratio, 4),
                        "label_a": labels[i],
                        "label_b": labels[j],
                        "msg_a_snippet": messages[i][:80],
                        "msg_b_snippet": messages[j][:80],
                    })

    return near_dups


# ──────────────────────────────────────────────────────────────────────────────
def clean_dataset(df: pd.DataFrame) -> pd.DataFrame:
    """
    Remove exact duplicates, empty messages, and resolve conflicts.
    Returns a clean DataFrame.
    """
    original_len = len(df)

    # Strip whitespace
    df[COL_MESSAGE] = df[COL_MESSAGE].astype(str).str.strip()

    # Remove empty messages
    df = df[df[COL_MESSAGE].str.len() > 0].copy()

    # Remove exact duplicate rows (keep first)
    df = df.drop_duplicates(subset=[COL_MESSAGE], keep="first").copy()

    # Remove conflicting duplicates (keep first occurrence)
    df = df.drop_duplicates(subset=[COL_MESSAGE], keep="first").copy()

    df = df.reset_index(drop=True)
    print(f"[CLEAN] {original_len} -> {len(df)} rows "
          f"(removed {original_len - len(df)} duplicates/empty)")
    return df


# ──────────────────────────────────────────────────────────────────────────────
def save_audit_report(report: dict, near_dups: list) -> None:
    """Save audit report as JSON."""
    os.makedirs(REPORT_DIR, exist_ok=True)
    out = {"audit": report, "near_duplicates": near_dups}
    path = os.path.join(REPORT_DIR, "data_quality_report.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2, default=str)
    print(f"[REPORT] Data quality report saved -> {path}")


# ──────────────────────────────────────────────────────────────────────────────
def print_audit_summary(report: dict, near_dups: list) -> None:
    """Print a human-readable summary to stdout."""
    print("=" * 70)
    print("  DATA QUALITY REPORT")
    print("=" * 70)
    print(f"  Total rows:              {report['rows']}")
    print(f"  Exact duplicate rows:    {report['exact_duplicate_rows']}")
    print(f"  Duplicate messages:      {report['duplicate_message_count']}")
    print(f"  Conflicting duplicates: {len(report['conflicting_duplicates'])}")
    print(f"  Empty messages:          {report['empty_messages']}")
    print(f"  Very short (<15 chars):  {report['very_short_messages']}")
    print(f"  Messages with URLs:      {report['messages_with_urls']}")
    print(f"  Messages with currency:  {report['messages_with_currency']}")
    print(f"  Near-duplicate pairs (>=90% similar): {len(near_dups)}")
    print()
    print("  Label distribution:")
    for label, cnt in report["label_distribution"].items():
        pct = cnt / report["rows"] * 100
        print(f"    {label:8s}: {cnt:4d}  ({pct:.1f}%)")
    print()
    print("  Language distribution:")
    for lang, cnt in report["language_distribution"].items():
        pct = cnt / report["rows"] * 100
        print(f"    {lang:12s}: {cnt:4d}  ({pct:.1f}%)")
    print()
    print("  Category distribution:")
    for cat, cnt in report["category_distribution"].items():
        pct = cnt / report["rows"] * 100
        print(f"    {cat:18s}: {cnt:4d}  ({pct:.1f}%)")
    print()
    print("  Message length stats:")
    s = report["message_length_stats"]
    print(f"    mean={s['mean']}, median={s['median']}, "
          f"std={s['std']}, min={s['min']}, max={s['max']}")
    print("=" * 70)


# ──────────────────────────────────────────────────────────────────────────────
def run() -> pd.DataFrame:
    """Execute audit + clean and return the clean DataFrame."""
    print("\n[STEP 1] Loading dataset ...")
    df = load_dataset()
    print(f"  Loaded {len(df)} rows, {len(df.columns)} columns")

    print("\n[STEP 1] Running audit ...")
    report = audit(df)

    print("\n[STEP 2] Detecting near-duplicates ...")
    near_dups = detect_near_duplicates(df, threshold=0.90)

    print_audit_summary(report, near_dups)
    save_audit_report(report, near_dups)

    print("\n[STEP 2] Cleaning dataset ...")
    df_clean = clean_dataset(df)

    return df_clean
