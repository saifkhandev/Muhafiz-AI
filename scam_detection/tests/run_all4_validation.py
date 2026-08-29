"""
All-4-Language Blind Validation of V2 Scam Detection Model.
Loads the saved model and runs predictions on 300 test messages
across English, Urdu, Roman Urdu, and Mixed.
NO retraining, fine-tuning, or model modification.
"""
import sys, os, io, time, warnings
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

warnings.filterwarnings("ignore")

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

# ── Load test data ──────────────────────────────────────────────────────────
from test_data_all4 import TEST_MESSAGES

print(f"Loaded {len(TEST_MESSAGES)} test messages")

messages = [m[0] for m in TEST_MESSAGES]
languages = [m[1] for m in TEST_MESSAGES]
labels_str = [m[2] for m in TEST_MESSAGES]
y_true = np.array([1 if l == "Scam" else 0 for l in labels_str])

# Language distribution
lang_series = pd.Series(languages)
print(f"\nLanguage distribution:")
for lang, cnt in lang_series.value_counts().items():
    scam_n = sum(1 for i in range(len(TEST_MESSAGES)) if languages[i] == lang and labels_str[i] == "Scam")
    safe_n = cnt - scam_n
    print(f"  {lang}: {cnt} (Scam={scam_n}, Safe={safe_n})")

# ── Load model (NO modification) ────────────────────────────────────────────
print(f"\nLoading model artifacts...")
pipeline = joblib.load(os.path.join(MODEL_DIR, "full_pipeline.joblib"))
threshold = joblib.load(os.path.join(MODEL_DIR, "threshold.joblib"))
le = joblib.load(os.path.join(MODEL_DIR, "label_encoder.joblib"))
metadata = joblib.load(os.path.join(MODEL_DIR, "model_metadata.joblib"))

print(f"  Model: {metadata.get('best_model_name', 'unknown')}")
print(f"  Threshold: {threshold}")

# ── Run predictions ─────────────────────────────────────────────────────────
print(f"\nRunning predictions on {len(messages)} messages...")
t0 = time.time()

y_pred_raw = pipeline.predict(messages)

y_proba = None
if hasattr(pipeline, 'predict_proba'):
    y_proba = pipeline.predict_proba(messages)[:, 1]
elif hasattr(pipeline, 'decision_function'):
    df_vals = pipeline.decision_function(messages)
    y_proba = 1 / (1 + np.exp(-df_vals))

y_pred = (y_proba >= threshold).astype(int) if y_proba is not None else y_pred_raw

elapsed = time.time() - t0
print(f"  Completed in {elapsed:.1f}s")

# ── Overall metrics ─────────────────────────────────────────────────────────
print(f"\n{'='*70}")
print(f"  OVERALL PERFORMANCE (n={len(messages)})")
print(f"{'='*70}")

accuracy = accuracy_score(y_true, y_pred)
precision = precision_score(y_true, y_pred, pos_label=1)
recall = recall_score(y_true, y_pred, pos_label=1)
f1 = f1_score(y_true, y_pred, pos_label=1)
try:
    roc_auc = roc_auc_score(y_true, y_proba) if y_proba is not None else None
except:
    roc_auc = None

cm = confusion_matrix(y_true, y_pred, labels=[0, 1])
tn, fp, fn, tp = cm.ravel()

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
print(f"  {'':20s} Pred Safe  Pred Scam")
print(f"  {'Actual Safe':20s} {tn:>10d}  {fp:>10d}")
print(f"  {'Actual Scam':20s} {fn:>10d}  {tp:>10d}")

# ── Per-language metrics ────────────────────────────────────────────────────
print(f"\n{'='*70}")
print(f"  PER-LANGUAGE PERFORMANCE")
print(f"{'='*70}")

lang_results = {}
for lang in ["English", "Urdu", "Roman Urdu", "Mixed"]:
    mask = np.array([l == lang for l in languages])
    n = mask.sum()
    if n == 0:
        continue
    yt = y_true[mask]
    yp = y_pred[mask]
    yp_proba = y_proba[mask] if y_proba is not None else None

    scam_n = int((yt == 1).sum())
    safe_n = int((yt == 0).sum())

    acc = accuracy_score(yt, yp)
    prec = precision_score(yt, yp, pos_label=1, zero_division=0)
    rec = recall_score(yt, yp, pos_label=1, zero_division=0)
    f1_l = f1_score(yt, yp, pos_label=1, zero_division=0)
    try:
        auc = roc_auc_score(yt, yp_proba) if yp_proba is not None and len(np.unique(yt)) > 1 else None
    except:
        auc = None

    cm_l = confusion_matrix(yt, yp, labels=[0, 1])
    tn_l, fp_l, fn_l, tp_l = cm_l.ravel()

    lang_results[lang] = {
        "n": int(n), "scam": scam_n, "safe": safe_n,
        "accuracy": float(acc), "precision": float(prec),
        "recall": float(rec), "f1": float(f1_l),
        "roc_auc": float(auc) if auc is not None and not np.isnan(auc) else None,
        "TP": int(tp_l), "TN": int(tn_l),
        "FP": int(fp_l), "FN": int(fn_l),
    }

    print(f"\n  [{lang}] n={n} (Scam={scam_n}, Safe={safe_n})")
    print(f"    Accuracy:  {acc:.4f} ({acc*100:.2f}%)")
    print(f"    Precision: {prec:.4f}")
    print(f"    Recall:    {rec:.4f}")
    print(f"    F1:        {f1_l:.4f}")
    if auc is not None and not np.isnan(auc):
        print(f"    AUC:       {auc:.4f}")
    else:
        print(f"    AUC:       N/A")
    print(f"    FP={fp_l}  FN={fn_l}")

