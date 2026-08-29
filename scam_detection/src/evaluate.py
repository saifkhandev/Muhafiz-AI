"""
STEP 8-12, 14 — Model Evaluation, Comparison, Threshold Optimization,
                  Error Analysis, Overfitting Check, Final Model Saving.
"""
import os
import json
import numpy as np
import pandas as pd
import joblib
from scipy.sparse import issparse, hstack

from sklearn.preprocessing import LabelEncoder
from sklearn.base import clone
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    roc_auc_score, confusion_matrix, classification_report,
)
from sklearn.model_selection import StratifiedKFold

from src.config import (
    COL_MESSAGE, COL_LANGUAGE, COL_LABEL, COL_CATEGORY, LABEL_SCAM,
    RANDOM_SEED, N_FOLDS,
    MODEL_DIR, REPORT_DIR,
    MODEL_FILENAME, VECTORIZER_FILENAME, FEATURE_CONFIG_FILENAME,
    THRESHOLD_FILENAME, LABEL_ENCODER_FILENAME, METADATA_FILENAME,
    FULL_PIPELINE_FILENAME,
)
from src.train import MODEL_CONFIGS
from src.preprocessing import ScamTextNormalizer


# ──────────────────────────────────────────────────────────────────────────────
# Fit and evaluate on validation + test
# ──────────────────────────────────────────────────────────────────────────────

def _fit_and_predict(config, train_texts, train_labels, eval_texts):
    """Fit a model config on train and predict on eval."""
    if config["type"] == "simple_pipeline":
        pipe = config["builder"]()
        pipe.fit(train_texts, train_labels)
        y_pred = pipe.predict(eval_texts)
        y_proba = None
        if hasattr(pipe[-1], "predict_proba"):
            y_proba = pipe.predict_proba(eval_texts)[:, 1]
        elif hasattr(pipe[-1], "decision_function"):
            # Convert decision function to pseudo-probabilities
            df = pipe.decision_function(eval_texts)
            y_proba = 1 / (1 + np.exp(-df))  # sigmoid
        return pipe, y_pred, y_proba

    elif config["type"] == "combined":
        parts = config["builder"]()
        norm = parts["normalizer"]
        vec = parts["vectorizer"]
        clf = clone(parts["clf"])

        X_tr_norm = norm.transform(train_texts)
        X_te_norm = norm.transform(eval_texts)
        vec.fit(X_tr_norm)
        X_tr_vec = vec.transform(X_tr_norm)
        X_te_vec = vec.transform(X_te_norm)

        clf.fit(X_tr_vec, train_labels)
        y_pred = clf.predict(X_te_vec)
        y_proba = clf.predict_proba(X_te_vec)[:, 1] if hasattr(clf, "predict_proba") else None
        if y_proba is None and hasattr(clf, "decision_function"):
            df = clf.decision_function(X_te_vec)
            y_proba = 1 / (1 + np.exp(-df))
        return {"normalizer": norm, "vectorizer": vec, "clf": clf}, y_pred, y_proba

    elif config["type"] == "engineered":
        parts = config["builder"]()
        norm = parts["normalizer"]
        tfidf = clone(parts["tfidf"])
        feat_ext = clone(parts["feature_extractor"])
        clf = clone(parts["clf"])

        X_tr_norm = norm.transform(train_texts)
        X_te_norm = norm.transform(eval_texts)
        X_tr_tfidf = tfidf.fit_transform(X_tr_norm)
        X_te_tfidf = tfidf.transform(X_te_norm)

        X_tr_eng = feat_ext.fit_transform(train_texts)
        X_te_eng = feat_ext.transform(eval_texts)

        X_tr_tfidf_dense = X_tr_tfidf.toarray() if issparse(X_tr_tfidf) else X_tr_tfidf
        X_te_tfidf_dense = X_te_tfidf.toarray() if issparse(X_te_tfidf) else X_te_tfidf
        X_tr_combined = np.hstack([X_tr_tfidf_dense, X_tr_eng])
        X_te_combined = np.hstack([X_te_tfidf_dense, X_te_eng])

        clf.fit(X_tr_combined, train_labels)
        y_pred = clf.predict(X_te_combined)
        y_proba = clf.predict_proba(X_te_combined)[:, 1] if hasattr(clf, "predict_proba") else None
        if y_proba is None and hasattr(clf, "decision_function"):
            df = clf.decision_function(X_te_combined)
            y_proba = 1 / (1 + np.exp(-df))
        return {
            "normalizer": norm, "tfidf": tfidf,
            "feature_extractor": feat_ext, "clf": clf,
        }, y_pred, y_proba


