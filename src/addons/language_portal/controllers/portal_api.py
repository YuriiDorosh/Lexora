import json
import logging
import os

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)

_ALLOWED_LANGUAGES = ('en', 'uk', 'el')
_MAX_WORD_LEN = 500
_MAX_CONTEXT_LEN = 2000
_MAX_URL_LEN = 2048
_TRANSLATION_SVC = os.environ.get('TRANSLATION_SERVICE_URL', 'http://translation-service:8000')


def _cors_headers():
    # Reflect the request Origin back — required when credentials are included.
    # Browsers reject the wildcard + credentials combination (CORS spec §7.1.5).
    # X-Lexora-Session-Id is the custom header used for the manual session bridge.
    origin = request.httprequest.headers.get('Origin', '')
    return {
        'Access-Control-Allow-Origin': origin or '*',
        'Access-Control-Allow-Headers': 'Content-Type, Cookie, X-Lexora-Session-Id',
        'Access-Control-Allow-Credentials': 'true',
        'Vary': 'Origin',
    }


def _json_response(data, status=200):
    headers = list(_cors_headers().items()) + [('Content-Type', 'application/json')]
    return request.make_response(json.dumps(data), headers=headers, status=status)


def _resolve_uid():
    """Return the authenticated uid, trying two paths:

    1. Standard session cookie (works when SameSite allows it).
    2. X-Lexora-Session-Id header (manual bridge for Chrome extensions where
       SameSite=Lax blocks the cookie on cross-origin HTTP requests).

    The header value is the raw Odoo session_id cookie value read by the
    extension via chrome.cookies API and forwarded as a custom header,
    bypassing SameSite restrictions entirely.
    """
    # Path 1 — cookie arrived normally
    uid = request.session.uid
    if uid:
        return uid

    # Path 2 — custom header bridge
    sid = request.httprequest.headers.get('X-Lexora-Session-Id', '').strip()
    if sid:
        try:
            session = http.root.session_store.get(sid)
            if session and session.get('uid'):
                return session['uid']
        except Exception:
            _logger.debug('X-Lexora-Session-Id lookup failed for sid=%r', sid[:8])

    return None


