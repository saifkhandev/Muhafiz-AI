"""
EXTERNAL VALIDATION: Blind test of trained scam detection model
on 1000-message phishing dataset. NO retraining or modification.
"""
import sys, os, warnings
warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np
import joblib
import sys as _sys
from datetime import datetime

# Fix Windows console encoding
if _sys.platform == 'win32':
    import io
    _sys.stdout = io.TextIOWrapper(_sys.stdout.buffer, encoding='utf-8', errors='replace')
    _sys.stderr = io.TextIOWrapper(_sys.stderr.buffer, encoding='utf-8', errors='replace')
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    roc_auc_score, confusion_matrix, classification_report
)

# ═══════════════════════════════════════════════════════════════════
#  STEP 1: LOAD EXTERNAL DATASET
# ═══════════════════════════════════════════════════════════════════
print("=" * 70)
print("  EXTERNAL VALIDATION: Blind Test on Unseen Phishing Dataset")
print("=" * 70)

EXT_PATH = r"C:\Users\Hp\Downloads\phishing_dataset_1000.xlsx"
print(f"\n[1] Loading external dataset: {EXT_PATH}")

df = pd.read_excel(EXT_PATH)
print(f"    Rows: {len(df)}")
print(f"    Columns: {list(df.columns)}")
print(f"    Shape: {df.shape}")

# Identify columns
text_col = None
label_col = None
for c in df.columns:
    cl = c.lower().strip()
    if cl in ["raw_text", "text", "message", "sms", "content"]:
        text_col = c
    if cl in ["labels", "label", "target", "class"]:
        label_col = c

if text_col is None or label_col is None:
    print(f"    ERROR: Could not identify text/label columns.")
    print(f"    text_col={text_col}, label_col={label_col}")
    sys.exit(1)

print(f"    Text column: '{text_col}'")
print(f"    Label column: '{label_col}'")

# ═══════════════════════════════════════════════════════════════════
#  STEP 2: INSPECT DATASET
# ═══════════════════════════════════════════════════════════════════
print(f"\n[2] Dataset Inspection")
print(f"    ─────────────────────────────────")

# Missing values
missing = df[[text_col, label_col]].isnull().sum()
print(f"    Missing values:")
print(f"      {text_col}: {missing[text_col]}")
print(f"      {label_col}: {missing[label_col]}")

# Drop rows with missing labels/text
df = df.dropna(subset=[text_col, label_col]).reset_index(drop=True)
print(f"    After dropping NaN: {len(df)} rows")

# Duplicates
n_dup = df[text_col].duplicated().sum()
print(f"    Duplicate messages: {n_dup}")

# Class distribution
print(f"    Label values: {sorted(df[label_col].unique())}")
label_counts = df[label_col].value_counts().sort_index()
print(f"    Class distribution:")
for lbl, cnt in label_counts.items():
    pct = cnt / len(df) * 100
    print(f"      Label {lbl}: {cnt} ({pct:.1f}%)")

# Map labels: 0=Safe, 1=Scam
y_true = df[label_col].astype(int).values
# Verify only 0 and 1
unique_labels = set(y_true)
if unique_labels != {0, 1}:
    print(f"    WARNING: unexpected labels {unique_labels}")
    # Try mapping
    label_map = {}
    for v in df[label_col].unique():
        vs = str(v).lower().strip()
        if vs in ["0", "safe", "legitimate", "ham", "not spam"]:
            label_map[v] = 0
        elif vs in ["1", "scam", "phishing", "spam", "fraud"]:
            label_map[v] = 1
    y_true = df[label_col].map(label_map).astype(int).values

messages = df[text_col].astype(str).values

# Source type distribution (if available)
if "Source_Type" in df.columns:
    print(f"\n    Source Type distribution:")
    for st, cnt in df["Source_Type"].value_counts().items():
        print(f"      {st}: {cnt}")

# Language estimation
def estimate_language(text):
    """Rough language detection for Roman Urdu / English / Mixed."""
    t = str(text).lower()
    urdu_chars = any('\u0600' <= c <= '\u06FF' for c in t)
    if urdu_chars:
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

languages = [estimate_language(m) for m in messages]
lang_dist = pd.Series(languages).value_counts()
print(f"\n    Estimated Language distribution:")
for lang, cnt in lang_dist.items():
    print(f"      {lang}: {cnt} ({cnt/len(df)*100:.1f}%)")

# ═══════════════════════════════════════════════════════════════════
#  STEP 3: LOAD EXISTING MODEL (NO MODIFICATION)
# ═══════════════════════════════════════════════════════════════════
MODEL_DIR = os.path.join(os.path.dirname(__file__), "models")
print(f"\n[3] Loading existing trained model (NO modification)")
print(f"    Model dir: {MODEL_DIR}")