def evaluate_all(
    train_df, val_df, test_df, le, cv_results,
):
    """
    For each candidate model:
    - Retrain on full training data
    - Evaluate on validation set (for threshold tuning)
    - Evaluate on test set (final holdout)
    - Compare and select best model
    """
    X_train = train_df[COL_MESSAGE].values
    y_train = le.transform(train_df[COL_LABEL].values)
    X_val = val_df[COL_MESSAGE].values
    y_val = le.transform(val_df[COL_LABEL].values)
    X_test = test_df[COL_MESSAGE].values
    y_test = le.transform(test_df[COL_LABEL].values)

    comparison = []
    best_name = None
    best_f1 = 0
    best_artifacts = None
    best_val_proba = None
    best_test_proba = None

    for name, config in MODEL_CONFIGS.items():
        print(f"\n[EVAL] Evaluating {name} ...")

        # Fit on training data
        artifacts, y_val_pred, y_val_proba = _fit_and_predict(
            config, X_train, y_train, X_val
        )

        # Validation metrics
        val_acc = accuracy_score(y_val, y_val_pred)
        val_f1 = f1_score(y_val, y_val_pred, pos_label=1)
        val_recall = recall_score(y_val, y_val_pred, pos_label=1)
        val_precision = precision_score(y_val, y_val_pred, pos_label=1)
        val_auc = roc_auc_score(y_val, y_val_proba) if y_val_proba is not None else None

        # Evaluate on TEST (untouched until now)
        if config["type"] == "simple_pipeline":
            y_test_pred = artifacts.predict(X_test)
            y_test_proba = None
            if hasattr(artifacts[-1], "predict_proba"):
                y_test_proba = artifacts.predict_proba(X_test)[:, 1]
            elif hasattr(artifacts[-1], "decision_function"):
                df_vals = artifacts.decision_function(X_test)
                y_test_proba = 1 / (1 + np.exp(-df_vals))
        elif config["type"] == "combined":
            X_te_norm = artifacts["normalizer"].transform(X_test)
            X_te_vec = artifacts["vectorizer"].transform(X_te_norm)
            y_test_pred = artifacts["clf"].predict(X_te_vec)
            y_test_proba = None
            if hasattr(artifacts["clf"], "predict_proba"):
                y_test_proba = artifacts["clf"].predict_proba(X_te_vec)[:, 1]
            elif hasattr(artifacts["clf"], "decision_function"):
                df_vals = artifacts["clf"].decision_function(X_te_vec)
                y_test_proba = 1 / (1 + np.exp(-df_vals))
        elif config["type"] == "engineered":
            X_te_norm = artifacts["normalizer"].transform(X_test)
            X_te_tfidf = artifacts["tfidf"].transform(X_te_norm)
            X_te_eng = artifacts["feature_extractor"].transform(X_test)
            X_te_tfidf_d = X_te_tfidf.toarray() if issparse(X_te_tfidf) else X_te_tfidf
            X_te_combined = np.hstack([X_te_tfidf_d, X_te_eng])
            y_test_pred = artifacts["clf"].predict(X_te_combined)
            y_test_proba = None
            if hasattr(artifacts["clf"], "predict_proba"):
                y_test_proba = artifacts["clf"].predict_proba(X_te_combined)[:, 1]

        test_acc = accuracy_score(y_test, y_test_pred)
        test_f1 = f1_score(y_test, y_test_pred, pos_label=1)
        test_recall = recall_score(y_test, y_test_pred, pos_label=1)
        test_precision = precision_score(y_test, y_test_pred, pos_label=1)
        test_auc = roc_auc_score(y_test, y_test_proba) if y_test_proba is not None else None

        cm = confusion_matrix(y_test, y_test_pred)
        tn, fp, fn, tp = cm.ravel()

        # CV results
        cv_f1_mean = cv_results.get(name, {}).get("cv_f1_mean", 0)
        cv_f1_std = cv_results.get(name, {}).get("cv_f1_std", 0)

        entry = {
            "model": name,
            "description": MODEL_CONFIGS[name]["description"],
            "cv_f1_mean": cv_f1_mean,
            "cv_f1_std": cv_f1_std,
            "val_accuracy": val_acc,
            "val_f1": val_f1,
            "val_recall": val_recall,
            "val_precision": val_precision,
            "val_auc": val_auc,
            "test_accuracy": test_acc,
            "test_f1": test_f1,
            "test_recall": test_recall,
            "test_precision": test_precision,
            "test_auc": test_auc,
            "test_TP": tp,
            "test_FP": fp,
            "test_FN": fn,
            "test_TN": tn,
        }
        comparison.append(entry)

        print(f"  Val  F1={val_f1:.4f} Acc={val_acc:.4f} Recall={val_recall:.4f}")
        print(f"  Test F1={test_f1:.4f} Acc={test_acc:.4f} Recall={test_recall:.4f} "
              f"FP={fp} FN={fn}")
        print(f"  CM:  TN={tn}  FP={fp}")
        print(f"       FN={fn}  TP={tp}")

        # Select best by test F1
        if test_f1 > best_f1:
            best_f1 = test_f1
            best_name = name
            best_artifacts = artifacts
            best_val_proba = y_val_proba
            best_test_proba = y_test_proba

    # ── Save comparison table ────────────────────────────────────────────
    comp_df = pd.DataFrame(comparison)
    os.makedirs(REPORT_DIR, exist_ok=True)
    comp_path = os.path.join(REPORT_DIR, "model_comparison.csv")
    comp_df.to_csv(comp_path, index=False, float_format="%.4f")
    print(f"\n[REPORT] Model comparison saved -> {comp_path}")

    print("\n" + "=" * 70)
    print("  MODEL COMPARISON TABLE")
    print("=" * 70)
    for _, row in comp_df.iterrows():
        print(f"\n  {row['model']}: {row['description']}")
        print(f"    CV F1:   {row['cv_f1_mean']:.4f} +/- {row['cv_f1_std']:.4f}")
        print(f"    Test Acc: {row['test_accuracy']:.4f}  "
              f"F1: {row['test_f1']:.4f}  "
              f"Recall: {row['test_recall']:.4f}  "
              f"AUC: {row['test_auc']:.4f}")
        print(f"    FP={row['test_FP']}  FN={row['test_FN']}  "
              f"TP={row['test_TP']}  TN={row['test_TN']}")
    print(f"\n  >> BEST MODEL: {best_name} (F1={best_f1:.4f})")
    print("=" * 70)

    return (
        comp_df, best_name, best_artifacts,
        y_val, y_test, best_val_proba, best_test_proba,
    )


