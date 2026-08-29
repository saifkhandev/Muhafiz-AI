"""
External Validation V2 — Blind evaluation of the NEW retrained model
on the locked 1,000-message external phishing dataset.

CRITICAL: This script does NOT modify the model in any way.
It loads the saved model and runs pure evaluation.
"""
import sys, os, io, json, time
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

import numpy as np
import pandas as pd
import joblib
from datetime import datetime
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    roc_auc_score, confusion_matrix,
)

# ── Paths ────────────────────────────────────────────────────────────────────
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

MODEL_DIR = os.path.join(PROJECT_ROOT, "models")
REPORT_DIR = os.path.join(PROJECT_ROOT, "reports")
EXT_DATASET = r"C:\Users\Hp\Downloads\phishing_dataset_1000.xlsx"

# ── Load model artifacts (NO modification) ──────────────────────────────────
print("Loading model artifacts...")
pipeline = joblib.load(os.path.join(MODEL_DIR, "full_pipeline.joblib"))
threshold = joblib.load(os.path.join(MODEL_DIR, "threshold.joblib"))
le = joblib.load(os.path.join(MODEL_DIR, "label_encoder.joblib"))
metadata = joblib.load(os.path.join(MODEL_DIR, "model_metadata.joblib"))

print(f"  Model: {metadata.get('best_model_name', 'unknown')}")
print(f"  Threshold: {threshold}")
print(f"  Type: {metadata.get('model_type', 'unknown')}")

# ── Load external dataset ───────────────────────────────────────────────────
print(f"\nLoading external dataset: {EXT_DATASET}")
ext_df = pd.read_excel(EXT_DATASET)
print(f"  Columns: {list(ext_df.columns)}")
print(f"  Rows: {len(ext_df)}")

# Identify columns
text_col = "Raw_text"
label_col = "Labels"
id_col = "ID"

# Inspect
print(f"  Label distribution: {ext_df[label_col].value_counts().to_dict()}")
dupes = ext_df[text_col].duplicated().sum()
print(f"  Duplicates: {dupes}")

# Detect language per message (Source_Type is category, not language)
lang_col = "Detected_Language"

def detect_lang(text):
    """Detect whether a message is Roman Urdu, English, or Mixed.
    EXACT same logic as v1 external validation for consistency."""
    t = str(text).lower()
    # Urdu script characters
    if any('\u0600' <= c <= '\u06FF' for c in t):
        return "Urdu"
    roman_urdu_words = [
        "kya", "hai", "karo", "karein", "bhai", "apka", "mein", "mein",
        "ho", "ga", "gi", "ne", "ko", "se", "ka", "ki", "ke", "par",
        "bhej", "karin", "kren", "krn", "krain", "karein", "dain",
        "nahi", "wala", "wali", "waja", "taraf", "liye", "liay",
        "mubarak", "inaam", "ghar", "account", "bank"
    ]
    words = t.split()
    roman_count = sum(1 for w in words if w in roman_urdu_words)
    if roman_count >= 3:
        # Check if also has significant English
        eng_words = ["your", "the", "is", "are", "this", "for", "and",
                     "please", "thank", "has", "have", "been", "from",
                     "will", "not", "with", "our", "you", "was"]
        eng_count = sum(1 for w in words if w in eng_words)
        if eng_count >= 3 and roman_count >= 3:
            return "Mixed"
        return "Roman Urdu"
    # Mostly English
    return "English"

ext_df[lang_col] = ext_df[text_col].apply(detect_lang)
print(f"  Language detection applied.")
print(f"  Language distribution: {ext_df[lang_col].value_counts().to_dict()}")

# ── Map labels: 0=Safe, 1=Scam ─────────────────────────────────────────────
y_true = ext_df[label_col].values  # 0=Safe, 1=Scam
messages = ext_df[text_col].astype(str).values

# ── Run predictions ─────────────────────────────────────────────────────────
print(f"\nRunning predictions on {len(messages)} messages...")
t0 = time.time()

# Get raw predictions from pipeline
y_pred_raw = pipeline.predict(messages)

# Get probabilities
y_proba = None
if hasattr(pipeline, 'predict_proba'):
    y_proba = pipeline.predict_proba(messages)[:, 1]