artifacts = joblib.load(os.path.join(MODEL_DIR, "full_pipeline.joblib"))
le = joblib.load(os.path.join(MODEL_DIR, "label_encoder.joblib"))
threshold = joblib.load(os.path.join(MODEL_DIR, "threshold.joblib"))

print(f"    Artifacts type: {type(artifacts)}")
print(f"    Label encoder classes: {list(le.classes_)}")
print(f"    Threshold: {threshold}")

# ═══════════════════════════════════════════════════════════════════
#  STEP 4: RUN PREDICTIONS
# ═══════════════════════════════════════════════════════════════════
print(f"\n[4] Running predictions on {len(messages)} messages...")
print(f"    (This may take a moment...)")

# Get probabilities
if hasattr(artifacts, "predict_proba"):
    proba = artifacts.predict_proba(messages)
    # Get scam probability (class=1)
    scam_idx = list(le.classes_).index("Scam") if "Scam" in le.classes_ else 1
    scam_proba = proba[:, scam_idx]
elif hasattr(artifacts, "decision_function"):
    raw_scores = artifacts.decision_function(messages)
    # Convert to probabilities using sigmoid
    scam_proba = 1 / (1 + np.exp(-raw_scores))
else:
    print("    ERROR: Model has neither predict_proba nor decision_function")
    sys.exit(1)

# Apply threshold
y_pred_binary = (scam_proba >= threshold).astype(int)

# Get predicted labels
y_pred_labels = np.where(y_pred_binary == 1, "Scam", "Safe")
y_true_labels = np.where(y_true == 1, "Scam", "Safe")

print(f"    Predictions complete.")
print(f"    Predicted Scam: {(y_pred_binary == 1).sum()}")
print(f"    Predicted Safe: {(y_pred_binary == 0).sum()}")

# ═══════════════════════════════════════════════════════════════════
#  STEP 5: CALCULATE METRICS
# ═══════════════════════════════════════════════════════════════════
print(f"\n[5] Performance Metrics")
print(f"    {'='*50}")

acc = accuracy_score(y_true, y_pred_binary)
prec = precision_score(y_true, y_pred_binary, pos_label=1, zero_division=0)
rec = recall_score(y_true, y_pred_binary, pos_label=1, zero_division=0)
f1 = f1_score(y_true, y_pred_binary, pos_label=1, zero_division=0)

# ROC-AUC
try:
    auc = roc_auc_score(y_true, scam_proba)
except:
    auc = float("nan")

cm = confusion_matrix(y_true, y_pred_binary, labels=[0, 1])
tn, fp, fn, tp = cm.ravel()

print(f"    Accuracy:        {acc:.4f}  ({acc*100:.2f}%)")
print(f"    Precision:       {prec:.4f}  ({prec*100:.2f}%)")
print(f"    Scam Recall:     {rec:.4f}  ({rec*100:.2f}%)")
print(f"    F1-Score:        {f1:.4f}")
print(f"    ROC-AUC:         {auc:.4f}")
print(f"")
print(f"    True Positives:  {tp}")
print(f"    True Negatives:  {tn}")
print(f"    False Positives: {fp}")
print(f"    False Negatives: {fn}")
print(f"")
print(f"    Confusion Matrix:")
print(f"                    Predicted")
print(f"                 Safe    Scam")
print(f"    Actual Safe  {tn:>6}  {fp:>6}")
print(f"    Actual Scam  {fn:>6}  {tp:>6}")

# ═══════════════════════════════════════════════════════════════════
#  STEP 6: PER-LANGUAGE PERFORMANCE
# ═══════════════════════════════════════════════════════════════════
print(f"\n[6] Per-Language Performance")
print(f"    {'='*50}")

lang_series = pd.Series(languages)
unique_langs = lang_series.unique()

for lang in sorted(unique_langs):
    mask = lang_series == lang
    n = mask.sum()
    if n < 5:
        continue
    yt = y_true[mask.values]
    yp = y_pred_binary[mask.values]
    sp = scam_proba[mask.values]

    la = accuracy_score(yt, yp)
    lp = precision_score(yt, yp, pos_label=1, zero_division=0)
    lr = recall_score(yt, yp, pos_label=1, zero_division=0)
    lf = f1_score(yt, yp, pos_label=1, zero_division=0)
    try:
        lauc = roc_auc_score(yt, sp)
    except:
        lauc = float("nan")

    lcm = confusion_matrix(yt, yp, labels=[0, 1])
    lfp = lcm[0, 1]
    lfn = lcm[1, 0]

    print(f"\n    [{lang}] (n={n})")
    print(f"      Accuracy:  {la:.4f}  F1: {lf:.4f}  AUC: {lauc:.4f}")
    print(f"      Precision: {lp:.4f}  Recall: {lr:.4f}")
    print(f"      FP={lfp}  FN={lfn}")

