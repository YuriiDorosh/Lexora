import json
import logging

from odoo import http
from odoo.exceptions import ValidationError
from odoo.http import request

_logger = logging.getLogger(__name__)

_ALLOWED_LANGUAGES = ('en', 'uk', 'el')
_MAX_WORD_LEN = 500
_MAX_CONTEXT_LEN = 2000
_MAX_URL_LEN = 2048


def _cors_headers():
    return {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type, Cookie',
        'Access-Control-Allow-Credentials': 'true',
    }


def _json_response(data, status=200):
    headers = list(_cors_headers().items()) + [('Content-Type', 'application/json')]
    return request.make_response(json.dumps(data), headers=headers, status=status)


class LexoraApiController(http.Controller):

    # ------------------------------------------------------------------
    # OPTIONS preflight — needed for Chrome Extension cross-origin calls
    # ------------------------------------------------------------------
    @http.route('/lexora_api/<path:subpath>', type='http', auth='none',
                methods=['OPTIONS'], csrf=False)
    def api_preflight(self, subpath, **kw):
        headers = list(_cors_headers().items()) + [
            ('Access-Control-Allow-Methods', 'GET, POST, OPTIONS'),
        ]
        return request.make_response('', headers=headers, status=204)

    # ------------------------------------------------------------------
    # POST /lexora_api/add_word
    # ------------------------------------------------------------------
    @http.route('/lexora_api/add_word', type='http', auth='user',
                methods=['POST'], csrf=False)
    def add_word(self, **kw):
        """Add a word to the current user's vocabulary from the browser extension.

        Request body (JSON):
            word              (str, required)  — the source text
            source_language   (str, optional)  — en / uk / el (auto-detected if omitted)
            translation       (str, optional)  — user-supplied translation
            context_sentence  (str, optional)  — surrounding sentence for Sentence Builder
            source_url        (str, optional)  — originating page URL

        Response:
            {"status": "ok",        "entry_id": N, "duplicate": false}
            {"status": "duplicate", "entry_id": N, "duplicate": true}
            {"status": "error",     "message": "..."}
        """
        try:
            raw = request.httprequest.get_data(as_text=True)
            data = json.loads(raw) if raw else {}
        except (ValueError, UnicodeDecodeError):
            data = {}

        # Also accept form-encoded fallback
        data = {**request.params, **data}

        word = (data.get('word') or '').strip()
        if not word:
            return _json_response({'status': 'error', 'message': 'word is required'}, 400)
        if len(word) > _MAX_WORD_LEN:
            return _json_response(
                {'status': 'error', 'message': f'word exceeds {_MAX_WORD_LEN} characters'}, 400)

        source_language = (data.get('source_language') or '').strip().lower()
        if source_language and source_language not in _ALLOWED_LANGUAGES:
            return _json_response(
                {'status': 'error',
                 'message': f'source_language must be one of {_ALLOWED_LANGUAGES}'}, 400)

        translation = (data.get('translation') or '').strip() or None
        context_sentence = (data.get('context_sentence') or '').strip()[:_MAX_CONTEXT_LEN] or None
        source_url = (data.get('source_url') or '').strip()[:_MAX_URL_LEN] or None

        # Auto-detect language if not provided
        if not source_language:
            source_language = _detect_language(word, request.env.user)

        user = request.env.user

        # Build entry vals
        vals = {
            'source_text': word,
            'source_language': source_language,
            'owner_id': user.id,
            'created_from': 'manual',
            'type': 'word',
        }
        if context_sentence:
            # Store context in the notes field if present, otherwise ignore gracefully
            if 'note' in request.env['language.entry']._fields:
                vals['note'] = context_sentence

        try:
            entry = request.env['language.entry'].sudo().with_context(
                uid=user.id
            ).create(vals)
        except ValidationError:
            # Dedup — find the existing record and return it
            from odoo.addons.language_words.models.language_entry import normalize
            normalized = normalize(word)
            existing = request.env['language.entry'].sudo().search([
                ('normalized_text', '=', normalized),
                ('source_language', '=', source_language),
                ('owner_id', '=', user.id),
            ], limit=1)
            entry_id = existing.id if existing else None
            _logger.info('Extension add_word: duplicate detected for user=%s word=%r', user.login, word)
            return _json_response({'status': 'duplicate', 'entry_id': entry_id, 'duplicate': True})

        # Persist a user-supplied translation immediately (bypass async queue)
        if translation and 'language.translation' in request.env.registry:
            _store_supplied_translation(request.env, entry, translation, source_language)

        _logger.info('Extension add_word: created entry id=%s word=%r user=%s', entry.id, word, user.login)
        return _json_response({'status': 'ok', 'entry_id': entry.id, 'duplicate': False})

    # ------------------------------------------------------------------
    # GET /lexora_api/daily_card  (M25 — New Tab)
    # ------------------------------------------------------------------
    @http.route('/lexora_api/daily_card', type='http', auth='user',
                methods=['GET'], csrf=False)
    def daily_card(self, **kw):
        """Return a random idiom for the New Tab override (M25)."""
        import random
        if 'language.idiom' in request.env.registry:
            idioms = request.env['language.idiom'].sudo().search([], limit=50)
            if idioms:
                idiom = random.choice(idioms)
                return _json_response({
                    'type': 'idiom',
                    'expression': idiom.expression,
                    'literal_meaning': idiom.literal_meaning,
                    'idiomatic_meaning': idiom.idiomatic_meaning,
                    'example_sentence': idiom.example_sentence,
                    'language': idiom.language,
                })
        return _json_response({'type': 'none'})

    # ------------------------------------------------------------------
    # GET /lexora_api/define  (M24 — Subtitles overlay)
    # ------------------------------------------------------------------
    @http.route('/lexora_api/define', type='http', auth='user',
                methods=['GET'], csrf=False)
    def define(self, word='', lang='en', **kw):
        """Return the best stored translation for a word (M24 subtitle overlay)."""
        word = word.strip()
        if not word:
            return _json_response({'status': 'error', 'message': 'word required'}, 400)

        if 'language.translation' not in request.env.registry:
            return _json_response({'status': 'ok', 'definition': None})

        from odoo.addons.language_words.models.language_entry import normalize
        normalized = normalize(word)
        entries = request.env['language.entry'].sudo().search([
            ('normalized_text', '=', normalized),
            ('source_language', '=', lang),
        ], limit=5)

        translations = []
        for entry in entries:
            for tr in entry.translation_ids.filtered(lambda t: t.status == 'completed'):
                translations.append({
                    'target_language': tr.target_language,
                    'translated_text': tr.translated_text,
                })
        return _json_response({'status': 'ok', 'word': word, 'translations': translations})

    # ------------------------------------------------------------------
    # POST /lexora_api/quick_explain  (M25 — Quick Explain popup)
    # ------------------------------------------------------------------
    @http.route('/lexora_api/quick_explain', type='http', auth='user',
                methods=['POST'], csrf=False)
    def quick_explain(self, **kw):
        """Trigger or return cached enrichment for a word (M25 Quick Explain)."""
        try:
            raw = request.httprequest.get_data(as_text=True)
            data = json.loads(raw) if raw else {}
        except (ValueError, UnicodeDecodeError):
            data = {}
        data = {**request.params, **data}

        word = (data.get('word') or '').strip()
        source_language = (data.get('source_language') or 'en').strip()

        if not word:
            return _json_response({'status': 'error', 'message': 'word required'}, 400)

        if 'language.enrichment' not in request.env.registry:
            return _json_response({'status': 'unavailable'})

        from odoo.addons.language_words.models.language_entry import normalize
        normalized = normalize(word)
        entry = request.env['language.entry'].sudo().search([
            ('normalized_text', '=', normalized),
            ('source_language', '=', source_language),
            ('owner_id', '=', request.env.user.id),
        ], limit=1)

        if not entry:
            return _json_response({'status': 'not_found',
                                   'message': 'Add this word to your vocabulary first'})

        enrichment = request.env['language.enrichment'].sudo().search([
            ('entry_id', '=', entry.id),
            ('language', '=', source_language),
        ], limit=1)

        if enrichment and enrichment.status == 'completed':
            return _json_response({
                'status': 'ok',
                'synonyms': enrichment._synonyms_list(),
                'antonyms': enrichment._antonyms_list(),
                'explanation': enrichment.explanation,
            })

        # Trigger async enrichment if not already in flight
        if not enrichment or enrichment.status == 'failed':
            if 'language.enrichment' in request.env.registry:
                request.env['language.enrichment'].sudo()._enqueue_single(
                    entry, source_language)
            return _json_response({'status': 'pending',
                                   'message': 'Enrichment started, check back in ~30s'})

        return _json_response({'status': 'pending',
                               'message': 'Enrichment in progress'})