elif hasattr(pipeline, 'decision_function'):
    df_vals = pipeline.decision_function(messages)
    y_proba = 1 / (1 + np.exp(-df_vals))  # sigmoid

# Apply threshold
if y_proba is not None:
    y_pred = (y_proba >= threshold).astype(int)
else:
    y_pred = y_pred_raw

elapsed_pred = time.time() - t0
print(f"  Predictions completed in {elapsed_pred:.1f}s")

# ── Calculate metrics ───────────────────────────────────────────────────────
print(f"\n{'='*70}")
print(f"  EXTERNAL VALIDATION V2 RESULTS")
print(f"{'='*70}")

accuracy = accuracy_score(y_true, y_pred)
precision = precision_score(y_true, y_pred, pos_label=1)
recall = recall_score(y_true, y_pred, pos_label=1)
f1 = f1_score(y_true, y_pred, pos_label=1)
try:
    roc_auc = roc_auc_score(y_true, y_proba) if y_proba is not None else None
except:
    roc_auc = None

cm = confusion_matrix(y_true, y_pred)
tn, fp, fn, tp = cm.ravel()

print(f"\n  Overall Performance (n={len(messages)}):")
print(f"  Accuracy:        {accuracy:.4f} ({accuracy*100:.2f}%)")
print(f"  Precision:       {precision:.4f} ({precision*100:.2f}%)")
print(f"  Scam Recall:     {recall:.4f} ({recall*100:.2f}%)")
print(f"  F1-Score:        {f1:.4f}")
print(f"  ROC-AUC:         {roc_auc:.4f}" if roc_auc else "  ROC-AUC: N/A")
print(f"  True Positives:  {tp}")
print(f"  True Negatives:  {tn}")
print(f"  False Positives: {fp}")
print(f"  False Negatives: {fn}")

print(f"\n  Confusion Matrix:")
print(f"  {'':20s} Predicted Safe  Predicted Scam")
print(f"  {'Actual Safe':20s} {tn:>14d}  {fp:>14d}")
print(f"  {'Actual Scam':20s} {fn:>14d}  {tp:>14d}")

# ── Language-specific performance ───────────────────────────────────────────
print(f"\n{'='*70}")
print(f"  LANGUAGE-SPECIFIC PERFORMANCE")
print(f"{'='*70}")

lang_results = {}
languages_present = ext_df[lang_col].unique() if lang_col else []

for lang in sorted(languages_present):
    mask = ext_df[lang_col] == lang
    n = mask.sum()
    if n < 2:
        continue
    yt = y_true[mask]
    yp = y_pred[mask]
    yp_proba = y_proba[mask] if y_proba is not None else None

    acc = accuracy_score(yt, yp)
    prec = precision_score(yt, yp, pos_label=1, zero_division=0)
    rec = recall_score(yt, yp, pos_label=1, zero_division=0)
    f1_lang = f1_score(yt, yp, pos_label=1, zero_division=0)
    try:
        auc = roc_auc_score(yt, yp_proba) if yp_proba is not None else None
    except:
        auc = None

    cm_lang = confusion_matrix(yt, yp, labels=[0, 1])
    tn_l, fp_l, fn_l, tp_l = cm_lang.ravel()

    lang_results[lang] = {
        "n": int(n), "accuracy": float(acc), "precision": float(prec),
        "recall": float(rec), "f1": float(f1_lang),
        "roc_auc": float(auc) if auc is not None else None,
        "TP": int(tp_l), "TN": int(tn_l),
        "FP": int(fp_l), "FN": int(fn_l),
    }
    print(f"\n  [{lang}] n={n}")
    print(f"    Accuracy:  {acc:.4f} ({acc*100:.2f}%)")
    print(f"    Precision: {prec:.4f}")
    print(f"    Recall:    {rec:.4f}")
    print(f"    F1:        {f1_lang:.4f}")
    print(f"    AUC:       {auc:.4f}" if auc else "    AUC: N/A")
    print(f"    FP={fp_l} FN={fn_l}")

# Check for missing languages
all_expected_langs = ["English", "Roman Urdu", "Urdu", "Mixed"]
missing_langs = [l for l in all_expected_langs if l not in languages_present]
if missing_langs:
    print(f"\n  NOTE: {', '.join(missing_langs)} were NOT present in this external dataset.")
    print(f"  {' and '.join(missing_langs)} were not externally validated by this dataset.")