def _require_session():
    """Return a 401 JSON response if no valid uid can be resolved, else None."""
    if not _resolve_uid():
        return _json_response(
            {'status': 'unauthorized', 'message': 'Session expired. Please log in to Lexora.'},
            status=401,
        )
    return None


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
    # GET /lexora_api/whoami  — lightweight auth probe for the extension
    # ------------------------------------------------------------------
    @http.route('/lexora_api/whoami', type='http', auth='none',
                methods=['GET'], csrf=False)
    def whoami(self, **kw):
        """Return minimal user info so the popup can confirm the session is valid."""
        err = _require_session()
        if err:
            return err
        user = request.env['res.users'].sudo().browse(_resolve_uid())
        return _json_response({
            'status': 'ok',
            'uid': user.id,
            'name': user.name,
            'login': user.login,
        })

    # ------------------------------------------------------------------
    # POST /lexora_api/add_word
    # ------------------------------------------------------------------
    @http.route('/lexora_api/add_word', type='http', auth='none',
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
            {"status": "unauthorized", "message": "..."}
            {"status": "error",     "message": "..."}
        """
        err = _require_session()
        if err:
            return err

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

        uid = _resolve_uid()
        env = request.env(user=uid)
        user = env['res.users'].browse(uid)

        if not source_language:
            source_language = _detect_language(word, user)

        vals = {
            'source_text': word,
            'source_language': source_language,
            'owner_id': uid,
            'created_from': 'manual',
            'type': 'word',
        }
        if context_sentence and 'note' in env['language.entry']._fields:
            vals['note'] = context_sentence

        try:
            entry = env['language.entry'].sudo().create(vals)
        except Exception as exc:
            # Dedup — find the existing record and return it
            try:
                from odoo.addons.language_words.models.language_entry import normalize
                normalized = normalize(word)
                existing = env['language.entry'].sudo().search([
                    ('normalized_text', '=', normalized),
                    ('source_language', '=', source_language),
                    ('owner_id', '=', uid),
                ], limit=1)
                entry_id = existing.id if existing else None
                _logger.info('Extension add_word: duplicate for user=%s word=%r', user.login, word)
                return _json_response({'status': 'duplicate', 'entry_id': entry_id, 'duplicate': True})
            except Exception:
                _logger.exception('Extension add_word: unexpected error: %s', exc)
                return _json_response({'status': 'error', 'message': str(exc)}, 500)

        if translation and 'language.translation' in request.env.registry:
            _store_supplied_translation(env, entry, translation, source_language)

        _logger.info('Extension add_word: created entry id=%s word=%r user=%s',
                     entry.id, word, user.login)
        return _json_response({'status': 'ok', 'entry_id': entry.id, 'duplicate': False})

    # ------------------------------------------------------------------
    # GET /lexora_api/daily_card  (M25 — New Tab)
    # ------------------------------------------------------------------
    @http.route('/lexora_api/daily_card', type='http', auth='none',
                methods=['GET'], csrf=False)
    def daily_card(self, **kw):
        """Return a random idiom for the New Tab override (M25)."""
        err = _require_session()
        if err:
            return err
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
    @http.route('/lexora_api/define', type='http', auth='none',
                methods=['GET'], csrf=False)
    def define(self, word='', lang='en', **kw):
        """Return the best stored translations for a word (M24 subtitle overlay).

        Search priority:
          1. Caller's own vocabulary entries matching the subtitle language
          2. Shared entries from other users matching the subtitle language
          3. Fallback: caller's own entries regardless of source_language
             (handles cases where the subtitle lang tag doesn't match how
              the word was stored, e.g. auto-detected vs. manually set)

        Always returns {"status": "ok", "translations": [...]} — never an error
        for a missing word, so the overlay always shows the Add-to-Vocabulary button.
        """
        err = _require_session()
        if err:
            return err

        word = (word or '').strip()
        if not word:
            return _json_response({'status': 'error', 'message': 'word required'}, 400)

        if 'language.translation' not in request.env.registry:
            return _json_response({'status': 'ok', 'word': word, 'translations': []})

        uid = _resolve_uid()
        lang = (lang or 'en').strip().lower()
        if lang not in ('en', 'uk', 'el'):
            lang = 'en'

        try:
            from odoo.addons.language_words.models.language_entry import normalize
            normalized = normalize(word)
        except Exception:
            normalized = word.strip().lower()

        Entry = request.env['language.entry'].sudo()

        # Priority 1 — caller's own entries matching subtitle language
        own_entries = Entry.search([
            ('normalized_text', '=', normalized),
            ('source_language', '=', lang),
            ('owner_id', '=', uid),
        ], limit=3)

        # Priority 2 — shared entries matching subtitle language
        shared_entries = Entry.search([
            ('normalized_text', '=', normalized),
            ('source_language', '=', lang),
            ('is_shared', '=', True),
            ('owner_id', '!=', uid),
        ], limit=3)

        all_entries = own_entries + shared_entries

        # Priority 3 — caller's own entries regardless of source_language.
        # Catches words stored under a different lang code than the subtitle
        # (e.g. word stored as 'en' but subtitle lang reported as 'uk').
        if not all_entries:
            all_entries = Entry.search([
                ('normalized_text', '=', normalized),
                ('owner_id', '=', uid),
            ], limit=3)

        seen_langs = set()
        translations = []
        for entry in all_entries:
            for tr in entry.translation_ids.filtered(lambda t: t.status == 'completed'):
                if tr.target_language not in seen_langs:
                    seen_langs.add(tr.target_language)
                    translations.append({
                        'target_language': tr.target_language,
                        'translated_text': tr.translated_text,
                    })

        live = False
        if not translations:
            _logger.info('define: no DB translations for word=%r lang=%s uid=%s — attempting live translate',
                         word, lang, uid)
            live_results = _live_translate(word, lang, uid, request.env)
            if live_results:
                translations = live_results
                live = True
                _logger.info('define: live translate succeeded for word=%r → %d result(s)', word, len(live_results))
            else:
                _logger.info('define: live translate returned no results for word=%r lang=%s', word, lang)

        _logger.info('define word=%r lang=%s uid=%s → %d translation(s) live=%s',
                     word, lang, uid, len(translations), live)
        return _json_response({'status': 'ok', 'word': word, 'translations': translations, 'live': live})

    # ------------------------------------------------------------------
    # POST /lexora_api/quick_explain  (M25 — Quick Explain popup)
    # ------------------------------------------------------------------
    @http.route('/lexora_api/quick_explain', type='http', auth='none',
                methods=['POST'], csrf=False)
    def quick_explain(self, **kw):
        """Trigger or return cached enrichment for a word (M25 Quick Explain)."""
        err = _require_session()
        if err:
            return err

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

        uid = _resolve_uid()
        from odoo.addons.language_words.models.language_entry import normalize
        normalized = normalize(word)
        entry = request.env['language.entry'].sudo().search([
            ('normalized_text', '=', normalized),
            ('source_language', '=', source_language),
            ('owner_id', '=', uid),
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

        if not enrichment or enrichment.status == 'failed':
            request.env['language.enrichment'].sudo()._enqueue_single(entry, source_language)
            return _json_response({'status': 'pending',
                                   'message': 'Enrichment started, check back in ~30s'})

        return _json_response({'status': 'pending', 'message': 'Enrichment in progress'})


# -------------------------------------------------------------------------
# Helpers
# -------------------------------------------------------------------------

def _detect_language(word, user):
    """Try langdetect; fall back to user profile default; final fallback 'en'."""
    profile = None
    try:
        profile = user.env['language.user.profile'].sudo().search(
            [('user_id', '=', user.id)], limit=1)
    except Exception:
        pass

    try:
        from langdetect import detect, DetectorFactory
        DetectorFactory.seed = 0
        code = detect(word)
        if code in _ALLOWED_LANGUAGES:
            return code
    except Exception:
        pass

    if profile and profile.default_source_language:
        return profile.default_source_language
    return 'en'


def _live_translate(word, source_lang, uid, env):
    """Call the translation service synchronously for up to 2 target languages.

    Returns a list of {target_language, translated_text} dicts.
    Results are NOT stored in the DB — the caller receives them as ephemeral
    "live" translations and the user can persist them via Add to Vocabulary.
    """
    import requests as _req

    # Determine target languages from user profile; fall back to all non-source
    target_langs = []
    try:
        profile = env['language.user.profile'].sudo().search(
            [('user_id', '=', uid)], limit=1)
        if profile and profile.learning_languages:
            target_langs = [l.code for l in profile.learning_languages
                            if l.code != source_lang]
    except Exception:
        pass

    if not target_langs:
        target_langs = [l for l in _ALLOWED_LANGUAGES if l != source_lang]

    results = []
    for tgt in target_langs[:2]:  # cap at 2 to keep p50 latency under 2 s
        try:
            _logger.info('_live_translate calling %s/translate — %s→%s word=%r',
                         _TRANSLATION_SVC, source_lang, tgt, word)
            resp = _req.post(
                f'{_TRANSLATION_SVC}/translate',
                json={'text': word, 'source': source_lang, 'target': tgt},
                timeout=8,
            )
            data = resp.json()
            _logger.info('_live_translate %s→%s HTTP %s data=%r', source_lang, tgt, resp.status_code, data)
            if data.get('status') == 'ok' and data.get('result'):
                results.append({
                    'target_language': tgt,
                    'translated_text': data['result'],
                })
        except Exception as exc:
            _logger.warning('_live_translate %s→%s FAILED (%s: %s) — svc=%s',
                            source_lang, tgt, type(exc).__name__, exc, _TRANSLATION_SVC)

    return results


def _store_supplied_translation(env, entry, translation_text, source_language):
    """Create a completed translation record for a user-supplied translation."""
    import uuid
    Translation = env['language.translation'].sudo()
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
                    Translation.create({
                        'entry_id': entry.id,
                        'target_language': lang.code,
                        'translated_text': translation_text,
                        'status': 'completed',
                        'job_id': str(uuid.uuid4()),
                    })
                break
