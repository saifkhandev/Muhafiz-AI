"""
Scam-Call Detection — Orchestration & Aggregation
Audio → Transcription → Per-segment classification → Call-level verdict.

Usage:
    from src.call_predict import predict_call
    result = predict_call("path/to/recording.mp3")
    print(result["overall_risk"])  # "High" | "Medium" | "Low"
"""
import os
import re
import sys
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config import (
    CALL_RISK_HIGH, CALL_RISK_MEDIUM,
    CALL_WEIGHT_MAX_PROB, CALL_WEIGHT_WEIGHTED_MEAN, CALL_WEIGHT_SCAM_RATIO,
    CALL_FORCE_HIGH_MAX_PROB, CALL_FORCE_MEDIUM_MAX_PROB,
)
from src.audio import load_audio, export_wav, cleanup_temp_files
from src.transcribe import load_stt_model, transcribe_audio, process_segments
from src.predict import predict_message, load_model


# ── Call-level scam-pattern detection ────────────────────────────────────────
# The per-segment classifier sees only a short window. These patterns look at
# the full call transcript and boost the risk when multiple scam indicators
# appear together across segments.

_CALL_SCAM_PATTERNS = [
    # Credit-/debit-card phishing: card brand + confirm/verify + security code
    {
        "name": "card_verification_scam",
        "keywords": ["visa", "mastercard", "credit card", "debit card", "card"],
        "demands": ["confirm", "verify", "security code", "cvv", "expiration", "expiry"],
    },
    # Fake bank/fraud-department impersonation
    {
        "name": "fraud_department_impersonation",
        "keywords": ["fraud", "fraud watch", "fraud division", "security department", "bank"],
        "demands": ["confirm", "verify", "details", "information", "card", "account"],
    },
    # OTP / code request (spoken, not SMS)
    {
        "name": "spoken_otp_request",
        "keywords": ["otp", "code", "verification code", "security code", "pin"],
        "demands": ["tell me", "share", "provide", "give me", "bata", "bataein", "batao"],
    },
    # Remote access / screen sharing
    {
        "name": "remote_access_scam",
        "keywords": ["anydesk", "teamviewer", "remote", "screen share", "install", "download"],
        "demands": ["install", "download", "open", "run", "click", "give access"],
    },
    # Prize/lottery + fee/payment request (spoken)
    {
        "name": "spoken_prize_scam",
        "keywords": ["won", "prize", "lottery", "lucky draw", "winner", "inaam", "jeet"],
        "demands": ["fee", "pay", "send", "bhej", "charges", "tax"],
    },
]


def _detect_call_scam_patterns(full_text: str) -> list:
    """
    Return names of call-level scam patterns matched in the full transcript.
    A pattern matches only if it finds at least one keyword AND at least one
    demand/action in the same call.
    """
    text_lower = full_text.lower()
    matched = []
    for pat in _CALL_SCAM_PATTERNS:
        has_keyword = any(kw.lower() in text_lower for kw in pat["keywords"])
        has_demand = any(d.lower() in text_lower for d in pat["demands"])
        if has_keyword and has_demand:
            matched.append(pat["name"])
    return matched


def _aggregate_predictions(
    segment_results: list,
    model_threshold: float,
    call_patterns: list = None,
) -> dict:
    """
    Aggregate per-segment predictions into a call-level risk score.

    Signals:
        1. max_prob — strongest single scam segment
        2. weighted_mean — temporal weighting (first/last 25% get 1.5x weight)
        3. scam_ratio — fraction of segments above model threshold
        4. call_patterns — cross-segment scam indicators (e.g. card + verify)

    Returns:
        {
            "overall_risk": str,
            "risk_score": float,
            "max_segment_probability": float,
            "scam_segment_count": int,
            "total_segments": int,
        }
    """
    call_patterns = call_patterns or []

    # Only count non-skipped segments
    active = [s for s in segment_results if not s["was_skipped"]]
    if not active:
        return {
            "overall_risk": "Low",
            "risk_score": 0.0,
            "max_segment_probability": 0.0,
            "scam_segment_count": 0,
            "total_segments": 0,
        }

    probs = [s["scam_probability"] for s in active]
    n = len(probs)

    # Signal 1: Max probability
    max_prob = max(probs)

    # Signal 2: Temporally weighted mean
    # Determine call boundaries for temporal weighting
    call_start = active[0]["start_time"]
    call_end = active[-1]["end_time"]
    call_duration = call_end - call_start

    if call_duration > 0:
        q1 = call_start + call_duration * 0.25
        q3 = call_start + call_duration * 0.75
    else:
        q1 = call_start
        q3 = call_end

    weighted_sum = 0.0
    weight_total = 0.0
    for seg, prob in zip(active, probs):
        mid = (seg["start_time"] + seg["end_time"]) / 2.0
        if mid <= q1 or mid >= q3:
            w = 1.5  # first or last quartile (pressure tactics)
        else:
            w = 1.0
        weighted_sum += w * prob
        weight_total += w

    weighted_mean = weighted_sum / weight_total if weight_total > 0 else 0.0

    # Signal 3: Scam segment ratio
    scam_count = sum(1 for p in probs if p >= model_threshold)
    scam_ratio = scam_count / n

    # Combined risk score
    risk_score = (
        CALL_WEIGHT_MAX_PROB * max_prob
        + CALL_WEIGHT_WEIGHTED_MEAN * weighted_mean
        + CALL_WEIGHT_SCAM_RATIO * scam_ratio
    )

    # Boost for cross-segment scam patterns (full-call context)
    if call_patterns:
        # Each matched pattern adds a small additive boost; cap to avoid
        # pushing arbitrary calls to High.
        risk_score += min(0.15, 0.05 * len(call_patterns))

    # Force floor based on the strongest single segment: a long call with a
    # few very scammy segments should not be drowned out by neutral segments.
    if max_prob >= CALL_FORCE_HIGH_MAX_PROB:
        risk_score = max(risk_score, CALL_RISK_HIGH + 0.10)
    elif max_prob >= CALL_FORCE_MEDIUM_MAX_PROB:
        risk_score = max(risk_score, CALL_RISK_MEDIUM + 0.10)

    # Cap at 1.0
    risk_score = min(risk_score, 1.0)

    # Determine verdict
    if risk_score >= CALL_RISK_HIGH:
        overall_risk = "High"
    elif risk_score >= CALL_RISK_MEDIUM:
        overall_risk = "Medium"
    else:
        overall_risk = "Low"

    return {
        "overall_risk": overall_risk,
        "risk_score": round(risk_score, 4),
        "max_segment_probability": round(max_prob, 4),
        "scam_segment_count": scam_count,
        "total_segments": n,
    }