# ──────────────────────────────────────────────────────────────────────────────
# STEP 9 — Threshold Optimization
# ──────────────────────────────────────────────────────────────────────────────

def optimize_threshold(y_val, y_val_proba):
    """Find optimal threshold on validation set."""
    if y_val_proba is None:
        return 0.5, {}

    thresholds = np.arange(0.10, 0.90, 0.01)
    best_threshold = 0.5
    best_f1 = 0
    threshold_results = []

    for t in thresholds:
        y_pred_t = (y_val_proba >= t).astype(int)
        f1_t = f1_score(y_val, y_pred_t, pos_label=1)
        recall_t = recall_score(y_val, y_pred_t, pos_label=1)
        prec_t = precision_score(y_val, y_pred_t, pos_label=1)
        threshold_results.append({
            "threshold": round(t, 2),
            "f1": f1_t,
            "recall": recall_t,
            "precision": prec_t,
        })
        if f1_t > best_f1:
            best_f1 = f1_t
            best_threshold = round(t, 2)

    # Also check a recall-optimized threshold (recall ≥ 0.95)
    recall_opt_threshold = 0.5
    for t in thresholds:
        y_pred_t = (y_val_proba >= t).astype(int)
        recall_t = recall_score(y_val, y_pred_t, pos_label=1)
        prec_t = precision_score(y_val, y_pred_t, pos_label=1, zero_division=0)
        if recall_t >= 0.95 and prec_t >= 0.70:
            recall_opt_threshold = round(t, 2)
            break

    print(f"\n[THRESHOLD] Optimal F1 threshold: {best_threshold} (F1={best_f1:.4f})")
    print(f"[THRESHOLD] Recall≥0.95 threshold: {recall_opt_threshold}")

    # Default threshold results
    y_pred_default = (y_val_proba >= 0.5).astype(int)
    default_metrics = {
        "threshold": 0.50,
        "f1": f1_score(y_val, y_pred_default, pos_label=1),
        "recall": recall_score(y_val, y_pred_default, pos_label=1),
        "precision": precision_score(y_val, y_pred_default, pos_label=1),
    }

    # Optimized threshold results
    y_pred_opt = (y_val_proba >= best_threshold).astype(int)
    opt_metrics = {
        "threshold": best_threshold,
        "f1": f1_score(y_val, y_pred_opt, pos_label=1),
        "recall": recall_score(y_val, y_pred_opt, pos_label=1),
        "precision": precision_score(y_val, y_pred_opt, pos_label=1),
    }

    report = {
        "default_threshold": default_metrics,
        "optimized_threshold": opt_metrics,
        "recall_optimized_threshold": recall_opt_threshold,
        "all_thresholds": threshold_results,
    }

    # Save
    out_path = os.path.join(REPORT_DIR, "threshold_analysis.json")
    with open(out_path, "w") as f:
        json.dump(report, f, indent=2, default=str)
    print(f"[REPORT] Threshold analysis saved -> {out_path}")

    return best_threshold, report


