"""Audio / TTS / STT Service — M6.

Responsibilities:
  1. TTS generation via edge-tts (online, Microsoft Edge free API, no key).
     Fallback: espeak-ng (local, system package).
  2. STT transcription via faster-whisper (CPU-only, int8 quantization).
     Default model: 'base' (~145 MB, ~300 MB resident).

Event flow:
  audio.generation.requested    -> _process_generation_job
      -> audio.generation.completed / audio.generation.failed

  audio.transcription.requested -> _process_transcription_job
      -> audio.transcription.completed / audio.transcription.failed

All jobs are acked regardless of outcome so the queue never wedges.
prefetch_count=1 ensures one job at a time (CPU-bound on 8 GiB server).
"""

import asyncio
import base64
import io
import json
import logging
import os
import subprocess
import tempfile
import threading
import time

import pika
from fastapi import FastAPI

_logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')

# ---------------------------------------------------------------------------
# Config from environment
# ---------------------------------------------------------------------------

RABBITMQ_HOST = os.environ.get('RABBITMQ_HOST', 'rabbitmq')
RABBITMQ_PORT = int(os.environ.get('RABBITMQ_PORT', 5672))
RABBITMQ_USER = os.environ.get('RABBITMQ_USER', 'guest')
RABBITMQ_PASS = os.environ.get('RABBITMQ_PASS', 'guest')
RABBITMQ_VHOST = os.environ.get('RABBITMQ_VHOST', '/')

TTS_ENGINE = os.environ.get('TTS_ENGINE', 'edge-tts')
TTS_FALLBACK_ENGINE = os.environ.get('TTS_FALLBACK_ENGINE', 'espeak-ng')
WHISPER_MODEL = os.environ.get('WHISPER_MODEL', 'base')
WHISPER_MODEL_DIR = os.environ.get('WHISPER_MODEL_DIR', '/models/whisper')
TRANSCRIPTION_ENABLED = os.environ.get('AUDIO_TRANSCRIPTION_ENABLED', '1') == '1'

# ---------------------------------------------------------------------------
# edge-tts voice map — neural voices for each supported language
# ---------------------------------------------------------------------------

_EDGE_VOICES = {
    'en': 'en-US-JennyNeural',
    'uk': 'uk-UA-PolinaNeural',
    'el': 'el-GR-AthinaNeural',
}

# espeak-ng language codes
_ESPEAK_LANGS = {'en': 'en', 'uk': 'uk', 'el': 'el'}

# ---------------------------------------------------------------------------
# Global state
# ---------------------------------------------------------------------------

_whisper_model = None
_whisper_ready = False
_consumer_alive = False

app = FastAPI(
    title='Lexora Audio / TTS / STT Service',
    description='edge-tts (primary) + espeak-ng (fallback) + faster-whisper STT. M6.',
    version='1.0.0',
)


# ---------------------------------------------------------------------------
# Whisper initialisation — daemon thread so /health is immediately responsive
# ---------------------------------------------------------------------------

def _init_whisper():
    global _whisper_model, _whisper_ready
    if not TRANSCRIPTION_ENABLED:
        _logger.info('Transcription disabled (AUDIO_TRANSCRIPTION_ENABLED=0)')
        return
    try:
        from faster_whisper import WhisperModel  # noqa: PLC0415
        os.makedirs(WHISPER_MODEL_DIR, exist_ok=True)
        _logger.info('Loading faster-whisper model=%s into %s ...', WHISPER_MODEL, WHISPER_MODEL_DIR)
        _whisper_model = WhisperModel(
            WHISPER_MODEL,
            device='cpu',
            compute_type='int8',
            download_root=WHISPER_MODEL_DIR,
        )
        _whisper_ready = True
        _logger.info('faster-whisper model=%s ready. Transcription enabled.', WHISPER_MODEL)
    except Exception as exc:
        _logger.error('faster-whisper load failed: %s — transcription will return empty strings', exc)


threading.Thread(target=_init_whisper, daemon=True, name='whisper-loader').start()


# ---------------------------------------------------------------------------
# TTS: edge-tts (primary — async)
# ---------------------------------------------------------------------------

async def _edge_tts_async(text: str, language: str) -> bytes:
    """Generate MP3 via edge-tts Communicate.stream(). Returns raw MP3 bytes.

    Times out after 45 seconds so a blocked network call doesn't stall the consumer.
    """
    import edge_tts  # noqa: PLC0415
    voice = _EDGE_VOICES.get(language, _EDGE_VOICES['en'])
    _logger.info('edge-tts: voice=%s text=%r', voice, text[:60])
    communicate = edge_tts.Communicate(text, voice)
    buf = io.BytesIO()

    async def _stream():
        async for chunk in communicate.stream():
            if chunk['type'] == 'audio':
                buf.write(chunk['data'])

    await asyncio.wait_for(_stream(), timeout=45.0)
    buf.seek(0)
    data = buf.read()
    if not data:
        raise RuntimeError('edge-tts returned empty audio')
    _logger.info('edge-tts: produced %d bytes', len(data))
    return data


