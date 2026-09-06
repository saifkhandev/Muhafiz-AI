# Muhafiz AI — AI/ML Technical Journey

## Purpose
This is the technical narrative for judges. It distinguishes verified outcomes from historical results, describes decisions that protected model reliability, and names the remaining limits.

## 1. The problem and design constraints
Muhafiz AI is a Pakistan-first decision-support system for SMS, chat messages, and recorded calls in English, Urdu script, Roman Urdu, and mixed language. The engineering constraints were equally important as accuracy:

- detect financial, credential, impersonation, utility, job, prize, and delivery scams;
- avoid falsely flagging legitimate bank, telecom, service, appointment, and payment notices;
- run cheaply on CPU without external inference APIs;
- show a probability, signals, and a recommended action rather than pretend to guarantee safety;
- preserve test-set independence and avoid retraining merely to raise a known score.

## 2. Text-model architecture
The deployed text lineage is `V4_adversarial_505`, using the `B_combined_C5` design:

```text
Message
  -> Pakistan-aware normalization
  -> FeatureUnion(word TF-IDF + character TF-IDF)
  -> LinearSVC(C=5.0, class_weight="balanced")
  -> Platt calibration (CalibratedClassifierCV)
  -> 0.63 decision threshold
  -> conservative post-model guardrails
  -> Scam / Safe, probability, explanation signals
```

Feature settings are word 1–2 grams and character-within-word 3–5 grams, each capped at 30,000 features. Character features tolerate spelling variation; word features preserve meaningful phrase context. The normalizer handles casing, URLs/emails, number/phone formatting, USSD tokens, and common Roman Urdu spelling and phrase variants.

A LinearSVC was selected over a transformer for a hackathon deployment because it has a small artifact footprint (about 3 MB), CPU text inference below 10 ms per message in the documented target environment, transparent sparse-text features, and no GPU or paid API dependency. Calibration converts the SVM decision function into a usable 0–1 risk probability for the user interface.

## 3. Training iterations and reliability decisions

### V3: controlled baseline
`reports/v3_metadata.json` records the V3 experiment:

- 868 original Pakistan-focused records plus 255 generated hard-negative/scam-expansion records;
- 1,123 combined records, split into 795 train / 141 validation / 187 test;
- five-fold CV accuracy 94.21%, F1 94.74%, and recall 95.63%;
- held-out test accuracy 97.33% (TP=100, FP=2, TN=82, FN=3);
- threshold 0.49 for that historical V3 experiment.

### V4: adversarial hardening
V4 expanded the corpus after deduplication to 1,637 records: 879 Scam and 758 Safe. The source breakdown documented in the project is 868 original records, 255 V3 augmentation records, and 505 adversarial records. The adversarial safe examples specifically mirror likely false-positive contexts such as legitimate bank deductions, service notices, and OTP messages.

The resulting V4 architecture remained `B_combined_C5` with a calibrated probability and a 0.63 threshold. The threshold was selected on validation data using a balanced composite of F1, F2, and specificity; it is not an arbitrary “50% means scam” cutoff.

### Retraining was intentionally stopped
Two later retraining attempts optimized F2 and F1 differently but regressed on independent suites. They were rejected rather than promoted. The current model artifacts and threshold were kept unchanged; reliability work moved to narrow, testable inference changes. This was deliberate: tuning to a small known fixture or broad keyword rules would overfit and make a demo metric look better while worsening real use.

## 4. Evaluation evidence
The following are the latest available results from the current local model/report state. Metrics from different suites must not be averaged because their composition and independence differ.

| Suite | Scope | Latest result | What it demonstrates |
|---|---:|---:|---|
| Final Blind-50 | 50 fresh messages | 98.0% accuracy; 24/25 scam recall; 25/25 safe specificity; 1 FN, 0 FP | Strong small independent generalization check |
| V4 holdout | 100 messages | 95.0% accuracy; 90.0% recall; 100% precision/specificity; 5 FN, 0 FP | Conservative threshold trade-off on a larger holdout |
| Hard-505 | 505 adversarial messages | 99.01% accuracy; 99.61% recall; 98.45% precision; 4 FP, 1 FN | Stress performance on curated adversarial patterns |
| All-4 multilingual | 318 fresh messages | 95.60% accuracy; 93.03% recall; 100% precision; 0 FP, 14 FN | Most useful current multilingual robustness evidence |
| Verified call transcript | 1 card-phishing call | High risk; TP=1, no error | Regression protection for a previously missed call pattern |

The All-4 report is intentionally candid: English was 99.15%, Urdu 93.94%, Roman Urdu 86.57%, and Mixed 100.0% on that fixture. Roman Urdu had 9 of the 14 false negatives. The current evidence supports a strong demo, not a claim of universal protection.

### Error analysis matters
Known false negatives include disguised account-verification, fake job/fee, SIM-block, courier-fee, prize, and payment-detail phishing messages. On the 100-message V4 holdout, five missed scams were close to or below the 0.63 threshold: fake store closure, subscription renewal, property installment, charity donation, and cloned-card messages. The Hard-505 false positives were legitimate health/loan notifications containing payment-like vocabulary. These examples motivate conservative explanation, direct-verification advice, and continued data collection.