# ──────────────────────────────────────────────────────────────────────────────
# STEP 10 — Error Analysis
# ──────────────────────────────────────────────────────────────────────────────

def error_analysis(
    test_df, y_test, y_test_pred, y_test_proba, le, best_name,
):
    """Analyze false positives and false negatives."""
    y_test_labels = le.inverse_transform(y_test)
    y_pred_labels = le.inverse_transform(y_test_pred)

    errors = []
    for i in range(len(test_df)):
        if y_test_pred[i] != y_test[i]:
            errors.append({
                "message": test_df.iloc[i][COL_MESSAGE],
                "true_label": y_test_labels[i],
                "predicted_label": y_pred_labels[i],
                "language": test_df.iloc[i][COL_LANGUAGE],
                "category": test_df.iloc[i][COL_CATEGORY],
                "probability": float(y_test_proba[i]) if y_test_proba is not None else None,
                "msg_length": len(str(test_df.iloc[i][COL_MESSAGE])),
                "error_type": (
                    "False Negative (missed scam)"
                    if y_test[i] == 1
                    else "False Positive (safe flagged)"
                ),
            })

    # Save error report
    err_df = pd.DataFrame(errors)
    err_path = os.path.join(REPORT_DIR, "error_analysis.csv")
    err_df.to_csv(err_path, index=False)

    # Print summary
    fn_errors = [e for e in errors if "False Negative" in e["error_type"]]
    fp_errors = [e for e in errors if "False Positive" in e["error_type"]]

    print(f"\n[ERRORS] Total errors: {len(errors)}")
    print(f"  False Negatives (missed scams): {len(fn_errors)}")
    print(f"  False Positives (safe flagged):  {len(fp_errors)}")

    if fn_errors:
        print("\n  ── False Negatives (missed scams) ──")
        for e in fn_errors[:5]:
            print(f"  [{e['language']}] {e['message'][:80]}...")
            print(f"    Category: {e['category']}, Prob: {e['probability']:.3f}" if e['probability'] else "")

    if fp_errors:
        print("\n  ── False Positives (safe flagged as scam) ──")
        for e in fp_errors[:5]:
            print(f"  [{e['language']}] {e['message'][:80]}...")
            print(f"    Category: {e['category']}, Prob: {e['probability']:.3f}" if e['probability'] else "")

    print(f"\n[REPORT] Error analysis saved -> {err_path}")
    return errors


# ──────────────────────────────────────────────────────────────────────────────
# STEP 11 — Language-Specific Evaluation
# ──────────────────────────────────────────────────────────────────────────────

