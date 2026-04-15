"""LLM Enrichment Service (FastAPI).

Consumes ``enrichment.requested`` from RabbitMQ, generates structured
enrichment data, and publishes ``enrichment.completed`` or
``enrichment.failed``.

Real implementation uses a local LLM (Qwen3 8B).  When the model is not
loaded (dev / CI), the service falls back to a clearly-marked stub so the
async event flow remains testable end-to-end without loading multi-GB weights.

Stub payload format (status key in /health):
    llm_ready: false
    consumer_alive: true
"""

import json
import logging
import os
import threading
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI

logging.basicConfig(level=logging.INFO)
_logger = logging.getLogger("llm-service")

# ---------------------------------------------------------------------------
# RabbitMQ configuration (from environment / docker-compose)
# ---------------------------------------------------------------------------

RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "rabbitmq")
RABBITMQ_PORT = int(os.getenv("RABBITMQ_PORT", "5672"))
RABBITMQ_VHOST = os.getenv("RABBITMQ_VHOST", "/")
RABBITMQ_USER = os.getenv("RABBITMQ_USER", "guest")
RABBITMQ_PASSWORD = os.getenv("RABBITMQ_PASSWORD", "guest")

QUEUE_IN = "enrichment.requested"
QUEUE_COMPLETED = "enrichment.completed"
QUEUE_FAILED = "enrichment.failed"

# ---------------------------------------------------------------------------
# LLM initialisation (optional — graceful fallback to stub)
# ---------------------------------------------------------------------------

_llm_ready = False


def _init_llm():
    """Attempt to load a local LLM model.  Returns True if successful.

    CPU-first strategy (no GPU assumed):
    - Lightweight path (recommended): Qwen2.5 1.5B or 3B via transformers (≤3 GB RAM).
      Install: pip install transformers torch --index-url https://download.pytorch.org/whl/cpu
      Then load with AutoModelForCausalLM and return True.
    - Heavier path (≥16 GB RAM): Qwen3 8B INT4 via llama-cpp-python.
      Install: pip install llama-cpp-python
      Then load a .gguf quantized checkpoint and return True.
    - Do NOT use unquantized FP16/FP32 Qwen3 8B on CPU — it requires 16–32 GB RAM
      and inference takes minutes, not seconds.

    Kept as stub (returns False) so the service starts in <1 second in dev/CI.
    In production: implement the load logic above, set _llm_ready = True, and
    use the model in _enrich() replacing the _stub_enrich() fallback.
    """
    return False


_llm_ready = _init_llm()

# ---------------------------------------------------------------------------
# Enrichment logic
# ---------------------------------------------------------------------------


def _enrich(source_text: str, source_language: str, language: str) -> dict:
    """Generate enrichment data.  Falls back to stub if LLM not loaded."""
    if _llm_ready:
        # Real LLM inference path (not yet implemented)
        raise NotImplementedError("Real LLM inference not wired up yet.")

    return _stub_enrich(source_text, source_language, language)


def _stub_enrich(source_text: str, source_language: str, language: str) -> dict:
    """Return clearly-marked stub enrichment so the event flow is testable."""
    prefix = f"[stub:{source_language}→{language}]"
    return {
        "synonyms": [f"{prefix} synonym1", f"{prefix} synonym2"],
        "antonyms": [f"{prefix} antonym1", f"{prefix} antonym2"],
        "example_sentences": [
            f"{prefix} Example sentence using '{source_text}'.",
            f"{prefix} Another example with '{source_text}'.",
            f"{prefix} A third example for '{source_text}'.",
        ],
        "explanation": (
            f"{prefix} No real explanation available — LLM not loaded. "
            f"Text: '{source_text}'"
        ),
    }


# ---------------------------------------------------------------------------
# RabbitMQ consumer thread
# ---------------------------------------------------------------------------

_consumer_alive = False


def _publish(channel, queue_name: str, payload: dict):
    """Declare queue (idempotent) and publish a JSON message."""
    import pika  # noqa: PLC0415

    channel.queue_declare(queue=queue_name, durable=True)
    channel.basic_publish(
        exchange="",
        routing_key=queue_name,
        body=json.dumps(payload),
        properties=pika.BasicProperties(delivery_mode=2),
    )


def _process_message(channel, method, properties, body):
    """Handle one enrichment.requested message."""
    message = {}
    try:
        message = json.loads(body)
        job_id = message.get("job_id", "")
        payload = message.get("payload", {})

        source_text = payload.get("source_text", "")
        source_language = payload.get("source_language", "en")
        language = payload.get("language", source_language)

        _logger.info(
            "Processing job_id=%s %s→%s text='%s'",
            job_id, source_language, language, source_text,
        )

        result = _enrich(source_text, source_language, language)

        _publish(channel, QUEUE_COMPLETED, {
            "job_id": job_id,
            "payload": result,
        })
        channel.basic_ack(delivery_tag=method.delivery_tag)
        _logger.info("Completed job_id=%s", job_id)

    except Exception as exc:  # noqa: BLE001
        job_id = message.get("job_id", "?") if message else "?"
        _logger.error("Failed job_id=%s: %s", job_id, exc)
        try:
            _publish(channel, QUEUE_FAILED, {
                "job_id": message.get("job_id", "") if message else "",
                "payload": {"error": str(exc)},
            })
            channel.basic_ack(delivery_tag=method.delivery_tag)
        except Exception:  # noqa: BLE001
            channel.basic_nack(delivery_tag=method.delivery_tag, requeue=False)


def _consumer_thread():
    """Background thread: connect to RabbitMQ and consume enrichment.requested."""
    global _consumer_alive  # noqa: PLW0603
    import pika  # noqa: PLC0415

    while True:
        try:
            credentials = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASSWORD)
            params = pika.ConnectionParameters(
                host=RABBITMQ_HOST,
                port=RABBITMQ_PORT,
                virtual_host=RABBITMQ_VHOST,
                credentials=credentials,
                heartbeat=30,
                blocked_connection_timeout=10,
            )
            connection = pika.BlockingConnection(params)
            channel = connection.channel()
            channel.queue_declare(queue=QUEUE_IN, durable=True)
            channel.basic_qos(prefetch_count=1)
            channel.basic_consume(queue=QUEUE_IN, on_message_callback=_process_message)
            _consumer_alive = True
            _logger.info(
                "LLM enrichment consumer started. llm_ready=%s. Waiting for messages…",
                _llm_ready,
            )
            channel.start_consuming()
        except Exception as exc:  # noqa: BLE001
            _consumer_alive = False
            _logger.warning("RabbitMQ connection lost: %s — reconnecting in 5s", exc)
            time.sleep(5)


# ---------------------------------------------------------------------------
# FastAPI application
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(app: FastAPI):
    t = threading.Thread(target=_consumer_thread, daemon=True, name="enrichment-consumer")
    t.start()
    yield


app = FastAPI(
    title="Lexora LLM Enrichment Service",
    description="Local LLM enrichment service (Qwen3 8B). Stub mode when model not loaded.",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "llm",
        "llm_ready": _llm_ready,
        "consumer_alive": _consumer_alive,
    }