# ── Comparison with OLD model ───────────────────────────────────────────────
print(f"\n{'='*70}")
print(f"  COMPARISON: OLD vs NEW MODEL (External Benchmark)")
print(f"{'='*70}")

old_results = {
    "accuracy": 0.8650,
    "recall": 0.7531,
    "f1": 0.8188,
    "roc_auc": 0.9586,
    "precision": 0.8971,
    "FP": 35, "FN": 100,
    "ru_accuracy": 0.7708,
    "ru_f1": 0.8168,
}

new_results = {
    "accuracy": accuracy,
    "recall": recall,
    "f1": f1,
    "roc_auc": roc_auc if roc_auc else 0,
    "precision": precision,
    "FP": fp, "FN": fn,
}
if "Roman Urdu" in lang_results:
    new_results["ru_accuracy"] = lang_results["Roman Urdu"]["accuracy"]
    new_results["ru_f1"] = lang_results["Roman Urdu"]["f1"]

comparison = [
    ("Accuracy", "accuracy", "%.4f"),
    ("Scam Recall", "recall", "%.4f"),
    ("F1", "f1", "%.4f"),
    ("ROC-AUC", "roc_auc", "%.4f"),
    ("Precision", "precision", "%.4f"),
    ("False Positives", "FP", "%d"),
    ("False Negatives", "FN", "%d"),
]

print(f"\n  {'Metric':20s} {'OLD':>10s} {'NEW':>10s} {'Change':>12s}")
print(f"  {'-'*52}")
for label, key, fmt in comparison:
    old_val = old_results.get(key, 0)
    new_val = new_results.get(key, 0)
    diff = new_val - old_val
    if key in ("FP", "FN"):
        sign = "+" if diff > 0 else ""
        print(f"  {label:20s} {old_val:>10d} {new_val:>10d} {sign}{diff:>10d}")
    else:
        sign = "+" if diff > 0 else ""
        print(f"  {label:20s} {old_val:>10.4f} {new_val:>10.4f} {sign}{diff:>10.4f}")

# Roman Urdu comparison
if "Roman Urdu" in lang_results:
    print(f"\n  {'Roman Urdu Metric':20s} {'OLD':>10s} {'NEW':>10s} {'Change':>12s}")
    print(f"  {'-'*52}")
    for label, key, fmt in [("Accuracy", "ru_accuracy", "%.4f"), ("F1", "ru_f1", "%.4f")]:
        old_val = old_results.get(key, 0)
        new_val = new_results.get(key, 0)
        diff = new_val - old_val
        sign = "+" if diff > 0 else ""
        print(f"  {label:20s} {old_val:>10.4f} {new_val:>10.4f} {sign}{diff:>10.4f}")

# ── Error analysis ──────────────────────────────────────────────────────────
print(f"\n{'='*70}")
print(f"  ERROR ANALYSIS")
print(f"{'='*70}")

errors = []
for i in range(len(ext_df)):
    if y_pred[i] != y_true[i]:
        lang = ext_df.iloc[i][lang_col] if lang_col else "Unknown"
        errors.append({
            "ID": ext_df.iloc[i][id_col] if id_col in ext_df.columns else i,
            "message": str(ext_df.iloc[i][text_col]),
            "true_label": "Scam" if y_true[i] == 1 else "Safe",
            "predicted_label": "Scam" if y_pred[i] == 1 else "Safe",
            "language": lang,
            "probability": float(y_proba[i]) if y_proba is not None else None,
            "error_type": "FN-missed-scam" if y_true[i] == 1 else "FP-safe-flagged",
        })

fn_errors = [e for e in errors if "FN" in e["error_type"]]
fp_errors = [e for e in errors if "FP" in e["error_type"]]

print(f"  Total errors: {len(errors)}")
print(f"  False Negatives (missed scams): {len(fn_errors)}")
print(f"  False Positives (safe flagged):  {len(fp_errors)}")

if fn_errors:
    print(f"\n  -- False Negatives (sample) --")
    for e in fn_errors[:15]:
        p_str = f"P={e['probability']:.4f}" if e['probability'] is not None else ""
        print(f"    ID={e['ID']} {p_str} Lang={e['language']}")
        print(f"    \"{e['message'][:100]}\"")