def predict_call(
    audio_path: str,
    artifacts=None,
    le=None,
    threshold=None,
    metadata=None,
    stt_model=None,
    stt_backend: str = None,
):
    """
    Run the full scam-call detection pipeline on an audio file.

    Args:
        audio_path: Path to audio file (WAV, MP3, M4A, WebM, etc.)
        artifacts: Pre-loaded model artifacts (from load_model())
        le: Pre-loaded label encoder
        threshold: Pre-loaded decision threshold
        metadata: Pre-loaded model metadata
        stt_model: Pre-loaded STT model (from load_stt_model())
        stt_backend: STT backend name ("faster-whisper" or "openai-whisper")

    Returns:
        Dict with:
            overall_risk: "High" | "Medium" | "Low"
            risk_score: float (0-1)
            segment_predictions: list of per-segment dicts
            scam_segment_count: int
            total_segments: int
            skipped_segments: int
            call_duration_seconds: float
            transcription_model: str
            language_detected: str
            model_name: str
            threshold_used: float
    """
    # Load text classification model if not provided
    if artifacts is None:
        artifacts, le, threshold, metadata = load_model()

    # Load STT model if not provided
    if stt_model is None:
        stt_model, stt_backend = load_stt_model()

    stt_label = f"{stt_backend}"

    # Step 1: Load and normalize audio
    print("  [1/4] Loading audio...")
    audio = load_audio(audio_path)
    call_duration = len(audio) / 1000.0

    # Step 2: Export to WAV and transcribe
    print("  [2/4] Transcribing speech to text...")
    wav_path = export_wav(audio)
    try:
        raw_segments, detected_lang = transcribe_audio(wav_path, stt_model, stt_backend)
    finally:
        cleanup_temp_files()

    if not raw_segments:
        return {
            "overall_risk": "Low",
            "risk_score": 0.0,
            "max_segment_probability": 0.0,
            "scam_segment_count": 0,
            "total_segments": 0,
            "skipped_segments": 0,
            "call_duration_seconds": call_duration,
            "transcription_model": stt_label,
            "language_detected": "unknown",
            "segment_predictions": [],
            "model_name": metadata.get("best_model_name", "unknown"),
            "threshold_used": threshold,
        }

    # Step 3: Process segments (filter fillers, concatenate short, clean text)
    print(f"  [3/4] Processing {len(raw_segments)} raw segments...")
    processed = process_segments(raw_segments)

    active_segments = [s for s in processed if not s["was_skipped"]]
    skipped_count = sum(1 for s in processed if s["was_skipped"])
    print(f"        {len(active_segments)} active, {skipped_count} skipped (filler/noise)")

    # Step 4: Classify each active segment
    print(f"  [4/4] Classifying {len(active_segments)} segments...")
    for seg in processed:
        if seg["was_skipped"]:
            seg["label"] = "Skipped"
            seg["scam_probability"] = 0.0
            seg["confidence"] = 0.0
            continue

        text_to_classify = seg["cleaned_text"] if seg["cleaned_text"] else seg["text"]
        if not text_to_classify.strip():
            seg["label"] = "Skipped"
            seg["scam_probability"] = 0.0
            seg["confidence"] = 0.0
            seg["was_skipped"] = True
            skipped_count += 1
            continue

        result = predict_message(
            text_to_classify,
            artifacts=artifacts,
            le=le,
            threshold=threshold,
            metadata=metadata,
        )
        seg["label"] = result["label"]
        seg["scam_probability"] = result["scam_probability"]
        seg["confidence"] = result["confidence"]

    # Aggregate
    # Build full transcript from active segments to detect cross-segment patterns
    full_transcript = " ".join(
        seg["cleaned_text"] if seg["cleaned_text"] else seg["text"]
        for seg in processed if not seg["was_skipped"]
    )
    call_patterns = _detect_call_scam_patterns(full_transcript)
    agg = _aggregate_predictions(processed, threshold, call_patterns)

    return {
        "overall_risk": agg["overall_risk"],
        "risk_score": agg["risk_score"],
        "max_segment_probability": agg["max_segment_probability"],
        "scam_segment_count": agg["scam_segment_count"],
        "total_segments": agg["total_segments"],
        "skipped_segments": skipped_count,
        "call_duration_seconds": round(call_duration, 2),
        "transcription_model": stt_label,
        "language_detected": detected_lang,
        "segment_predictions": processed,
        "model_name": metadata.get("best_model_name", "unknown"),
        "threshold_used": threshold,
    }
