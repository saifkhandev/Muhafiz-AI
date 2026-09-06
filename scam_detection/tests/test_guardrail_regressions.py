"""Regression checks for bounded text guardrails."""
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from src.guardrails import apply_guardrails

for message in [
    "Your account profile has been selected for a routine security review. Please confirm your registered information to keep your services active.",
    "Your account profile has been selected for a routine security review. Please confirm your registered information to keep services active.",
]:
    probability, label, rule = apply_guardrails(message, 0.20, "Safe")
    assert (probability, label, rule) == (0.93, "Scam", "account_security_review_scam_override")

safe_message = "Your service is active. No information or verification is requested."
probability, label, rule = apply_guardrails(safe_message, 0.20, "Safe")
assert (probability, label, rule) == (0.20, "Safe", None)

print("Guardrail regression tests passed.")