# ═══════════════════════════════════════════════════════════════════
#  STEP 7: ERROR ANALYSIS
# ═══════════════════════════════════════════════════════════════════
print(f"\n[7] Error Analysis")
print(f"    {'='*50}")

# Build results dataframe
results_df = pd.DataFrame({
    "ID": range(1, len(messages) + 1),
    "Message": messages,
    "Language": languages,
    "Actual_Label": y_true_labels,
    "Predicted_Label": y_pred_labels,
    "Scam_Probability": scam_proba,
    "Correct": y_true == y_pred_binary,
})

# False Positives: Actual=Safe, Predicted=Scam
fps = results_df[(results_df["Actual_Label"] == "Safe") & (results_df["Predicted_Label"] == "Scam")]
# False Negatives: Actual=Scam, Predicted=Safe
fns = results_df[(results_df["Actual_Label"] == "Scam") & (results_df["Predicted_Label"] == "Safe")]

safe = lambda s: s.encode("ascii", errors="replace").decode("ascii")[:90]

print(f"\n    False Positives ({len(fps)}): Safe messages incorrectly flagged as Scam")
print(f"    {'─'*50}")
for _, row in fps.head(15).iterrows():
    print(f"      ID={row['ID']:4d} | P={row['Scam_Probability']:.4f} | Lang={row['Language']}")
    print(f"        \"{safe(row['Message'])}\"")
    # Show source type if available
    if "Source_Type" in df.columns and row["ID"] - 1 < len(df):
        print(f"        Source: {df.iloc[row['ID']-1]['Source_Type']}")
    print()

print(f"\n    False Negatives ({len(fns)}): Scam messages missed (classified as Safe)")
print(f"    {'─'*50}")
for _, row in fns.head(15).iterrows():
    print(f"      ID={row['ID']:4d} | P={row['Scam_Probability']:.4f} | Lang={row['Language']}")
    print(f"        \"{safe(row['Message'])}\"")
    if "Source_Type" in df.columns and row["ID"] - 1 < len(df):
        print(f"        Source: {df.iloc[row['ID']-1]['Source_Type']}")
    print()

# ═══════════════════════════════════════════════════════════════════
#  STEP 8: COMPARISON WITH INTERNAL HOLDOUT
# ═══════════════════════════════════════════════════════════════════
print(f"\n[8] Comparison: External vs Internal Holdout")
print(f"    {'='*50}")
print(f"    {'Metric':<20} {'Internal':>10} {'External':>10} {'Delta':>10}")
print(f"    {'─'*52}")

int_acc, int_rec, int_f1, int_auc = 0.9697, 0.9821, 0.9706, 0.9965

print(f"    {'Accuracy':<20} {int_acc:>10.4f} {acc:>10.4f} {acc-int_acc:>+10.4f}")
print(f"    {'Scam Recall':<20} {int_rec:>10.4f} {rec:>10.4f} {rec-int_rec:>+10.4f}")
print(f"    {'F1-Score':<20} {int_f1:>10.4f} {f1:>10.4f} {f1-int_f1:>+10.4f}")
print(f"    {'ROC-AUC':<20} {int_auc:>10.4f} {auc:>10.4f} {auc-int_auc:>+10.4f}")
print(f"    {'FP':<20} {'7':>10} {fp:>10} {'':>10}")
print(f"    {'FN':<20} {'3':>10} {fn:>10} {'':>10}")

# Generalization verdict
print(f"\n    GENERALIZATION VERDICT:")
gap = abs(acc - int_acc)
if gap < 0.02:
    verdict = "EXCELLENT — model generalizes well (< 2% gap)"
elif gap < 0.05:
    verdict = "GOOD — acceptable generalization (2-5% gap)"
elif gap < 0.10:
    verdict = "MODERATE — some degradation (5-10% gap)"
else:
    verdict = "POOR — significant degradation (> 10% gap)"
print(f"    {verdict}")
print(f"    Accuracy gap: {gap:.4f} ({gap*100:.2f}%)")

# ═══════════════════════════════════════════════════════════════════
#  STEP 9: SAVE OUTPUTS
# ═══════════════════════════════════════════════════════════════════
REPORT_DIR = os.path.join(os.path.dirname(__file__), "reports")
os.makedirs(REPORT_DIR, exist_ok=True)

# Save predictions CSV
csv_path = os.path.join(REPORT_DIR, "external_test_predictions.csv")
results_df.to_csv(csv_path, index=False, encoding="utf-8-sig")
print(f"\n[9] Outputs saved:")
print(f"    Predictions CSV: {csv_path}")