# ---------------------------------------------------------------------------
# TTS: espeak-ng (fallback — subprocess)
# ---------------------------------------------------------------------------

def _espeak_tts(text: str, language: str) -> bytes:
    """Generate audio via espeak-ng, convert to MP3 via ffmpeg. Returns MP3 bytes."""
    lang_code = _ESPEAK_LANGS.get(language, 'en')
    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as wav_f:
        wav_path = wav_f.name
    try:
        subprocess.run(
            ['espeak-ng', '-v', lang_code, '-w', wav_path, text],
            check=True, capture_output=True, timeout=30,
        )
        result = subprocess.run(
            ['ffmpeg', '-y', '-i', wav_path, '-f', 'mp3', '-'],
            check=True, capture_output=True, timeout=30,
        )
        return result.stdout
    finally:
        try:
            os.unlink(wav_path)
        except OSError:
            pass


# ---------------------------------------------------------------------------
# TTS dispatcher
# ---------------------------------------------------------------------------

def _generate_tts(text: str, language: str) -> tuple:
    """Return (mp3_bytes: bytes, engine_name: str).

    Tries TTS_ENGINE first, falls back to TTS_FALLBACK_ENGINE on any error.
    Raises RuntimeError if all engines fail.
    """
    if TTS_ENGINE == 'edge-tts':
        try:
            mp3 = asyncio.run(_edge_tts_async(text, language))
            return mp3, 'edge-tts'
        except Exception as exc:
            _logger.warning('edge-tts failed (%s); trying fallback %s', exc, TTS_FALLBACK_ENGINE)

    if TTS_ENGINE == 'espeak-ng' or TTS_FALLBACK_ENGINE == 'espeak-ng':
        try:
            mp3 = _espeak_tts(text, language)
            return mp3, 'espeak-ng'
        except Exception as exc:
            _logger.error('espeak-ng failed: %s', exc)
            raise RuntimeError(f'All TTS engines failed. espeak-ng error: {exc}') from exc

    raise RuntimeError(f'No usable TTS engine configured (TTS_ENGINE={TTS_ENGINE})')


# ---------------------------------------------------------------------------
# STT: faster-whisper
# ---------------------------------------------------------------------------

def _transcribe(audio_bytes: bytes, language: str) -> str:
    """Transcribe audio bytes using faster-whisper. Returns joined transcript text."""
    if not _whisper_ready or _whisper_model is None:
        _logger.warning('Whisper not ready — returning empty transcription')
        return ''

    with tempfile.NamedTemporaryFile(suffix='.audio', delete=False) as f:
        f.write(audio_bytes)
        tmp_path = f.name
    try:
        segments, _ = _whisper_model.transcribe(
            tmp_path,
            language=language,
            beam_size=5,
        )
        return ' '.join(seg.text.strip() for seg in segments).strip()
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


# ---------------------------------------------------------------------------
# Job processors
# ---------------------------------------------------------------------------

def _process_generation_job(payload: dict) -> dict:
    job_id = payload.get('job_id', '')
    source_text = payload.get('source_text', '')
    language = payload.get('language', 'en')
    _logger.info('TTS job: job_id=%s text=%r lang=%s', job_id, source_text[:50], language)

    mp3_bytes, engine = _generate_tts(source_text, language)
    audio_b64 = base64.b64encode(mp3_bytes).decode('utf-8')
    _logger.info('TTS complete: job_id=%s engine=%s size=%d bytes', job_id, engine, len(mp3_bytes))
    return {
        'job_id': job_id,
        'audio_b64': audio_b64,
        'tts_engine': engine,
        'file_size_bytes': len(mp3_bytes),
    }


def _process_transcription_job(payload: dict) -> dict:
    job_id = payload.get('job_id', '')
    audio_id = payload.get('audio_id')
    language = payload.get('language', 'en')
    audio_b64 = payload.get('audio_data_b64', '')
    _logger.info('STT job: job_id=%s audio_id=%s lang=%s', job_id, audio_id, language)

    audio_bytes = base64.b64decode(audio_b64)
    transcript = _transcribe(audio_bytes, language)
    _logger.info('STT complete: job_id=%s chars=%d', job_id, len(transcript))
    return {
        'job_id': job_id,
        'audio_id': audio_id,
        'transcription': transcript,
    }


