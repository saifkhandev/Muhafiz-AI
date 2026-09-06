"""
Scam-Call Detection — Orchestration & Aggregation
Audio → Transcription → Per-segment classification → Call-level verdict.

Usage:
    from src.call_predict import predict_call
    result = predict_call("path/to/recording.mp3")
    print(result["overall_risk"])  # "High" | "Medium" | "Low"
"""
import logging
import os
import sys
from time import perf_counter

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config import (
    CALL_FORCE_HIGH_MAX_PROB,
    CALL_FORCE_MEDIUM_MAX_PROB,
    CALL_RISK_HIGH,
    CALL_RISK_MEDIUM,
    CALL_WEIGHT_MAX_PROB,
    CALL_WEIGHT_SCAM_RATIO,
    CALL_WEIGHT_WEIGHTED_MEAN,
    CALL_WINDOW_GAP_SECONDS,
    CALL_WINDOW_OVERLAP_SECONDS,
    CALL_WINDOW_SECONDS,
)
from src.audio import cleanup_temp_files, export_wav, load_audio
from src.predict import load_model, predict_messages
from src.transcribe import build_time_windows, load_stt_model, transcribe_audio

logger = logging.getLogger("uvicorn.error")


def _log_timing(stage: str, elapsed: float, **fields) -> None:
    """Write timing diagnostics without logging call contents or filenames."""
    details = " ".join(f"{key}={value}" for key, value in fields.items())
    logger.info("audio_timing stage=%s seconds=%.3f %s", stage, elapsed, details)


# ── Call-level scam-pattern detection ────────────────────────────────────────
# The per-segment classifier sees only a short window. These patterns look at
# the full call transcript and boost the risk when multiple scam indicators
# appear together across segments.

_CALL_SCAM_PATTERNS = [
    # Credit-/debit-card phishing: card context + credential/verification demand.
    {
        "name": "card_verification_scam",
        "context_groups": [["visa", "mastercard", "credit card", "debit card"]],
        "demands": ["confirm", "verify", "security code", "cvv", "expiration", "expiry"],
    },
    # Fake fraud-department impersonation requires both the claimed department
    # and card/account context; merely discussing fraud is not enough.
    {
        "name": "fraud_department_impersonation",
        "context_groups": [
            ["fraud watch", "fraud division", "fraud department", "security department"],
            ["visa", "mastercard", "credit card", "debit card", "card", "account"],
        ],
        "demands": ["confirm", "verify", "details", "information", "security code", "card number"],
    },
    # OTP / code request (spoken, not an informational SMS).
    {
        "name": "spoken_otp_request",
        "context_groups": [["otp", "verification code", "security code", "pin"]],
        "demands": ["tell me", "share", "provide", "give me", "bata", "bataein", "batao"],
    },
    # Remote access / screen sharing.
    {
        "name": "remote_access_scam",
        "context_groups": [["anydesk", "teamviewer", "remote", "screen share"]],
        "demands": ["install", "download", "open", "run", "click", "give access"],
    },
    # Prize/lottery + fee/payment request (spoken).
    {
        "name": "spoken_prize_scam",
        "context_groups": [["won", "prize", "lottery", "lucky draw", "winner", "inaam", "jeet"]],
        "demands": ["fee", "pay", "send", "bhej", "charges", "tax"],
    },
]


def _detect_call_scam_patterns(full_text: str) -> list:
    """Return contextual scam patterns that span otherwise separate windows."""
    text_lower = full_text.lower()
    matched = []
    for pattern in _CALL_SCAM_PATTERNS:
        has_context = all(
            any(term in text_lower for term in group)
            for group in pattern["context_groups"]
        )
        has_demand = any(term in text_lower for term in pattern["demands"])
        if has_context and has_demand:
            matched.append(pattern["name"])
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

    # A strong short window alone is insufficient to force High: legitimate
    # support/bank calls can include similar vocabulary. Require a separate
    # full-call pattern for that escalation, while retaining a Medium floor so
    # a reviewer can see the strongest suspicious evidence.
    if call_patterns and max_prob >= CALL_FORCE_HIGH_MAX_PROB:
        risk_score = max(risk_score, CALL_RISK_HIGH + 0.10)
    elif max_prob >= CALL_FORCE_MEDIUM_MAX_PROB:
        risk_score = max(risk_score, CALL_RISK_MEDIUM + 0.10)

    # The weighted formula can otherwise cross the High threshold from one
    # isolated window. Keep that situation at Medium until another suspicious
    # window or a separate full-call pattern corroborates it.
    if not call_patterns and scam_count == 1 and max_prob >= CALL_FORCE_HIGH_MAX_PROB:
        risk_score = min(risk_score, CALL_RISK_HIGH - 0.0001)

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


def _classify_windows(windows, artifacts, le, threshold, metadata) -> int:
    """Classify non-empty call windows in a single vectorization/model pass."""
    active_windows = []
    texts = []
    skipped_count = 0
    for window in windows:
        text = (window.get("cleaned_text") or window.get("text") or "").strip()
        if window.get("was_skipped") or not text:
            window["was_skipped"] = True
            window["label"] = "Skipped"
            window["scam_probability"] = 0.0
            window["confidence"] = 0.0
            skipped_count += 1
            continue
        active_windows.append(window)
        texts.append(text)

    predictions = predict_messages(
        texts,
        artifacts=artifacts,
        le=le,
        threshold=threshold,
        metadata=metadata,
    )
    for window, prediction in zip(active_windows, predictions):
        window["label"] = prediction["label"]
        window["scam_probability"] = prediction["scam_probability"]
        window["confidence"] = prediction["confidence"]
        window["guardrail"] = prediction["guardrail"]
    return skipped_count