# Save report TXT
txt_path = os.path.join(REPORT_DIR, "external_test_report.txt")
with open(txt_path, "w", encoding="utf-8") as f:
    f.write("EXTERNAL VALIDATION REPORT\n")
    f.write("=" * 70 + "\n")
    f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    f.write(f"Dataset: phishing_dataset_1000.xlsx ({len(df)} messages)\n")
    f.write(f"Model: full_pipeline.joblib (NO modification)\n")
    f.write(f"Threshold: {threshold}\n\n")

    f.write("DATASET INSPECTION\n")
    f.write("-" * 40 + "\n")
    f.write(f"Total messages: {len(df)}\n")
    f.write(f"Duplicates: {n_dup}\n")
    f.write(f"Label distribution: {dict(label_counts)}\n")
    f.write(f"Language distribution: {dict(lang_dist)}\n\n")

    f.write("PERFORMANCE METRICS\n")
    f.write("-" * 40 + "\n")
    f.write(f"Accuracy:        {acc:.4f} ({acc*100:.2f}%)\n")
    f.write(f"Precision:       {prec:.4f} ({prec*100:.2f}%)\n")
    f.write(f"Scam Recall:     {rec:.4f} ({rec*100:.2f}%)\n")
    f.write(f"F1-Score:        {f1:.4f}\n")
    f.write(f"ROC-AUC:         {auc:.4f}\n")
    f.write(f"True Positives:  {tp}\n")
    f.write(f"True Negatives:  {tn}\n")
    f.write(f"False Positives: {fp}\n")
    f.write(f"False Negatives: {fn}\n\n")

    f.write("CONFUSION MATRIX\n")
    f.write("-" * 40 + "\n")
    f.write(f"              Predicted Safe  Predicted Scam\n")
    f.write(f"Actual Safe   {tn:>14}  {fp:>14}\n")
    f.write(f"Actual Scam   {fn:>14}  {tp:>14}\n\n")

    f.write("PER-LANGUAGE PERFORMANCE\n")
    f.write("-" * 40 + "\n")
    for lang in sorted(unique_langs):
        mask = lang_series == lang
        n = mask.sum()
        if n < 5:
            continue
        yt = y_true[mask.values]
        yp = y_pred_binary[mask.values]
        sp = scam_proba[mask.values]
        la = accuracy_score(yt, yp)
        lf = f1_score(yt, yp, pos_label=1, zero_division=0)
        try:
            lauc = roc_auc_score(yt, sp)
        except:
            lauc = float("nan")
        lcm = confusion_matrix(yt, yp, labels=[0, 1])
        f.write(f"[{lang}] n={n} Acc={la:.4f} F1={lf:.4f} AUC={lauc:.4f} FP={lcm[0,1]} FN={lcm[1,0]}\n")
    f.write("\n")

    f.write("FALSE POSITIVES (sample)\n")
    f.write("-" * 40 + "\n")
    for _, row in fps.head(15).iterrows():
        f.write(f"  ID={row['ID']} P={row['Scam_Probability']:.4f} Lang={row['Language']}\n")
        f.write(f"  \"{safe(row['Message'])}\"\n\n")

    f.write("FALSE NEGATIVES (sample)\n")
    f.write("-" * 40 + "\n")
    for _, row in fns.head(15).iterrows():
        f.write(f"  ID={row['ID']} P={row['Scam_Probability']:.4f} Lang={row['Language']}\n")
        f.write(f"  \"{safe(row['Message'])}\"\n\n")

    f.write("COMPARISON WITH INTERNAL HOLDOUT\n")
    f.write("-" * 40 + "\n")
    f.write(f"Internal Accuracy: {int_acc:.4f}  External: {acc:.4f}  Gap: {acc-int_acc:+.4f}\n")
    f.write(f"Internal Recall:   {int_rec:.4f}  External: {rec:.4f}  Gap: {rec-int_rec:+.4f}\n")
    f.write(f"Internal F1:       {int_f1:.4f}  External: {f1:.4f}  Gap: {f1-int_f1:+.4f}\n")
    f.write(f"Internal AUC:      {int_auc:.4f}  External: {auc:.4f}  Gap: {auc-int_auc:+.4f}\n\n")
    f.write(f"Verdict: {verdict}\n")

print(f"    Report TXT:    {txt_path}")

# Save confusion matrix as separate file
cm_path = os.path.join(REPORT_DIR, "external_confusion_matrix.csv")
cm_df = pd.DataFrame(cm, index=["Actual Safe", "Actual Scam"],
                     columns=["Predicted Safe", "Predicted Scam"])
cm_df.to_csv(cm_path)
print(f"    Confusion Matrix: {cm_path}")

# Save error analysis
err_path = os.path.join(REPORT_DIR, "external_error_analysis.csv")
errors_df = results_df[~results_df["Correct"]]
errors_df.to_csv(err_path, index=False, encoding="utf-8-sig")
print(f"    Error Analysis:   {err_path}")

print(f"\n{'='*70}")
print(f"  EXTERNAL VALIDATION COMPLETE")
print(f"  Model was NOT modified in any way.")
print(f"{'='*70}")
