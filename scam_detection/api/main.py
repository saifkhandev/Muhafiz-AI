"""
Muhafiz AI — FastAPI backend serving the real V4 model.
Endpoints:
  POST /api/analyze-text
  POST /api/analyze-audio
"""
import os
import sys
import json
import shutil
import tempfile
import warnings
from contextlib import asynccontextmanager
from typing import List, Dict, Any

warnings.filterwarnings("ignore")

# Add project root to path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from src.predict import predict_message, load_model
from src.call_predict import predict_call
from src.transcribe import load_stt_model
from src.config import MAX_AUDIO_DURATION_SECONDS
from src.preprocessing import (
    URGENCY_KEYWORDS,
    FINANCIAL_KEYWORDS,
    CREDENTIAL_KEYWORDS,
    PRIZE_KEYWORDS,
    THREAT_KEYWORDS,
    OTP_KEYWORDS,
)

# ── Load model version from report ──────────────────────────────────────────
def _load_model_version() -> str:
    """Safely read model_version from the results JSON."""
    report_path = os.path.join(PROJECT_ROOT, "reports", "hard_test_500_results.json")
    try:
        with open(report_path, "r", encoding="utf-8") as f:
            return json.load(f).get("model_version", "4.0")
    except (FileNotFoundError, json.JSONDecodeError, KeyError):
        return "4.0"

# ── Shared state loaded once at startup ─────────────────────────────────────
_app_state = {
    "artifacts": None,
    "le": None,
    "threshold": None,
    "metadata": None,
    "stt_model": None,
    "stt_backend": None,
}


SIGNAL_CATEGORIES = {
    "Urgency / time pressure": URGENCY_KEYWORDS,
    "Financial request": FINANCIAL_KEYWORDS,
    "Credential / OTP request": CREDENTIAL_KEYWORDS,
    "Prize / lottery": PRIZE_KEYWORDS,
    "Threat / account block": THREAT_KEYWORDS,
    "OTP-specific": OTP_KEYWORDS,
}


# ── Pydantic models ─────────────────────────────────────────────────────────
class TextRequest(BaseModel):
    text: str


class TextResponse(BaseModel):
    verdict: str
    riskScore: float
    riskLabel: str
    detectedLanguage: str
    signals: List[Dict[str, Any]]
    recommendedAction: str
    modelName: str
    thresholdUsed: float


class SegmentResponse(BaseModel):
    text: str
    startTime: float
    endTime: float
    label: str
    scamProbability: float


class AudioResponse(BaseModel):
    overallRisk: str
    riskScore: float
    callDurationSeconds: float
    totalSegments: int
    skippedSegments: int
    transcriptionModel: str
    languageDetected: str
    segments: List[SegmentResponse]


# ── Helpers ─────────────────────────────────────────────────────────────────
def _detect_language(text: str) -> str:
    has_urdu = any("\u0600" <= c <= "\u06FF" for c in text)
    has_roman = any(
        w in text.lower()
        for w in ["hai", "hain", "karo", "bhej", "kren", "rs.", "aap", "ka", "ko", "ki"]
    )
    if has_urdu and has_roman:
        return "Mixed"
    if has_urdu:
        return "Urdu"
    if has_roman:
        return "Roman Urdu"
    return "English"


def _detect_signals(text: str) -> List[Dict[str, Any]]:
    lowered = text.lower()
    signals = []
    for category, keywords in SIGNAL_CATEGORIES.items():
        matched = []
        for kw in keywords:
            kw_lower = kw.lower()
            if kw_lower in lowered:
                matched.append(kw)
        if matched:
            signals.append({"category": category, "matchedTerms": matched})
    return signals


def _recommended_action(verdict: str, risk_label: str, signals: List[Dict]) -> str:
    if verdict == "Safe":
        return "No action needed - this message appears legitimate."
    if risk_label == "High":
        return "Do not respond, click links, or share any personal information. Report or block the sender."
    if any(s["category"] == "Credential / OTP request" for s in signals):
        return "Never share passwords, PINs, or OTPs. Contact the organization directly through official channels."
    if any(s["category"] == "Prize / lottery" for s in signals):
        return "Legitimate prizes never require upfront fees. Verify through official sources before paying."
    return "Treat with caution. Verify the sender through an official channel before acting."


def _risk_label_from_probability(prob: float) -> str:
    if prob >= 0.60:
        return "High"
    if prob >= 0.35:
        return "Medium"
    return "Low"


# ── Lifespan ────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("[BACKEND] Loading V4 model artifacts...")
    artifacts, le, threshold, metadata = load_model()
    _app_state["artifacts"] = artifacts
    _app_state["le"] = le
    _app_state["threshold"] = threshold
    _app_state["metadata"] = metadata
    print(f"[BACKEND] Model loaded: {metadata.get('version', 'unknown')}, threshold={threshold}")

    # Audio/STT is optional: set ENABLE_AUDIO=false on small hosting tiers.
    # The Whisper medium model needs a ~1.5GB download and ~1.5GB RAM at runtime.
    enable_audio = os.environ.get("ENABLE_AUDIO", "true").lower() in ("1", "true", "yes")
    if not enable_audio:
        _app_state["stt_model"] = None
        _app_state["stt_backend"] = None
        print("[BACKEND] STT skipped (ENABLE_AUDIO=false) - audio endpoint disabled, text analysis active")
    else:
        print("[BACKEND] Loading STT model (medium Whisper)...")
        try:
            stt_model, stt_backend = load_stt_model()
            _app_state["stt_model"] = stt_model
            _app_state["stt_backend"] = stt_backend
            print(f"[BACKEND] STT loaded: {stt_backend}")
        except Exception as e:
            _app_state["stt_model"] = None
            _app_state["stt_backend"] = None
            print(f"[BACKEND] STT load failed ({e}) - audio endpoint disabled, text analysis active")

    yield

    print("[BACKEND] Shutdown")


