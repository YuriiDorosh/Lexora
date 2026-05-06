"""Portal controller for the AI Speaking Coach (M30).

End-to-end synchronous pipeline (no RabbitMQ):
  1. /my/speaking            GET   page render
  2. /my/speaking/topic      POST  JSON-RPC → LLM /generate-topic
  3. /my/speaking/transcribe POST  multipart → audio /transcribe-sync
                                   creates language.speaking.session
                                   (status='analyzing')
  4. /my/speaking/analyze    POST  JSON-RPC → LLM /analyze-speech
                                   persists feedback, sets status='completed'
  5. /my/speaking/<id>       GET   detail page
"""

import base64
import logging
import os
from datetime import timedelta

import requests as _requests
from odoo import http
from odoo.exceptions import AccessError
from odoo.http import request

_logger = logging.getLogger(__name__)

_LLM_SVC = os.environ.get("LLM_SERVICE_URL", "http://llm-service:8000").rstrip("/")
_AUDIO_SVC = os.environ.get("AUDIO_SERVICE_URL", "http://audio-service:8000").rstrip("/")

_DEFAULT_LANGUAGES = [
    ("en", "English"),
    ("uk", "Ukrainian"),
    ("el", "Greek"),
    ("pl", "Polish"),
]
_RECENT_LIMIT = 10
_VALID_LANGS = {"en", "uk", "el", "pl"}

# Sync HTTP timeouts (seconds)
_LLM_TIMEOUT = 90       # /analyze-speech can run 20-40 s on Qwen 1.5B CPU
_AUDIO_TIMEOUT = 120    # /transcribe-sync covers 90 s of audio + Whisper time


