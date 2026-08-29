"""
Speech-to-text transcription for scam-call detection.
Primary: faster-whisper (CTranslate2 INT8). Fallback: openai-whisper.
"""
import re
import os
import warnings

from src.config import WHISPER_MODEL_SIZE, WHISPER_COMPUTE_TYPE

# ── Filler patterns to skip ──────────────────────────────────────────────────
FILLER_PATTERNS = {
    "uh", "um", "umm", "hmm", "mm", "ah", "oh", "huh",
    "uhh", "ummm", "mhm", "huhh", "huh-huh", "...", "hmmm",
}

# ── Spoken-text cleanup regexes ──────────────────────────────────────────────
_FILLER_RE = re.compile(r'\b(uh|um|hmm|uhh|ummm|mhm|hmmm|huh)\b', re.IGNORECASE)
_STUTTER_RE = re.compile(r'(\w+)-\1(-\1)+', re.IGNORECASE)
_REPEAT_RE = re.compile(r'\b(\w+)(\s+\1){2,}\b', re.IGNORECASE)


def clean_spoken_text(text: str) -> str:
    """
    Clean transcribed speech for the text classifier.
    1. Remove inline fillers (uh, um, hmm, etc.)
    2. Collapse stutter patterns (pa-pa-pakistan → pa)
    3. Collapse 3+ repeated words to at most 2
    4. Strip extra whitespace
    """
    text = _FILLER_RE.sub("", text)
    text = _STUTTER_RE.sub(r"\1", text)
    text = _REPEAT_RE.sub(r"\1 \1", text)
    # Collapse multiple spaces
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def is_filler_segment(text: str) -> bool:
    """Check if a segment is pure filler/noise and should be skipped."""
    cleaned = text.strip().lower()
    # Remove punctuation for comparison
    cleaned = re.sub(r'[^\w\s]', '', cleaned).strip()
    if cleaned in FILLER_PATTERNS:
        return True
    # Single-word segments with no scam-keyword content
    words = cleaned.split()
    if len(words) <= 1 and not _has_scam_keywords(cleaned):
        return True
    return False


def _has_scam_keywords(text: str) -> bool:
    """Quick check for scam-related keywords that shouldn't be skipped."""
    keywords = [
        "otp", "pin", "password", "verify", "blocked", "suspended",
        "account", "transfer", "payment", "prize", "won", "winner",
        "send", "bhej", "paisa", "paise", "rs", "rupee", "rupay",
        "scam", "fraud", "click", "link", "code",
    ]
    text_lower = text.lower()
    return any(kw in text_lower for kw in keywords)


# ── Whisper model loading ────────────────────────────────────────────────────

_model_cache = {}  # (model_size, compute_type) → loaded model


def _load_faster_whisper(model_size: str, compute_type: str):
    """Load a faster-whisper model (CTranslate2 backend)."""
    from faster_whisper import WhisperModel
    cache_key = ("faster", model_size, compute_type)
    if cache_key not in _model_cache:
        # Check for local model directory first
        local_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                   "models", "whisper-medium")
        if os.path.isdir(local_path) and os.path.exists(os.path.join(local_path, "model.bin")):
            print(f"  [STT] Loading faster-whisper from local: {local_path} ({compute_type})...")
            _model_cache[cache_key] = WhisperModel(
                local_path, compute_type=compute_type, device="cpu"
            )
        else:
            print(f"  [STT] Loading faster-whisper model: {model_size} ({compute_type})...")
            _model_cache[cache_key] = WhisperModel(
                model_size, compute_type=compute_type, device="cpu"
            )
    return _model_cache[cache_key]


def _load_openai_whisper(model_size: str):
    """Fallback: load stock openai-whisper model."""
    import whisper
    cache_key = ("whisper", model_size, "fp32")
    if cache_key not in _model_cache:
        print(f"  [STT] Loading openai-whisper model: {model_size} (fallback)...")
        _model_cache[cache_key] = whisper.load_model(model_size)
    return _model_cache[cache_key]


