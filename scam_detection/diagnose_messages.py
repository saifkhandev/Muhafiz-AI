"""
Diagnostic script for 3 misclassified messages.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import json
import numpy as np
from src.predict import load_model, predict_message
from src.features import ScamFeatureExtractor
from src.preprocessing import (
    URGENCY_KEYWORDS, FINANCIAL_KEYWORDS, CREDENTIAL_KEYWORDS,
    PRIZE_KEYWORDS, THREAT_KEYWORDS, OTP_KEYWORDS,
    ALL_LEGIT_BRANDS, DO_NOT_SHARE_PATTERNS, TXN_ID_PATTERNS,
    ImprovedScamTextNormalizer,
)

MESSAGES = [
    ("FP-1", "Safe", "JazzCash Mobile Account kholne ka shukria. Account istemal krne k liyeJazzCash App download karain aur apni MPIN bnaeain. Download: https://onelink.to/JazzCash"),
    ("FP-2", "Safe", "Your MPIN for JazzCash Mobile Account has been created. Your mobile number is also your Mobile Account number. Never share your MPIN with anyone. Helpline: 4444"),
    ("FN-1", "Scam", "Your parcel from Mantra is delivered. Kindly tell us the OTP sent to your email address to confirm the delivery process"),
]

def matched_keywords(text_lower, keywords):
    return [kw for kw in keywords if kw.lower() in text_lower]

def main():
    artifacts, le, threshold, metadata = load_model()
    extractor = ScamFeatureExtractor()
    normalizer = ImprovedScamTextNormalizer()

    print(f"Model: {metadata.get('best_model_name', 'unknown')}")
    print(f"Threshold: {threshold}")
    print(f"Model type: {metadata.get('model_type', 'unknown')}")
    print("=" * 80)

    for tag, true_label, msg in MESSAGES:
        result = predict_message(msg, artifacts=artifacts, le=le, threshold=threshold, metadata=metadata)
        prob = result["scam_probability"]
        dist = prob - threshold

        print(f"\n[{tag}] TRUE: {true_label} | PRED: {result['label']} | PROB: {prob:.4f} | DISTANCE FROM THRESHOLD: {dist:+.4f}")
        print(f"Message: {msg}")
        print(f"Model: {result['model_name']}")

        # Normalized text
        norm_text = normalizer.transform([msg])[0]
        print(f"\nNormalized: {norm_text}")

        # Feature values
        feats = extractor.transform([msg])[0]
        feat_names = extractor.FEATURE_NAMES
        print("\n--- Feature vector (non-zero) ---")
        for name, val in zip(feat_names, feats):
            if val != 0:
                print(f"  {name}: {val}")

        # Keyword matches
        t_lower = msg.lower()
        print("\n--- Keyword matches ---")
        print(f"  Urgency: {matched_keywords(t_lower, URGENCY_KEYWORDS)}")
        print(f"  Financial: {matched_keywords(t_lower, FINANCIAL_KEYWORDS)}")
        print(f"  Credential: {matched_keywords(t_lower, CREDENTIAL_KEYWORDS)}")
        print(f"  Prize: {matched_keywords(t_lower, PRIZE_KEYWORDS)}")
        print(f"  Threat: {matched_keywords(t_lower, THREAT_KEYWORDS)}")
        print(f"  OTP: {matched_keywords(t_lower, OTP_KEYWORDS)}")
        print(f"  Legit brands matched: {[b for b in ALL_LEGIT_BRANDS if b in t_lower]}")
        print(f"  Do-not-share matched: {[p for p in DO_NOT_SHARE_PATTERNS if p in t_lower]}")
        print(f"  Txn ID patterns matched: {[p for p in TXN_ID_PATTERNS if p in t_lower]}")

        print("\n" + "-" * 80)

if __name__ == "__main__":
    main()
