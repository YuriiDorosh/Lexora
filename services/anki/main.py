"""
Anki Import Service — M5 implementation.

Parses .apkg (SQLite inside zip) and .txt (TSV) Anki exports.
Consumes 'anki.import.requested' from RabbitMQ; publishes
'anki.import.completed' or 'anki.import.failed'.

Completed payload shape:
  {
    "entries":     [{"source_text": "...", "translation": "...", "audio_filename": "..."}, ...],
    "audio_data":  {"filename.mp3": "<base64>", ...},
    "parse_errors":[{"reason": "..."}, ...]
  }

Env vars (all optional; defaults work for docker-compose dev stack):
  RABBITMQ_HOST      default: rabbitmq
  RABBITMQ_PORT      default: 5672
  RABBITMQ_VHOST     default: /
  RABBITMQ_USER      default: guest
  RABBITMQ_PASSWORD  default: guest
"""

import base64
import json
import logging
import os
import re
import sqlite3
import tempfile
import threading
import time
import uuid
import zipfile
from contextlib import asynccontextmanager

import pika
from fastapi import FastAPI

try:
    import zstandard as _zstd
    _ZSTD_AVAILABLE = True
except ImportError:
    _zstd = None  # type: ignore[assignment]
    _ZSTD_AVAILABLE = False

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
_logger = logging.getLogger("anki-service")

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "rabbitmq")
RABBITMQ_PORT = int(os.getenv("RABBITMQ_PORT", "5672"))
RABBITMQ_VHOST = os.getenv("RABBITMQ_VHOST", "/")
RABBITMQ_USER = os.getenv("RABBITMQ_USER", "guest")
RABBITMQ_PASSWORD = os.getenv("RABBITMQ_PASSWORD", "guest")

QUEUE_REQUESTED = "anki.import.requested"
QUEUE_COMPLETED = "anki.import.completed"
QUEUE_FAILED = "anki.import.failed"

# Regex: matches [sound:filename.ext] tags embedded in Anki card fields.
_SOUND_RE = re.compile(r'\[sound:([^\]]+)\]', re.IGNORECASE)

# Stub note text Anki embeds as the only card in an incompatible export.
_STUB_NOTE_FRAGMENT = 'please update to the latest anki'

ZSTD_MAGIC = b'\x28\xB5\x2F\xFD'
SQLITE_MAGIC = b'SQLite format 3\x00'


def _decompress_if_needed(data: bytes, label: str) -> bytes:
    """Decompress Zstd-compressed bytes; return plain bytes unchanged."""
    if data[:4] != ZSTD_MAGIC:
        return data
    if not _ZSTD_AVAILABLE:
        raise RuntimeError(
            f'{label} is Zstd-compressed but the "zstandard" package is not installed. '
            'Add zstandard==0.22.0 to requirements.txt and rebuild the image.'
        )
    _logger.info('%s: Zstd-compressed — decompressing…', label)
    return _zstd.ZstdDecompressor().decompress(data, max_output_size=512 * 1024 * 1024)

_AUDIO_EXTENSIONS = {'.mp3', '.ogg', '.wav', '.m4a', '.flac'}

# ---------------------------------------------------------------------------
# HTML stripping
# ---------------------------------------------------------------------------

try:
    from bs4 import BeautifulSoup as _BS  # noqa: PLC0415
    def _strip_html(text: str) -> str:
        return _BS(text, 'html.parser').get_text(separator=' ')
except ImportError:
    _logger.warning('beautifulsoup4 not installed — falling back to regex HTML strip')
    _TAG_RE = re.compile(r'<[^>]+>')
    def _strip_html(text: str) -> str:  # type: ignore[misc]
        return _TAG_RE.sub('', text)


def _clean_field(raw: str) -> tuple[str, list[str]]:
    """Strip HTML and extract sound filenames from an Anki field value.

    Returns (cleaned_text, [audio_filenames]).
    Sound tags are removed from the displayed text; their filenames are
    returned separately for audio extraction.
    """
    sounds = _SOUND_RE.findall(raw)
    no_sound = _SOUND_RE.sub('', raw)
    text = _strip_html(no_sound).strip()
    # Collapse whitespace left behind by removed tags/sounds.
    text = re.sub(r'\s+', ' ', text).strip()
    audio = [s for s in sounds if os.path.splitext(s)[1].lower() in _AUDIO_EXTENSIONS]
    return text, audio


# ---------------------------------------------------------------------------
# .txt parser (M5-08a)
# ---------------------------------------------------------------------------

