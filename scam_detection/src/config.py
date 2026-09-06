"""
Configuration constants for the scam detection pipeline.
"""
import os

# Load scam_detection/.env if present, so local runs pick up secrets like
# GROQ_API_KEY without exporting them by hand. Real environment variables
# always win, which is what hosted deploys (Render, Vercel) rely on.
try:
    from dotenv import load_dotenv

    load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))
except ImportError:
    pass

# ── Paths ───────────────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
MODEL_DIR = os.path.join(BASE_DIR, "models")
REPORT_DIR = os.path.join(BASE_DIR, "reports")

DATASET_PATH = os.path.join(DATA_DIR, "scam_messages_dataset.xlsx")
SHEET_NAME = "Scam Detection Dataset"

# Column names
COL_MESSAGE = "Message Content"
COL_LANGUAGE = "Language Type"
COL_CATEGORY = "Scam Category"
COL_LABEL = "Label"

# ── Reproducibility ─────────────────────────────────────────────────────────
RANDOM_SEED = 42
N_FOLDS = 5
TEST_SIZE = 0.20
VAL_SIZE = 0.15  # validation fraction from the non-test portion

# ── Labels ──────────────────────────────────────────────────────────────────
LABEL_SCAM = "Scam"
LABEL_SAFE = "Safe"

# ── Model artifacts ─────────────────────────────────────────────────────────
MODEL_FILENAME = "best_model.joblib"
VECTORIZER_FILENAME = "vectorizer.joblib"
FEATURE_CONFIG_FILENAME = "feature_config.joblib"
THRESHOLD_FILENAME = "threshold.joblib"
LABEL_ENCODER_FILENAME = "label_encoder.joblib"
METADATA_FILENAME = "model_metadata.joblib"
FULL_PIPELINE_FILENAME = "full_pipeline.joblib"

# ── Whisper / Speech-to-Text ────────────────────────────────────────────────
# Model size can be overridden via env var for deployment speed tuning:
#   WHISPER_MODEL_SIZE=small  → ~2-3x faster than medium, slightly less accurate
#   WHISPER_MODEL_SIZE=medium → default, best accuracy
WHISPER_MODEL_SIZE = os.environ.get("WHISPER_MODEL_SIZE", "medium")
WHISPER_COMPUTE_TYPE = os.environ.get("WHISPER_COMPUTE_TYPE", "int8")  # "int8" for speed, "float16" for accuracy
MAX_AUDIO_DURATION_SECONDS = 300    # cap at 5 minutes (scam tactics are front-loaded)
TEMP_AUDIO_DIR = os.path.join(BASE_DIR, "temp_audio")

# ── STT backend selection ───────────────────────────────────────────────────
# STT_BACKEND=local → faster-whisper on this machine. Private (audio never
#                     leaves the server) but needs a 1.5GB model and ~2.7GB RAM.
# STT_BACKEND=groq  → Groq-hosted Whisper over HTTP. No local model, ~220MB RAM,
#                     so the backend fits a 512MB free tier. Audio is uploaded
#                     to Groq for transcription.
STT_BACKEND = os.environ.get("STT_BACKEND", "local").strip().lower()

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "").strip()
# whisper-large-v3 is more accurate on Urdu / Roman Urdu than the -turbo variant,
# which is faster but weaker on non-English audio.
GROQ_STT_MODEL = os.environ.get("GROQ_STT_MODEL", "whisper-large-v3")
GROQ_API_BASE = os.environ.get("GROQ_API_BASE", "https://api.groq.com/openai/v1").rstrip("/")
GROQ_TIMEOUT_SECONDS = float(os.environ.get("GROQ_TIMEOUT_SECONDS", "120"))
# Groq rejects uploads above 25MB on the free tier. A 5-minute 16kHz mono WAV
# is ~9.6MB, so MAX_AUDIO_DURATION_SECONDS already keeps us under the cap.
GROQ_MAX_UPLOAD_BYTES = 25 * 1024 * 1024

# Whisper routinely labels Pakistani Urdu speech as Hindi and writes it in
# Devanagari. The classifier was trained on Urdu (Arabic script), Roman Urdu and
# English, so Devanagari is out-of-distribution and produces false negatives.
# When auto-detection returns Hindi we re-transcribe with language=ur, which
# yields proper Urdu script. Set GROQ_LANGUAGE to force a language and skip the
# retry (e.g. "ur", "en"); leave empty for auto-detect.
GROQ_LANGUAGE = os.environ.get("GROQ_LANGUAGE", "").strip().lower()
GROQ_RETRY_HINDI_AS_URDU = os.environ.get(
    "GROQ_RETRY_HINDI_AS_URDU", "true"
).strip().lower() in ("1", "true", "yes")


# ── Call-level risk aggregation ──────────────────────────────────────────────
CALL_RISK_HIGH = 0.55       # risk_score >= this → High risk
CALL_RISK_MEDIUM = 0.30     # risk_score >= this → Medium risk
# Aggregation weights (must sum to 1.0)
# Max-prob gets higher weight: one very strong scam segment in a long call
# should not be drowned out by many neutral segments.
CALL_WEIGHT_MAX_PROB = 0.45
CALL_WEIGHT_WEIGHTED_MEAN = 0.30
CALL_WEIGHT_SCAM_RATIO = 0.25
# If any single segment crosses these probabilities, force a minimum call risk.
CALL_FORCE_HIGH_MAX_PROB = 0.90
CALL_FORCE_MEDIUM_MAX_PROB = 0.70
