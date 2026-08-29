# Model Artifacts

## What's included in this repo

| File | Size | Purpose |
|------|------|---------|
| `full_pipeline.joblib` | ~3 MB | Trained V4 model (TF-IDF + LinearSVC, CalibratedClassifierCV) |
| `label_encoder.joblib` | <1 KB | Label encoder (Safe=0, Scam=1) |
| `threshold.joblib` | <1 KB | Optimized decision threshold (0.63) |
| `model_metadata.joblib` | <1 KB | Training metadata and validation metrics |

## What's NOT included (too large for Git)

### `whisper-medium/` (~1.4 GB)
The faster-whisper **medium** model used for audio call transcription. It is loaded from
`models/whisper-medium/` at backend startup (INT8 quantized, CPU inference).

**To download it, run:**

```python
from faster_whisper import WhisperModel

# Downloads and converts the medium model to CTranslate2 INT8 format
model = WhisperModel("medium", device="cpu", compute_type="int8", download_root=".")
```

Then move the downloaded `models--Systran--faster-whisper-medium` content into
`models/whisper-medium/` so the folder contains `config.json`, `model.bin`, and the
tokenizer files directly.

**Verify it works:**

```bash
python -c "from src.transcribe import load_stt_model; m, b = load_stt_model(); print(b)"
# Expected output: faster-whisper
```

### `backup_v31/`
A backup of the previous V3.1 model kept locally for rollback. Not needed to run V4.

## Notes

- The web backend (`api/main.py`) requires the Whisper model only for the
  **audio analysis** endpoint. Text analysis works without it.
- On first request, model artifacts are loaded once at server startup and reused
  for all requests.
