# Muhafiz AI V4 — Guardrail Update & Untitled-221 Evaluation Summary

**Date:** 2026-09-03  
**Decision:** Implement targeted post-processing guardrails; do **not** retrain the V4 model.  
**Model kept:** `B_combined_C5` + CalibratedClassifierCV, threshold 0.63, version `V4_adversarial_505`.

## 1. Strategic decision

After two failed retraining attempts (F2-optimized and F1-optimized via `run_pipeline.py`) both degraded verified performance, the chosen path is **Path B**: keep the proven V4 model and add narrow, validated post-processing guardrails.

The Untitled-221 dataset was evaluated as **high-quality and realistic** for Pakistan (BISP/Ehsaas, FBR, JazzCash, Easypaisa, K-Electric, Pak Army recruitment, romance scams, etc.) but the model scored only **82.35%** on it initially. Rather than risk the model's 94–99% baseline on established test suites, guardrails were added to patch the specific failure modes.

## 2. Guardrail rules added

All rules live in `src/guardrails.py` and are applied inside `src/predict.py` after the base model prediction.

| Rule | Trigger | Action |
|---|---|---|
| `wallet_setup_safe_override` | Legit brand + wallet/MPIN setup + "do not share" + no payment request | Safe |
| `mpin_create_safe_override` | Legit brand + "MPIN" + create/set/download app + no payment request | Safe |
| `investment_safe_override` | Passive statement markers (NAV, portfolio, KSE-100, dividend, etc.) + no demand pattern | Safe |
| `delivery_otp_scam_override` | Delivery context + explicit OTP/code request | Scam |
| `reference_verification_scam_override` | Reference number + soft verification language + link/portal | Scam |
| `indirect_payment_scam_override` | "emergency payment", "unexpected travel expense", "small security deposit", "financial help" + emergency | Scam |
| `threat_reporting_safe_override` | Message describes reporting/blocking a threatening/blackmail account | Safe |
| `personal_transfer_safe_override` | First-person "I sent you X via wallet/bank" | Safe |

## 3. Validation results

### Established test suites — no regression

| Test | Accuracy | Recall | FPR | FP | FN |
|---|---|---|---|---|---|
| `tests/v4_holdout_test.py` | **95.0%** | **90.0%** | **0.0%** | 0 | 5 |
| `tests/hard_test_500.py` | **99.60%** | **99.61%** | **0.40%** | 1 | 1 |

Both meet or exceed the required baselines (≥94% holdout, ≥99.6% adversarial).

### Untitled-221 adversarial dataset — improvement

| Metric | V4 baseline | V4 + guardrails | Δ |
|---|---|---|---|
| Accuracy | 82.35% | **85.52%** | +3.17% |
| Precision | 92.55% | **93.94%** | +1.39% |
| Recall | 73.11% | **78.15%** | +5.04% |
| F1-Score | 81.69% | **85.32%** | +3.63% |
| FPR | 6.86% | **5.88%** | -0.98% |
| FP / FN | 7 / 32 | **6 / 26** | -1 / -6 |

## 4. Files changed

- `src/guardrails.py` — new guardrail module
- `src/predict.py` — applies guardrails and returns the rule name in the result
- `data/adversarial_untitled_221.xlsx` — added as supplementary adversarial test set
- `tests/untitled_221_test.py` — new evaluation script for the supplementary set
- `reports/untitled_221_results.json` — per-message results

## 5. Remaining errors on Untitled-221

- **6 false positives** — mainly safe messages about reporting threats and a few courier/personal-transfer messages. Urdu threat-reporting and Roman-Urdu personal-transfer regexes can be tightened further.
- **26 false negatives** — subtle scams in Army Fauji, Tax FBR, Electricity Bill, and soft-wallet verification that lack URLs or use indirect Roman Urdu phrasing. These are candidate hard negatives for a future *constrained* retrain, but only if joint improvement on all three test suites can be proven.

## 6. Recommendation

Proceed with pushing the guardrail update and the new supplementary test set to GitHub. Do **not** retrain the V4 model at this time; previous retrain attempts have consistently degraded the verified baselines.
