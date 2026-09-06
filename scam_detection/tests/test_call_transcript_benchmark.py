"""Regression test for the labeled card-phishing call transcript fixture."""
import json
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from src.call_predict import predict_call_from_transcript
from src.predict import load_model

fixture_path = os.path.join(PROJECT_ROOT, "tests", "fixtures", "verified_call_transcripts.json")
with open(fixture_path, encoding="utf-8") as fixture_file:
    record = json.load(fixture_file)["records"][0]

artifacts, label_encoder, threshold, metadata = load_model()
result = predict_call_from_transcript(
    record["transcript"],
    artifacts=artifacts,
    le=label_encoder,
    threshold=threshold,
    metadata=metadata,
)

assert result["overall_risk"] == "High", result
assert "card_verification_scam" in result["call_patterns"], result
assert "fraud_department_impersonation" in result["call_patterns"], result
print("Call transcript benchmark regression passed.")