# ── Error analysis ──────────────────────────────────────────────────────────
print(f"\n{'='*70}")
print(f"  ERROR ANALYSIS")
print(f"{'='*70}")

errors = []
for i in range(len(messages)):
    if y_pred[i] != y_true[i]:
        errors.append({
            "ID": i + 1,
            "message": messages[i],
            "language": languages[i],
            "true_label": "Scam" if y_true[i] == 1 else "Safe",
            "predicted_label": "Scam" if y_pred[i] == 1 else "Safe",
            "probability": float(y_proba[i]) if y_proba is not None else None,
            "error_type": "FN-missed-scam" if y_true[i] == 1 else "FP-safe-flagged",
        })

fn_errors = [e for e in errors if "FN" in e["error_type"]]
fp_errors = [e for e in errors if "FP" in e["error_type"]]

print(f"  Total errors: {len(errors)}")
print(f"  False Negatives (missed scams): {len(fn_errors)}")
print(f"  False Positives (safe flagged): {len(fp_errors)}")

# FP by language
fp_by_lang = {}
for e in fp_errors:
    fp_by_lang.setdefault(e["language"], []).append(e)

print(f"\n  -- False Positives by Language --")
for lang, errs in sorted(fp_by_lang.items()):
    print(f"    {lang}: {len(errs)}")
    for e in errs[:5]:
        p_str = f"P={e['probability']:.4f}" if e['probability'] is not None else ""
        print(f"      ID={e['ID']} {p_str}")
        print(f"      \"{e['message'][:100]}\"")

# FN by language
fn_by_lang = {}
for e in fn_errors:
    fn_by_lang.setdefault(e["language"], []).append(e)

if fn_errors:
    print(f"\n  -- False Negatives by Language --")
    for lang, errs in sorted(fn_by_lang.items()):
        print(f"    {lang}: {len(errs)}")
        for e in errs[:10]:
            p_str = f"P={e['probability']:.4f}" if e['probability'] is not None else ""
            print(f"      ID={e['ID']} {p_str}")
            print(f"      \"{e['message'][:100]}\"")

# ── Save reports ────────────────────────────────────────────────────────────
print(f"\n{'='*70}")
print(f"  SAVING REPORTS")
print(f"{'='*70}")

os.makedirs(REPORT_DIR, exist_ok=True)

# 1. Predictions CSV
pred_df = pd.DataFrame({
    "ID": range(1, len(messages) + 1),
    "Message": messages,
    "Language": languages,
    "Actual_Label": ["Scam" if y == 1 else "Safe" for y in y_true],
    "Predicted_Label": ["Scam" if y == 1 else "Safe" for y in y_pred],
    "Scam_Probability": [round(float(p), 4) if p is not None else None for p in y_proba] if y_proba is not None else [None]*len(y_pred),
    "Correct": [y_pred[i] == y_true[i] for i in range(len(y_true))],
})
p1 = os.path.join(REPORT_DIR, "all4_external_test_predictions.csv")
pred_df.to_csv(p1, index=False)
print(f"  Saved: {p1}")

# 2. Confusion matrix CSV
cm_df = pd.DataFrame(cm, index=["Actual Safe", "Actual Scam"],
                     columns=["Predicted Safe", "Predicted Scam"])
p2 = os.path.join(REPORT_DIR, "all4_external_confusion_matrix.csv")
cm_df.to_csv(p2)
print(f"  Saved: {p2}")

# 3. Error analysis CSV
err_df = pd.DataFrame(errors)
p3 = os.path.join(REPORT_DIR, "all4_external_error_analysis.csv")
err_df.to_csv(p3, index=False)
print(f"  Saved: {p3}")