# ── App ─────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="Muhafiz AI API",
    version=_load_model_version(),
    lifespan=lifespan,
)

# Allowed origins: set CORS_ORIGINS env var in production (comma-separated).
# Falls back to Vercel + common dev origins.
_allowed_origins = [
    o.strip()
    for o in os.environ.get(
        "CORS_ORIGINS",
        "https://muhafiz-ai-six.vercel.app,https://muhafiz-ai.vercel.app,http://localhost:3000,http://localhost:3001,http://localhost:8080",
    ).split(",")
    if o.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)


# ── Endpoints ───────────────────────────────────────────────────────────────
@app.options("/{rest_of_path:path}")
async def preflight_handler(rest_of_path: str):
    """Handle CORS preflight requests explicitly for all routes."""
    return {}


@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "model": _app_state["metadata"].get("version", "unknown") if _app_state["metadata"] else "unknown",
        "threshold": _app_state["threshold"],
        "stt": _app_state["stt_backend"] or "disabled",
        "audioEnabled": _app_state["stt_model"] is not None,
    }


@app.post("/api/analyze-text", response_model=TextResponse)
async def analyze_text(req: TextRequest):
    text = req.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Text is required")

    try:
        result = predict_message(
            text,
            artifacts=_app_state["artifacts"],
            le=_app_state["le"],
            threshold=_app_state["threshold"],
            metadata=_app_state["metadata"],
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail="Model inference failed")

    prob = result.get("scam_probability") or 0.0
    verdict = result.get("label", "Safe")
    risk_score = round(prob * 100, 2)
    risk_label = _risk_label_from_probability(prob)
    detected_language = _detect_language(text)
    signals = _detect_signals(text)
    action = _recommended_action(verdict, risk_label, signals)

    return TextResponse(
        verdict=verdict,
        riskScore=risk_score,
        riskLabel=risk_label,
        detectedLanguage=detected_language,
        signals=signals,
        recommendedAction=action,
        modelName=_app_state["metadata"].get("version", "V4"),
        thresholdUsed=round(_app_state["threshold"], 2),
    )


@app.post("/api/analyze-audio", response_model=AudioResponse)
async def analyze_audio(audio: UploadFile = File(...)):
    if _app_state["stt_model"] is None:
        raise HTTPException(
            status_code=503,
            detail="Audio analysis is unavailable on this server (speech model not loaded). Text analysis is fully available.",
        )
    if not audio.content_type or not audio.content_type.startswith("audio/"):
        raise HTTPException(status_code=400, detail="Uploaded file must be an audio file")

    ext = os.path.splitext(audio.filename or "upload.wav")[1].lower()
    allowed = {".mp3", ".wav", ".m4a", ".webm", ".aac", ".ogg", ".flac"}
    if ext not in allowed:
        raise HTTPException(status_code=400, detail=f"Unsupported audio format: {ext}")

    temp_dir = tempfile.mkdtemp(prefix="muhafiz_audio_")
    temp_path = os.path.join(temp_dir, f"upload{ext}")

    try:
        with open(temp_path, "wb") as f:
            shutil.copyfileobj(audio.file, f)

        # Enforce max duration server-side
        try:
            from pydub import AudioSegment
            audio_segment = AudioSegment.from_file(temp_path)
            duration = len(audio_segment) / 1000.0
            if duration > MAX_AUDIO_DURATION_SECONDS:
                raise HTTPException(
                    status_code=400,
                    detail=f"Audio duration {duration:.1f}s exceeds maximum of {MAX_AUDIO_DURATION_SECONDS}s",
                )
        except HTTPException:
            raise
        except Exception as import_err:
            # If pydub fails to inspect, continue rather than block the request
            print(f"[BACKEND] Could not inspect audio duration: {import_err}")

        result = predict_call(
            temp_path,
            artifacts=_app_state["artifacts"],
            le=_app_state["le"],
            threshold=_app_state["threshold"],
            metadata=_app_state["metadata"],
            stt_model=_app_state["stt_model"],
            stt_backend=_app_state["stt_backend"],
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail="Audio analysis failed. Please try again with a different file.")
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

    segments = [
        SegmentResponse(
            text=s.get("text", ""),
            startTime=s.get("start_time", 0.0),
            endTime=s.get("end_time", 0.0),
            label=s.get("label", "Skipped"),
            scamProbability=round((s.get("scam_probability") or 0.0) * 100, 2),
        )
        for s in result.get("segment_predictions", [])
    ]

    return AudioResponse(
        overallRisk=result.get("overall_risk", "Low"),
        riskScore=round((result.get("risk_score") or 0.0) * 100, 2),
        callDurationSeconds=result.get("call_duration_seconds", 0.0),
        totalSegments=result.get("total_segments", 0),
        skippedSegments=result.get("skipped_segments", 0),
        transcriptionModel=result.get("transcription_model", "unknown"),
        languageDetected=result.get("language_detected", "unknown"),
        segments=segments,
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
