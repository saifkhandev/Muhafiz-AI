"""
STEP 15 — Prediction Interface
Accepts a single message and returns scam/safe classification with confidence.

Usage:
    python predict.py "Your message text here"
    python predict.py "Aap ka account block hone wala hai. Rs. 5000 bhejein."
"""
import sys
import os
import numpy as np
import joblib

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config import MODEL_DIR, LABEL_SCAM, FULL_PIPELINE_FILENAME, LABEL_ENCODER_FILENAME, THRESHOLD_FILENAME, METADATA_FILENAME
from src.train import MODEL_CONFIGS
from src.guardrails import apply_guardrails


def load_model():
    """Load the saved model artifacts."""
    artifacts = joblib.load(os.path.join(MODEL_DIR, FULL_PIPELINE_FILENAME))
    le = joblib.load(os.path.join(MODEL_DIR, LABEL_ENCODER_FILENAME))
    threshold = joblib.load(os.path.join(MODEL_DIR, THRESHOLD_FILENAME))
    metadata = joblib.load(os.path.join(MODEL_DIR, METADATA_FILENAME))
    return artifacts, le, threshold, metadata


def predict_message(message: str, artifacts=None, le=None, threshold=None, metadata=None):
    """
    Classify a single message.

    Returns:
        dict with:
            label: "Scam" or "Safe"
            scam_probability: float 0-1
            confidence: float 0-1
            threshold_used: float
            model_name: str
    """
    if artifacts is None:
        artifacts, le, threshold, metadata = load_model()

    model_name = metadata["best_model_name"]
    model_type = metadata["model_type"]

    from scipy.sparse import issparse

    if model_type == "simple_pipeline":
        # sklearn Pipeline or CalibratedClassifierCV
        if hasattr(artifacts, "predict_proba"):
            # CalibratedClassifierCV or Pipeline with predict_proba
            proba = artifacts.predict_proba([message])[:, 1][0]
        elif hasattr(artifacts[-1], "predict_proba"):
            proba = artifacts.predict_proba([message])[:, 1][0]
        elif hasattr(artifacts[-1], "decision_function"):
            df = artifacts.decision_function([message])[0]
            proba = 1 / (1 + np.exp(-df))
        elif hasattr(artifacts, "decision_function"):
            df = artifacts.decision_function([message])[0]
            proba = 1 / (1 + np.exp(-df))
        else:
            proba = None
        pred_label_idx = int(proba >= threshold) if proba is not None else int(artifacts.predict([message])[0])

    elif model_type == "combined":
        norm = artifacts["normalizer"]
        vec = artifacts["vectorizer"]
        clf = artifacts["clf"]
        X_norm = norm.transform([message])
        X_vec = vec.transform(X_norm)
        if hasattr(clf, "predict_proba"):
            proba = clf.predict_proba(X_vec)[:, 1][0]
        elif hasattr(clf, "decision_function"):
            df = clf.decision_function(X_vec)[0]
            proba = 1 / (1 + np.exp(-df))
        else:
            proba = None
        pred_label_idx = int(proba >= threshold) if proba is not None else int(clf.predict(X_vec)[0])

    elif model_type == "engineered":
        norm = artifacts["normalizer"]
        tfidf = artifacts["tfidf"]
        feat_ext = artifacts["feature_extractor"]
        clf = artifacts["clf"]

        X_norm = norm.transform([message])
        X_tfidf = tfidf.transform(X_norm)
        X_eng = feat_ext.transform([message])

        X_tfidf_d = X_tfidf.toarray() if issparse(X_tfidf) else X_tfidf
        X_combined = np.hstack([X_tfidf_d, X_eng])

        if hasattr(clf, "predict_proba"):
            proba = clf.predict_proba(X_combined)[:, 1][0]
        elif hasattr(clf, "decision_function"):
            df = clf.decision_function(X_combined)[0]
            proba = 1 / (1 + np.exp(-df))
        else:
            proba = None
        pred_label_idx = int(proba >= threshold) if proba is not None else int(clf.predict(X_combined)[0])

    label = le.inverse_transform([pred_label_idx])[0]
    scam_prob = float(proba) if proba is not None else None
    confidence = max(proba, 1 - proba) if proba is not None else None

    # Apply targeted post-processing guardrails for known failure modes
    guardrail_proba, guardrail_label, guardrail_rule = apply_guardrails(
        message, scam_prob, label
    )
    if guardrail_rule is not None:
        scam_prob = guardrail_proba
        label = guardrail_label
        pred_label_idx = le.transform([label])[0]
        confidence = max(scam_prob, 1 - scam_prob) if scam_prob is not None else None

    return {
        "label": label,
        "scam_probability": round(scam_prob, 4) if scam_prob is not None else None,
        "confidence": round(confidence, 4) if confidence is not None else None,
        "threshold_used": threshold,
        "model_name": model_name,
        "model_description": metadata.get("model_description", ""),
        "guardrail": guardrail_rule,
    }


# ──────────────────────────────────────────────────────────────────────────────
# For call-level scam detection (audio → STT → classification → verdict),
# see: src/call_predict.py — predict_call()
# ──────────────────────────────────────────────────────────────────────────────

# ──────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python predict.py \"Your message text here\"")
        print("Example: python predict.py \"Your account has been blocked. Verify immediately.\"")
        sys.exit(1)

    message = " ".join(sys.argv[1:])
    print(f"\nAnalyzing message:\n  \"{message}\"\n")

    result = predict_message(message)

    print(f"  Result:        {result['label'].upper()}")
    print(f"  Scam Prob:     {result['scam_probability']:.4f}" if result['scam_probability'] is not None else "  Scam Prob:     N/A")
    print(f"  Confidence:    {result['confidence']:.4f}" if result['confidence'] is not None else "  Confidence:    N/A")
    print(f"  Threshold:     {result['threshold_used']}")
    print(f"  Model:         {result['model_name']}")
    print(f"  Description:   {result['model_description']}")
    print()
