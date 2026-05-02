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
_TRANSLATION_SVC = os.environ.get('TRANSLATION_SERVICE_URL', 'http://translation-service:8000').rstrip('/')
_LLM_SVC = os.environ.get('LLM_SERVICE_URL', 'http://llm-service:8000').rstrip('/')


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
    @http.route(['/lexora_api/<path:subpath>'], type='http', auth='none',
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
        """Return a random card for the New Tab override.

        Priority:
          1. A random vocabulary entry owned by the user that has at least
             one completed translation (shows real learning progress).
          2. A random published idiom (M19 model) — fallback when the user
             has no vocabulary yet.
          3. Empty response (type='none') when neither is available.
        """
        err = _require_session()
        if err:
            return err

        import random
        uid = _resolve_uid()

        # ── Priority 1: user's own vocabulary with translations ────────
        if ('language.entry' in request.env.registry and
                'language.translation' in request.env.registry):
            entries = request.env['language.entry'].sudo().search([
                ('owner_id', '=', uid),
                ('status', '=', 'active'),
            ], limit=100)

            eligible = [
                e for e in entries
                if any(t.status == 'completed' for t in e.translation_ids)
            ]

            if eligible:
                entry = random.choice(eligible)
                translations = [
                    {'target_language': t.target_language,
                     'translated_text': t.translated_text}
                    for t in entry.translation_ids
                    if t.status == 'completed'
                ]

                # Best example sentence from enrichment (if available)
                example = ''
                if 'language.enrichment' in request.env.registry:
                    enrichment = request.env['language.enrichment'].sudo().search([
                        ('entry_id', '=', entry.id),
                        ('status', '=', 'completed'),
                    ], limit=1)
                    if enrichment:
                        sentences = enrichment._example_sentences_list()
                        if sentences:
                            example = sentences[0]

                return _json_response({
                    'type': 'vocabulary',
                    'word': entry.source_text,
                    'source_language': entry.source_language,
                    'translations': translations,
                    'example_sentence': example,
                    'entry_id': entry.id,
                })

        # ── Priority 2: random idiom ───────────────────────────────────
        if 'language.idiom' in request.env.registry:
            idioms = request.env['language.idiom'].sudo().search([], limit=100)
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
    @http.route(['/lexora_api/define', '/lexora_api/define_v2'], type='http', auth='none',
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
        # ── CANARY ── must appear in Odoo logs on EVERY call (routes: /define + /define_v2).
        # If ABSENT after module reload, Odoo is still running old bytecode.
        # Fix: --update language_portal --stop-after-init && docker restart odoo
        _logger.error('CANARY define CALLED — word=%r lang=%r svc=%s path=%s',
                      word, lang, _TRANSLATION_SVC,
                      request.httprequest.path)

        # Connectivity probe — shows in logs whether the translation service is reachable
        try:
            import requests as _req_probe
            _probe = _req_probe.get(f'{_TRANSLATION_SVC}/health', timeout=3)
            _logger.error('CANARY translation-svc /health → HTTP %s body=%r',
                          _probe.status_code, _probe.text[:120])
        except Exception as _probe_exc:
            _logger.error('CANARY translation-svc /health UNREACHABLE: %s — svc=%s',
                          _probe_exc, _TRANSLATION_SVC)

        err = _require_session()
        if err:
            _logger.error('CANARY define — session check FAILED (unauthorized), returning 401')
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
        _logger.error('CANARY /define — DB lookup done: found %d entry(ies), %d translation(s) for word=%r',
                      len(all_entries), len(translations), word)

        if not translations:
            _logger.error('CANARY /define — NO DB translations for word=%r lang=%s uid=%s'
                          ' — calling _live_translate now', word, lang, uid)
            live_results = _live_translate(word, lang, uid, request.env)
            if live_results:
                translations = live_results
                live = True
                _logger.error('CANARY /define — live translate SUCCEEDED for word=%r → %d result(s)',
                               word, len(live_results))
            else:
                _logger.error('CANARY /define — live translate returned NOTHING for word=%r lang=%s'
                               ' svc=%s — check translation-service logs', word, lang, _TRANSLATION_SVC)

        _logger.error('CANARY /define DONE — word=%r lang=%s uid=%s → %d translation(s) live=%s',
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


    # ------------------------------------------------------------------
    # GET /lexora_api/get_learned_words  (M27 — Review in the Wild)
    # ------------------------------------------------------------------
    @http.route('/lexora_api/get_learned_words', type='http', auth='none',
                methods=['GET'], csrf=False)
    def get_learned_words(self, **kw):
        """Return the user's vocabulary with SRS metadata for page highlighting.

        Response (≤500 entries, ordered by most-recently reviewed first):
            {
              "status": "ok",
              "words": [
                {
                  "id": 42,
                  "word": "ephemeral",
                  "normalized": "ephemeral",
                  "lang": "en",
                  "best_translation": "короткочасний",
                  "srs_state": "review",   // "new" | "learning" | "review" | null
                  "days_ago": 3            // null if never reviewed
                }
              ],
              "generated_at": 1746300000   // Unix timestamp for client-side TTL
            }

        The extension caches this response for 15 minutes in chrome.storage.local.
        Cache is invalidated when the user adds a word via the extension popup.
        """
        err = _require_session()
        if err:
            return err

        import time
        from datetime import date as _date

        uid = _resolve_uid()

        if 'language.entry' not in request.env.registry:
            return _json_response({'status': 'ok', 'words': [],
                                   'generated_at': int(time.time())})

        entries = request.env['language.entry'].sudo().search([
            ('owner_id', '=', uid),
            ('status', '=', 'active'),
        ], limit=500, order='write_date desc')

        # Build SRS lookup: entry_id → review record
        srs_map = {}
        if 'language.review' in request.env.registry:
            reviews = request.env['language.review'].sudo().search([
                ('user_id', '=', uid),
                ('entry_id', 'in', entries.ids),
            ])
            srs_map = {r.entry_id.id: r for r in reviews}

        # Build translation lookup: entry_id → first completed translated_text
        trans_map = {}
        if 'language.translation' in request.env.registry:
            translations = request.env['language.translation'].sudo().search([
                ('entry_id', 'in', entries.ids),
                ('status', '=', 'completed'),
            ], order='id asc')
            for t in translations:
                if t.entry_id.id not in trans_map:
                    trans_map[t.entry_id.id] = t.translated_text

        today = _date.today()
        words = []
        for entry in entries:
            review = srs_map.get(entry.id)
            srs_state = review.state if review else None
            days_ago = None
            if review and review.last_review_date:
                days_ago = (today - review.last_review_date.date()).days

            words.append({
                'id': entry.id,
                'word': entry.source_text,
                'normalized': entry.normalized_text or entry.source_text.lower(),
                'lang': entry.source_language,
                'best_translation': trans_map.get(entry.id) or '',
                'srs_state': srs_state,
                'days_ago': days_ago,
            })

        return _json_response({
            'status': 'ok',
            'words': words,
            'generated_at': int(time.time()),
        })

    # ------------------------------------------------------------------
    # POST /lexora_api/explain_grammar  (M28 — Grammar Explainer)
    # ------------------------------------------------------------------
    @http.route('/lexora_api/explain_grammar', type='http', auth='none',
                methods=['POST'], csrf=False)
    def explain_grammar(self, **kw):
        """Proxy a grammar explanation request to the LLM service.

        Request body (JSON):
            phrase    (str, required)  — the phrase or sentence to explain
            language  (str, optional)  — language hint: en / uk / el (default 'en')

        Response:
            {"status": "ok",          "explanation": "..."}
            {"status": "unavailable", "explanation": "LLM not ready — try again in 30s."}
            {"status": "error",       "message": "..."}

        The LLM service runs Qwen2.5-1.5B-Instruct locally. Expected latency on the
        target server (E5-2680 v2, AVX-only): 10–40 s. The extension should show
        a "Explaining…" state while waiting.
        """
        err = _require_session()
        if err:
            return err

        try:
            raw = request.httprequest.get_data(as_text=True)
            data = json.loads(raw) if raw else {}
        except (ValueError, UnicodeDecodeError):
            data = {}
        data = {**request.params, **data}

        phrase = (data.get('phrase') or '').strip()[:_MAX_WORD_LEN]
        if not phrase:
            return _json_response({'status': 'error', 'message': 'phrase is required'}, 400)

        language = (data.get('language') or 'en').strip().lower()
        if language not in _ALLOWED_LANGUAGES:
            language = 'en'

        try:
            import requests as _req
            resp = _req.post(
                f'{_LLM_SVC}/explain-grammar',
                json={'phrase': phrase, 'language': language},
                timeout=60,
            )
            resp.raise_for_status()
            result = json.loads(resp.content.decode('utf-8', errors='replace'))
            return _json_response(result)
        except Exception as exc:
            _logger.warning('explain_grammar proxy error: %s', exc)
            return _json_response({
                'status': 'unavailable',
                'explanation': 'LLM service unavailable — please try again shortly.',
            })


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

    translate_url = f'{_TRANSLATION_SVC}/translate'
    _logger.error('_live_translate ENTER — word=%r source=%s uid=%s url=%s',
                  word, source_lang, uid, translate_url)

    # Determine target languages from user profile; fall back to all non-source
    target_langs = []
    try:
        profile = env['language.user.profile'].sudo().search(
            [('user_id', '=', uid)], limit=1)
        if profile and profile.learning_languages:
            target_langs = [l.code for l in profile.learning_languages
                            if l.code != source_lang]
        _logger.error('_live_translate profile target_langs=%r', target_langs)
    except Exception as exc:
        _logger.error('_live_translate profile lookup FAILED: %s', exc)

    if not target_langs:
        target_langs = [l for l in _ALLOWED_LANGUAGES if l != source_lang]
        _logger.error('_live_translate fallback target_langs=%r', target_langs)

    results = []
    for tgt in target_langs[:2]:  # cap at 2 to keep p50 latency under 2 s
        try:
            _logger.error('_live_translate POST %s — %s→%s word=%r',
                          translate_url, source_lang, tgt, word)
            resp = _req.post(
                translate_url,
                json={'text': word, 'source': source_lang, 'target': tgt},
                timeout=8,
            )
            _logger.error('_live_translate %s→%s HTTP %s body=%r',
                          source_lang, tgt, resp.status_code, resp.text[:200])
            data = resp.json()
            if data.get('status') == 'ok' and data.get('result'):
                results.append({
                    'target_language': tgt,
                    'translated_text': data['result'],
                })
            else:
                _logger.error('_live_translate %s→%s unexpected response data=%r', source_lang, tgt, data)
        except Exception as exc:
            _logger.error('_live_translate %s→%s EXCEPTION %s: %s — url=%s',
                          source_lang, tgt, type(exc).__name__, exc, translate_url)

    if not results:
        _logger.error('_live_translate returned NOTHING for word=%r lang=%s — all attempts failed',
                      word, source_lang)

    _logger.error('_live_translate EXIT — word=%r → %d result(s)', word, len(results))
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
