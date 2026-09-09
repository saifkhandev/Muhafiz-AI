"""
Audio loading and format normalization for scam-call detection.
Uses pydub + ffmpeg to convert any audio format to 16 kHz mono WAV.
"""
import os
import shutil
import subprocess
import tempfile

from src.config import TEMP_AUDIO_DIR, MAX_AUDIO_DURATION_SECONDS


def _find_ffmpeg() -> str | None:
    """Locate ffmpeg binary: system PATH first, then imageio-ffmpeg bundle."""
    # 1. Check system PATH
    system_ffmpeg = shutil.which("ffmpeg")
    if system_ffmpeg:
        return system_ffmpeg
    # 2. Check imageio-ffmpeg bundled binary
    try:
        import imageio_ffmpeg
        bundled = imageio_ffmpeg.get_ffmpeg_exe()
        if bundled and os.path.isfile(bundled):
            return bundled
    except ImportError:
        pass
    return None


def _configure_pydub():
    """Point pydub at the discovered ffmpeg binary."""
    ffmpeg_path = _find_ffmpeg()
    if ffmpeg_path:
        from pydub import AudioSegment
        AudioSegment.converter = ffmpeg_path
        AudioSegment.ffprobe = ffmpeg_path
    return ffmpeg_path


# Auto-configure on import
_ffmpeg_path = _configure_pydub()


def _ensure_temp_dir():
    """Create the temp audio directory if it doesn't exist."""
    os.makedirs(TEMP_AUDIO_DIR, exist_ok=True)


def load_audio(audio_path: str):
    """
    Load an audio file in any format and return a pydub AudioSegment
    normalized to 16 kHz mono 16-bit.

    Args:
        audio_path: Path to audio file (WAV, MP3, M4A, WebM, OGG, etc.)

    Returns:
        pydub.AudioSegment at 16 kHz mono

    Raises:
        FileNotFoundError: If audio file doesn't exist
        RuntimeError: If ffmpeg is not installed
    """
    if not os.path.isfile(audio_path):
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    try:
        from pydub import AudioSegment
    except Exception as import_err:
        import sys
        raise RuntimeError(
            f"Failed to import pydub. Error: {import_err}\n"
            "Run: pip install pydub>=0.25.1 audioop-lts\n"
            f"Python: {sys.executable}"
        )

    if _ffmpeg_path is None:
        raise RuntimeError(
            "ffmpeg is not installed or not in PATH.\n"
            "Install with: pip install imageio-ffmpeg\n"
            "Or: winget install Gyan.FFmpeg\n"
            "Then restart your terminal."
        )

    try:
        audio = AudioSegment.from_file(audio_path)
    except Exception as e:
        err_msg = str(e).lower()
        if (
            "ffmpeg" in err_msg
            or "ffprobe" in err_msg
            or "winerror 2" in err_msg
            or "no such file or directory" in err_msg
        ):
            raise RuntimeError(
                f"ffmpeg failed or not found.\n"
                f"Detected ffmpeg: {_ffmpeg_path}\n"
                f"Original error: {e}\n"
                "Try: pip install imageio-ffmpeg\n"
                "Then restart your terminal."
            )
        raise

    # Normalize to 16 kHz mono 16-bit (what Whisper expects)
    audio = audio.set_frame_rate(16000).set_channels(1).set_sample_width(2)

    # Enforce max duration
    duration_s = len(audio) / 1000.0
    if duration_s > MAX_AUDIO_DURATION_SECONDS:
        audio = audio[:MAX_AUDIO_DURATION_SECONDS * 1000]  # pydub uses ms

    return audio


def export_wav(audio, output_path: str = None) -> str:
    """
    Export an AudioSegment to a 16 kHz mono WAV file.

    Args:
        audio: pydub AudioSegment (already normalized)
        output_path: Output path. If None, creates a temp file.

    Returns:
        Path to the exported WAV file.
    """
    if output_path is None:
        _ensure_temp_dir()
        fd, output_path = tempfile.mkstemp(suffix=".wav", dir=TEMP_AUDIO_DIR)
        os.close(fd)

    audio.export(output_path, format="wav")
    return output_path


def audio_duration_seconds(audio_path: str) -> float:
    """Get the duration of an audio file in seconds without full loading."""
    audio = load_audio(audio_path)
    return len(audio) / 1000.0


def cleanup_temp_files():
    """Remove all temporary WAV files from the temp directory."""
    if os.path.isdir(TEMP_AUDIO_DIR):
        for f in os.listdir(TEMP_AUDIO_DIR):
            if f.endswith(".wav"):
                try:
                    os.remove(os.path.join(TEMP_AUDIO_DIR, f))
                except OSError:
                    pass
