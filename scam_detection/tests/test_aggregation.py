"""Quick unit test for call_predict aggregation logic."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.call_predict import _aggregate_predictions

# Test 1: Mixed scam/safe — 2 scam segments out of 4
segs = [
    {"start_time": 0.0,  "end_time": 5.0,  "scam_probability": 0.80, "was_skipped": False},
    {"start_time": 5.0,  "end_time": 10.0, "scam_probability": 0.20, "was_skipped": False},
    {"start_time": 10.0, "end_time": 15.0, "scam_probability": 0.70, "was_skipped": False},
    {"start_time": 15.0, "end_time": 20.0, "scam_probability": 0.10, "was_skipped": False},
]
r = _aggregate_predictions(segs, 0.49)
print(f"Test 1 (2 scam + 2 safe):")
print(f"  Risk={r['overall_risk']}, Score={r['risk_score']}, Scam={r['scam_segment_count']}/{r['total_segments']}")
assert r["overall_risk"] in ("High", "Medium"), f"Expected High/Medium, got {r['overall_risk']}"

# Test 2: All safe
segs2 = [
    {"start_time": 0.0,  "end_time": 5.0,  "scam_probability": 0.15, "was_skipped": False},
    {"start_time": 5.0,  "end_time": 10.0, "scam_probability": 0.10, "was_skipped": False},
    {"start_time": 10.0, "end_time": 15.0, "scam_probability": 0.20, "was_skipped": False},
    {"start_time": 15.0, "end_time": 20.0, "scam_probability": 0.05, "was_skipped": False},
]
r2 = _aggregate_predictions(segs2, 0.49)
print(f"\nTest 2 (all safe):")
print(f"  Risk={r2['overall_risk']}, Score={r2['risk_score']}, Scam={r2['scam_segment_count']}/{r2['total_segments']}")
assert r2["overall_risk"] == "Low", f"Expected Low, got {r2['overall_risk']}"

# Test 3: All scam
segs3 = [
    {"start_time": 0.0,  "end_time": 5.0,  "scam_probability": 0.85, "was_skipped": False},
    {"start_time": 5.0,  "end_time": 10.0, "scam_probability": 0.75, "was_skipped": False},
    {"start_time": 10.0, "end_time": 15.0, "scam_probability": 0.90, "was_skipped": False},
    {"start_time": 15.0, "end_time": 20.0, "scam_probability": 0.80, "was_skipped": False},
]
r3 = _aggregate_predictions(segs3, 0.49)
print(f"\nTest 3 (all scam):")
print(f"  Risk={r3['overall_risk']}, Score={r3['risk_score']}, Scam={r3['scam_segment_count']}/{r3['total_segments']}")
assert r3["overall_risk"] == "High", f"Expected High, got {r3['overall_risk']}"

# Test 4: Empty (all skipped)
r4 = _aggregate_predictions([], 0.49)
print(f"\nTest 4 (empty):")
print(f"  Risk={r4['overall_risk']}, Score={r4['risk_score']}")
assert r4["overall_risk"] == "Low"

# Test 5: Some segments skipped
segs5 = [
    {"start_time": 0.0,  "end_time": 5.0,  "scam_probability": 0.80, "was_skipped": False},
    {"start_time": 5.0,  "end_time": 6.0,  "scam_probability": 0.00, "was_skipped": True},
    {"start_time": 6.0,  "end_time": 11.0, "scam_probability": 0.70, "was_skipped": False},
]
r5 = _aggregate_predictions(segs5, 0.49)
print(f"\nTest 5 (with skipped segment):")
print(f"  Risk={r5['overall_risk']}, Score={r5['risk_score']}, Total={r5['total_segments']}")
assert r5["total_segments"] == 2, f"Expected 2 active, got {r5['total_segments']}"

print("\nAll aggregation tests PASSED!")
