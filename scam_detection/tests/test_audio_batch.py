"""Batch audio test: run 3 audio files through the scam-call detection pipeline."""
import sys, os, io, warnings, time
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
warnings.filterwarnings("ignore")

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from src.call_predict import predict_call
from src.predict import load_model
from src.transcribe import load_stt_model

AUDIO_FILES = [
    r"c:\Users\Hp\Downloads\Automated.aac",
    r"c:\Users\Hp\Downloads\WhatsApp Audio 2026-08-29 at 8.17.48 AM.aac",
    r"c:\Users\Hp\Downloads\WhatsApp Audio 2026-08-29 at 8.18.56 AM.aac",
]

def format_time(seconds):
    m, s = divmod(int(seconds), 60)
    return f"{m:02d}:{s:02d}"

def print_result(name, result):
    risk = result["overall_risk"]
    score = result["risk_score"]
    risk_display = {"High": "HIGH RISK", "Medium": "MEDIUM RISK", "Low": "LOW RISK"}

    print(f"\n{'=' * 75}")
    print(f"  FILE: {name}")
    print(f"{'=' * 75}")
    print(f"  Verdict:          {risk_display.get(risk, risk)}")
    print(f"  Risk Score:       {score:.4f}")
    print(f"  Max Segment Prob: {result['max_segment_probability']:.4f}")
    print(f"  Scam Segments:    {result['scam_segment_count']}/{result['total_segments']}")
    print(f"  Skipped (filler): {result['skipped_segments']}")
    print(f"  Call Duration:    {result['call_duration_seconds']:.1f}s")
    print(f"  STT Model:        {result['transcription_model']}")
    print(f"  Language:         {result['language_detected']}")

    active_segs = [s for s in result["segment_predictions"] if not s["was_skipped"]]
    if active_segs:
        print(f"\n  SEGMENT-LEVEL ANALYSIS ({len(active_segs)} segments):")
        print(f"  {'-' * 70}")
        for seg in active_segs:
            ts = f"[{format_time(seg['start_time'])}-{format_time(seg['end_time'])}]"
            label = seg["label"]
            prob = seg["scam_probability"]
            text = seg["cleaned_text"] if seg["cleaned_text"] else seg["text"]
            display_text = text[:85] + "..." if len(text) > 85 else text
            concat = " (merged)" if seg["was_concatenated"] else ""
            print(f"  {ts} {label:<5s} P={prob:.3f}  {display_text}{concat}")
    print(f"{'=' * 75}")

def main():
    print(f"\nScam-Call Detection — Batch Audio Test")
    print(f"Files: {len(AUDIO_FILES)}")
    print(f"{'=' * 50}")

    # Load models once
    print("\n  Loading text classification model...")
    t0 = time.time()
    artifacts, le, threshold, metadata = load_model()
    print(f"  Done in {time.time()-t0:.1f}s")

    print("  Loading speech-to-text model (first run downloads ~1.5 GB)...")
    t0 = time.time()
    stt_model, stt_backend = load_stt_model()
    print(f"  Done in {time.time()-t0:.1f}s")

    results_summary = []
    for audio_path in AUDIO_FILES:
        name = os.path.basename(audio_path)
        print(f"\n{'─' * 50}")
        print(f"Processing: {name}")
        print(f"{'─' * 50}")

        t0 = time.time()
        try:
            result = predict_call(
                audio_path,
                artifacts=artifacts, le=le, threshold=threshold, metadata=metadata,
                stt_model=stt_model, stt_backend=stt_backend,
            )
            elapsed = time.time() - t0
            print_result(name, result)
            print(f"  Processed in {elapsed:.1f}s")
            results_summary.append((name, result["overall_risk"], result["risk_score"],
                                     result["scam_segment_count"], result["total_segments"],
                                     result["call_duration_seconds"]))
        except Exception as e:
            print(f"  ERROR: {e}")
            results_summary.append((name, "ERROR", 0, 0, 0, 0))

    # Summary table
    print(f"\n{'=' * 75}")
    print(f"  SUMMARY")
    print(f"{'=' * 75}")
    print(f"  {'File':<45s} {'Verdict':<8s} {'Score':>6s} {'Scam/Tot':>8s} {'Dur':>6s}")
    print(f"  {'-' * 75}")
    for name, risk, score, scam_ct, total, dur in results_summary:
        short_name = name[:42] + "..." if len(name) > 45 else name
        print(f"  {short_name:<45s} {risk:<8s} {score:>6.3f} {scam_ct}/{total:>4d}  {dur:>5.1f}s")

if __name__ == "__main__":
    main()