class SpeakingPortal(http.Controller):
    # ------------------------------------------------------------------
    # GET /my/speaking — main page
    # ------------------------------------------------------------------

    @http.route("/my/speaking", type="http", auth="user", website=True, methods=["GET"])
    def speaking_index(self, **kw):
        Session = request.env["language.speaking.session"].sudo()
        uid = request.env.user.id

        recent = Session.search(
            [("user_id", "=", uid)],
            order="create_date desc",
            limit=_RECENT_LIMIT,
        )

        profile = request.env["language.user.profile"].sudo().search(
            [("user_id", "=", uid)], limit=1
        )
        default_lang = "en"
        if profile and profile.learning_languages:
            default_lang = profile.learning_languages[0].code

        return request.render(
            "language_portal.portal_speaking_index",
            {
                "recent_sessions": recent,
                "languages": _DEFAULT_LANGUAGES,
                "default_lang": default_lang,
                "page_name": "speaking",
            },
        )

    # ------------------------------------------------------------------
    # GET /my/speaking/<id> — session detail
    # ------------------------------------------------------------------

    @http.route("/my/speaking/<int:session_id>", type="http",
                auth="user", website=True, methods=["GET"])
    def speaking_detail(self, session_id, **kw):
        Session = request.env["language.speaking.session"]
        session = Session.browse(session_id).exists()
        if not session or session.user_id.id != request.env.user.id:
            return request.not_found()

        return request.render(
            "language_portal.portal_speaking_detail",
            {
                "session": session,
                "corrections": session._corrections_list(),
                "synonyms": session._synonyms_list(),
                "page_name": "speaking",
            },
        )

    # ------------------------------------------------------------------
    # POST /my/speaking/topic — JSON-RPC, proxies to LLM /generate-topic
    # ------------------------------------------------------------------

    @http.route("/my/speaking/topic", type="json", auth="user", methods=["POST"])
    def speaking_topic(self, language="en", **kw):
        lang = (language or "en").lower()
        if lang not in _VALID_LANGS:
            lang = "en"

        try:
            resp = _requests.post(
                f"{_LLM_SVC}/generate-topic",
                json={"language": lang},
                timeout=_LLM_TIMEOUT,
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception as exc:
            _logger.error("speaking_topic LLM call failed: %s", exc)
            return {"status": "error", "message": str(exc), "topic": ""}

        return {
            "status": data.get("status", "ok"),
            "topic": (data.get("topic") or "").strip(),
            "language": lang,
        }

    # ------------------------------------------------------------------
    # POST /my/speaking/transcribe — multipart upload, proxies to audio
    # service, creates language.speaking.session
    # ------------------------------------------------------------------

    @http.route("/my/speaking/transcribe", type="http", auth="user",
                methods=["POST"], csrf=False)
    def speaking_transcribe(self, audio=None, language="en", topic="", **kw):
        """Receive recording, transcribe via audio service, persist session.

        Returns JSON: {status, session_id, transcript, duration, language, error?}
        """
        Session = request.env["language.speaking.session"].sudo()

        lang = (language or "en").lower()
        if lang not in _VALID_LANGS:
            lang = "en"

        if not audio or not hasattr(audio, "read"):
            return request.make_json_response(
                {"status": "error", "message": "No audio file received."}, status=400)

        audio_bytes = audio.read()
        if not audio_bytes:
            return request.make_json_response(
                {"status": "error", "message": "Empty audio upload."}, status=400)

        # Pre-create the session in 'transcribing' state so a failure mid-flow
        # leaves a row the user can see + retry.
        session = Session.create_for_user(
            user_id=request.env.user.id,
            target_language=lang,
            topic=(topic or "").strip()[:500],
        )
        session.sudo().write({"status": "transcribing"})

        # Send to audio-service /transcribe-sync
        try:
            files = {"audio": (
                getattr(audio, "filename", "speech.webm") or "speech.webm",
                audio_bytes,
                getattr(audio, "content_type", None) or "audio/webm",
            )}
            data = {"language": lang}
            resp = _requests.post(
                f"{_AUDIO_SVC}/transcribe-sync",
                files=files,
                data=data,
                timeout=_AUDIO_TIMEOUT,
            )
        except Exception as exc:
            _logger.error("speaking_transcribe audio call failed: %s", exc)
            session.mark_failed(f"transcribe call failed: {exc}")
            return request.make_json_response(
                {"status": "error", "session_id": session.id, "message": str(exc)},
                status=502,
            )

        if resp.status_code != 200:
            err = resp.text[:200]
            _logger.error(
                "speaking_transcribe audio HTTP %s: %s", resp.status_code, err)
            session.mark_failed(f"audio service HTTP {resp.status_code}: {err}")
            return request.make_json_response(
                {"status": "error", "session_id": session.id,
                 "message": err, "http_status": resp.status_code},
                status=resp.status_code,
            )

        try:
            payload = resp.json()
        except Exception as exc:
            session.mark_failed(f"audio service returned non-JSON: {exc}")
            return request.make_json_response(
                {"status": "error", "session_id": session.id,
                 "message": "Audio service returned non-JSON response."}, status=502,
            )

        transcript = (payload.get("transcript") or "").strip()
        duration = float(payload.get("duration") or 0.0)
        detected_lang = payload.get("language") or lang

        # Persist transcript and flip status → analyzing
        session.write_transcript(transcript, duration=duration)

        # Best-effort: stash the audio as a private ir.attachment on the session
        try:
            attachment = request.env["ir.attachment"].sudo().create({
                "name": f"speaking-{session.id}.webm",
                "datas": base64.b64encode(audio_bytes),
                "res_model": "language.speaking.session",
                "res_id": session.id,
                "mimetype": getattr(audio, "content_type", None) or "audio/webm",
                "public": False,
            })
            session.sudo().write({"audio_attachment_id": attachment.id})
        except Exception as exc:
            _logger.warning("Could not persist audio attachment: %s", exc)

        return request.make_json_response({
            "status": "ok",
            "session_id": session.id,
            "transcript": transcript,
            "duration": duration,
            "language": detected_lang,
        })

    # ------------------------------------------------------------------
    # POST /my/speaking/analyze — JSON-RPC, proxies to LLM /analyze-speech
    # ------------------------------------------------------------------

    @http.route("/my/speaking/analyze", type="json", auth="user", methods=["POST"])
    def speaking_analyze(self, session_id=None, **kw):
        if not session_id:
            return {"status": "error", "message": "session_id required"}

        Session = request.env["language.speaking.session"]
        session = Session.browse(int(session_id)).exists()
        if not session or session.user_id.id != request.env.user.id:
            raise AccessError("Session not found.")

        if not session.transcript:
            return {"status": "error", "message": "No transcript to analyze."}

        try:
            resp = _requests.post(
                f"{_LLM_SVC}/analyze-speech",
                json={
                    "transcript": session.transcript,
                    "language": session.target_language,
                    "topic": session.topic or "",
                },
                timeout=_LLM_TIMEOUT,
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception as exc:
            _logger.error("speaking_analyze LLM call failed: %s", exc)
            session.mark_failed(f"analyze call failed: {exc}")
            return {"status": "error", "session_id": session.id, "message": str(exc)}

        corrections = data.get("corrections") or []
        synonyms = data.get("synonyms") or []
        improved = data.get("improved") or session.transcript

        session.write_feedback(corrections, synonyms, improved)

        return {
            "status": "ok",
            "session_id": session.id,
            "corrections": corrections,
            "synonyms": synonyms,
            "improved": improved,
            "parse_error": bool(data.get("parse_error")),
        }
