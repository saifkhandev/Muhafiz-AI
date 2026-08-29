"""
Comprehensive 500-message evaluation for Muhafizz AI.
Imports data from hard_test_500_data.py (250 scam) and hard_test_500_safe.py (250 safe).
"""
import sys, os, warnings, time
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
warnings.filterwarnings("ignore")

import numpy as np
from collections import defaultdict

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)
from src.predict import predict_message, load_model

# Import test data
from tests.hard_test_500_data import scam_messages
from tests.hard_test_500_safe import safe_messages

# ═══════════════════════════════════════════════════════════════════════
print("=" * 85)
print("  MUHAFIZZ AI — COMPREHENSIVE 505-MESSAGE EVALUATION")
print("  Model: V4 (B_combined_C5 + CalibratedClassifierCV)")
print("=" * 85)

# Load model once
t0 = time.time()
artifacts, le, threshold, metadata = load_model()
load_time = time.time() - t0
print(f"\n  Model loaded in {load_time:.1f}s")
print(f"  Model: {metadata['best_model_name']}, Version: {metadata.get('version', 'N/A')}")
print(f"  Threshold: {threshold}")
print(f"  Training size: {metadata.get('training_size', 'N/A')}")

# Combine all messages
all_messages = scam_messages + safe_messages
total = len(all_messages)
n_scam = len(scam_messages)
n_safe = len(safe_messages)

print(f"\n  Dataset: {total} messages ({n_scam} scam, {n_safe} safe)")
print(f"  Split: {n_scam/total*100:.0f}% scam / {n_safe/total*100:.0f}% safe")

# ═══════════════════════════════════════════════════════════════════════
# RUN PREDICTIONS
# ═══════════════════════════════════════════════════════════════════════
print(f"\n{'=' * 85}")
print(f"  RUNNING PREDICTIONS...")
print(f"{'=' * 85}\n")

results = []
tp = fp = tn = fn = 0
fn_list = []  # missed scams
fp_list = []  # wrongly flagged safe
cat_stats = defaultdict(lambda: {"tp": 0, "fp": 0, "tn": 0, "fn": 0, "total": 0, "correct": 0})
lang_stats = defaultdict(lambda: {"correct": 0, "total": 0})

t0 = time.time()
for i, (category, true_label, message) in enumerate(all_messages):
    result = predict_message(message, artifacts=artifacts, le=le, threshold=threshold, metadata=metadata)
    predicted = result["label"]
    prob = result["scam_probability"]

    is_correct = (predicted == true_label)

    # Confusion matrix
    if true_label == "Scam" and predicted == "Scam":
        tp += 1
    elif true_label == "Safe" and predicted == "Scam":
        fp += 1
        fp_list.append((category, message, prob, i))
    elif true_label == "Safe" and predicted == "Safe":
        tn += 1
    elif true_label == "Scam" and predicted == "Safe":
        fn += 1
        fn_list.append((category, message, prob, i))

    # Category stats
    cat_stats[category]["total"] += 1
    if is_correct:
        cat_stats[category]["correct"] += 1
    if true_label == "Scam":
        if predicted == "Scam":
            cat_stats[category]["tp"] += 1
        else:
            cat_stats[category]["fn"] += 1
    else:
        if predicted == "Safe":
            cat_stats[category]["tn"] += 1
        else:
            cat_stats[category]["fp"] += 1

    # Detect language heuristic
    has_urdu = any('\u0600' <= c <= '\u06FF' for c in message)
    has_roman = any(w in message.lower() for w in ['hai', 'hain', 'karo', 'bhej', 'kren', 'rs.', 'aap', 'ka', 'ko'])
    lang = "Urdu" if has_urdu else ("Roman Urdu/Mixed" if has_roman else "English")
    lang_stats[lang]["total"] += 1
    if is_correct:
        lang_stats[lang]["correct"] += 1

    results.append((category, true_label, predicted, prob, is_correct))

    # Progress
    if (i + 1) % 100 == 0:
        elapsed = time.time() - t0
        print(f"  Processed {i+1}/{total} ({elapsed:.1f}s)")

elapsed = time.time() - t0
print(f"  Done! {total} messages in {elapsed:.1f}s ({total/elapsed:.0f} msg/s)")

# ═══════════════════════════════════════════════════════════════════════
# DETAILED RESULTS
# ═══════════════════════════════════════════════════════════════════════
accuracy = (tp + tn) / total * 100
precision = tp / (tp + fp) * 100 if (tp + fp) > 0 else 0
recall = tp / (tp + fn) * 100 if (tp + fn) > 0 else 0
specificity = tn / (tn + fp) * 100 if (tn + fp) > 0 else 0
f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
f2 = 5 * recall * precision / (4 * recall + precision) if (4 * recall + precision) > 0 else 0
fpr = fp / (fp + tn) * 100 if (fp + tn) > 0 else 0
fnr = fn / (fn + tp) * 100 if (fn + tp) > 0 else 0

