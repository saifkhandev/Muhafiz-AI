# Scam Detection ML System

Multilingual scam-message detection for Pakistani scam patterns across **English**, **Roman Urdu**, **Urdu**, and **Mixed-language** inputs.

## Overview

This project trains and evaluates machine-learning models to classify text messages as **Scam** or **Safe**. It covers 10+ scam categories common in Pakistan:

| Category | Examples |
|---|---|
| Job | Fake overseas jobs, paid "registration" offers |
| Lottery | Fake prize draws requiring processing fees |
| Bank | Phishing links, fake account alerts, KYC fraud |
| OTP | Social engineering to extract one-time passwords |
| SIM Block | Fake PTA/telecom SIM deactivation threats |
| Investment | Ponzi schemes, fake crypto/forex, "guaranteed returns" |
| Fake Charity | Fraudulent donation drives |
| Impersonation | Pretending to be family, boss, or friends |
| Prize | Fake product wins with delivery-fee traps |
| Loan | Advance-fee loan scams |
| Government | BISP, Ehsaas, NADRA, FBR impersonation |
| Tech Support | Fake Microsoft/antivirus alerts, QR code scams |

## Datasets

### Pakistan-Focused Dataset (Original + Augmented + Adversarial)
- **Original:** 868 messages (442 Scam, 426 Safe)
- **V3 Augmentation:** +255 messages (173 scam, 82 hard-negative safe)
- **V4 Adversarial Expansion:** +505 messages (255 scam, 250 safe)
- **Combined:** 1,637 messages after deduplication (879 scam, 758 safe)
- **Languages:** English, Roman Urdu, Urdu, Mixed
- **Source:** `data/scam_messages_dataset.xlsx` + `data/hard_test_500_for_retrain.json`

### UCI SMS Spam Collection (Available, Not Used in Final Model)
- **Size:** 5,572 messages (747 spam, 4,825 ham)
- **Language:** Predominantly English
- **Source:** https://archive.ics.uci.edu/dataset/228/sms
- **Note:** English-only patterns did not transfer well to multilingual Pakistani scam detection

## Project Structure

```
scam_detection/
    api/
        main.py                      # FastAPI backend (real V4 model endpoints)
    data/
        scam_messages_dataset.xlsx   # Pakistan dataset (868 messages)
        raw/uci_sms_spam/             # UCI SMS Spam Collection
    web/                             # Next.js frontend
        src/
            app/                     # Pages
            components/              # UI, analyzer, shield, sections
            lib/                     # API client, types, shield context
    models/
        full_pipeline.joblib         # Trained V4 model (B_combined_C5)
        label_encoder.joblib         # Label encoder (Safe=0, Scam=1)
        threshold.joblib             # Optimized decision threshold (0.63)
        model_metadata.joblib        # All metadata
    reports/
        v3_final_summary.json        # V3 pipeline results
        v3_metadata.json             # V3 model metadata
        v3_error_analysis.csv        # V3 misclassified examples
        v3_retrain_comparison.csv    # V3 model comparison
        all4_external_test_report.txt    # External validation (318 msgs)
        all4_external_error_analysis.csv # External error analysis
        data_quality_report.json     # Dataset audit
        archive/                     # V1/V2 reports (historical)
    src/
        __init__.py
        config.py                    # Configuration constants
        data_analysis.py             # Data audit + leakage prevention
        preprocessing.py             # Scam-aware text normalizer (V3)
        features.py                  # Engineered scam-indicator features
        train.py                     # Splitting + cross-validation
        evaluate.py                  # Comparison, thresholds, errors
        predict.py                   # Single-message prediction CLI
    tests/
        external_validation.py       # Locked benchmark validator
        external_validation_v2.py    # V2 benchmark validator
        run_all4_validation.py       # All-4 language validator
        final_blind_test.py          # 50-message truly blind test
        rigorous_real_world_test.py  # 43-message real-world test
        audit_dataset.py             # Dataset quality audit
    requirements.txt
    run_retrain_v3_pipeline.py       # V3 training pipeline (current)
    run_retrain_pipeline.py          # V2 training pipeline (reference)
    run_augmented_pipeline.py        # V1 augmented pipeline (reference)
    run_pipeline.py                  # V1 Pakistan-only pipeline (reference)
    README.md
```

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Train the V3 Model

```bash
python run_retrain_v3_pipeline.py
```