if fp_errors:
    print(f"\n  -- False Positives (sample) --")
    for e in fp_errors[:15]:
        p_str = f"P={e['probability']:.4f}" if e['probability'] is not None else ""
        print(f"    ID={e['ID']} {p_str} Lang={e['language']}")
        print(f"    \"{e['message'][:100]}\"")

# ── Save reports ────────────────────────────────────────────────────────────
print(f"\n{'='*70}")
print(f"  SAVING REPORTS")
print(f"{'='*70}")

os.makedirs(REPORT_DIR, exist_ok=True)

# 1. Predictions CSV
pred_df = pd.DataFrame({
    "ID": ext_df[id_col].values if id_col in ext_df.columns else range(len(ext_df)),
    "Message": messages,
    "Language": ext_df[lang_col].values,
    "True_Label": ["Scam" if y == 1 else "Safe" for y in y_true],
    "Predicted_Label": ["Scam" if y == 1 else "Safe" for y in y_pred],
    "Scam_Probability": [round(float(p), 4) if p is not None else None for p in y_proba] if y_proba is not None else [None]*len(y_pred),
    "Correct": [y_pred[i] == y_true[i] for i in range(len(y_true))],
})
pred_path = os.path.join(REPORT_DIR, "external_test_predictions_v2.csv")
pred_df.to_csv(pred_path, index=False)
print(f"  Saved: {pred_path}")

# 2. Confusion matrix CSV
cm_df = pd.DataFrame(cm, index=["Actual Safe", "Actual Scam"],
                     columns=["Predicted Safe", "Predicted Scam"])
cm_path = os.path.join(REPORT_DIR, "external_confusion_matrix_v2.csv")
cm_df.to_csv(cm_path)
print(f"  Saved: {cm_path}")

# 3. Error analysis CSV
err_df = pd.DataFrame(errors)
err_path = os.path.join(REPORT_DIR, "external_error_analysis_v2.csv")
err_df.to_csv(err_path, index=False)
print(f"  Saved: {err_path}")

