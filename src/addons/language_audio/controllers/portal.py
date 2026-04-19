"""Portal controller for audio recording, TTS generation, STT transcription.

Routes:
  POST /my/audio/upload/<entry_id>        — multipart file upload (recorded audio)
  POST /my/audio/generate/<entry_id>      — enqueue TTS generation job
  POST /my/audio/transcribe/<audio_id>    — enqueue Whisper transcription job
  GET  /my/audio/<audio_id>/stream        — serve audio bytes with correct MIME type

All POST routes require auth='user' (portal login). Ownership of the target
entry is verified before any write — non-owners get a 404 (not 403, to avoid
leaking existence of the entry).

Upload path rationale: browser <input type="file" capture="microphone"> is used
instead of MediaRecorder API. The OS handles recording natively (mobile = mic app,
desktop = file picker). The file arrives as a standard multipart upload, which
Odoo's werkzeug integration can read directly via request.httprequest.files.
This avoids JS blob assembly complexity and is cross-browser compatible.
"""

import base64
import logging

from werkzeug.exceptions import NotFound
from werkzeug.wrappers import Response

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)

# Audio MIME types accepted for upload (anything starting with 'audio/' is accepted).
_ACCEPTED_MIME_PREFIXES = ('audio/',)

# System parameter key for max upload size.
_PARAM_MAX_BYTES = 'language.audio.max_upload_bytes'
_DEFAULT_MAX_BYTES = 10 * 1024 * 1024  # 10 MB


def _get_max_upload_bytes():
    try:
        val = request.env['ir.config_parameter'].sudo().get_param(_PARAM_MAX_BYTES)
        return int(val) if val else _DEFAULT_MAX_BYTES
    except Exception:
        return _DEFAULT_MAX_BYTES


def _get_entry_or_404(entry_id):
    """Return language.entry if owned by current user, else raise NotFound."""
    entry = request.env['language.entry'].browse(entry_id)
    if not entry.exists() or entry.owner_id.id != request.env.user.id:
        raise NotFound()
    return entry


def _json_response(data: dict, status: int = 200):
    import json  # noqa: PLC0415
    return Response(
        json.dumps(data),
        status=status,
        mimetype='application/json',
    )


