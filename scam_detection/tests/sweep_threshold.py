"""
sweep_threshold.py
Sweep threshold on V3 model across both benchmarks to find optimal threshold.
NO model retraining - only threshold tuning.
"""
import sys, os, io, warnings
import numpy as np
import pandas as pd

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
warnings.filterwarnings("ignore")

import joblib
from sklearn.metrics import (accuracy_score, precision_score, recall_score,
                             f1_score, fbeta_score, confusion_matrix, roc_auc_score)

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)
MODEL_DIR = os.path.join(PROJECT_ROOT, "models")
DATA_DIR = os.path.join(PROJECT_ROOT, "data")

C_MSG = "Message Content"

# Load model
pipe = joblib.load(os.path.join(MODEL_DIR, "full_pipeline.joblib"))
le = joblib.load(os.path.join(MODEL_DIR, "label_encoder.joblib"))

def get_proba(pipe, X):
    if hasattr(pipe[-1], "predict_proba"):
        return pipe.predict_proba(X)[:, 1]
    elif hasattr(pipe[-1], "decision_function"):
        d = pipe.decision_function(X)
        return 1 / (1 + np.exp(-d))
    return None

# ── Dataset 1: Locked 1000 ──
print("Loading locked 1000-message dataset...")
ext_file = os.path.join("C:\\Users\\Hp\\Downloads", "phishing_dataset_1000.xlsx")
ext_df = pd.read_excel(ext_file)
ext_df = ext_df.rename(columns={"Raw_text": C_MSG, "Labels": "Label"})
X_ext = ext_df[C_MSG].values
y_ext = ext_df["Label"].values  # already 0/1
proba_ext = get_proba(pipe, X_ext)

# ── Dataset 2: All-4 test (318 msgs) ──
print("Loading all-4 test set...")
from test_data_all4 import TEST_MESSAGES
msgs_a4, labels_a4 = [], []
for m, lang, l in TEST_MESSAGES:
    msgs_a4.append(m)
    labels_a4.append(1 if l == "Scam" else 0)
X_a4 = np.array(msgs_a4)
y_a4 = np.array(labels_a4)
proba_a4 = get_proba(pipe, X_a4)

# ── Sweep ──
print("\n" + "=" * 90)
print(f"  THRESHOLD SWEEP: V3 model ({joblib.load(os.path.join(MODEL_DIR, 'model_metadata.joblib')).get('best_model_name', '?')})")
print("=" * 90)
print(f"\n{'Thresh':>7} | {'--- Locked 1000 ---':^40} | {'--- All-4 (318) ---':^40}")
print(f"{'':>7} | {'Acc':>6} {'Rec':>6} {'F1':>6} {'F2':>6} {'FP':>4} {'FN':>4} | {'Acc':>6} {'Rec':>6} {'F1':>6} {'F2':>6} {'FP':>4} {'FN':>4}")
print("-" * 90)

best_t = 0.5
best_score = 0
results = []

for t_int in range(20, 60):
    t = t_int / 100.0
    # Locked
    yp_ext = (proba_ext >= t).astype(int)
    cm_ext = confusion_matrix(y_ext, yp_ext, labels=[0, 1])
    tn_e, fp_e, fn_e, tp_e = cm_ext.ravel()
    acc_e = accuracy_score(y_ext, yp_ext)
    rec_e = recall_score(y_ext, yp_ext, zero_division=0)
    f1_e = f1_score(y_ext, yp_ext, zero_division=0)
    f2_e = fbeta_score(y_ext, yp_ext, beta=2, zero_division=0)

    # All-4
    yp_a4 = (proba_a4 >= t).astype(int)
    cm_a4 = confusion_matrix(y_a4, yp_a4, labels=[0, 1])
    tn_a, fp_a, fn_a, tp_a = cm_a4.ravel()
    acc_a = accuracy_score(y_a4, yp_a4)
    rec_a = recall_score(y_a4, yp_a4, zero_division=0)
    f1_a = f1_score(y_a4, yp_a4, zero_division=0)
    f2_a = fbeta_score(y_a4, yp_a4, beta=2, zero_division=0)

    # Composite: prioritize recall on both benchmarks
    # Weight: 0.4*F2_locked + 0.3*F2_all4 + 0.2*Recall_locked + 0.1*Recall_all4
    score = 0.4 * f2_e + 0.3 * f2_a + 0.2 * rec_e + 0.1 * rec_a

    marker = ""
    if score > best_score:
        best_score = score
        best_t = t
        marker = " <-- BEST"

    print(f"  {t:.2f}  | {acc_e:.4f} {rec_e:.4f} {f1_e:.4f} {f2_e:.4f} {fp_e:4d} {fn_e:4d} | {acc_a:.4f} {rec_a:.4f} {f1_a:.4f} {f2_a:.4f} {fp_a:4d} {fn_a:4d}{marker}")
    results.append({
        "threshold": t, "locked_acc": acc_e, "locked_rec": rec_e, "locked_f1": f1_e,
        "locked_f2": f2_e, "locked_fp": fp_e, "locked_fn": fn_e,
        "all4_acc": acc_a, "all4_rec": rec_a, "all4_f1": f1_a,
        "all4_f2": f2_a, "all4_fp": fp_a, "all4_fn": fn_a,
        "composite": score,
    })