# 4. Full report TXT
report_path = os.path.join(REPORT_DIR, "external_test_report_v2.txt")
with open(report_path, "w", encoding="utf-8") as f:
    f.write("EXTERNAL VALIDATION REPORT V2\n")
    f.write("=" * 70 + "\n")
    f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    f.write(f"Dataset: phishing_dataset_1000.xlsx ({len(ext_df)} messages)\n")
    f.write(f"Model: {metadata.get('best_model_name', 'unknown')} (full_pipeline.joblib)\n")
    f.write(f"Threshold: {threshold}\n")
    f.write(f"Model was NOT modified for this evaluation.\n\n")

    f.write("OVERALL PERFORMANCE\n")
    f.write("-" * 40 + "\n")
    f.write(f"Accuracy:        {accuracy:.4f} ({accuracy*100:.2f}%)\n")
    f.write(f"Precision:       {precision:.4f} ({precision*100:.2f}%)\n")
    f.write(f"Scam Recall:     {recall:.4f} ({recall*100:.2f}%)\n")
    f.write(f"F1-Score:        {f1:.4f}\n")
    f.write(f"ROC-AUC:         {roc_auc:.4f}\n" if roc_auc else "ROC-AUC: N/A\n")
    f.write(f"True Positives:  {tp}\n")
    f.write(f"True Negatives:  {tn}\n")
    f.write(f"False Positives: {fp}\n")
    f.write(f"False Negatives: {fn}\n\n")

    f.write("CONFUSION MATRIX\n")
    f.write("-" * 40 + "\n")
    f.write(f"{'':20s} Predicted Safe  Predicted Scam\n")
    f.write(f"{'Actual Safe':20s} {tn:>14d}  {fp:>14d}\n")
    f.write(f"{'Actual Scam':20s} {fn:>14d}  {tp:>14d}\n\n")

    f.write("PER-LANGUAGE PERFORMANCE\n")
    f.write("-" * 40 + "\n")
    for lang, lr in lang_results.items():
        f.write(f"[{lang}] n={lr['n']} Acc={lr['accuracy']:.4f} "
                f"P={lr['precision']:.4f} R={lr['recall']:.4f} F1={lr['f1']:.4f}")
        if lr['roc_auc']:
            f.write(f" AUC={lr['roc_auc']:.4f}")
        f.write(f" FP={lr['FP']} FN={lr['FN']}\n")

    if missing_langs:
        f.write(f"\n{', '.join(missing_langs)} were not externally validated by this dataset.\n")

    f.write(f"\nCOMPARISON WITH OLD MODEL\n")
    f.write("-" * 40 + "\n")
    f.write(f"{'Metric':20s} {'OLD':>10s} {'NEW':>10s} {'Change':>12s}\n")
    for label, key, fmt in comparison:
        old_val = old_results.get(key, 0)
        new_val = new_results.get(key, 0)
        diff = new_val - old_val
        if key in ("FP", "FN"):
            f.write(f"{label:20s} {old_val:>10d} {new_val:>10d} {diff:>+10d}\n")
        else:
            f.write(f"{label:20s} {old_val:>10.4f} {new_val:>10.4f} {diff:>+10.4f}\n")

    if "Roman Urdu" in lang_results:
        f.write(f"\nRoman Urdu:\n")
        f.write(f"  Accuracy: {old_results['ru_accuracy']:.4f} -> {new_results['ru_accuracy']:.4f} "
                f"(change: {new_results['ru_accuracy'] - old_results['ru_accuracy']:+.4f})\n")
        f.write(f"  F1:       {old_results['ru_f1']:.4f} -> {new_results['ru_f1']:.4f} "
                f"(change: {new_results['ru_f1'] - old_results['ru_f1']:+.4f})\n")

    f.write(f"\nVERDICT\n")
    f.write("-" * 40 + "\n")
    ru_improved = "Roman Urdu" in lang_results and lang_results["Roman Urdu"]["accuracy"] > old_results["ru_accuracy"]
    overall_improved = accuracy > old_results["accuracy"]
    f.write(f"1. Roman Urdu generalization improved: {ru_improved}\n")
    f.write(f"2. Overall external performance improved: {overall_improved}\n")
    f.write(f"3. Scams missed (FN): {fn}\n")
    f.write(f"4. FP reduced from {old_results['FP']} to {fp}\n")

print(f"  Saved: {report_path}")

# ── Final verdict ───────────────────────────────────────────────────────────
print(f"\n{'='*70}")
print(f"  FINAL VERDICT")
print(f"{'='*70}")

ru_improved = "Roman Urdu" in lang_results and lang_results["Roman Urdu"]["accuracy"] > old_results["ru_accuracy"]
overall_improved = accuracy > old_results["accuracy"]

print(f"\n  1. Did Roman Urdu generalization improve?")
if "Roman Urdu" in lang_results:
    ru_acc = lang_results["Roman Urdu"]["accuracy"]
    ru_old = old_results["ru_accuracy"]
    print(f"     {'YES' if ru_improved else 'NO'} — {ru_old*100:.2f}% -> {ru_acc*100:.2f}% "
          f"(change: {(ru_acc-ru_old)*100:+.2f}%)")
else:
    print(f"     N/A — Roman Urdu not found in dataset")

print(f"\n  2. Did overall external performance improve?")
print(f"     {'YES' if overall_improved else 'NO'} — {old_results['accuracy']*100:.2f}% -> {accuracy*100:.2f}% "
      f"(change: {(accuracy-old_results['accuracy'])*100:+.2f}%)")

print(f"\n  3. How many scams were missed?")
print(f"     {fn} false negatives (old: {old_results['FN']})")

print(f"\n  4. Is the new model ready for final AI integration?")
if overall_improved and ru_improved and fn < old_results["FN"]:
    print(f"     YES — Significant improvement across all key metrics")
elif overall_improved and ru_improved:
    print(f"     LIKELY — Performance improved but review remaining weaknesses")
else:
    print(f"     REVIEW NEEDED — See detailed comparison above")

print(f"\n  5. What remains to be externally validated?")
missing_str = ", ".join(missing_langs) if missing_langs else "None"
print(f"     Languages not in external dataset: {missing_str}")
print(f"     These were not externally validated by this dataset.")

print(f"\n{'='*70}")
print(f"  External validation complete. Model was NOT modified.")
print(f"{'='*70}")
