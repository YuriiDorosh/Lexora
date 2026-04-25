"""
Translation Service — M4c implementation.

Translates text between uk/en/el via deep_translator (ADR-028).
Consumes 'translation.requested' from RabbitMQ; publishes
'translation.completed' or 'translation.failed'.

Provider chain (both configurable via env vars):
  Primary:  TRANSLATE_PROVIDER         (default: google)
  Fallback: TRANSLATE_FALLBACK_PROVIDER (default: mymemory)

On any primary exception the fallback is tried once.  If both fail,
'translation.failed' is published with a descriptive error message.

Env vars:
  RABBITMQ_HOST                default: rabbitmq
  RABBITMQ_PORT                default: 5672
  RABBITMQ_VHOST               default: /
  RABBITMQ_USER                default: guest
  RABBITMQ_PASSWORD            default: guest
  TRANSLATE_PROVIDER           default: google
  TRANSLATE_FALLBACK_PROVIDER  default: mymemory
  TRANSLATE_TIMEOUT_SECONDS    default: 10
"""

import contextlib
from contextlib import asynccontextmanager
import json
import logging
import os
import socket
import threading
import time
import uuid

from fastapi import FastAPI
import pika
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
_logger = logging.getLogger("translation-service")

# ---------------------------------------------------------------------------
# Config from environment
# ---------------------------------------------------------------------------

RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "rabbitmq")
RABBITMQ_PORT = int(os.getenv("RABBITMQ_PORT", "5672"))
RABBITMQ_VHOST = os.getenv("RABBITMQ_VHOST", "/")
RABBITMQ_USER = os.getenv("RABBITMQ_USER", "guest")
RABBITMQ_PASSWORD = os.getenv("RABBITMQ_PASSWORD", "guest")

TRANSLATE_PROVIDER = os.getenv("TRANSLATE_PROVIDER", "google").lower()
TRANSLATE_FALLBACK_PROVIDER = os.getenv("TRANSLATE_FALLBACK_PROVIDER", "mymemory").lower()
TRANSLATE_TIMEOUT_SECONDS = int(os.getenv("TRANSLATE_TIMEOUT_SECONDS", "10"))

QUEUE_REQUESTED = "translation.requested"
QUEUE_COMPLETED = "translation.completed"
QUEUE_FAILED = "translation.failed"

# Apply a global socket timeout once at startup so all deep_translator HTTP
# calls respect it.  Safe here because the consumer is single-threaded and
# the only outbound caller in this process.
socket.setdefaulttimeout(TRANSLATE_TIMEOUT_SECONDS)

# ---------------------------------------------------------------------------
# Translation helpers
# ---------------------------------------------------------------------------

# MyMemory requires region-tagged locale codes rather than bare ISO-639 codes.
_MYMEMORY_LOCALES: dict[str, str] = {
    "en": "en-US",
    "uk": "uk-UA",
    "el": "el-GR",
}


def _translate_with_provider(provider: str, text: str, source: str, target: str) -> str:
    """Call the given deep_translator provider.  Raises on any failure."""
    if provider == "google":
        from deep_translator import GoogleTranslator

        return GoogleTranslator(source=source, target=target).translate(text)
    if provider == "mymemory":
        from deep_translator import MyMemoryTranslator

        src_locale = _MYMEMORY_LOCALES.get(source, source)
        tgt_locale = _MYMEMORY_LOCALES.get(target, target)
        return MyMemoryTranslator(source=src_locale, target=tgt_locale).translate(text)
    raise ValueError(f"Unknown TRANSLATE_PROVIDER value: {provider!r}")


def _translate(source_text: str, source_language: str, target_language: str) -> str:
    """Translate text using the configured provider with automatic fallback.

    Returns the translated string.  Raises on total failure (both providers
    exhausted) so the caller can publish translation.failed.
    """
    if source_language == target_language:
        return source_text

    try:
        result = _translate_with_provider(
            TRANSLATE_PROVIDER, source_text, source_language, target_language
        )
        _logger.debug(
            "Provider '%s' succeeded for %s→%s",
            TRANSLATE_PROVIDER,
            source_language,
            target_language,
        )
        return result
    except Exception as primary_exc:
        _logger.warning(
            "Primary provider '%s' failed (%s) — switching to fallback '%s'",
            TRANSLATE_PROVIDER,
            primary_exc,
            TRANSLATE_FALLBACK_PROVIDER,
        )

    try:
        result = _translate_with_provider(
            TRANSLATE_FALLBACK_PROVIDER, source_text, source_language, target_language
        )
        _logger.info(
            "Fallback provider '%s' succeeded for %s→%s",
            TRANSLATE_FALLBACK_PROVIDER,
            source_language,
            target_language,
        )
        return result
    except Exception as fallback_exc:
        _logger.error(
            "Fallback provider '%s' also failed: %s",
            TRANSLATE_FALLBACK_PROVIDER,
            fallback_exc,
        )
        raise fallback_exc


# ---------------------------------------------------------------------------
# RabbitMQ publisher helper
# ---------------------------------------------------------------------------


