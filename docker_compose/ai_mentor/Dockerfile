FROM python:3.11-slim

# Build tools required by llama-cpp-python source wheel (fallback if no manylinux wheel)
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential cmake git ca-certificates curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Cache HuggingFace downloads to the mounted volume
ENV HF_HOME=/models/.hf-cache
ENV FASTEMBED_CACHE_PATH=/models/.fastembed-cache

COPY services/ai_mentor/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY services/ai_mentor/ /app/

EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
