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


def _base_predictions(messages, artifacts, le, threshold, metadata):
    """Return unmodified model predictions for a batch of messages."""
    if not messages:
        return []

    model_type = metadata["model_type"]
    from scipy.sparse import issparse

    if model_type == "simple_pipeline":
        predictor = artifacts
        if hasattr(predictor, "predict_proba"):
            probabilities = predictor.predict_proba(messages)[:, 1]
        elif hasattr(predictor, "decision_function"):
            decisions = predictor.decision_function(messages)
            probabilities = 1 / (1 + np.exp(-decisions))
        else:
            probabilities = None
        predicted_indices = (
            (probabilities >= threshold).astype(int)
            if probabilities is not None
            else np.asarray(predictor.predict(messages), dtype=int)
        )

    elif model_type == "combined":
        normalizer = artifacts["normalizer"]
        vectorizer = artifacts["vectorizer"]
        classifier = artifacts["clf"]
        normalized = normalizer.transform(messages)
        features = vectorizer.transform(normalized)
        if hasattr(classifier, "predict_proba"):
            probabilities = classifier.predict_proba(features)[:, 1]
        elif hasattr(classifier, "decision_function"):
            decisions = classifier.decision_function(features)
            probabilities = 1 / (1 + np.exp(-decisions))
        else:
            probabilities = None
        predicted_indices = (
            (probabilities >= threshold).astype(int)
            if probabilities is not None
            else np.asarray(classifier.predict(features), dtype=int)
        )

    elif model_type == "engineered":
        normalizer = artifacts["normalizer"]
        tfidf = artifacts["tfidf"]
        feature_extractor = artifacts["feature_extractor"]
        classifier = artifacts["clf"]
        normalized = normalizer.transform(messages)
        tfidf_features = tfidf.transform(normalized)
        engineered_features = feature_extractor.transform(messages)
        dense_tfidf = tfidf_features.toarray() if issparse(tfidf_features) else tfidf_features
        features = np.hstack([dense_tfidf, engineered_features])
        if hasattr(classifier, "predict_proba"):
            probabilities = classifier.predict_proba(features)[:, 1]
        elif hasattr(classifier, "decision_function"):
            decisions = classifier.decision_function(features)
            probabilities = 1 / (1 + np.exp(-decisions))
        else:
            probabilities = None
        predicted_indices = (
            (probabilities >= threshold).astype(int)
            if probabilities is not None
            else np.asarray(classifier.predict(features), dtype=int)
        )

    else:
        raise ValueError(f"Unsupported model type: {model_type}")

    labels = le.inverse_transform(predicted_indices)
    return [
        {
            "base_label": str(label),
            "base_scam_probability": float(probabilities[index]) if probabilities is not None else None,
        }
        for index, label in enumerate(labels)
    ]


def predict_messages(messages, artifacts=None, le=None, threshold=None, metadata=None):
    """
    Classify a batch of messages with one vectorization/model pass.

    Guardrails remain per-message because they depend on contextual language.
    Each result exposes the base-model result so benchmark reports can identify
    whether a guardrail changed the final verdict.
    """
    if artifacts is None:
        artifacts, le, threshold, metadata = load_model()
    if not messages:
        return []

    base_predictions = _base_predictions(messages, artifacts, le, threshold, metadata)
    model_name = metadata["best_model_name"]
    results = []

    for message, base in zip(messages, base_predictions):
        base_probability = base["base_scam_probability"]
        label = base["base_label"]
        scam_probability = base_probability
        guardrail_probability, guardrail_label, guardrail_rule = apply_guardrails(
            message, scam_probability, label
        )
        if guardrail_rule is not None:
            scam_probability = guardrail_probability
            label = guardrail_label

        confidence = (
            max(scam_probability, 1 - scam_probability)
            if scam_probability is not None
            else None
        )
        results.append({
            "label": label,
            "scam_probability": round(scam_probability, 4) if scam_probability is not None else None,
            "confidence": round(confidence, 4) if confidence is not None else None,
            "threshold_used": threshold,
            "model_name": model_name,
            "model_description": metadata.get("model_description", ""),
            "guardrail": guardrail_rule,
            "base_label": base["base_label"],
            "base_scam_probability": (
                round(base_probability, 4) if base_probability is not None else None
            ),
            "guardrail_changed_prediction": bool(
                guardrail_rule is not None and label != base["base_label"]
            ),
        })
    return results


def predict_message(message: str, artifacts=None, le=None, threshold=None, metadata=None):
    """Classify one message; use :func:`predict_messages` for batches."""
    return predict_messages(
        [message],
        artifacts=artifacts,
        le=le,
        threshold=threshold,
        metadata=metadata,
    )[0]


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