def _build_call_result(
    windows,
    skipped_count: int,
    call_duration: float,
    transcription_model: str,
    language_detected: str,
    metadata,
    threshold: float,
    timings: dict,
) -> dict:
    """Aggregate classified windows and return the public call-analysis shape."""
    full_transcript = " ".join(
        window.get("cleaned_text") or window.get("text", "")
        for window in windows
        if not window.get("was_skipped")
    )
    aggregate_started = perf_counter()
    call_patterns = _detect_call_scam_patterns(full_transcript)
    aggregation = _aggregate_predictions(windows, threshold, call_patterns)
    timings["aggregation"] = perf_counter() - aggregate_started
    _log_timing(
        "aggregation",
        timings["aggregation"],
        windows=aggregation["total_segments"],
        patterns=len(call_patterns),
    )

    return {
        "overall_risk": aggregation["overall_risk"],
        "risk_score": aggregation["risk_score"],
        "max_segment_probability": aggregation["max_segment_probability"],
        "scam_segment_count": aggregation["scam_segment_count"],
        "total_segments": aggregation["total_segments"],
        "skipped_segments": skipped_count,
        "call_duration_seconds": round(call_duration, 2),
        "transcription_model": transcription_model,
        "language_detected": language_detected,
        "segment_predictions": windows,
        "model_name": metadata.get("best_model_name", "unknown"),
        "threshold_used": threshold,
        "call_patterns": call_patterns,
        "timings": {name: round(seconds, 4) for name, seconds in timings.items()},
    }


def predict_call_from_transcript(
    transcript: str,
    artifacts=None,
    le=None,
    threshold=None,
    metadata=None,
):
    """Evaluate a labeled transcript fixture without audio decoding or Whisper."""
    if artifacts is None:
        artifacts, le, threshold, metadata = load_model()
    text = transcript.strip()
    if not text:
        return _build_call_result(
            [], 0, 0.0, "transcript-fixture", "unknown", metadata, threshold, {}
        )

    started = perf_counter()
    estimated_duration = max(CALL_WINDOW_SECONDS, len(text.split()) / 2.5)
    windows = [{
        "segment_index": 0,
        "start_time": 0.0,
        "end_time": round(estimated_duration, 3),
        "text": text,
        "cleaned_text": text,
        "was_concatenated": False,
        "was_skipped": False,
        "source_segment_count": 1,
    }]
    classification_started = perf_counter()
    skipped_count = _classify_windows(windows, artifacts, le, threshold, metadata)
    timings = {"classification": perf_counter() - classification_started}
    _log_timing("transcript_classification", timings["classification"], windows=len(windows))
    result = _build_call_result(
        windows,
        skipped_count,
        estimated_duration,
        "transcript-fixture",
        "unknown",
        metadata,
        threshold,
        timings,
    )
    result["timings"]["total"] = round(perf_counter() - started, 4)
    return result


def predict_call(
    audio_path: str,
    artifacts=None,
    le=None,
    threshold=None,
    metadata=None,
    stt_model=None,
    stt_backend: str = None,
):
    """Run audio normalization, transcription, batch classification, and aggregation."""
    started = perf_counter()
    if artifacts is None:
        artifacts, le, threshold, metadata = load_model()
    if stt_model is None:
        stt_model, stt_backend = load_stt_model()

    stt_label = str(stt_backend)
    timings = {}

    audio_started = perf_counter()
    audio = load_audio(audio_path)
    call_duration = len(audio) / 1000.0
    timings["audio_load_duration_inspection"] = perf_counter() - audio_started
    _log_timing(
        "audio_load_duration_inspection",
        timings["audio_load_duration_inspection"],
        duration_seconds=round(call_duration, 2),
    )

    conversion_started = perf_counter()
    wav_path = export_wav(audio)
    timings["audio_conversion"] = perf_counter() - conversion_started
    _log_timing("audio_conversion", timings["audio_conversion"])

    transcription_started = perf_counter()
    try:
        raw_segments, detected_lang = transcribe_audio(wav_path, stt_model, stt_backend)
    finally:
        cleanup_temp_files()
    timings["transcription"] = perf_counter() - transcription_started
    _log_timing("transcription", timings["transcription"], raw_segments=len(raw_segments))

    if not raw_segments:
        empty_result = _build_call_result(
            [], 0, call_duration, stt_label, "unknown", metadata, threshold, timings
        )
        empty_result["timings"]["total"] = round(perf_counter() - started, 4)
        _log_timing("call_total", perf_counter() - started, raw_segments=0)
        return empty_result

    cleanup_started = perf_counter()
    windows, skipped_count = build_time_windows(
        raw_segments,
        window_seconds=CALL_WINDOW_SECONDS,
        overlap_seconds=CALL_WINDOW_OVERLAP_SECONDS,
        gap_seconds=CALL_WINDOW_GAP_SECONDS,
    )
    timings["text_cleanup_windowing"] = perf_counter() - cleanup_started
    _log_timing(
        "text_cleanup_windowing",
        timings["text_cleanup_windowing"],
        raw_segments=len(raw_segments),
        windows=len(windows),
        skipped=skipped_count,
    )

    classification_started = perf_counter()
    skipped_count += _classify_windows(windows, artifacts, le, threshold, metadata)
    timings["classification"] = perf_counter() - classification_started
    _log_timing("classification", timings["classification"], windows=len(windows))

    result = _build_call_result(
        windows,
        skipped_count,
        call_duration,
        stt_label,
        detected_lang,
        metadata,
        threshold,
        timings,
    )
    result["timings"]["total"] = round(perf_counter() - started, 4)
    _log_timing("call_total", perf_counter() - started, windows=len(windows))
    return result
