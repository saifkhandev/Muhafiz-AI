"""Regression tests for time-based call windows and contextual aggregation."""
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from src.call_predict import _aggregate_predictions, _detect_call_scam_patterns
from src.transcribe import build_time_windows

RAW_SEGMENTS = [
    {"start": 0.0, "end": 2.0, "text": "Hello this is the fraud watch division"},
    {"start": 2.0, "end": 5.0, "text": "about your Visa and Mastercard account"},
    {"start": 5.0, "end": 8.0, "text": "Please confirm your card"},
    {"start": 8.0, "end": 8.4, "text": "um"},
    {"start": 10.0, "end": 13.0, "text": "to receive a security code which card will you be using today"},
]

windows, skipped = build_time_windows(RAW_SEGMENTS, window_seconds=12.0, overlap_seconds=2.0)
assert skipped == 1
assert len(windows) == 2
assert all(window["end_time"] - window["start_time"] <= 12.0 for window in windows)
assert "confirm your card" in windows[0]["cleaned_text"].lower()
assert "security code" in windows[1]["cleaned_text"].lower()

patterns = _detect_call_scam_patterns(" ".join(window["text"] for window in windows))
assert "card_verification_scam" in patterns
assert "fraud_department_impersonation" in patterns

sparse_high_signal = [
    {"start_time": 0.0, "end_time": 12.0, "scam_probability": 0.95, "was_skipped": False},
    {"start_time": 12.0, "end_time": 24.0, "scam_probability": 0.05, "was_skipped": False},
    {"start_time": 24.0, "end_time": 36.0, "scam_probability": 0.05, "was_skipped": False},
    {"start_time": 36.0, "end_time": 48.0, "scam_probability": 0.05, "was_skipped": False},
]
without_context = _aggregate_predictions(sparse_high_signal, 0.63, [])
with_context = _aggregate_predictions(sparse_high_signal, 0.63, ["card_verification_scam"])
assert without_context["overall_risk"] != "High"
assert with_context["overall_risk"] == "High"

print("Call window and aggregation tests passed.")
