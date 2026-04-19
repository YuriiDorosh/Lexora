FROM python:3.11-slim

WORKDIR /app

# ffmpeg: audio format probing / conversion.
# espeak-ng: fallback TTS when edge-tts is unavailable (offline/IP blocked).
RUN apt-get update && apt-get install -y --no-install-recommends \
        ffmpeg \
        espeak-ng \
    && rm -rf /var/lib/apt/lists/*

# HF_HOME: huggingface cache (faster-whisper downloads models here).
ENV HF_HOME=/models/.hf-cache
ENV WHISPER_MODEL_DIR=/models/whisper

COPY services/audio/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY services/audio/ .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