def _make_connection():
    credentials = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASSWORD)
    params = pika.ConnectionParameters(
        host=RABBITMQ_HOST,
        port=RABBITMQ_PORT,
        virtual_host=RABBITMQ_VHOST,
        credentials=credentials,
        connection_attempts=5,
        retry_delay=3,
        heartbeat=30,
    )
    return pika.BlockingConnection(params)


def _publish_result(channel, queue_name: str, job_id: str, payload: dict):
    message = {
        "job_id": job_id,
        "event_type": queue_name,
        "payload": payload,
    }
    channel.queue_declare(queue=queue_name, durable=True)
    channel.basic_publish(
        exchange="",
        routing_key=queue_name,
        body=json.dumps(message, ensure_ascii=False),
        properties=pika.BasicProperties(
            delivery_mode=2,
            content_type="application/json",
        ),
    )


# ---------------------------------------------------------------------------
# Message handler
# ---------------------------------------------------------------------------


def _handle_message(channel, method, _properties, body):
    """Process a single translation.requested message."""
    message: dict = {}
    try:
        message = json.loads(body)
        job_id = message.get("job_id", str(uuid.uuid4()))
        payload = message.get("payload", {})

        source_text = payload.get("source_text", "")
        source_language = payload.get("source_language", "")
        target_language = payload.get("target_language", "")

        _logger.info(
            "Processing job_id=%s %s→%s text=%r",
            job_id,
            source_language,
            target_language,
            source_text[:50],
        )

        translated = _translate(source_text, source_language, target_language)
        _publish_result(
            channel,
            QUEUE_COMPLETED,
            job_id,
            {
                "translated_text": translated,
                "source_language": source_language,
                "target_language": target_language,
            },
        )
        channel.basic_ack(delivery_tag=method.delivery_tag)
        _logger.info("Completed job_id=%s result=%r", job_id, translated[:60])

    except Exception as exc:
        _logger.error("Translation failed for job_id=%s: %s", message.get("job_id", "?"), exc)
        with contextlib.suppress(Exception):
            _publish_result(
                channel,
                QUEUE_FAILED,
                message.get("job_id", str(uuid.uuid4())),
                {
                    "error": str(exc),
                },
            )
        channel.basic_ack(delivery_tag=method.delivery_tag)


# ---------------------------------------------------------------------------
# Consumer thread
# ---------------------------------------------------------------------------

_consumer_thread: threading.Thread | None = None
_stop_event = threading.Event()


def _run_consumer():
    """Consumer loop — runs in a daemon thread.  Reconnects on failure."""
    while not _stop_event.is_set():
        try:
            _logger.info("Connecting to RabbitMQ at %s:%s…", RABBITMQ_HOST, RABBITMQ_PORT)
            connection = _make_connection()
            channel = connection.channel()
            channel.queue_declare(queue=QUEUE_REQUESTED, durable=True)
            channel.basic_qos(prefetch_count=1)
            channel.basic_consume(queue=QUEUE_REQUESTED, on_message_callback=_handle_message)
            _logger.info(
                "Translation consumer started (provider=%s, fallback=%s). Waiting for messages…",
                TRANSLATE_PROVIDER,
                TRANSLATE_FALLBACK_PROVIDER,
            )
            channel.start_consuming()
        except Exception as exc:
            if _stop_event.is_set():
                break
            _logger.warning("RabbitMQ connection lost: %s — retrying in 5s…", exc)
            time.sleep(5)


# ---------------------------------------------------------------------------
# FastAPI app with lifespan
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Start the consumer thread on startup; stop it on shutdown."""
    global _consumer_thread
    _stop_event.clear()
    _consumer_thread = threading.Thread(target=_run_consumer, daemon=True, name="rmq-consumer")
    _consumer_thread.start()
    _logger.info(
        "Translation service started (provider=%s, timeout=%ss).",
        TRANSLATE_PROVIDER,
        TRANSLATE_TIMEOUT_SECONDS,
    )
    yield
    _logger.info("Translation service shutting down…")
    _stop_event.set()


app = FastAPI(
    title="Lexora Translation Service",
    description="Online translation service (deep_translator via RabbitMQ). M4c.",
    version="0.4.0",
    lifespan=lifespan,
)


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "translation",
        "provider": TRANSLATE_PROVIDER,
        "fallback_provider": TRANSLATE_FALLBACK_PROVIDER,
        "ready": True,
        "consumer_alive": _consumer_thread.is_alive() if _consumer_thread else False,
    }


# ---------------------------------------------------------------------------
# Synchronous HTTP endpoint — used by the Lexora Translator Tool (M15)
# ---------------------------------------------------------------------------


class TranslateRequest(BaseModel):
    text: str
    source: str  # en / uk / el
    target: str  # en / uk / el


@app.post("/translate")
def translate_sync(req: TranslateRequest):
    """Synchronous translation endpoint for the interactive Translator UI.
    Returns JSON immediately — no RabbitMQ involved."""
    text = req.text.strip()
    if not text:
        return {"status": "error", "message": "Empty text"}
    if req.source == req.target:
        return {"status": "ok", "result": text}
    try:
        result = _translate(text, req.source, req.target)
        return {"status": "ok", "result": result}
    except Exception as exc:
        _logger.warning("sync /translate failed: %s", exc)
        return {"status": "error", "message": str(exc)}