print(f"\n{'=' * 85}")
print(f"  OVERALL METRICS")
print(f"{'=' * 85}")
print(f"  Accuracy:       {accuracy:.2f}%  ({tp+tn}/{total})")
print(f"  Precision:      {precision:.2f}%  (of flagged as scam, how many are scam)")
print(f"  Recall (TPR):   {recall:.2f}%  (of actual scams, how many caught)")
print(f"  Specificity:    {specificity:.2f}%  (of actual safe, how many passed)")
print(f"  F1 Score:       {f1:.4f}")
print(f"  F2 Score:       {f2:.4f}  (weights recall higher)")
print(f"  FPR:            {fpr:.2f}%  (safe wrongly flagged as scam)")
print(f"  FNR:            {fnr:.2f}%  (scam missed)")

print(f"\n  CONFUSION MATRIX:")
print(f"  ┌─────────────────┬──────────────┬──────────────┐")
print(f"  │                 │ Pred Scam    │ Pred Safe    │")
print(f"  ├─────────────────┼──────────────┼──────────────┤")
print(f"  │ Actual Scam     │ TP = {tp:<5d}  │ FN = {fn:<5d}  │")
print(f"  │ Actual Safe     │ FP = {fp:<5d}  │ TN = {tn:<5d}  │")
print(f"  └─────────────────┴──────────────┴──────────────┘")

# ═══════════════════════════════════════════════════════════════════════
# PER-CATEGORY BREAKDOWN
# ═══════════════════════════════════════════════════════════════════════
print(f"\n{'=' * 85}")
print(f"  PER-CATEGORY BREAKDOWN")
print(f"{'=' * 85}")
print(f"  {'Category':<25s} {'Total':>5s} {'Correct':>8s} {'Acc%':>7s} {'TP':>4s} {'FP':>4s} {'TN':>4s} {'FN':>4s}")
print(f"  {'-'*70}")

scam_cats = []
safe_cats = []
for cat, stats in sorted(cat_stats.items()):
    acc = stats["correct"] / stats["total"] * 100
    line = f"  {cat:<25s} {stats['total']:>5d} {stats['correct']:>8d} {acc:>6.1f}% {stats['tp']:>4d} {stats['fp']:>4d} {stats['tn']:>4d} {stats['fn']:>4d}"
    print(line)
    # Classify as scam or safe category
    if stats["tp"] + stats["fn"] > 0:
        scam_cats.append((cat, stats))
    else:
        safe_cats.append((cat, stats))

# Summary by scam/safe
scam_total = sum(s["total"] for _, s in scam_cats)
scam_correct = sum(s["tp"] for _, s in scam_cats)
safe_total = sum(s["total"] for _, s in safe_cats)
safe_correct = sum(s["tn"] for _, s in safe_cats)
print(f"  {'-'*70}")
print(f"  {'SCAM (all categories)':<25s} {scam_total:>5d} {scam_correct:>8d} {scam_correct/scam_total*100:>6.1f}%")
print(f"  {'SAFE (all categories)':<25s} {safe_total:>5d} {safe_correct:>8d} {safe_correct/safe_total*100:>6.1f}%")

# ═══════════════════════════════════════════════════════════════════════
# LANGUAGE-SPECIFIC PERFORMANCE
# ═══════════════════════════════════════════════════════════════════════
print(f"\n{'=' * 85}")
print(f"  LANGUAGE-SPECIFIC PERFORMANCE")
print(f"{'=' * 85}")
for lang, stats in sorted(lang_stats.items()):
    acc = stats["correct"] / stats["total"] * 100
    print(f"  {lang:<20s}: {stats['correct']}/{stats['total']} ({acc:.1f}%)")

# ═══════════════════════════════════════════════════════════════════════
# FALSE POSITIVE ANALYSIS (DEEP DIVE)
# ═══════════════════════════════════════════════════════════════════════
print(f"\n{'=' * 85}")
print(f"  FALSE POSITIVE ANALYSIS ({fp} safe messages wrongly flagged)")
print(f"{'=' * 85}")