def _parse_txt(file_bytes: bytes) -> tuple[list, list]:
    """Parse a tab-separated text file.

    Column 0 = source_text, column 1 = translation (optional).
    Lines starting with # are treated as comments and skipped.

    Returns (entries, parse_errors).
    """
    entries: list[dict] = []
    parse_errors: list[dict] = []

    try:
        text = file_bytes.decode('utf-8', errors='replace')
    except Exception as exc:
        return [], [{'reason': f'Cannot decode file as UTF-8: {exc}'}]

    for line_num, raw_line in enumerate(text.splitlines(), 1):
        line = raw_line.rstrip('\r\n')
        if not line or line.lstrip().startswith('#'):
            continue

        parts = line.split('\t')
        source_text = _strip_html(parts[0]).strip() if parts else ''
        if not source_text:
            parse_errors.append({'reason': f'Line {line_num}: empty source text'})
            continue

        entry: dict = {'source_text': source_text}
        if len(parts) >= 2:
            translation = _strip_html(parts[1]).strip()
            if translation:
                entry['translation'] = translation

        entries.append(entry)

    _logger.info('TXT parsed: %d entries, %d errors', len(entries), len(parse_errors))
    return entries, parse_errors


# ---------------------------------------------------------------------------
# .apkg parser (M5-08b)
# ---------------------------------------------------------------------------

def _detect_field_indices(cur: sqlite3.Cursor, field_mapping: dict) -> tuple[int, int]:
    """Return (source_idx, translation_idx).

    Priority:
    1. Explicit integer indices in field_mapping ({"source": 0, "translation": 1}).
    2. Auto-detect Front/Back field names from the col table's models JSON.
    3. Default: (0, 1).
    """
    # 1. Explicit index override from Odoo portal field-mapping UI.
    if isinstance(field_mapping.get('source'), int):
        src = int(field_mapping['source'])
        tgt = int(field_mapping.get('translation', 1 if src != 1 else 0))
        return src, tgt

    # 2. Auto-detect by field name (Front/Back convention).
    try:
        cur.execute("SELECT models FROM col LIMIT 1")
        row = cur.fetchone()
        if row:
            models_json = json.loads(row[0])
            for model in models_json.values():
                field_names = [f.get('name', '').lower() for f in model.get('flds', [])]
                if 'front' in field_names:
                    src_idx = field_names.index('front')
                    tgt_idx = field_names.index('back') if 'back' in field_names else (
                        1 if src_idx == 0 else 0
                    )
                    _logger.debug('Auto-detected Front/Back at indices %d/%d', src_idx, tgt_idx)
                    return src_idx, tgt_idx
    except Exception as exc:
        _logger.debug('Field auto-detection failed: %s — using defaults', exc)

    return 0, 1