## 5. Guardrails: narrow post-model corrections
`src/guardrails.py` runs after the base-model prediction and returns the final probability, label, and rule name. It is not a replacement for the classifier. Each override requires multiple contextual signals and uses decisive probabilities only when the pattern is unambiguous.

Implemented classes include:

- safe wallet/MPIN setup and legitimate investment-statement overrides;
- delivery context plus explicit OTP request;
- reference number + verification request + link/portal impersonation;
- account-security review + verification demand + urgency/service threat;
- indirect emergency-payment and romance/emergency money requests;
- utility-bill threat plus payment request;
- safe descriptions of reporting/blocking threats and first-person legitimate transfers.

The account-security guardrail was extended to cover both “keep your services active” and “keep services active.” Its regression test requires both phishing variants to be Scam and a passive service-status message to remain Safe. Guardrails are designed to be auditable: predictions carry the rule identifier, while keyword-based UI “signals” remain separate from the model decision.

A prior V4 guardrail evaluation documented an Untitled-221 improvement from 82.35% to 85.52% accuracy, with recall rising from 73.11% to 78.15%, while established suites were checked for regression. That result is evidence for targeted patches, not a license to add unrestricted rules.

## 6. Call-transcript processing and aggregation
The audio path is deliberately separate from the text classifier:

```text
Audio upload / recording
  -> pydub decode and five-minute server-side duration cap
  -> faster-whisper medium, CTranslate2 INT8 on CPU
  -> VAD-filtered timestamped transcript
  -> filler removal and short-segment merging
  -> 12-second windows with 2-second overlap and 5-second gap boundary
  -> batched text-model inference
  -> contextual call-pattern detection and weighted aggregation
  -> High / Medium / Low risk with per-window evidence
```

The current aggregation configuration uses maximum probability (0.45), duration-weighted mean (0.30), and scam-window ratio (0.25). A single strong window cannot force High risk without a separate full-call contextual scam pattern; it can still raise Medium. This was added after an isolated fragment was able to overstate risk. High and Medium thresholds are 0.55 and 0.30 respectively.

The regression fixture for the supplied card-phishing transcript now produces High risk, risk score 1.0, and two contextual patterns: `card_verification_scam` and `fraud_department_impersonation`. The associated classification/aggregation time is roughly 0.035 seconds because this is a transcript-only test; it does not include speech-to-text.

## 7. Latency work
Audio latency was traced by stage: upload write, duration inspection, transcription, classification, aggregation, call pipeline, and total request. Logs record stage timing without recording call content or filename.

A local CPU INT8 comparison found:

| Model | Mean processing time on three short samples | Interpretation |
|---|---:|---|
| faster-whisper medium | 24.7 s | Accuracy baseline |
| faster-whisper small | 6.3 s | 3.9x faster but Urdu/Hindi transcript and risk differences occurred |

`small` was not promoted as the default because verified transcription ground truth was unavailable for the samples where it changed content. The honest product expectation remains approximately 23–35 seconds for CPU audio analysis; text is the instant path.

## 8. Data governance and candidate datasets
The core spreadsheet currently has 868 labeled messages (442 Scam / 426 Safe) across Urdu, Roman Urdu, English, and mixed language. Candidate Data Set 01 and Data Set 02 were stored under `data/candidates/` as synthetic evaluation/diagnostic material only:

- Data Set 01: 50 records, 25 Scam / 25 Safe.
- Data Set 02: 50 records, 28 Scam / 22 Safe.
- Both passed the recorded duplicate/label-conflict/overlap audit against the core corpus and each other.
- Both contain synthetic templates and call speaker markers that do not represent raw STT output.

Neither candidate is loaded by `run_retrain_v3_pipeline.py`; the loader reads only the core workbook and programmatically generated V3 additions. The public `rafiyz/Spam-SMS` source was rejected for training due to missing license/provenance, duplicate and conflicting labels, incompatible Fraud/Promotional/Normal taxonomy, and no Urdu-script coverage.

## 9. Authorship, deployment, and operational posture
Agreed ML/backend commits were re-authored as Amaan while preserving Saifullah’s UI/documentation ownership. Local Git identity is now Amaan-khan-lodhi. The user-facing frontend is live on Vercel; the documented backend is FastAPI on Render. Free-tier Render has audio disabled (`ENABLE_AUDIO=false`), so the public service must return an explicit 503 for audio rather than fabricate a result; full call analysis is a local-demo capability when Whisper is installed.

## 10. Honest conclusion
Muhafiz AI is technically credible for a hackathon demonstration because it has a real trained model, calibrated decision path, independent checks, conservative guardrails, an end-to-end call pipeline, and transparent limitations. It is not yet a production anti-fraud service: it needs substantially more licensed human-reviewed data, a balanced real-call benchmark, continuous monitoring, and a controlled retraining/rollback process.

## Evidence sources
- `README.md` — architecture and historical benchmark lineage.
- `reports/v3_metadata.json` — V3 experiment metrics.
- `reports/v4_holdout_100_results.json`, `reports/hard_test_500_results.json`, `reports/all4_external_test_report.txt` — current text-suite results.
- `reports/call_transcript_benchmark.json`, `reports/audio_latency_comparison.json` — call and latency evidence.
- `src/guardrails.py`, `src/call_predict.py`, `src/transcribe.py`, `src/config.py` — current inference behavior.