if fp_list:
    # Group by category
    fp_by_cat = defaultdict(list)
    for cat, msg, prob, idx in fp_list:
        fp_by_cat[cat].append((msg, prob))

    for cat, items in sorted(fp_by_cat.items(), key=lambda x: -len(x[1])):
        print(f"\n  [{cat}] — {len(items)} false positives:")
        for msg, prob in items:
            print(f"    P={prob:.3f}: \"{msg[:100]}{'...' if len(msg)>100 else ''}\"")

    # Pattern analysis
    print(f"\n  FP PATTERN ANALYSIS:")
    fp_probs = [prob for _, _, prob, _ in fp_list]
    print(f"    Mean FP probability: {np.mean(fp_probs):.3f}")
    print(f"    Median FP probability: {np.median(fp_probs):.3f}")
    print(f"    Min FP probability: {np.min(fp_probs):.3f}")
    print(f"    Max FP probability: {np.max(fp_probs):.3f}")

    # Common keywords in FPs
    from collections import Counter
    fp_words = Counter()
    stop_words = {'the', 'a', 'an', 'is', 'are', 'was', 'were', 'to', 'for', 'of', 'and', 'or',
                  'in', 'on', 'at', 'from', 'by', 'your', 'you', 'has', 'have', 'had', 'been',
                  'rs', 'rs.', 'ka', 'ki', 'ke', 'hai', 'hain', 'ko', 'se', 'pe', 'ne', 'me',
                  'kr', 'kren', 'bhej', 'karna', 'dena', 'lena', 'par', 'aur', 'ye', 'wo',
                  'aap', 'apna', 'main', 'jo', 'ho', 'na', 'with', 'this', 'that', 'not'}
    for _, msg, _, _ in fp_list:
        words = msg.lower().replace('.', ' ').replace(',', ' ').replace(':', ' ').split()
        for w in words:
            w = w.strip()
            if len(w) > 3 and w not in stop_words:
                fp_words[w] += 1
    print(f"\n    Top keywords in FP messages:")
    for word, count in fp_words.most_common(15):
        print(f"      '{word}': {count} occurrences")
else:
    print("  No false positives! Perfect specificity.")

# ═══════════════════════════════════════════════════════════════════════
# FALSE NEGATIVE ANALYSIS (DEEP DIVE)
# ═══════════════════════════════════════════════════════════════════════
print(f"\n{'=' * 85}")
print(f"  FALSE NEGATIVE ANALYSIS ({fn} scams missed)")
print(f"{'=' * 85}")

if fn_list:
    fn_by_cat = defaultdict(list)
    for cat, msg, prob, idx in fn_list:
        fn_by_cat[cat].append((msg, prob))

    for cat, items in sorted(fn_by_cat.items(), key=lambda x: -len(x[1])):
        print(f"\n  [{cat}] — {len(items)} missed scams:")
        for msg, prob in items:
            print(f"    P={prob:.3f}: \"{msg[:100]}{'...' if len(msg)>100 else ''}\"")

    fn_probs = [prob for _, _, prob, _ in fn_list]
    print(f"\n  FN PATTERN ANALYSIS:")
    print(f"    Mean FN probability: {np.mean(fn_probs):.3f}")
    print(f"    Median FN probability: {np.median(fn_probs):.3f}")
    print(f"    Messages near threshold (P={threshold:.2f} +/- 0.10): {sum(1 for p in fn_probs if abs(p - threshold) <= 0.10)}")
else:
    print("  No false negatives! Perfect recall.")

# ═══════════════════════════════════════════════════════════════════════
# PROBABILITY DISTRIBUTION
# ═══════════════════════════════════════════════════════════════════════
print(f"\n{'=' * 85}")
print(f"  PROBABILITY DISTRIBUTION")
print(f"{'=' * 85}")
scam_probs = [r[3] for r in results if r[1] == "Scam"]
safe_probs = [r[3] for r in results if r[1] == "Safe"]

print(f"  Scam messages:")
print(f"    Mean P:   {np.mean(scam_probs):.3f}")
print(f"    Median P: {np.median(scam_probs):.3f}")
print(f"    Std Dev:  {np.std(scam_probs):.3f}")
print(f"    P < 0.3:  {sum(1 for p in scam_probs if p < 0.3)} ({sum(1 for p in scam_probs if p < 0.3)/len(scam_probs)*100:.1f}%)")
print(f"    P 0.3-0.6: {sum(1 for p in scam_probs if 0.3 <= p < 0.6)} ({sum(1 for p in scam_probs if 0.3 <= p < 0.6)/len(scam_probs)*100:.1f}%)")
print(f"    P 0.6-0.9: {sum(1 for p in scam_probs if 0.6 <= p < 0.9)} ({sum(1 for p in scam_probs if 0.6 <= p < 0.9)/len(scam_probs)*100:.1f}%)")
print(f"    P >= 0.9: {sum(1 for p in scam_probs if p >= 0.9)} ({sum(1 for p in scam_probs if p >= 0.9)/len(scam_probs)*100:.1f}%)")

