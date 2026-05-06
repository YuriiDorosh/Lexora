"""Portal controller for the AI Speaking Coach (M30, Step 1 — foundation).

This commit lands the GET /my/speaking page and stub POST routes.
Real LLM and audio-service calls land in M30 Steps 2-4. The stubs
return ``{"status": "pending"}`` so the JS layer can be wired up in
parallel with the service-side endpoints.
"""

import logging

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)

_DEFAULT_LANGUAGES = [
    ("en", "English"),
    ("uk", "Ukrainian"),
    ("el", "Greek"),
    ("pl", "Polish"),
]
_RECENT_LIMIT = 10


class SpeakingPortal(http.Controller):
    # ------------------------------------------------------------------
    # GET /my/speaking — main page
    # ------------------------------------------------------------------

    @http.route("/my/speaking", type="http", auth="user", website=True, methods=["GET"])
    def speaking_index(self, **kw):
        """Render the Speaking Coach landing page."""
        Session = request.env["language.speaking.session"].sudo()
        uid = request.env.user.id

        recent = Session.search(
            [("user_id", "=", uid)],
            order="create_date desc",
            limit=_RECENT_LIMIT,
        )

        # Profile lookup — pre-select the user's first learning language if set.
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
    # Stub POST routes — full bodies land in Steps 2-4.
    # ------------------------------------------------------------------

    @http.route("/my/speaking/topic", type="json", auth="user", methods=["POST"])
    def speaking_topic(self, language="en", **kw):
        """Stub: returns a placeholder topic until LLM /generate-topic ships."""
        return {
            "status": "pending",
            "topic": "",
            "message": "Topic generation lands in M30 Step 2.",
            "language": language,
        }

    @http.route("/my/speaking/transcribe", type="http", auth="user",
                methods=["POST"], csrf=False)
    def speaking_transcribe(self, **kw):
        """Stub: full multipart upload + audio-service round-trip in Step 4."""
        return request.make_json_response(
            {
                "status": "pending",
                "message": "Transcription endpoint lands in M30 Step 4.",
            }
        )

    @http.route("/my/speaking/analyze", type="json", auth="user", methods=["POST"])
    def speaking_analyze(self, session_id=None, **kw):
        """Stub: real LLM /analyze-speech proxy in Step 4."""
        return {
            "status": "pending",
            "session_id": session_id,
            "message": "Analysis endpoint lands in M30 Step 4.",
        }