# -------------------------------------------------------------------------
# Helpers
# -------------------------------------------------------------------------

def _detect_language(word, user):
    """Try langdetect; fall back to user profile default; final fallback 'en'."""
    profile = None
    try:
        from odoo.addons.language_words.models.language_user_profile import LanguageUserProfile  # noqa
        profile = user.env['language.user.profile'].sudo().search(
            [('user_id', '=', user.id)], limit=1)
    except Exception:
        pass

    try:
        from langdetect import detect, DetectorFactory, LangDetectException
        DetectorFactory.seed = 0
        code = detect(word)
        if code in _ALLOWED_LANGUAGES:
            return code
    except Exception:
        pass

    if profile and profile.default_source_language:
        return profile.default_source_language
    return 'en'


def _store_supplied_translation(env, entry, translation_text, source_language):
    """Create a completed translation record for a user-supplied translation."""
    Translation = env['language.translation'].sudo()
    # Pick the first learning language that isn't the source language as target
    profile = env['language.user.profile'].sudo().search(
        [('user_id', '=', entry.owner_id.id)], limit=1)
    if profile and profile.learning_languages:
        for lang in profile.learning_languages:
            if lang.code != source_language:
                existing = Translation.search([
                    ('entry_id', '=', entry.id),
                    ('target_language', '=', lang.code),
                ], limit=1)
                if not existing:
                    import uuid
                    Translation.create({
                        'entry_id': entry.id,
                        'target_language': lang.code,
                        'translated_text': translation_text,
                        'status': 'completed',
                        'job_id': str(uuid.uuid4()),
                    })
                break
