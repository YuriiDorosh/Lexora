"""
Translation Service — M3 implementation.

Provides offline translation between uk/en/el via Argos Translate.
Consumes 'translation.requested' from RabbitMQ; publishes
'translation.completed' or 'translation.failed'.

Architecture:
  - FastAPI app with /health endpoint (checked by Docker healthchecks)
  - Background thread runs the RabbitMQ consumer loop on startup
  - Argos Translate packages are downloaded/installed on first use

Two-hop routing for uk↔el (no direct Argos model):
  uk → en → el  and  el → en → uk
Quality limitation: two-hop degrades accuracy (ADR, OD-2).

Env vars (all optional; defaults work for docker-compose dev stack):
  RABBITMQ_HOST      default: rabbitmq
  RABBITMQ_PORT      default: 5672
  RABBITMQ_VHOST     default: /
  RABBITMQ_USER      default: guest
  RABBITMQ_PASSWORD  default: guest
"""

import json
import logging
import os
import threading
import time
import uuid
from contextlib import asynccontextmanager

import pika
from fastapi import FastAPI

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
_logger = logging.getLogger("translation-service")

# ---------------------------------------------------------------------------
# RabbitMQ config from environment
# ---------------------------------------------------------------------------

RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "rabbitmq")
RABBITMQ_PORT = int(os.getenv("RABBITMQ_PORT", "5672"))
RABBITMQ_VHOST = os.getenv("RABBITMQ_VHOST", "/")
RABBITMQ_USER = os.getenv("RABBITMQ_USER", "guest")
RABBITMQ_PASSWORD = os.getenv("RABBITMQ_PASSWORD", "guest")

QUEUE_REQUESTED = "translation.requested"
QUEUE_COMPLETED = "translation.completed"
QUEUE_FAILED = "translation.failed"

# ---------------------------------------------------------------------------
# Argos Translate — lazy init with graceful fallback
# ---------------------------------------------------------------------------

_argos_ready = False
_argos_lock = threading.Lock()


def _init_argos():
    """Download and install Argos Translate language packages on first call.

    Supported pairs: en↔uk, en↔el (uk↔el is two-hop via en).
    Returns True if packages are ready, False if argostranslate is not installed.
    """
    global _argos_ready  # noqa: PLW0603
    with _argos_lock:
        if _argos_ready:
            return True
        try:
            import argostranslate.package  # noqa: PLC0415
            import argostranslate.translate  # noqa: PLC0415

            _logger.info("Checking Argos Translate packages…")
            argostranslate.package.update_package_index()
            available = argostranslate.package.get_available_packages()

            needed = [
                ("en", "uk"), ("uk", "en"),
                ("en", "el"), ("el", "en"),
            ]
            for from_code, to_code in needed:
                pkg = next(
                    (p for p in available if p.from_code == from_code and p.to_code == to_code),
                    None,
                )
                if pkg:
                    installed = argostranslate.package.get_installed_packages()
                    already = any(
                        p.from_code == from_code and p.to_code == to_code
                        for p in installed
                    )
                    if not already:
                        _logger.info("Installing Argos package %s→%s…", from_code, to_code)
                        argostranslate.package.install_from_path(pkg.download())
                else:
                    _logger.warning("Argos package %s→%s not found in index", from_code, to_code)

            _argos_ready = True
            _logger.info("Argos Translate ready.")
            return True
        except ImportError:
            _logger.warning(
                "argostranslate not installed — using stub translation fallback."
                " Install argostranslate and rebuild the image to enable real translation."
            )
            return False
        except Exception as exc:
            _logger.error("Argos Translate init failed: %s", exc)
            return False


def _translate(source_text: str, source_language: str, target_language: str) -> str:
    """Translate text.  Falls back to a stub if Argos is unavailable."""
    if source_language == target_language:
        return source_text

    ready = _init_argos()
    if not ready:
        return _stub_translate(source_text, source_language, target_language)

    try:
        import argostranslate.translate  # noqa: PLC0415

        # Direct translation if a model exists; otherwise two-hop via English.
        installed = argostranslate.translate.get_installed_languages()
        from_lang = next((l for l in installed if l.code == source_language), None)  # noqa: E741
        if from_lang is None:
            raise RuntimeError(f"Source language '{source_language}' not installed in Argos")

        to_lang = next((l for l in installed if l.code == target_language), None)
        if to_lang is None:
            raise RuntimeError(f"Target language '{target_language}' not installed in Argos")

        translation_obj = from_lang.get_translation(to_lang)
        if translation_obj:
            return translation_obj.translate(source_text)

        # Two-hop via English for uk↔el.
        if source_language != "en" and target_language != "en":
            _logger.info("Two-hop translation %s→en→%s", source_language, target_language)
            en_lang = next((l for l in installed if l.code == "en"), None)
            if en_lang:
                step1 = from_lang.get_translation(en_lang)
                step2 = en_lang.get_translation(to_lang)
                if step1 and step2:
                    intermediate = step1.translate(source_text)
                    return step2.translate(intermediate)

        raise RuntimeError(f"No translation path {source_language}→{target_language}")
    except Exception as exc:
        _logger.error("Argos translation error: %s", exc)
        raise


def _stub_translate(source_text: str, source_language: str, target_language: str) -> str:
    """Stub translation used when argostranslate is not available."""
    return f"[stub:{source_language}→{target_language}] {source_text}"


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
    try:
        message = json.loads(body)
        job_id = message.get("job_id", str(uuid.uuid4()))
        payload = message.get("payload", {})

        source_text = payload.get("source_text", "")
        source_language = payload.get("source_language", "")
        target_language = payload.get("target_language", "")

        _logger.info(
            "Processing job_id=%s %s→%s text=%r",
            job_id, source_language, target_language, source_text[:50],
        )

        translated = _translate(source_text, source_language, target_language)
        _publish_result(channel, QUEUE_COMPLETED, job_id, {
            "translated_text": translated,
            "source_language": source_language,
            "target_language": target_language,
        })
        channel.basic_ack(delivery_tag=method.delivery_tag)
        _logger.info("Completed job_id=%s", job_id)

    except Exception as exc:  # noqa: BLE001
        _logger.error("Translation failed for job_id=%s: %s", message.get("job_id", "?"), exc)
        try:
            _publish_result(channel, QUEUE_FAILED, message.get("job_id", str(uuid.uuid4())), {
                "error": str(exc),
            })
        except Exception:
            pass
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
            _logger.info("Translation consumer started. Waiting for messages…")
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
    global _consumer_thread  # noqa: PLW0603
    _stop_event.clear()
    _consumer_thread = threading.Thread(target=_run_consumer, daemon=True, name="rmq-consumer")
    _consumer_thread.start()
    _logger.info("Translation service started.")
    yield
    _logger.info("Translation service shutting down…")
    _stop_event.set()


app = FastAPI(
    title="Lexora Translation Service",
    description="Offline translation service (Argos Translate via RabbitMQ). M3.",
    version="0.3.0",
    lifespan=lifespan,
)


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "translation",
        "argos_ready": _argos_ready,
        "consumer_alive": _consumer_thread.is_alive() if _consumer_thread else False,
    }
