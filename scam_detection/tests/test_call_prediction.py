"""
Test script for scam-call detection pipeline.
Accepts an audio file path, runs the full pipeline, and prints results.

Usage:
    python tests/test_call_prediction.py path/to/recording.mp3
    python tests/test_call_prediction.py path/to/recording.wav
"""
import sys
import os
import io

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from src.call_predict import predict_call
from src.predict import load_model
from src.transcribe import load_stt_model


def format_time(seconds: float) -> str:
    """Format seconds as MM:SS."""
    m, s = divmod(int(seconds), 60)
    return f"{m:02d}:{s:02d}"


def print_result(result: dict):
    """Pretty-print the call prediction result."""
    risk = result["overall_risk"]
    score = result["risk_score"]

    # Risk color (emoji fallback for Windows console)
    risk_indicator = {"High": "HIGH RISK", "Medium": "MEDIUM RISK", "Low": "LOW RISK"}

    print(f"\n{'=' * 70}")
    print(f"  SCAM-CALL DETECTION RESULT")
    print(f"{'=' * 70}")
    print(f"  Verdict:          {risk_indicator.get(risk, risk)}")
    print(f"  Risk Score:       {score:.4f}")
    print(f"  Max Segment Prob: {result['max_segment_probability']:.4f}")
    print(f"  Scam Segments:    {result['scam_segment_count']}/{result['total_segments']}")
    print(f"  Skipped (filler): {result['skipped_segments']}")
    print(f"  Call Duration:    {result['call_duration_seconds']:.1f}s")
    print(f"  STT Model:        {result['transcription_model']}")
    print(f"  Language:         {result['language_detected']}")
    print(f"  Text Model:       {result['model_name']}")

    print(f"\n{'─' * 70}")
    print(f"  SEGMENT-LEVEL ANALYSIS")
    print(f"{'─' * 70}")

    for seg in result["segment_predictions"]:
        if seg["was_skipped"]:
            continue

        ts = f"[{format_time(seg['start_time'])}-{format_time(seg['end_time'])}]"
        label = seg["label"]
        prob = seg["scam_probability"]
        text = seg["cleaned_text"] if seg["cleaned_text"] else seg["text"]

        # Truncate long text for display
        display_text = text[:80] + "..." if len(text) > 80 else text
        concat = " (merged)" if seg["was_concatenated"] else ""

        print(f"  {ts} {label:<5s} P={prob:.3f}  {display_text}{concat}")

    print(f"{'=' * 70}")
    print()


def main():
    if len(sys.argv) < 2:
        print("Usage: python tests/test_call_prediction.py <audio_file>")
        print("  Supported formats: WAV, MP3, M4A, WebM, OGG")
        sys.exit(1)

    audio_path = sys.argv[1]
    if not os.path.isfile(audio_path):
        print(f"Error: File not found: {audio_path}")
        sys.exit(1)

    print(f"\nScam-Call Detection Pipeline")
    print(f"Audio: {audio_path}")
    print(f"{'─' * 50}")

    # Load models once
    print("  Loading text classification model...")
    artifacts, le, threshold, metadata = load_model()

    print("  Loading speech-to-text model...")
    stt_model, stt_backend = load_stt_model()

    # Run pipeline
    print(f"{'─' * 50}")
    result = predict_call(
        audio_path,
        artifacts=artifacts,
        le=le,
        threshold=threshold,
        metadata=metadata,
        stt_model=stt_model,
        stt_backend=stt_backend,
    )

    print_result(result)


if __name__ == "__main__":
    main()