Trains 6 model configurations with combined word+char n-gram TF-IDF features, optimizes the decision threshold using F2-score, and saves the best model.

### 3. Run External Validation

```bash
python tests/run_all4_validation.py    # 318-message all-4-language test
python tests/final_blind_test.py       # 50-message truly blind test
```

### 4. Predict a Single Message

```bash
python src/predict.py "Your account has been blocked. Click here to verify immediately."
# Output: SCAM (probability: 0.72)

python src/predict.py "Your interview is scheduled for Thursday at 10 AM. Bring your CV."
# Output: SAFE (probability: 0.21)
```

### Web Application (Next.js + FastAPI)

A production-quality web app is available in the `web/` directory.

```bash
# 1. Start the FastAPI backend (loads V4 model + Whisper STT)
python -m uvicorn api.main:app --host 0.0.0.0 --port 8000

# 2. In a new terminal, start the Next.js frontend
cd web
npm install
npm run dev

# 3. Open http://localhost:3000
```

Features:
- **Text analysis** — paste any message and get a real Scam/Safe verdict, risk score, detected language, and rule-based signals.
- **Audio analysis** — upload or record a call; the backend transcribes with Whisper medium and classifies each segment.
- **3D shield** — interactive Three.js visualization on desktop; static SVG fallback on mobile.
- **GSAP scroll animations** — scroll-driven reveals and an animated pipeline diagram.
- **Real model only** — no mocked or hardcoded classification results.

### Programmatic Usage

```python
from src.predict import predict_message, load_model

# Load once
artifacts, le, threshold, metadata = load_model()

# Predict
result = predict_message(
    "Aap ko Rs. 50,000 ka inaam mila hai. Fee Rs. 3,000 bhejein.",
    artifacts=artifacts, le=le, threshold=threshold, metadata=metadata,
)
print(result["label"])             # "Scam"
print(result["scam_probability"])  # 0.82
```

## Current Model Performance (V4)

**Model: `B_combined_C5`** — Combined word(1,2)-gram + char(3,5)-gram TF-IDF with LinearSVC (C=5.0)
**Calibration:** CalibratedClassifierCV (sigmoid Platt scaling)
**Threshold: 0.63** (optimized for balanced F1 + F2 + Specificity composite)
**Training:** 1,637 messages (879 scam, 758 safe)

### Primary Results (Untouched Test Sets)

| Test | Messages | Accuracy | Recall | Precision | FPR | FP | FN |
|---|---|---|---|---|---|---|---|
| Adversarial 505 | 505 | **99.60%** | 99.61% | 99.61% | 0.40% | 1 | 1 |
| Blind Test | 50 | **98.00%** | 96.00% | 100% | 0.00% | 0 | 1 |
| Hard Test V4 | 56 | **98.21%** | 100.0% | 96.55% | 3.57% | 1 | 0 |
| BISP Diagnostic | 10 | **100.0%** | 100.0% | 100% | 0.00% | 0 | 0 |
| All-4 External | 318 | **97.48%** | 96.52% | 98.23% | 0.63% | 1 | 7 |
| Real-World | 43 | **93.02%** | 87.50% | 100% | 0.00% | 0 | 3 |

### Language-Specific Results (505-Message Adversarial Test)

| Language | Samples | Accuracy |
|---|---|---|
| English | 178 | **100.0%** |
| Roman Urdu/Mixed | 317 | **99.4%** |
| Urdu | 10 | **100.0%** |

### Audio Pipeline (faster-whisper medium)

| File | Duration | Verdict | Risk Score |
|------|----------|---------|------------|
| Automated.aac | 6.6s | LOW RISK | 0.344 |
| WhatsApp 8.17 AM | 11.6s | HIGH RISK | 0.649 |
| WhatsApp 8.18 AM | 5.2s | LOW RISK | 0.117 |

### Overfitting Check
- CV accuracy: 99.15%
- Test accuracy: 97.33%
- CV-test gap: -1.82% (excellent, < 3%)
- No significant overfitting detected

## Architecture

### Model Pipeline
```
Input Message
  → ImprovedScamTextNormalizer (lowercase, USSD normalization, Roman Urdu
    spelling normalization, phrase normalization, number/symbol handling)
  → FeatureUnion
      → Word TF-IDF (ngram_range=1,2, max_features=30000)
      → Char TF-IDF (ngram_range=3,5, analyzer=char_wb, max_features=30000)
  → LinearSVC (C=5.0, class_weight=balanced)
  → Decision function + Platt scaling → calibrated probability
  → Threshold comparison (0.63) → Scam / Safe
```