def _parse_apkg(file_bytes: bytes, field_mapping: dict) -> tuple[list, dict, list]:
    """Parse an Anki .apkg file.

    Supports both classic SQLite databases and the modern Anki format where
    collection.anki21b / the media file are Zstd-compressed.

    DB priority: collection.anki21b (Zstd) → collection.anki21 → collection.anki2.

    Returns (entries, audio_data, parse_errors).
      entries    — list of {"source_text", "translation"?, "audio_filename"?}
      audio_data — {"filename.mp3": "<base64>"}
      parse_errors — [{"reason": "..."}]
    """
    entries: list[dict] = []
    audio_data: dict[str, str] = {}
    parse_errors: list[dict] = []

    with tempfile.TemporaryDirectory() as tmpdir:
        zip_path = os.path.join(tmpdir, 'deck.apkg')
        with open(zip_path, 'wb') as fh:
            fh.write(file_bytes)

        try:
            with zipfile.ZipFile(zip_path, 'r') as zf:
                zip_names = set(zf.namelist())

                # --- Media map (may itself be Zstd-compressed in newer Anki) ---
                media_map: dict[str, str] = {}
                if 'media' in zip_names:
                    try:
                        raw_media = zf.read('media')
                        raw_media = _decompress_if_needed(raw_media, 'media')
                        media_map = json.loads(raw_media.decode('utf-8'))
                    except Exception as exc:
                        _logger.warning('Could not read media map: %s', exc)
                # Reverse map: filename → zip key
                rev_media = {v: k for k, v in media_map.items()}

                # --- Locate collection DB (priority: anki21b > anki21 > anki2) ---
                db_name = next(
                    (n for n in ('collection.anki21b', 'collection.anki21', 'collection.anki2')
                     if n in zip_names),
                    None,
                )
                if db_name is None:
                    parse_errors.append({'reason': 'No collection database found in archive'})
                    return entries, audio_data, parse_errors

                _logger.info('Using collection DB: %s', db_name)
                db_bytes = zf.read(db_name)
                db_bytes = _decompress_if_needed(db_bytes, db_name)

                if db_bytes[:16] != SQLITE_MAGIC:
                    parse_errors.append({
                        'reason': f'{db_name} is not a valid SQLite database after decompression'
                    })
                    return entries, audio_data, parse_errors

                db_path = os.path.join(tmpdir, 'collection.db')
                with open(db_path, 'wb') as fh:
                    fh.write(db_bytes)

                # --- Query notes ---
                conn = sqlite3.connect(db_path)
                conn.row_factory = sqlite3.Row
                cur = conn.cursor()

                src_idx, tgt_idx = _detect_field_indices(cur, field_mapping)

                cur.execute("SELECT flds FROM notes")
                rows = cur.fetchall()
                conn.close()

                _logger.info(
                    'apkg: %d notes, field indices src=%d tgt=%d, media=%d files',
                    len(rows), src_idx, tgt_idx, len(media_map),
                )

                for row_num, row in enumerate(rows, 1):
                    flds_raw = row['flds']

                    # Skip the "Please update Anki" stub note that Anki injects
                    # into incompatible exports when the deck contains no real cards.
                    if _STUB_NOTE_FRAGMENT in flds_raw.lower():
                        _logger.debug('Row %d: skipping Anki stub note', row_num)
                        continue

                    fields = flds_raw.split('\x1f')
                    try:
                        src_raw = fields[src_idx] if src_idx < len(fields) else ''
                        src_text, src_audio = _clean_field(src_raw)

                        if not src_text:
                            parse_errors.append(
                                {'reason': f'Row {row_num}: empty source text after cleaning'}
                            )
                            continue

                        entry: dict = {'source_text': src_text}

                        # Translation field
                        if tgt_idx < len(fields):
                            tgt_text, tgt_audio = _clean_field(fields[tgt_idx])
                            if tgt_text:
                                entry['translation'] = tgt_text
                        else:
                            tgt_audio = []

                        # Audio: first audio ref from source, then translation
                        chosen_audio = next(
                            (s for s in src_audio + tgt_audio),
                            None,
                        )
                        if chosen_audio:
                            entry['audio_filename'] = chosen_audio
                            # Extract binary only once per filename.
                            if chosen_audio not in audio_data:
                                zip_key = rev_media.get(chosen_audio)
                                if zip_key and zip_key in zip_names:
                                    try:
                                        raw = zf.read(zip_key)
                                        audio_data[chosen_audio] = base64.b64encode(raw).decode('ascii')
                                    except Exception as exc:
                                        _logger.warning(
                                            'Row %d: audio extraction failed for %r: %s',
                                            row_num, chosen_audio, exc,
                                        )

                        entries.append(entry)

                    except Exception as exc:
                        parse_errors.append({'reason': f'Row {row_num}: {exc}'})
                        _logger.warning('apkg row %d parse error: %s', row_num, exc)

        except zipfile.BadZipFile:
            parse_errors.append({'reason': 'Invalid .apkg file (not a valid zip archive)'})
        except RuntimeError as exc:
            # Raised by _decompress_if_needed when zstandard is missing.
            parse_errors.append({'reason': str(exc)})
            _logger.error('apkg parse failed: %s', exc)
        except Exception as exc:
            parse_errors.append({'reason': f'Unexpected error parsing .apkg: {exc}'})
            _logger.error('apkg parse failed: %s', exc)

    _logger.info(
        'apkg result: %d entries, %d audio files, %d errors',
        len(entries), len(audio_data), len(parse_errors),
    )
    return entries, audio_data, parse_errors


# ---------------------------------------------------------------------------
# Job dispatcher (M5-09)
# ---------------------------------------------------------------------------

def _process_job(payload: dict) -> tuple[list, dict, list]:
    """Decode file data and route to the correct parser.

    Returns (entries, audio_data, parse_errors).
    Raises on unrecoverable decode failure so the caller publishes .failed.
    """
    file_b64 = payload.get('file_data', '')
    file_format = payload.get('file_format', 'apkg').lower()
    field_mapping_raw = payload.get('field_mapping', '{}') or '{}'

    try:
        field_mapping = json.loads(field_mapping_raw)
    except (json.JSONDecodeError, TypeError):
        field_mapping = {}

    try:
        file_bytes = base64.b64decode(file_b64)
    except Exception as exc:
        raise ValueError(f'Cannot decode file_data: {exc}') from exc

    if not file_bytes:
        raise ValueError('file_data is empty')

    if file_format == 'txt':
        entries, parse_errors = _parse_txt(file_bytes)
        return entries, {}, parse_errors

    # Default: apkg
    return _parse_apkg(file_bytes, field_mapping)


