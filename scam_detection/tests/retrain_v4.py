"""
V4 Retrain: Integrate 505 hard-test messages into training data.
Key changes from V3.1:
1. Add 505 adversarial messages (255 scam + 250 safe) to training
2. Optimize threshold with FP penalty (balanced F1 + specificity)
3. Expected: significant FP reduction while maintaining high recall
"""
import sys, os, warnings, time, json
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
import joblib
from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline, FeatureUnion
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.svm import LinearSVC
from sklearn.calibration import CalibratedClassifierCV
from sklearn.metrics import accuracy_score, f1_score, fbeta_score, confusion_matrix

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from run_retrain_v3_pipeline import load_and_combine_data, C_MSG, C_LBL
from src.preprocessing import ImprovedScamTextNormalizer

SEED = 42
np.random.seed(SEED)

def get_proba(model, X):
    if hasattr(model, "predict_proba"):
        return model.predict_proba(X)[:, 1]
    elif hasattr(model, "decision_function"):
        from scipy.special import expit
        return expit(model.decision_function(X))
    return None

def main():
    t0 = time.time()
    print("=" * 70)
    print("  V4 RETRAIN: Integrate 505 Adversarial Messages")
    print("  B_combined_C5 + CalibratedClassifierCV")
    print("=" * 70)

    # ── Step 1: Load existing data ──────────────────────────────────────
    print("\n[1] Loading existing data...")
    orig_df, aug_df, combined_df = load_and_combine_data()
    existing_count = len(combined_df)
    print(f"  Existing: {existing_count} messages")
    print(f"  Scam: {len(combined_df[combined_df[C_LBL]=='Scam'])}")
    print(f"  Safe: {len(combined_df[combined_df[C_LBL]=='Safe'])}")

    # ── Step 2: Load new 505 messages ───────────────────────────────────
    print("\n[2] Loading new 505 adversarial messages...")
    retrain_path = os.path.join(PROJECT_ROOT, "data", "hard_test_500_for_retrain.json")
    with open(retrain_path, "r", encoding="utf-8") as f:
        new_data = json.load(f)

    new_df = pd.DataFrame(new_data)
    new_df = new_df.rename(columns={"message": C_MSG, "label": C_LBL})
    new_df = new_df[[C_MSG, C_LBL]]

    new_scam = len(new_df[new_df[C_LBL] == "Scam"])
    new_safe = len(new_df[new_df[C_LBL] == "Safe"])
    print(f"  New messages: {len(new_df)} ({new_scam} scam, {new_safe} safe)")

    # ── Step 3: Combine ─────────────────────────────────────────────────
    print("\n[3] Combining datasets...")
    # Convert Arrow columns to plain strings before concat
    combined_df[C_MSG] = combined_df[C_MSG].astype(str)
    combined_df[C_LBL] = combined_df[C_LBL].astype(str)
    combined_df = pd.concat([combined_df, new_df], ignore_index=True)

    # Deduplicate
    before_dedup = len(combined_df)
    combined_df = combined_df.drop_duplicates(subset=[C_MSG], keep="first")
    after_dedup = len(combined_df)
    removed = before_dedup - after_dedup
    print(f"  Combined: {after_dedup} messages (removed {removed} duplicates)")
    print(f"  Scam: {len(combined_df[combined_df[C_LBL]=='Scam'])}")
    print(f"  Safe: {len(combined_df[combined_df[C_LBL]=='Safe'])}")

    # ── Step 4: Train/Val split ─────────────────────────────────────────
    print("\n[4] Splitting data...")
    le = LabelEncoder()
    y = le.fit_transform(combined_df[C_LBL].tolist())
    X = combined_df[C_MSG].tolist()

    X_train, X_val, y_train, y_val = train_test_split(
        X, y, test_size=0.15, random_state=SEED, stratify=y
    )
    print(f"  Train: {len(X_train)}, Val: {len(X_val)}")

    # ── Step 5: Build pipeline ──────────────────────────────────────────
    print("\n[5] Building B_combined_C5 pipeline...")
    norm = ImprovedScamTextNormalizer()
    word_tfidf = TfidfVectorizer(
        analyzer="word", ngram_range=(1, 2), min_df=2, max_df=0.95,
        sublinear_tf=True, max_features=50000
    )
    char_tfidf = TfidfVectorizer(
        analyzer="char_wb", ngram_range=(3, 5), min_df=2, max_df=0.95,
        sublinear_tf=True, max_features=50000
    )
    combined_features = FeatureUnion([
        ("word", word_tfidf),
        ("char", char_tfidf),
    ])
    svm = LinearSVC(C=5.0, class_weight="balanced", max_iter=10000, random_state=SEED)

    pipe = Pipeline([
        ("norm", norm),
        ("features", combined_features),
        ("svm", svm),
    ])

    # Train
    print("  Training...")
    pipe.fit(X_train, y_train)
    print(f"  Trained in {time.time()-t0:.1f}s")

    # Calibrate
    print("  Calibrating...")
    calibrated_pipe = CalibratedClassifierCV(estimator=pipe, cv=3, method="sigmoid")
    calibrated_pipe.fit(X_train, y_train)
    print(f"  Calibrated in {time.time()-t0:.1f}s")

    # ── Step 6: Threshold optimization ──────────────────────────────────
    print("\n[6] Optimizing threshold...")
    val_proba = get_proba(calibrated_pipe, X_val)

    # Use a COMPOSITE score that balances recall, precision, and specificity
    # V4 goal: reduce FPs while keeping recall > 90%
    print("  Using balanced composite: 0.4*F1 + 0.3*F2 + 0.3*Specificity")
    best_t = 0.5
    best_comp = 0
    threshold_results = []

    for t in np.arange(0.15, 0.75, 0.01):
        y_pred = (val_proba >= t).astype(int)
        cm = confusion_matrix(y_val, y_pred)
        tn, fp, fn, tp = cm.ravel()

        recall = tp / (tp + fn) if (tp + fn) > 0 else 0
        specificity = tn / (tn + fp) if (tn + fp) > 0 else 0
        f1 = f1_score(y_val, y_pred, zero_division=0)
        f2 = fbeta_score(y_val, y_pred, beta=2, zero_division=0)
        fpr = fp / (fp + tn) if (fp + tn) > 0 else 0

        # Composite: balance detection + FP reduction
        # Require recall >= 0.90 (don't sacrifice too much recall)
        if recall < 0.85:
            continue
        comp = 0.4 * f1 + 0.3 * f2 + 0.3 * specificity
        threshold_results.append((t, f1, f2, recall, specificity, fpr, comp, tp, fp, tn, fn))
        if comp > best_comp:
            best_comp = comp
            best_t = t

    print(f"  Best threshold: {best_t:.2f} (composite={best_comp:.4f})")

    # Show a few threshold options
    print(f"\n  Threshold sweep (top candidates):")
    print(f"  {'Thresh':>6s} {'F1':>7s} {'F2':>7s} {'Recall':>7s} {'Spec':>7s} {'FPR':>7s} {'TP':>4s} {'FP':>4s} {'TN':>4s} {'FN':>4s}")
    for t, f1, f2, recall, spec, fpr, comp, tp, fp, tn, fn in sorted(threshold_results, key=lambda x: -x[6])[:8]:
        marker = " <-- BEST" if abs(t - best_t) < 0.005 else ""
        print(f"  {t:>6.2f} {f1:>7.4f} {f2:>7.4f} {recall:>7.4f} {spec:>7.4f} {fpr:>7.4f} {tp:>4d} {fp:>4d} {tn:>4d} {fn:>4d}{marker}")

    # ── Step 7: Final validation ────────────────────────────────────────
    print(f"\n[7] Final Validation (threshold={best_t:.2f}):")
    y_pred = (val_proba >= best_t).astype(int)
    acc = accuracy_score(y_val, y_pred)
    f1 = f1_score(y_val, y_pred, zero_division=0)
    f2 = fbeta_score(y_val, y_pred, beta=2, zero_division=0)
    cm = confusion_matrix(y_val, y_pred)
    tn, fp, fn, tp = cm.ravel()
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0
    specificity = tn / (tn + fp) if (tn + fp) > 0 else 0
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    fpr = fp / (fp + tn) if (fp + tn) > 0 else 0

    print(f"  Accuracy:    {acc:.4f}")
    print(f"  Precision:   {precision:.4f}")
    print(f"  Recall:      {recall:.4f}")
    print(f"  Specificity: {specificity:.4f}")
    print(f"  F1:          {f1:.4f}")
    print(f"  F2:          {f2:.4f}")
    print(f"  FPR:         {fpr:.4f}")
    print(f"  TP={tp} FP={fp} TN={tn} FN={fn}")

    # ── Step 8: Save model ──────────────────────────────────────────────
    print(f"\n[8] Saving V4 model...")
    models_dir = os.path.join(PROJECT_ROOT, "models")

    # Backup V3.1
    import shutil
    backup_dir = os.path.join(models_dir, "backup_v31")
    os.makedirs(backup_dir, exist_ok=True)
    for fname in ["full_pipeline.joblib", "threshold.joblib", "label_encoder.joblib", "model_metadata.joblib"]:
        src = os.path.join(models_dir, fname)
        dst = os.path.join(backup_dir, fname)
        if os.path.exists(src):
            shutil.copy2(src, dst)
    print(f"  V3.1 backup saved to: {backup_dir}")

    # Save V4
    joblib.dump(calibrated_pipe, os.path.join(models_dir, "full_pipeline.joblib"))
    joblib.dump(best_t, os.path.join(models_dir, "threshold.joblib"))
    joblib.dump(le, os.path.join(models_dir, "label_encoder.joblib"))
    joblib.dump({
        "version": "V4_adversarial_505",
        "threshold": best_t,
        "training_size": len(X_train),
        "total_data": after_dedup,
        "new_messages_added": len(new_data),
        "best_model_name": "B_combined_C5",
        "model_type": "simple_pipeline",
        "val_accuracy": round(acc, 4),
        "val_f1": round(f1, 4),
        "val_f2": round(f2, 4),
        "val_recall": round(recall, 4),
        "val_specificity": round(specificity, 4),
        "val_fpr": round(fpr, 4),
    }, os.path.join(models_dir, "model_metadata.joblib"))
    print(f"  V4 model saved!")

    elapsed = time.time() - t0
    print(f"\n{'=' * 70}")
    print(f"  V4 RETRAIN COMPLETE in {elapsed:.1f}s")
    print(f"  Training data: {after_dedup} messages (+{len(new_data)} new)")
    print(f"  Threshold: {best_t:.2f} (was 0.23 in V3.1)")
    print(f"  Val Accuracy: {acc*100:.1f}% | Recall: {recall*100:.1f}% | FPR: {fpr*100:.1f}%")
    print(f"{'=' * 70}")

if __name__ == "__main__":
    main()
