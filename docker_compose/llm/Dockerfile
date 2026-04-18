FROM python:3.11-slim

WORKDIR /app

# Build dependencies for llama-cpp-python.  When a manylinux x86_64 wheel is
# available for the pinned version, pip uses the prebuilt wheel and these
# tools are only a safety net; leaving them installed adds ~300 MB to the
# image but keeps builds resilient across pip-index / index-url changes.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        cmake \
        git \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY services/llm/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY services/llm/ .

# Model files live on a Docker volume mounted at /models (see compose file);
# they are NOT baked into the image.  Huggingface cache also goes under
# /models so re-downloads are skipped across restarts.
ENV HF_HOME=/models/.hf-cache

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
