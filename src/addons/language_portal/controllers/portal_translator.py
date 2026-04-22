"""
Lexora Translator Tool — M15.

Routes:
  GET  /translator                   — interactive translator page (public)
  POST /translator/translate         — JSON: call translation service sync API
  POST /translator/add               — JSON: save entry + translation to vocabulary (auth)
"""

import logging
import os

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)

TRANSLATION_SVC = os.environ.get("TRANSLATION_SERVICE_URL", "http://translation-service:8000")

LANG_NAMES = {"en": "English", "uk": "Ukrainian", "el": "Greek"}
LANG_FLAGS = {"en": "🇬🇧", "uk": "🇺🇦", "el": "🇬🇷"}


class TranslatorController(http.Controller):

    # ------------------------------------------------------------------
    # Page
    # ------------------------------------------------------------------

    @http.route("/translator", type="http", auth="public", website=True)
    def translator_page(self, src="en", tgt="uk", **kw):
        return request.render(
            "language_portal.portal_translator",
            {
                "lang_names": LANG_NAMES,
                "lang_flags": LANG_FLAGS,
                "default_src": src if src in LANG_NAMES else "en",
                "default_tgt": tgt if tgt in LANG_NAMES else "uk",
                "is_public": request.env.user._is_public(),
            },
        )

    # ------------------------------------------------------------------
    # Translate (AJAX POST, public)
    # ------------------------------------------------------------------

    @http.route(
        "/translator/translate",
        type="http",
        auth="public",
        methods=["POST"],
        website=True,
        csrf=False,
    )
    def do_translate(self, text="", source_lang="en", target_lang="uk", **kw):
        import requests as _req  # stdlib requests available in Odoo container

        text = (text or "").strip()
        if not text:
            return request.make_json_response({"status": "error", "message": "Empty input"})
        if source_lang == target_lang:
            return request.make_json_response({"status": "ok", "result": text})

        try:
            resp = _req.post(
                f"{TRANSLATION_SVC}/translate",
                json={"text": text, "source": source_lang, "target": target_lang},
                timeout=20,
            )
            data = resp.json()
            if data.get("status") == "ok":
                return request.make_json_response({"status": "ok", "result": data["result"]})
            return request.make_json_response(
                {"status": "error", "message": data.get("message", "Translation failed")}
            )
        except Exception as exc:
            _logger.warning("Translator call to %s failed: %s", TRANSLATION_SVC, exc)
            return request.make_json_response({"status": "error", "message": str(exc)})

    # ------------------------------------------------------------------
    # Add to Vocabulary (auth required)
    # ------------------------------------------------------------------

    @http.route(
        "/translator/add",
        type="http",
        auth="user",
        methods=["POST"],
        website=True,
    )
    def add_to_vocabulary(
        self, text="", translation="", source_lang="en", target_lang="uk", **kw
    ):
        text = (text or "").strip()
        translation = (translation or "").strip()
        if not text:
            return request.make_json_response({"status": "error", "message": "No text"})

        user = request.env.user
        Entry = request.env["language.entry"]
        Trans = request.env["language.translation"]

        try:
            entry = Entry.sudo().create(
                {
                    "source_text": text,
                    "source_language": source_lang,
                    "owner_id": user.id,
                    "created_from": "manual",
                }
            )
            if translation:
                Trans.sudo().create(
                    {
                        "entry_id": entry.id,
                        "target_language": target_lang,
                        "translated_text": translation,
                        "status": "completed",
                    }
                )
            return request.make_json_response(
                {"status": "ok", "entry_id": entry.id, "vocab_url": f"/my/vocabulary/{entry.id}"}
            )
        except Exception as exc:
            _logger.warning("Add to vocab failed: %s", exc)
            return request.make_json_response({"status": "error", "message": str(exc)})
