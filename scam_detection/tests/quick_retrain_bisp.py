"""Quick retrain: just train B_combined_C5 on full dataset with diverse BISP data."""
import sys, os, warnings, time
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

# Import the data generation functions
from run_retrain_v3_pipeline import (
    load_and_combine_data, C_MSG, C_LBL
)
from src.preprocessing import ImprovedScamTextNormalizer

SEED = 42
np.random.seed(SEED)

def get_proba(model, X):
    """Extract scam probabilities from model."""
    if hasattr(model, "predict_proba"):
        return model.predict_proba(X)[:, 1]
    elif hasattr(model, "decision_function"):
        scores = model.decision_function(X)
        from scipy.special import expit
        return expit(scores)
    return None

def main():
    t0 = time.time()
    print("=" * 60)
    print("  QUICK RETRAIN: B_combined_C5 with Diverse BISP")
    print("=" * 60)

    # Load and combine data
    print("\n[1] Loading data...")
    orig_df, aug_df, combined_df = load_and_combine_data()
    print(f"  Combined: {len(combined_df)} messages")
    print(f"  Scam: {len(combined_df[combined_df[C_LBL]=='Scam'])} / Safe: {len(combined_df[combined_df[C_LBL]=='Safe'])}")

    # Encode labels
    le = LabelEncoder()
    y = le.fit_transform(combined_df[C_LBL].tolist())
    X = combined_df[C_MSG].tolist()  # Convert to plain list to avoid Arrow issues

    # Split for validation
    X_train, X_val, y_train, y_val = train_test_split(
        X, y, test_size=0.15, random_state=SEED, stratify=y
    )
    print(f"  Train: {len(X_train)}, Val: {len(X_val)}")

    # Build B_combined_C5 pipeline
    print("\n[2] Building B_combined_C5 pipeline...")
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
    print("  Training on full training set...")
    pipe.fit(X_train, y_train)
    print(f"  Done in {time.time()-t0:.1f}s")

    # Calibrate for probabilities
    print("  Calibrating probabilities...")
    calibrated_pipe = CalibratedClassifierCV(estimator=pipe, cv=3, method="sigmoid")
    calibrated_pipe.fit(X_train, y_train)
    print(f"  Calibration done")

    # Validate
    print("\n[3] Validating...")
    val_proba = get_proba(calibrated_pipe, X_val)
    if val_proba is None:
        print("  ERROR: Could not get probabilities")
        return

    # Find best threshold using F2
    print("  Optimizing threshold (F2 + composite)...")
    best_t = 0.5
    best_comp = 0
    for t in np.arange(0.15, 0.65, 0.01):
        y_pred = (val_proba >= t).astype(int)
        f2 = fbeta_score(y_val, y_pred, beta=2, zero_division=0)
        acc = accuracy_score(y_val, y_pred)
        comp = 0.6 * f2 + 0.4 * acc
        if comp > best_comp:
            best_comp = comp
            best_t = t

    print(f"  Best threshold: {best_t:.2f} (composite={best_comp:.4f})")

    # Final evaluation
    y_pred = (val_proba >= best_t).astype(int)
    acc = accuracy_score(y_val, y_pred)
    f1 = f1_score(y_val, y_pred, zero_division=0)
    f2 = fbeta_score(y_val, y_pred, beta=2, zero_division=0)
    cm = confusion_matrix(y_val, y_pred)
    tn, fp, fn, tp = cm.ravel()

    print(f"\n[4] Validation Results:")
    print(f"  Accuracy: {acc:.4f}")
    print(f"  F1:       {f1:.4f}")
    print(f"  F2:       {f2:.4f}")
    print(f"  TP={tp} FP={fp} TN={tn} FN={fn}")
    print(f"  Recall:   {tp/(tp+fn) if (tp+fn)>0 else 0:.4f}")
    print(f"  Precision:{tp/(tp+fp) if (tp+fp)>0 else 0:.4f}")

    # Save model
    print("\n[5] Saving model...")
    models_dir = os.path.join(PROJECT_ROOT, "models")
    joblib.dump(calibrated_pipe, os.path.join(models_dir, "full_pipeline.joblib"))
    joblib.dump(best_t, os.path.join(models_dir, "threshold.joblib"))
    joblib.dump(le, os.path.join(models_dir, "label_encoder.joblib"))
    joblib.dump({"version": "V3.1_diverse_bisp", "threshold": best_t, "training_size": len(X_train),
                 "best_model_name": "B_combined_C5", "model_type": "simple_pipeline"},
                os.path.join(models_dir, "model_metadata.joblib"))
    print("  Saved: full_pipeline.joblib, threshold.joblib, label_encoder.joblib")

    print(f"\n{'=' * 60}")
    print(f"  DONE in {time.time()-t0:.1f}s")
    print(f"{'=' * 60}")

if __name__ == "__main__":
    main()
