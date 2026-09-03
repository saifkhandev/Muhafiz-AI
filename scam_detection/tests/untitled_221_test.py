"""
Adversarial evaluation on the Untitled-221 dataset.
221 realistic Pakistani scam/safe messages across 13 categories and 4 difficulty levels.
"""
import sys, os, warnings
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
warnings.filterwarnings("ignore")

import pandas as pd
import numpy as np

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)
from src.predict import predict_message, load_model

FILE_PATH = os.path.join(PROJECT_ROOT, "data", "adversarial_untitled_221.xlsx")
SHEET_NAME = "Dataset"


def main():
    df = pd.read_excel(FILE_PATH, sheet_name=SHEET_NAME)
    artifacts, le, threshold, metadata = load_model()

    results = []
    for _, row in df.iterrows():
        text = str(row["Message Text"])
        result = predict_message(text, artifacts=artifacts, le=le, threshold=threshold, metadata=metadata)
        results.append({
            "id": row["ID"],
            "true": row["Label"],
            "pred": result["label"],
            "prob": result["scam_probability"],
            "difficulty": row["Difficulty"],
            "category": row["Category"],
            "guardrail": result.get("guardrail"),
        })

    rdf = pd.DataFrame(results)
    tp = ((rdf["true"] == "Scam") & (rdf["pred"] == "Scam")).sum()
    fp = ((rdf["true"] == "Safe") & (rdf["pred"] == "Scam")).sum()
    tn = ((rdf["true"] == "Safe") & (rdf["pred"] == "Safe")).sum()
    fn = ((rdf["true"] == "Scam") & (rdf["pred"] == "Safe")).sum()

    accuracy = (tp + tn) / len(rdf) * 100
    precision = tp / (tp + fp) * 100 if (tp + fp) > 0 else 0
    recall = tp / (tp + fn) * 100 if (tp + fn) > 0 else 0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
    fpr = fp / (fp + tn) * 100 if (fp + tn) > 0 else 0

    print("=" * 80)
    print("  UNTITLED-221 ADVERSARIAL EVALUATION")
    print("=" * 80)
    print(f"  Total messages: {len(rdf)}")
    print(f"  Accuracy:  {accuracy:.2f}%")
    print(f"  Precision: {precision:.2f}%")
    print(f"  Recall:    {recall:.2f}%")
    print(f"  F1-Score:  {f1:.2f}%")
    print(f"  FPR:       {fpr:.2f}%")
    print(f"  TP={tp} FP={fp} TN={tn} FN={fn}")

    print("\n  Difficulty breakdown:")
    for diff in ["Easy", "Medium", "Hard", "Very Hard"]:
        sub = rdf[rdf["difficulty"] == diff]
        if len(sub) == 0:
            continue
        correct = (sub["true"] == sub["pred"]).sum()
        print(f"    {diff:<12s}: {correct}/{len(sub)} ({correct/len(sub)*100:.1f}%)")

    print("\n  Category breakdown:")
    for cat in sorted(rdf["category"].unique()):
        sub = rdf[rdf["category"] == cat]
        correct = (sub["true"] == sub["pred"]).sum()
        print(f"    {cat:<25s}: {correct}/{len(sub)} ({correct/len(sub)*100:.1f}%)")

    # Guardrail usage
    print("\n  Guardrail usage:")
    for rule, count in rdf["guardrail"].value_counts(dropna=False).items():
        print(f"    {rule}: {count}")

    # Save results
    out_path = os.path.join(PROJECT_ROOT, "reports", "untitled_221_results.json")
    rdf.to_json(out_path, orient="records", indent=2, force_ascii=False)
    print(f"\n  Results saved to: {out_path}")


if __name__ == "__main__":
    main()
