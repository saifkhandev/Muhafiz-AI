# Backend image for the Muhafiz AI FastAPI service.
#
# Uses the serving dependency profile (requirements-serve.txt) and
# STT_BACKEND=groq, which keeps the container around 176MB RSS so it fits
# Render's 512MB free tier. Local Whisper (STT_BACKEND=local) needs ~2.7GB and
# will be OOM-killed there — run that profile on your own machine instead.

FROM python:3.12-slim

# ffmpeg is required: pydub shells out to ffmpeg/ffprobe for every format
# except wav, and the browser recorder uploads webm.
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements first so dependency layers cache across code changes.
COPY requirements-serve.txt .
RUN pip install --no-cache-dir -r requirements-serve.txt

COPY . .

ENV PYTHONUNBUFFERED=1 \
    ENABLE_AUDIO=true \
    STT_BACKEND=groq \
    PORT=8000

EXPOSE 8000

# Render assigns $PORT at runtime and kills services that bind to anything else.
# One worker only: the model is loaded into memory per process.
CMD ["sh", "-c", "uvicorn api.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1"]