def load_stt_model(model_size: str = None, compute_type: str = None):
    """
    Load the speech-to-text model.
    Tries faster-whisper first, falls back to openai-whisper.

    Returns:
        (model, backend) tuple where backend is "faster-whisper" or "openai-whisper"
    """
    model_size = model_size or WHISPER_MODEL_SIZE
    compute_type = compute_type or WHISPER_COMPUTE_TYPE

    try:
        model = _load_faster_whisper(model_size, compute_type)
        return model, "faster-whisper"
    except ImportError:
        warnings.warn(
            "faster-whisper not available. Falling back to openai-whisper. "
            "Install faster-whisper for 4-6x speedup: pip install faster-whisper"
        )
        model = _load_openai_whisper(model_size)
        return model, "openai-whisper"


# ── Transcription ────────────────────────────────────────────────────────────

def transcribe_audio(wav_path: str, model=None, backend: str = None):
    """
    Transcribe a 16 kHz mono WAV file into timestamped segments.

    Args:
        wav_path: Path to WAV file (use src.audio.export_wav first)
        model: Pre-loaded STT model (or None to load default)
        backend: "faster-whisper" or "openai-whisper" (or None to auto-detect)

    Returns:
        list of dicts: [{"start": float, "end": float, "text": str}, ...]
        Also returns detected language as second element.
    """
    if model is None:
        model, backend = load_stt_model()

    if backend == "faster-whisper":
        segments_iter, info = model.transcribe(
            wav_path,
            beam_size=5,
            vad_filter=True,
            vad_parameters=dict(min_silence_duration_ms=500),
        )
        detected_lang = info.language
        segments = []
        for seg in segments_iter:
            segments.append({
                "start": seg.start,
                "end": seg.end,
                "text": seg.text.strip(),
            })

    elif backend == "openai-whisper":
        result = model.transcribe(wav_path, fp16=False)
        detected_lang = result.get("language", "unknown")
        segments = []
        for seg in result.get("segments", []):
            segments.append({
                "start": seg["start"],
                "end": seg["end"],
                "text": seg["text"].strip(),
            })
    else:
        raise ValueError(f"Unknown STT backend: {backend}")

    return segments, detected_lang


# ── Segment processing ───────────────────────────────────────────────────────

def process_segments(raw_segments: list, min_words: int = 4, gap_seconds: float = 5.0):
    """
    Process raw Whisper segments:
    1. Filter out filler/noise segments
    2. Concatenate short adjacent segments (until min_words reached or gap appears)
    3. Clean spoken text for each segment

    Args:
        raw_segments: List of {"start", "end", "text"} from transcribe_audio()
        min_words: Minimum word count before a segment is classified
        gap_seconds: Max time gap between concatenated segments

    Returns:
        List of processed segment dicts:
        [{
            "segment_index": int,
            "start_time": float,
            "end_time": float,
            "text": str,           # original
            "cleaned_text": str,   # after spoken-text cleanup
            "was_concatenated": bool,
            "was_skipped": bool,
        }, ...]
    """
    results = []
    idx = 0
    i = 0

    while i < len(raw_segments):
        seg = raw_segments[i]
        text = seg["text"]

        # Skip fillers
        if is_filler_segment(text):
            results.append({
                "segment_index": idx,
                "start_time": seg["start"],
                "end_time": seg["end"],
                "text": text,
                "cleaned_text": "",
                "was_concatenated": False,
                "was_skipped": True,
            })
            idx += 1
            i += 1
            continue

        # Accumulate short segments
        accumulated_text = text
        start = seg["start"]
        end = seg["end"]
        concatenated = False
        j = i + 1

        while len(accumulated_text.split()) < min_words and j < len(raw_segments):
            next_seg = raw_segments[j]
            # Check time gap — if > gap_seconds, stop accumulating
            if next_seg["start"] - end > gap_seconds:
                break
            # Skip fillers during concatenation
            if is_filler_segment(next_seg["text"]):
                j += 1
                continue
            accumulated_text += " " + next_seg["text"]
            end = next_seg["end"]
            concatenated = True
            j += 1

        cleaned = clean_spoken_text(accumulated_text)

        results.append({
            "segment_index": idx,
            "start_time": start,
            "end_time": end,
            "text": accumulated_text,
            "cleaned_text": cleaned,
            "was_concatenated": concatenated,
            "was_skipped": False,
        })
        idx += 1
        i = j  # skip past concatenated segments

    return results
