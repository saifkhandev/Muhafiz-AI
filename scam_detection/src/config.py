"""
Configuration constants for the scam detection pipeline.
"""
import os

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
WHISPER_MODEL_SIZE = "medium"       # medium model downloaded to models/whisper-medium/
WHISPER_COMPUTE_TYPE = "int8"       # "int8" for speed, "float16" for accuracy
MAX_AUDIO_DURATION_SECONDS = 300    # cap at 5 minutes (scam tactics are front-loaded)
TEMP_AUDIO_DIR = os.path.join(BASE_DIR, "temp_audio")

# ── Call-level risk aggregation ──────────────────────────────────────────────
CALL_RISK_HIGH = 0.60       # risk_score >= this → High risk
CALL_RISK_MEDIUM = 0.35     # risk_score >= this → Medium risk
# Aggregation weights (must sum to 1.0)
CALL_WEIGHT_MAX_PROB = 0.35
CALL_WEIGHT_WEIGHTED_MEAN = 0.35
CALL_WEIGHT_SCAM_RATIO = 0.30
