"""Evaluate labeled call transcripts without the variability of speech recognition."""
import json
import sys
from collections import defaultdict
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.call_predict import predict_call_from_transcript
from src.predict import load_model

FIXTURE_PATH = PROJECT_ROOT / "tests" / "fixtures" / "verified_call_transcripts.json"
REPORT_PATH = PROJECT_ROOT / "reports" / "call_transcript_benchmark.json"
REQUIRED_FIELDS = {"id", "label", "category", "transcript"}


def _safe_divide(numerator, denominator):
    return numerator / denominator if denominator else 0.0


def _metrics(rows):
    tp = sum(row["label"] == "Scam" and row["binary_prediction"] == "Scam" for row in rows)
    fp = sum(row["label"] == "Safe" and row["binary_prediction"] == "Scam" for row in rows)
    tn = sum(row["label"] == "Safe" and row["binary_prediction"] == "Safe" for row in rows)
    fn = sum(row["label"] == "Scam" and row["binary_prediction"] == "Safe" for row in rows)
    precision = _safe_divide(tp, tp + fp)
    recall = _safe_divide(tp, tp + fn)
    return {
        "total": len(rows),
        "accuracy": round(_safe_divide(tp + tn, len(rows)), 4),
        "scam_precision": round(precision, 4),
        "scam_recall": round(recall, 4),
        "f1": round(_safe_divide(2 * precision * recall, precision + recall), 4),
        "confusion_matrix": {"tp": tp, "fp": fp, "tn": tn, "fn": fn},
    }


def _load_records():
    with FIXTURE_PATH.open("r", encoding="utf-8") as fixture_file:
        fixture = json.load(fixture_file)
    if fixture.get("schema_version") != 1:
        raise ValueError("Fixture schema_version must be 1")
    records = fixture.get("records", [])
    ids = set()
    for index, record in enumerate(records):
        missing = REQUIRED_FIELDS.difference(record)
        if missing:
            raise ValueError(f"Record {index} is missing fields: {sorted(missing)}")
        if record["id"] in ids:
            raise ValueError(f"Duplicate fixture ID: {record['id']}")
        if record["label"] not in {"Scam", "Safe"}:
            raise ValueError(f"Record {record['id']} has an invalid label")
        ids.add(record["id"])
    return records


def main():
    records = _load_records()
    report = {
        "fixture": str(FIXTURE_PATH.relative_to(PROJECT_ROOT)),
        "status": "awaiting_labeled_records" if not records else "complete",
        "record_count": len(records),
    }
    if records:
        artifacts, label_encoder, threshold, metadata = load_model()
        rows = []
        for record in records:
            result = predict_call_from_transcript(
                record["transcript"],
                artifacts=artifacts,
                le=label_encoder,
                threshold=threshold,
                metadata=metadata,
            )
            rows.append({
                "id": record["id"],
                "label": record["label"],
                "category": record["category"],
                "risk_prediction": result["overall_risk"],
                "binary_prediction": "Scam" if result["overall_risk"] != "Low" else "Safe",
                "risk_score": result["risk_score"],
                "max_segment_probability": result["max_segment_probability"],
                "call_patterns": result["call_patterns"],
                "timings": result["timings"],
            })
        by_category = defaultdict(list)
        for row in rows:
            by_category[row["category"]].append(row)
        report.update({
            "model": metadata.get("version", metadata.get("best_model_name", "unknown")),
            "threshold": threshold,
            "metrics": _metrics(rows),
            "by_category": {key: _metrics(value) for key, value in sorted(by_category.items())},
            "high_risk_misses": [
                row for row in rows
                if row["label"] == "Scam" and row["risk_prediction"] != "High"
            ],
            "false_negatives": [
                row for row in rows
                if row["label"] == "Scam" and row["binary_prediction"] == "Safe"
            ],
            "false_positives": [
                row for row in rows
                if row["label"] == "Safe" and row["binary_prediction"] == "Scam"
            ],
            "rows": rows,
        })

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with REPORT_PATH.open("w", encoding="utf-8") as report_file:
        json.dump(report, report_file, ensure_ascii=False, indent=2)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