# ---------------------------------------------------------------------------
# RabbitMQ helpers
# ---------------------------------------------------------------------------

def _make_connection():
    creds = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASSWORD)
    params = pika.ConnectionParameters(
        host=RABBITMQ_HOST,
        port=RABBITMQ_PORT,
        virtual_host=RABBITMQ_VHOST,
        credentials=creds,
        connection_attempts=5,
        retry_delay=3,
        heartbeat=30,
    )
    return pika.BlockingConnection(params)


def _publish_result(channel, queue_name: str, job_id: str, payload: dict):
    message = {
        'job_id': job_id,
        'event_type': queue_name,
        'payload': payload,
    }
    channel.queue_declare(queue=queue_name, durable=True)
    channel.basic_publish(
        exchange='',
        routing_key=queue_name,
        body=json.dumps(message, ensure_ascii=False),
        properties=pika.BasicProperties(
            delivery_mode=2,
            content_type='application/json',
        ),
    )


# ---------------------------------------------------------------------------
# Message handler
# ---------------------------------------------------------------------------

def _handle_message(channel, method, _props, body):
    """Handle a single anki.import.requested message."""
    message: dict = {}
    try:
        message = json.loads(body)
        job_id = message.get('job_id', str(uuid.uuid4()))
        payload = message.get('payload', {})

        _logger.info(
            'Processing job_id=%s format=%s filename=%s',
            job_id,
            payload.get('file_format', '?'),
            payload.get('filename', '?') if 'filename' in payload else '(no filename)',
        )

        entries, audio_data, parse_errors = _process_job(payload)

        _publish_result(channel, QUEUE_COMPLETED, job_id, {
            'entries': entries,
            'audio_data': audio_data,
            'parse_errors': parse_errors,
        })
        channel.basic_ack(delivery_tag=method.delivery_tag)
        _logger.info(
            'Completed job_id=%s entries=%d audio=%d errors=%d',
            job_id, len(entries), len(audio_data), len(parse_errors),
        )

    except Exception as exc:  # noqa: BLE001
        job_id = message.get('job_id', str(uuid.uuid4())) if message else str(uuid.uuid4())
        _logger.error('Import failed for job_id=%s: %s', job_id, exc)
        try:
            _publish_result(channel, QUEUE_FAILED, job_id, {'error': str(exc)})
        except Exception:
            pass
        channel.basic_ack(delivery_tag=method.delivery_tag)


# ---------------------------------------------------------------------------
# Consumer thread
# ---------------------------------------------------------------------------

_consumer_thread: threading.Thread | None = None
_stop_event = threading.Event()


def _run_consumer():
    """Consumer loop — daemon thread, reconnects on failure."""
    while not _stop_event.is_set():
        try:
            _logger.info('Connecting to RabbitMQ at %s:%s…', RABBITMQ_HOST, RABBITMQ_PORT)
            connection = _make_connection()
            channel = connection.channel()
            channel.queue_declare(queue=QUEUE_REQUESTED, durable=True)
            channel.basic_qos(prefetch_count=1)
            channel.basic_consume(queue=QUEUE_REQUESTED, on_message_callback=_handle_message)
            _logger.info('Anki consumer started. Waiting for messages…')
            channel.start_consuming()
        except Exception as exc:
            if _stop_event.is_set():
                break
            _logger.warning('RabbitMQ connection lost: %s — retrying in 5s…', exc)
            time.sleep(5)


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    global _consumer_thread  # noqa: PLW0603
    _stop_event.clear()
    _consumer_thread = threading.Thread(target=_run_consumer, daemon=True, name='rmq-consumer')
    _consumer_thread.start()
    _logger.info('Anki service started.')
    yield
    _logger.info('Anki service shutting down…')
    _stop_event.set()


app = FastAPI(
    title='Lexora Anki Import Service',
    description='Parses .apkg and .txt Anki exports via RabbitMQ. M5.',
    version='0.5.0',
    lifespan=lifespan,
)


@app.get('/health')
def health():
    return {
        'status': 'ok',
        'service': 'anki',
        'consumer_alive': _consumer_thread.is_alive() if _consumer_thread else False,
    }