class AudioPortal(http.Controller):

    # ------------------------------------------------------------------
    # Upload recorded audio
    # ------------------------------------------------------------------

    @http.route(
        '/my/audio/upload/<int:entry_id>',
        type='http', auth='user', website=True, methods=['POST'], csrf=True,
    )
    def audio_upload(self, entry_id, **post):
        """Accept a multipart audio file, store as ir.attachment + language.audio."""
        try:
            entry = _get_entry_or_404(entry_id)
        except NotFound:
            return _json_response({'status': 'error', 'message': 'Not found'}, 404)

        audio_file = request.httprequest.files.get('audio_file')
        if not audio_file:
            return _json_response({'status': 'error', 'message': 'No file provided'}, 400)

        # Validate MIME type.
        mime = audio_file.mimetype or ''
        if not any(mime.startswith(p) for p in _ACCEPTED_MIME_PREFIXES):
            return _json_response(
                {'status': 'error', 'message': f'Unsupported file type: {mime}'},
                400,
            )

        # Read data and enforce size limit.
        file_data = audio_file.read()
        max_bytes = _get_max_upload_bytes()
        if len(file_data) > max_bytes:
            return _json_response(
                {'status': 'error',
                 'message': f'File too large ({len(file_data):,} bytes). Max {max_bytes:,} bytes.'},
                413,
            )

        language = post.get('language') or entry.source_language
        filename = audio_file.filename or f'recording_{entry_id}.audio'

        try:
            # Create ir.attachment (sudo — portal user has no create rights on ir.attachment).
            b64_data = base64.b64encode(file_data).decode('utf-8')
            attachment = request.env['ir.attachment'].sudo().create({
                'name': filename,
                'datas': b64_data,
                'res_model': 'language.entry',
                'res_id': entry.id,
                'mimetype': mime or 'audio/mpeg',
            })

            # Create/update language.audio record.
            # The create() override in language_audio.py updates in-place for 'recorded'.
            audio_record = request.env['language.audio'].sudo().create({
                'entry_id': entry.id,
                'audio_type': 'recorded',
                'language': language,
                'status': 'completed',
                'attachment_id': attachment.id,
                'file_size_bytes': len(file_data),
            })

            _logger.info(
                'audio.upload: entry=%d user=%d size=%d mime=%s audio_id=%d',
                entry.id, request.env.user.id, len(file_data), mime, audio_record.id,
            )
            return _json_response({
                'status': 'ok',
                'audio_id': audio_record.id,
                'entry_id': entry.id,
            })
        except Exception as exc:
            _logger.error('audio.upload failed for entry=%d: %s', entry_id, exc)
            return _json_response({'status': 'error', 'message': str(exc)}, 500)

    # ------------------------------------------------------------------
    # Enqueue TTS generation
    # ------------------------------------------------------------------

    @http.route(
        '/my/audio/generate/<int:entry_id>',
        type='http', auth='user', website=True, methods=['POST'], csrf=True,
    )
    def audio_generate(self, entry_id, **post):
        """Enqueue a TTS generation job for the entry."""
        entry = _get_entry_or_404(entry_id)
        language = post.get('language') or entry.source_language
        try:
            request.env['language.audio']._enqueue_tts(entry, language)
        except Exception as exc:
            _logger.error('audio.generate failed for entry=%d: %s', entry_id, exc)
        return request.redirect('/my/vocabulary/%d' % entry_id)

    # ------------------------------------------------------------------
    # Enqueue STT transcription
    # ------------------------------------------------------------------

    @http.route(
        '/my/audio/transcribe/<int:audio_id>',
        type='http', auth='user', website=True, methods=['POST'], csrf=True,
    )
    def audio_transcribe(self, audio_id, **post):
        """Enqueue a Whisper transcription job for an existing audio record."""
        audio = request.env['language.audio'].sudo().browse(audio_id)
        if not audio.exists():
            return request.not_found()

        entry = audio.entry_id
        if not entry.exists() or entry.owner_id.id != request.env.user.id:
            return request.not_found()

        if not audio.attachment_id:
            return request.redirect('/my/vocabulary/%d?error=no_audio' % entry.id)

        try:
            request.env['language.audio']._enqueue_transcription(audio)
        except Exception as exc:
            _logger.error('audio.transcribe failed for audio_id=%d: %s', audio_id, exc)

        return request.redirect('/my/vocabulary/%d' % entry.id)

    # ------------------------------------------------------------------
    # Stream audio file
    # ------------------------------------------------------------------

    @http.route(
        '/my/audio/<int:audio_id>/stream',
        type='http', auth='user', website=True, methods=['GET'],
    )
    def audio_stream(self, audio_id, **kwargs):
        """Serve audio bytes from ir.attachment with correct Content-Type."""
        audio = request.env['language.audio'].sudo().browse(audio_id)
        if not audio.exists():
            return request.not_found()

        entry = audio.entry_id
        if not entry.exists() or entry.owner_id.id != request.env.user.id:
            return request.not_found()

        if not audio.attachment_id:
            return request.not_found()

        attachment = audio.attachment_id
        raw_data = attachment.datas
        if not raw_data:
            return request.not_found()

        # attachment.datas is a base64-encoded string (bytes or str).
        if isinstance(raw_data, bytes):
            audio_bytes = base64.b64decode(raw_data)
        else:
            audio_bytes = base64.b64decode(raw_data.encode('utf-8'))

        mime = attachment.mimetype or 'audio/mpeg'
        return Response(
            audio_bytes,
            status=200,
            mimetype=mime,
            headers={
                'Content-Disposition': 'inline',
                'Cache-Control': 'private, max-age=3600',
                'Content-Length': str(len(audio_bytes)),
            },
        )