# 4. Full report
p4 = os.path.join(REPORT_DIR, "all4_external_test_report.txt")
with open(p4, "w", encoding="utf-8") as f:
    f.write("ALL-4-LANGUAGE BLIND VALIDATION REPORT\n")
    f.write("=" * 70 + "\n")
    f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    f.write(f"Test Set: {len(messages)} fresh messages (not from training or benchmarks)\n")
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
    f.write(f"{'':20s} Pred Safe  Pred Scam\n")
    f.write(f"{'Actual Safe':20s} {tn:>10d}  {fp:>10d}\n")
    f.write(f"{'Actual Scam':20s} {fn:>10d}  {tp:>10d}\n\n")

    f.write("PER-LANGUAGE PERFORMANCE\n")
    f.write("-" * 40 + "\n")
    for lang, lr in lang_results.items():
        f.write(f"\n[{lang}] n={lr['n']} (Scam={lr['scam']}, Safe={lr['safe']})\n")
        f.write(f"  Accuracy:  {lr['accuracy']:.4f} ({lr['accuracy']*100:.2f}%)\n")
        f.write(f"  Precision: {lr['precision']:.4f}\n")
        f.write(f"  Recall:    {lr['recall']:.4f}\n")
        f.write(f"  F1:        {lr['f1']:.4f}\n")
        if lr['roc_auc'] is not None:
            f.write(f"  AUC:       {lr['roc_auc']:.4f}\n")
        else:
            f.write(f"  AUC:       N/A\n")
        f.write(f"  FP={lr['FP']}  FN={lr['FN']}\n")

    f.write(f"\nERROR ANALYSIS\n")
    f.write("-" * 40 + "\n")
    f.write(f"Total errors: {len(errors)}\n")
    f.write(f"False Negatives (missed scams): {len(fn_errors)}\n")
    f.write(f"False Positives (safe flagged): {len(fp_errors)}\n\n")

    if fn_errors:
        f.write("False Negatives (detail):\n")
        for e in fn_errors:
            f.write(f"  ID={e['ID']} Lang={e['language']} P={e['probability']:.4f}\n")
            f.write(f"    \"{e['message'][:120]}\"\n")
        f.write("\n")

    if fp_errors:
        f.write("False Positives (detail):\n")
        for e in fp_errors:
            f.write(f"  ID={e['ID']} Lang={e['language']} P={e['probability']:.4f}\n")
            f.write(f"    \"{e['message'][:120]}\"\n")
        f.write("\n")

    # Answer key questions
    f.write("KEY QUESTIONS\n")
    f.write("-" * 40 + "\n")
    f.write(f"1. Overall performance: {accuracy*100:.2f}% accuracy, {f1:.4f} F1, {recall*100:.2f}% recall\n")
    for lang in ["English", "Urdu", "Roman Urdu", "Mixed"]:
        if lang in lang_results:
            lr = lang_results[lang]
            f.write(f"{'2345'[['English','Urdu','Roman Urdu','Mixed'].index(lang)]}. {lang}: {lr['accuracy']*100:.2f}% accuracy, {lr['f1']:.4f} F1, FP={lr['FP']}, FN={lr['FN']}\n")

    weakest = min(lang_results.items(), key=lambda x: x[1]["accuracy"])
    f.write(f"6. Weakest language: {weakest[0]} ({weakest[1]['accuracy']*100:.2f}%)\n")
    f.write(f"7. Scams missed (FN): {fn}\n")
    f.write(f"8. Safe falsely flagged (FP): {fp}\n")
    f.write(f"9. Ready for AI integration: {'YES' if recall >= 0.95 and fn <= 3 else 'NEEDS REVIEW'}\n")

print(f"  Saved: {p4}")

# ── Final summary ───────────────────────────────────────────────────────────
print(f"\n{'='*70}")
print(f"  KEY QUESTIONS — ANSWERS")
print(f"{'='*70}")

print(f"\n  1. Overall performance: {accuracy*100:.2f}% accuracy, {f1:.4f} F1, {recall*100:.2f}% scam recall")

for idx, lang in enumerate(["English", "Urdu", "Roman Urdu", "Mixed"], 2):
    if lang in lang_results:
        lr = lang_results[lang]
        print(f"  {idx}. {lang}: {lr['accuracy']*100:.2f}% accuracy, F1={lr['f1']:.4f}, "
              f"FP={lr['FP']}, FN={lr['FN']}")

weakest = min(lang_results.items(), key=lambda x: x[1]["accuracy"])
print(f"\n  6. Weakest language: {weakest[0]} ({weakest[1]['accuracy']*100:.2f}%)")
print(f"  7. Scams missed (FN): {fn}")
print(f"  8. Safe falsely flagged (FP): {fp}")
print(f"  9. Ready for AI integration: {'YES' if recall >= 0.95 and fn <= 3 else 'NEEDS REVIEW'}")

print(f"\n{'='*70}")
print(f"  All-4-language validation complete. Model was NOT modified.")
print(f"{'='*70}")