def language_evaluation(test_df, y_test, y_test_pred, le):
    """Evaluate performance per language type."""
    y_test_labels = le.inverse_transform(y_test)
    y_pred_labels = le.inverse_transform(y_test_pred)

    results = {}
    for lang in test_df[COL_LANGUAGE].unique():
        mask = test_df[COL_LANGUAGE] == lang
        if mask.sum() < 2:
            continue
        y_true_lang = y_test[mask]
        y_pred_lang = y_test_pred[mask]

        acc = accuracy_score(y_true_lang, y_pred_lang)
        prec = precision_score(y_true_lang, y_pred_lang, pos_label=1, zero_division=0)
        rec = recall_score(y_true_lang, y_pred_lang, pos_label=1, zero_division=0)
        f1 = f1_score(y_true_lang, y_pred_lang, pos_label=1, zero_division=0)

        results[lang] = {
            "samples": int(mask.sum()),
            "accuracy": round(acc, 4),
            "precision": round(prec, 4),
            "recall": round(rec, 4),
            "f1": round(f1, 4),
        }
        print(f"  [{lang:12s}] n={mask.sum():3d}  "
              f"Acc={acc:.4f}  P={prec:.4f}  R={rec:.4f}  F1={f1:.4f}")

    # Save
    lang_path = os.path.join(REPORT_DIR, "language_evaluation.json")
    with open(lang_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\n[REPORT] Language evaluation saved -> {lang_path}")
    return results


# ──────────────────────────────────────────────────────────────────────────────
# STEP 12 — Overfitting Check
# ──────────────────────────────────────────────────────────────────────────────

def overfitting_check(cv_results, best_name, test_metrics):
    """Compare train vs CV vs test to detect overfitting."""
    cv = cv_results.get(best_name, {})
    report = {
        "best_model": best_name,
        "cv_accuracy_mean": cv.get("cv_accuracy_mean", 0),
        "cv_f1_mean": cv.get("cv_f1_mean", 0),
        "train_accuracy_mean": cv.get("train_accuracy_mean", 0),
        "train_f1_mean": cv.get("train_f1_mean", 0),
        "test_accuracy": test_metrics.get("accuracy", 0),
        "test_f1": test_metrics.get("f1", 0),
    }

    # Gap analysis
    acc_gap = report["train_accuracy_mean"] - report["test_accuracy"]
    f1_gap = report["train_f1_mean"] - report["test_f1"]

    print(f"\n[OVERFITTING CHECK]")
    print(f"  Train Acc:  {report['train_accuracy_mean']:.4f}")
    print(f"  CV Acc:     {report['cv_accuracy_mean']:.4f}")
    print(f"  Test Acc:   {report['test_accuracy']:.4f}")
    print(f"  Acc gap (train - test): {acc_gap:.4f}")
    print(f"  Train F1:   {report['train_f1_mean']:.4f}")
    print(f"  CV F1:      {report['cv_f1_mean']:.4f}")
    print(f"  Test F1:    {report['test_f1']:.4f}")
    print(f"  F1 gap (train - test):  {f1_gap:.4f}")

    if acc_gap > 0.10 or f1_gap > 0.10:
        print("  [WARNING] Significant overfitting detected (gap > 0.10)")
    else:
        print("  [OK] No significant overfitting detected")

    report["accuracy_gap"] = round(acc_gap, 4)
    report["f1_gap"] = round(f1_gap, 4)
    report["overfitting_detected"] = acc_gap > 0.10 or f1_gap > 0.10

    return report


# ──────────────────────────────────────────────────────────────────────────────
# STEP 14 — Save Final Model
# ──────────────────────────────────────────────────────────────────────────────

def save_final_model(
    best_name, best_artifacts, best_threshold, le,
    cv_results, test_metrics, overfit_report, lang_results,
):
    """Save all model artifacts using joblib."""
    os.makedirs(MODEL_DIR, exist_ok=True)

    # Save label encoder
    joblib.dump(le, os.path.join(MODEL_DIR, LABEL_ENCODER_FILENAME))

    # Save threshold
    joblib.dump(best_threshold, os.path.join(MODEL_DIR, THRESHOLD_FILENAME))

    # Save model artifacts
    config = MODEL_CONFIGS[best_name]
    if config["type"] == "simple_pipeline":
        joblib.dump(best_artifacts, os.path.join(MODEL_DIR, FULL_PIPELINE_FILENAME))
    elif config["type"] == "combined":
        joblib.dump(best_artifacts, os.path.join(MODEL_DIR, FULL_PIPELINE_FILENAME))
    elif config["type"] == "engineered":
        joblib.dump(best_artifacts, os.path.join(MODEL_DIR, FULL_PIPELINE_FILENAME))

    # Save metadata
    metadata = {
        "best_model_name": best_name,
        "model_description": config["description"],
        "model_type": config["type"],
        "random_seed": RANDOM_SEED,
        "n_folds": N_FOLDS,
        "threshold": best_threshold,
        "label_mapping": {int(k): v for k, v in zip(
            le.transform(le.classes_), le.classes_
        )},
        "cv_results": cv_results.get(best_name, {}),
        "test_metrics": test_metrics,
        "overfitting_check": overfit_report,
        "language_results": lang_results,
    }
    joblib.dump(metadata, os.path.join(MODEL_DIR, METADATA_FILENAME))

    # Also save as JSON for readability
    meta_json_path = os.path.join(REPORT_DIR, "model_metadata.json")
    with open(meta_json_path, "w") as f:
        json.dump(metadata, f, indent=2, default=str)

    print(f"\n[SAVE] Final model artifacts saved to {MODEL_DIR}/")
    print(f"  - {FULL_PIPELINE_FILENAME}")
    print(f"  - {LABEL_ENCODER_FILENAME}")
    print(f"  - {THRESHOLD_FILENAME}")
    print(f"  - {METADATA_FILENAME}")
    print(f"[SAVE] Model metadata JSON -> {meta_json_path}")

    return metadata