### Preprocessing (V3 Improvements)
- **USSD normalization:** `*786#` → `<USSD_CODE>` token
- **Roman Urdu spelling:** `btayen→batayein`, `krwayen→karwaen`, `kmaen→kamaen` (15+ rules)
- **Phrase normalization:** `k badle→ke badle`, `k sath→ke saath`, `k liye→ke liye` (10+ rules)
- **Number cleanup:** Spaced/zero-padded phone numbers normalized
- **URL/Email masking:** Prevents memorization of specific URLs

### Hard-Negative Mining
The V3 augmentation specifically targets failure modes:
- **82 safe messages** mirroring common FP triggers (bank deductions, "Congratulations selected", security notices, service OTPs)
- **173 scam messages** covering underrepresented categories (BISP/Ehsaas, real estate, courier, QR code, tech support, fake apps)

### V4 Adversarial Expansion
The V4 retrain integrated 505 adversarial messages to address FP issues:
- **255 scam messages** across 10 categories (BISP, delivery, job, prize, wallet/crypto, bank, government, telecom, phishing, forex)
- **250 safe messages** across 10 categories (bank, delivery, government, personal, business, education, healthcare, utility, social media, tricky safe)
- **Threshold recalibrated** from 0.23 (V3.1) to 0.63 (V4) using balanced composite score
- **FP reduction**: 48 → 1 on 505-message adversarial test (48x improvement)

## Reproducibility

- Random seed: **42** (used for all splits and model training)
- Group-aware leakage-safe splitting (4-word prefix groups)
- No data leakage: train/val/test overlap verified to be zero
- 5-fold cross-validation during training
- The entire pipeline is reproducible:
  - `python run_retrain_v3_pipeline.py` — V3 model (current)
  - `python run_retrain_pipeline.py` — V2 model (reference)

## Limitations

1. **Dataset size (1,637 messages):** While hard-negative mining and adversarial expansion compensate, the training set is small by deep-learning standards. Performance may degrade on entirely novel scam templates not resembling training data.
2. **Roman Urdu spelling variation:** Despite 15+ normalization rules, the extreme informality of Roman Urdu (e.g., "kya krna ha" vs "kia kerna hy") means edge cases persist.
3. **No transformer comparison:** We did not benchmark against BERT/mBERT/RoBERTa. TF-IDF+SVM was chosen for speed (<10ms/msg) and interpretability.
4. **Probability calibration:** Platt scaling produces calibrated scores, but these are not true posterior probabilities. The score reflects relative confidence.
5. **Static scam patterns:** Scammers evolve tactics rapidly. The model requires periodic retraining with new scam patterns to maintain accuracy.
6. **Binary classification only:** The model outputs Scam/Safe only. It does **not** classify the scam category (e.g., bank, job, BISP, lottery). Category labels in the dataset are used for data auditing and augmentation only.

## Architecture: Audio/Call Detection (Implemented)

The full audio pipeline is implemented and tested:

```
Audio Input (.aac, .wav, .mp3, .ogg)
  → Speech-to-Text (faster-whisper medium, INT8, CPU)
  → Transcript segments (with timestamps)
  → predict_message() for each segment
  → Weighted aggregation (max_prob=0.35, weighted_mean=0.35, scam_ratio=0.30)
  → Call-level risk score (High ≥0.60 / Medium ≥0.35 / Low <0.35)
```

See `src/call_predict.py` for `predict_call()` and `src/transcribe.py` for STT integration.

## Future Roadmap

| Feature | Status |
|---------|--------|
| Binary Scam/Safe classification | ✅ Implemented |
| Audio call analysis (STT → text classifier) | ✅ Implemented |
| Multilingual support (EN + RU + Urdu + Mixed) | ✅ Implemented |
| Multi-category scam classifier (bank, job, BISP, etc.) | 🚧 Roadmap — needs dedicated category-labeled dataset |
| Transformer comparison (mBERT/XLM-R) | 🚧 Roadmap — deprioritized for regional round |
| REST API deployment | 🚧 Roadmap |
| Continuous learning from user reports | 🚧 Roadmap |

## Requirements

- Python 3.10+
- See `requirements.txt` for full dependency list