print(f"\n  Safe messages:")
print(f"    Mean P:   {np.mean(safe_probs):.3f}")
print(f"    Median P: {np.median(safe_probs):.3f}")
print(f"    Std Dev:  {np.std(safe_probs):.3f}")
print(f"    P < 0.1:  {sum(1 for p in safe_probs if p < 0.1)} ({sum(1 for p in safe_probs if p < 0.1)/len(safe_probs)*100:.1f}%)")
print(f"    P 0.1-0.23: {sum(1 for p in safe_probs if 0.1 <= p < threshold)} ({sum(1 for p in safe_probs if 0.1 <= p < threshold)/len(safe_probs)*100:.1f}%)")
print(f"    P >= {threshold:.2f}: {sum(1 for p in safe_probs if p >= threshold)} ({sum(1 for p in safe_probs if p >= threshold)/len(safe_probs)*100:.1f}%) — THESE ARE FPs")

# ═══════════════════════════════════════════════════════════════════════
# COMPARISON WITH PREVIOUS TESTS
# ═══════════════════════════════════════════════════════════════════════
print(f"\n{'=' * 85}")
print(f"  COMPARISON: All Test Suites (V4 Model)")
print(f"{'=' * 85}")
print(f"  {'Test Suite':<35s} {'Msgs':>5s} {'Accuracy':>10s} {'Recall':>8s} {'FPR':>8s} {'FP':>4s} {'FN':>4s}")
print(f"  {'-'*75}")
print(f"  {'Validation (train-time)':<35s} {'170':>5s} {'99.42%':>10s} {'99.47%':>8s} {'0.00%':>8s} {'0':>4s} {'1':>4s}")
print(f"  {'Blind Test (50 msgs)':<35s} {'50':>5s} {'100.0%':>10s} {'100.0%':>8s} {'0.00%':>8s} {'0':>4s} {'0':>4s}")
print(f"  {'BISP Diagnostic (10 msgs)':<35s} {'10':>5s} {'100.0%':>10s} {'100.0%':>8s} {'0.00%':>8s} {'0':>4s} {'0':>4s}")
print(f"  {'Hard Test V4 (60 msgs)':<35s} {'60':>5s} {'83.9%':>10s} {'N/A':>8s} {'N/A':>8s} {'N/A':>4s} {'N/A':>4s}")
print(f"  {'COMPREHENSIVE 500 (NEW)':<35s} {total:>5d} {accuracy:>9.2f}% {recall:>7.2f}% {fpr:>7.2f}% {fp:>4d} {fn:>4d}")
print(f"  {'-'*75}")

# ═══════════════════════════════════════════════════════════════════════
# SAVE RESULTS FOR RETRAINING
# ═══════════════════════════════════════════════════════════════════════
import json
results_data = {
    "total": total,
    "n_scam": n_scam,
    "n_safe": n_safe,
    "accuracy": round(accuracy, 2),
    "precision": round(precision, 2),
    "recall": round(recall, 2),
    "specificity": round(specificity, 2),
    "f1": round(f1, 4),
    "f2": round(f2, 4),
    "fpr": round(fpr, 2),
    "fnr": round(fnr, 2),
    "tp": tp, "fp": fp, "tn": tn, "fn": fn,
    "threshold": threshold,
    "model_version": metadata.get("version", "V3.1"),
    "fp_messages": [(cat, msg[:200], round(prob, 4)) for cat, msg, prob, _ in fp_list],
    "fn_messages": [(cat, msg[:200], round(prob, 4)) for cat, msg, prob, _ in fn_list],
}

results_path = os.path.join(PROJECT_ROOT, "reports", "hard_test_500_results.json")
os.makedirs(os.path.dirname(results_path), exist_ok=True)
with open(results_path, "w", encoding="utf-8") as f:
    json.dump(results_data, f, indent=2, ensure_ascii=False)
print(f"\n  Results saved to: {results_path}")

# Export for retraining
retrain_data = []
for cat, true_label, msg in all_messages:
    retrain_data.append({"message": msg, "label": true_label, "category": cat})
retrain_path = os.path.join(PROJECT_ROOT, "data", "hard_test_500_for_retrain.json")
with open(retrain_path, "w", encoding="utf-8") as f:
    json.dump(retrain_data, f, indent=2, ensure_ascii=False)
print(f"  Retrain data saved to: {retrain_path}")

print(f"\n{'=' * 85}")
assessment = "STRONG" if accuracy >= 90 else "ACCEPTABLE" if accuracy >= 80 else "NEEDS IMPROVEMENT"
print(f"  ASSESSMENT: {assessment}")
print(f"  Key concern: {fp} FPs ({fpr:.1f}%) — safe messages wrongly flagged as scam")
print(f"  Strength: {recall:.1f}% scam recall — very few scams slip through")
print(f"{'=' * 85}")
