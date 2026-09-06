"""Run an independent, labeled text fixture against the deployed V4 artifacts."""
import argparse
import json
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.predict import load_model, predict_messages

FIXTURE_PATH = PROJECT_ROOT / "tests" / "fixtures" / "amaan_heldout_messages.json"
REPORT_PATH = PROJECT_ROOT / "reports" / "heldout_text_benchmark.json"
REQUIRED_FIELDS = {"id", "text", "label", "language", "category"}
VALID_LABELS = {"Scam", "Safe"}


def _safe_divide(numerator, denominator):
    return numerator / denominator if denominator else 0.0


def _metrics(rows, prediction_key="label"):
    tp = sum(row["label"] == "Scam" and row[prediction_key] == "Scam" for row in rows)
    fp = sum(row["label"] == "Safe" and row[prediction_key] == "Scam" for row in rows)
    tn = sum(row["label"] == "Safe" and row[prediction_key] == "Safe" for row in rows)
    fn = sum(row["label"] == "Scam" and row[prediction_key] == "Safe" for row in rows)
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


def _breakdown(rows, field):
    grouped = defaultdict(list)
    for row in rows:
        grouped[row[field]].append(row)
    return {key: _metrics(group) for key, group in sorted(grouped.items())}


def _load_fixture(path):
    with path.open("r", encoding="utf-8") as fixture_file:
        fixture = json.load(fixture_file)
    if fixture.get("schema_version") != 1:
        raise ValueError("Fixture schema_version must be 1")

    records = fixture.get("records", [])
    seen_ids = set()
    for index, record in enumerate(records):
        missing = REQUIRED_FIELDS.difference(record)
        if missing:
            raise ValueError(f"Record {index} is missing fields: {sorted(missing)}")
        if record["id"] in seen_ids:
            raise ValueError(f"Duplicate fixture ID: {record['id']}")
        if record["label"] not in VALID_LABELS:
            raise ValueError(f"Record {record['id']} has invalid label: {record['label']}")
        if not all(isinstance(record[field], str) and record[field].strip() for field in REQUIRED_FIELDS):
            raise ValueError(f"Record {record['id']} has an empty required value")
        seen_ids.add(record["id"])
    return records


def run_benchmark(fixture_path=FIXTURE_PATH, output_path=REPORT_PATH):
    records = _load_fixture(fixture_path)
    report = {
        "fixture": str(fixture_path.relative_to(PROJECT_ROOT)),
        "status": "awaiting_labeled_records" if not records else "complete",
        "record_count": len(records),
    }
    if records:
        artifacts, label_encoder, threshold, metadata = load_model()
        predictions = predict_messages(
            [record["text"] for record in records],
            artifacts=artifacts,
            le=label_encoder,
            threshold=threshold,
            metadata=metadata,
        )
        rows = []
        for record, prediction in zip(records, predictions):
            rows.append({
                **record,
                "prediction": prediction["label"],
                "base_prediction": prediction["base_label"],
                "scam_probability": prediction["scam_probability"],
                "base_scam_probability": prediction["base_scam_probability"],
                "guardrail": prediction["guardrail"],
                "guardrail_changed_prediction": prediction["guardrail_changed_prediction"],
            })

        report.update({
            "model": metadata.get("version", metadata.get("best_model_name", "unknown")),
            "threshold": threshold,
            "final_metrics": _metrics(rows, "prediction"),
            "base_model_metrics": _metrics(rows, "base_prediction"),
            "by_language": _breakdown(rows, "language"),
            "by_category": _breakdown(rows, "category"),
            "guardrail_usage": dict(Counter(row["guardrail"] or "none" for row in rows)),
            "guardrail_changes": [
                row for row in rows if row["guardrail_changed_prediction"]
            ],
            "false_negatives": [
                row for row in rows
                if row["label"] == "Scam" and row["prediction"] == "Safe"
            ],
            "false_positives": [
                row for row in rows
                if row["label"] == "Safe" and row["prediction"] == "Scam"
            ],
        })

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as output_file:
        json.dump(report, output_file, ensure_ascii=False, indent=2)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", type=Path, default=FIXTURE_PATH)
    parser.add_argument("--output", type=Path, default=REPORT_PATH)
    args = parser.parse_args()
    report = run_benchmark(args.fixture, args.output)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