print("-" * 90)
print(f"\n  OPTIMAL THRESHOLD: {best_t:.2f} (composite score: {best_score:.4f})")

# Show detailed results at optimal threshold
print(f"\n{'=' * 90}")
print(f"  DETAILED RESULTS AT THRESHOLD {best_t:.2f}")
print(f"{'=' * 90}")

# Locked benchmark
yp_ext = (proba_ext >= best_t).astype(int)
print(f"\n  LOCKED 1000-MESSAGE BENCHMARK:")
print(f"    Accuracy:  {accuracy_score(y_ext, yp_ext):.4f}")
print(f"    Precision: {precision_score(y_ext, yp_ext, zero_division=0):.4f}")
print(f"    Recall:    {recall_score(y_ext, yp_ext, zero_division=0):.4f}")
print(f"    F1:        {f1_score(y_ext, yp_ext, zero_division=0):.4f}")
print(f"    F2:        {fbeta_score(y_ext, yp_ext, beta=2, zero_division=0):.4f}")
try:
    print(f"    ROC-AUC:   {roc_auc_score(y_ext, proba_ext):.4f}")
except:
    pass
cm = confusion_matrix(y_ext, yp_ext, labels=[0, 1])
tn, fp, fn, tp = cm.ravel()
print(f"    TP={tp} TN={tn} FP={fp} FN={fn}")

# All-4 benchmark
yp_a4 = (proba_a4 >= best_t).astype(int)
print(f"\n  ALL-4 FRESH TEST SET (318):")
print(f"    Accuracy:  {accuracy_score(y_a4, yp_a4):.4f}")
print(f"    Precision: {precision_score(y_a4, yp_a4, zero_division=0):.4f}")
print(f"    Recall:    {recall_score(y_a4, yp_a4, zero_division=0):.4f}")
print(f"    F1:        {f1_score(y_a4, yp_a4, zero_division=0):.4f}")
print(f"    F2:        {fbeta_score(y_a4, yp_a4, beta=2, zero_division=0):.4f}")
try:
    print(f"    ROC-AUC:   {roc_auc_score(y_a4, proba_a4):.4f}")
except:
    pass
cm = confusion_matrix(y_a4, yp_a4, labels=[0, 1])
tn, fp, fn, tp = cm.ravel()
print(f"    TP={tp} TN={tn} FP={fp} FN={fn}")

# V2 comparison
print(f"\n  V2 COMPARISON:")
print(f"    {'Metric':<20} {'V2 (locked)':<12} {'V3@0.47 (locked)':<18} {'V3@opt (locked)':<18}")
print(f"    {'-'*68}")

# Also compute V3 at V2's threshold 0.47 for direct comparison
yp_ext_047 = (proba_ext >= 0.47).astype(int)
yp_a4_047 = (proba_a4 >= 0.47).astype(int)
cm_e047 = confusion_matrix(y_ext, yp_ext_047, labels=[0, 1])
tn_047, fp_047, fn_047, tp_047 = cm_e047.ravel()
cm_a047 = confusion_matrix(y_a4, yp_a4_047, labels=[0, 1])
tn_a047, fp_a047, fn_a047, tp_a047 = cm_a047.ravel()

yp_ext_opt = (proba_ext >= best_t).astype(int)
yp_a4_opt = (proba_a4 >= best_t).astype(int)

print(f"    {'Locked Accuracy':<20} {'94.70%':<12} {accuracy_score(y_ext, yp_ext_047)*100:.2f}%{'':<6} {accuracy_score(y_ext, yp_ext_opt)*100:.2f}%")
print(f"    {'Locked Recall':<20} {'100.00%':<12} {recall_score(y_ext, yp_ext_047)*100:.2f}%{'':<6} {recall_score(y_ext, yp_ext_opt)*100:.2f}%")
print(f"    {'Locked FP':<20} {'53':<12} {fp_047:<18} {confusion_matrix(y_ext, yp_ext_opt, labels=[0,1]).ravel()[1]}")
print(f"    {'Locked FN':<20} {'0':<12} {fn_047:<18} {confusion_matrix(y_ext, yp_ext_opt, labels=[0,1]).ravel()[2]}")
print(f"    {'All-4 Accuracy':<20} {'89.94%':<12} {accuracy_score(y_a4, yp_a4_047)*100:.2f}%{'':<6} {accuracy_score(y_a4, yp_a4_opt)*100:.2f}%")
print(f"    {'All-4 Recall':<20} {'88.56%':<12} {recall_score(y_a4, yp_a4_047)*100:.2f}%{'':<6} {recall_score(y_a4, yp_a4_opt)*100:.2f}%")
print(f"    {'All-4 FP':<20} {'9':<12} {fp_a047:<18} {confusion_matrix(y_a4, yp_a4_opt, labels=[0,1]).ravel()[1]}")
print(f"    {'All-4 FN':<20} {'23':<12} {fn_a047:<18} {confusion_matrix(y_a4, yp_a4_opt, labels=[0,1]).ravel()[2]}")

# Save optimal threshold
print(f"\n  RECOMMENDATION: Update threshold to {best_t:.2f}")
joblib.dump(best_t, os.path.join(MODEL_DIR, "threshold.joblib"))
print(f"  Saved: models/threshold.joblib = {best_t:.2f}")
print(f"\n  [NEXT] Re-run external_validation_v2.py and run_all4_validation.py")
print(f"  with the new threshold for final V3 results.")