# ---------------------------------------------------------------------------
# RabbitMQ consumer
# ---------------------------------------------------------------------------

def _publish(channel, routing_key: str, body: dict):
    channel.basic_publish(
        exchange='',
        routing_key=routing_key,
        body=json.dumps(body, ensure_ascii=False).encode(),
        properties=pika.BasicProperties(
            delivery_mode=2,
            content_type='application/json',
        ),
    )


def _handle_message(channel, method, _properties, body):
    routing_key = method.routing_key
    _logger.info('Message received: routing_key=%s body_len=%d', routing_key, len(body))
    try:
        payload = json.loads(body)
    except Exception as exc:
        _logger.error('Failed to parse JSON on %s: %s | body=%r', routing_key, exc, body[:200])
        channel.basic_ack(delivery_tag=method.delivery_tag)
        return

    job_id = payload.get('job_id', '')
    _logger.info('Processing job_id=%s on queue=%s', job_id, routing_key)

    try:
        if routing_key == 'audio.generation.requested':
            result = _process_generation_job(payload)
            _publish(channel, 'audio.generation.completed', result)
            _logger.info('Published audio.generation.completed for job_id=%s', job_id)
        elif routing_key == 'audio.transcription.requested':
            result = _process_transcription_job(payload)
            _publish(channel, 'audio.transcription.completed', result)
            _logger.info('Published audio.transcription.completed for job_id=%s', job_id)
        else:
            _logger.warning('Unknown routing key: %s — acking and skipping', routing_key)
    except Exception as exc:
        _logger.error('Job FAILED job_id=%s queue=%s: %s', job_id, routing_key, exc, exc_info=True)
        fail_key = routing_key.replace('.requested', '.failed')
        error_payload = {'job_id': job_id, 'error': str(exc)}
        if routing_key == 'audio.transcription.requested':
            error_payload['audio_id'] = payload.get('audio_id')
        try:
            _publish(channel, fail_key, error_payload)
            _logger.info('Published %s for job_id=%s', fail_key, job_id)
        except Exception as pub_exc:
            _logger.error('Could not publish failure event %s: %s', fail_key, pub_exc)
    finally:
        channel.basic_ack(delivery_tag=method.delivery_tag)
        _logger.info('ACKed delivery_tag=%s for job_id=%s', method.delivery_tag, job_id)


def _consumer_loop():
    """Push-based RabbitMQ consumer for audio generation and transcription jobs.

    heartbeat=600: TTS + Whisper jobs can take 30–120 s on slow CPU.
    The 60 s default causes pika to close the connection mid-job;
    600 s gives safe headroom. The internal Docker network is stable,
    so a large heartbeat value is safe.
    """
    global _consumer_alive
    queues = ['audio.generation.requested', 'audio.transcription.requested']
    while True:
        try:
            creds = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASS)
            params = pika.ConnectionParameters(
                host=RABBITMQ_HOST,
                port=RABBITMQ_PORT,
                virtual_host=RABBITMQ_VHOST,
                credentials=creds,
                heartbeat=600,
                blocked_connection_timeout=300,
                connection_attempts=3,
                retry_delay=2,
            )
            _logger.info('Audio consumer: connecting to RabbitMQ at %s:%d vhost=%s',
                         RABBITMQ_HOST, RABBITMQ_PORT, RABBITMQ_VHOST)
            connection = pika.BlockingConnection(params)
            channel = connection.channel()
            channel.basic_qos(prefetch_count=1)
            for q in queues:
                channel.queue_declare(queue=q, durable=True)
                channel.basic_consume(queue=q, on_message_callback=_handle_message)
            _consumer_alive = True
            _logger.info('Audio consumer ready. Listening on queues: %s', queues)
            channel.start_consuming()
        except Exception as exc:
            _consumer_alive = False
            _logger.error('Audio consumer disconnected: %s — reconnecting in 5 s', exc)
            time.sleep(5)


threading.Thread(target=_consumer_loop, daemon=True, name='audio-consumer').start()


# ---------------------------------------------------------------------------
# FastAPI health endpoint
# ---------------------------------------------------------------------------

@app.get('/health')
def health():
    return {
        'status': 'ok',
        'service': 'audio',
        'tts_engine': TTS_ENGINE,
        'tts_fallback': TTS_FALLBACK_ENGINE,
        'whisper_model': WHISPER_MODEL,
        'whisper_ready': _whisper_ready,
        'transcription_enabled': TRANSCRIPTION_ENABLED,
        'consumer_alive': _consumer_alive,
    }
