import json
import logging
import os
import time
from datetime import date as _date, datetime as _datetime

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)

_ALLOWED_LANGUAGES = ('en', 'uk', 'el', 'pl')
_MAX_WORD_LEN = 1000
_MAX_WRITER_TEXT = 4000   # M31: cap for /writer_check text body, matches LLM /analyze-writing
_MAX_SHADOW_TEXT = 500    # M33: cap for shadow_tts/shadow_evaluate reference text
_MAX_RADAR_VOCAB = int(os.environ.get('LEXORA_RADAR_VOCAB_LIMIT', '1000'))   # M34: cap for /my_vocab response
_AUDIO_SVC = os.environ.get('AUDIO_SERVICE_URL', 'http://audio-service:8000').rstrip('/')
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
            source_language   (str, optional)  — en / uk / el / pl (auto-detected if omitted)
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
        if lang not in ('en', 'uk', 'el', 'pl'):
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

        # Build translation lookup: entry_id → {lang_code: translated_text}
        trans_map = {}
        if 'language.translation' in request.env.registry:
            translations = request.env['language.translation'].sudo().search([
                ('entry_id', 'in', entries.ids),
                ('status', '=', 'completed'),
            ], order='id asc')
            for t in translations:
                entry_trans = trans_map.setdefault(t.entry_id.id, {})
                # Keep first result per language (order='id asc' → earliest job wins)
                if t.target_language not in entry_trans:
                    entry_trans[t.target_language] = t.translated_text

        today = _date.today()
        words = []
        for entry in entries:
            review = srs_map.get(entry.id)
            srs_state = review.state if review else None
            days_ago = None
            if review and review.last_review_date:
                lrd = review.last_review_date
                # Odoo Date → date object; Odoo Datetime → datetime object
                lrd_date = lrd.date() if isinstance(lrd, _datetime) else lrd
                days_ago = (today - lrd_date).days

            words.append({
                'id': entry.id,
                'word': entry.source_text,
                'normalized': entry.normalized_text or entry.source_text.lower(),
                'lang': entry.source_language,
                'translations': trans_map.get(entry.id) or {},
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
            language  (str, optional)  — language hint: en / uk / el / pl (default 'en')

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

    # ------------------------------------------------------------------
    # POST /lexora_api/writer_check  (M31 — Lexora Writer)
    # ------------------------------------------------------------------
    @http.route('/lexora_api/writer_check', type='http', auth='none',
                methods=['POST'], csrf=False)
    def writer_check(self, **kw):
        """Proxy a writing-analysis request to the LLM service.

        Used by the browser extension's floating "L" FAB on every focused
        <textarea> / [contenteditable]. The user clicks the FAB; the
        extension sends the field's text here; we forward to the LLM
        service's POST /analyze-writing and pass the JSON back unchanged.

        Request body (JSON):
            text      (str, required)  — the field's value, capped at
                                         _MAX_WRITER_TEXT (4000) chars.
            language  (str, optional)  — en / uk / el / pl (default 'en').
            context   (str, optional)  — placeholder / aria-label of the
                                         input, gives the model genre
                                         awareness ("email", "tweet", etc).

        Response (LLM payload + injected status):
            {"status":"ok",
             "corrections":[{"wrong":"...","correct":"...","note":"..."}],
             "improved":"..."}
            {"status":"error",       "message":"text is required", ...}
            {"status":"unavailable", "message":"LLM service unavailable..."}

        Latency contract: same as M28 explain-grammar / M30 analyze-speech —
        Qwen2.5-1.5B on the target server runs ~15-30 s for typical
        comment-length text. The extension shows an "Analysing…" pill.
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

        text = (data.get('text') or '').strip()
        if not text:
            return _json_response(
                {'status': 'error', 'message': 'text is required'}, 400)
        if len(text) > _MAX_WRITER_TEXT:
            text = text[:_MAX_WRITER_TEXT]

        language = (data.get('language') or 'en').strip().lower()
        if language not in _ALLOWED_LANGUAGES:
            language = 'en'

        # Optional context (field placeholder/aria-label). Cap defensively
        # so we don't blow up the LLM user-message budget.
        context = (data.get('context') or '').strip()
        if context:
            context = context[:200]

        payload = {'text': text, 'language': language}
        if context:
            payload['context'] = context

        try:
            import requests as _req
            resp = _req.post(
                f'{_LLM_SVC}/analyze-writing',
                json=payload,
                timeout=60,
            )
            resp.raise_for_status()
            result = json.loads(resp.content.decode('utf-8', errors='replace'))
        except Exception as exc:
            _logger.warning('writer_check proxy error: %s', exc)
            return _json_response({
                'status': 'unavailable',
                'message': 'LLM service unavailable — please try again shortly.',
                'corrections': [],
                'improved': text,
            })

        # The LLM endpoint already injects status='ok'; defensive belt-and-braces.
        if 'status' not in result:
            result['status'] = 'ok'
        return _json_response(result)

    # ------------------------------------------------------------------
    # POST /lexora_api/explain_slang  (M32 — Slang & Idiom Explainer)
    # ------------------------------------------------------------------
    @http.route('/lexora_api/explain_slang', type='http', auth='none',
                methods=['POST'], csrf=False)
    def explain_slang(self, **kw):
        """Proxy a slang/idiom explanation request to the LLM service.

        Used by the Quick Look (content.js) and YouTube subtitle
        (overlay.js) overlays' new "Explain Slang/Idiom" button. Sends
        the selected phrase to the LLM service's /explain-slang endpoint
        and passes the JSON back unchanged (defensive status injection).

        Request body (JSON):
            phrase           (str, required) — the phrase to classify.
                                                Capped at _MAX_WORD_LEN
                                                (1000) chars.
            source_language  (str, optional) — language of the phrase
                                                itself (en/uk/el/pl).
                                                Default 'en'.
            native_language  (str, optional) — language to render the
                                                figurative/literal
                                                explanations in. Resolution
                                                order: client value →
                                                caller's
                                                language.user.profile.
                                                native_language → 'en'.

        Response (LLM payload + injected status):
            {"status":"ok",
             "kind":"idiom" | "slang" | "phrasal_verb" | "literal" |
                    "unknown",
             "figurative_meaning":"...",
             "literal_meaning":"...",
             "example":"...",
             "confidence":"high" | "medium" | "low"}
            {"status":"error",       "message":"phrase is required", ...}
            {"status":"unavailable", "message":"LLM service unavailable..."}

        Latency: same envelope as /explain_grammar / /writer_check —
        Qwen2.5-1.5B on the target server typically returns in
        10-25 seconds for a single phrase.
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
            return _json_response(
                {'status': 'error', 'message': 'phrase is required'}, 400)

        source_language = (data.get('source_language') or 'en').strip().lower()
        if source_language not in _ALLOWED_LANGUAGES:
            source_language = 'en'

        # native_language resolution: client → profile → 'en'.
        native_language = (data.get('native_language') or '').strip().lower()
        if native_language and native_language not in _ALLOWED_LANGUAGES:
            native_language = ''
        if not native_language:
            try:
                uid = _resolve_uid()
                profile = request.env['language.user.profile'].sudo().search(
                    [('user_id', '=', uid)], limit=1)
                if profile and profile.native_language in _ALLOWED_LANGUAGES:
                    native_language = profile.native_language
            except Exception as exc:
                _logger.debug('explain_slang profile lookup failed: %s', exc)
        if not native_language:
            native_language = 'en'

        try:
            import requests as _req
            resp = _req.post(
                f'{_LLM_SVC}/explain-slang',
                json={
                    'phrase': phrase,
                    'source_language': source_language,
                    'native_language': native_language,
                },
                timeout=60,
            )
            resp.raise_for_status()
            result = json.loads(resp.content.decode('utf-8', errors='replace'))
        except Exception as exc:
            _logger.warning('explain_slang proxy error: %s', exc)
            return _json_response({
                'status': 'unavailable',
                'message': 'LLM service unavailable — please try again shortly.',
                'kind': 'unknown',
                'figurative_meaning': '',
                'literal_meaning': phrase,
                'example': '',
                'confidence': 'low',
            })

        if 'status' not in result:
            result['status'] = 'ok'
        return _json_response(result)

    # ------------------------------------------------------------------
    # POST /lexora_api/shadow_tts  (M33 — Webpage Shadowing: Play Original)
    # ------------------------------------------------------------------
    @http.route('/lexora_api/shadow_tts', type='http', auth='none',
                methods=['POST'], csrf=False)
    def shadow_tts(self, **kw):
        """Proxy a synchronous TTS request to the audio service.

        The browser extension's "▶ Play Original" button POSTs the
        reference phrase here; we forward to audio /tts-sync and stream
        the audio/mpeg bytes back to the extension, which feeds them
        into an <audio> element.

        Request body (JSON):
            text      (str, required)  — reference phrase, capped at
                                         _MAX_SHADOW_TEXT (500) chars.
            language  (str, optional)  — en / uk / el / pl (default 'en').

        Response:
            200 audio/mpeg bytes on success.
            400 / 413 / 502 / 503 JSON error envelope on failure.
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

        text = (data.get('text') or '').strip()
        if not text:
            return _json_response(
                {'status': 'error', 'message': 'text is required'}, 400)
        if len(text) > _MAX_SHADOW_TEXT:
            return _json_response(
                {'status': 'error',
                 'message': f'text exceeds {_MAX_SHADOW_TEXT} chars'}, 413)

        language = (data.get('language') or 'en').strip().lower()
        if language not in _ALLOWED_LANGUAGES:
            language = 'en'

        try:
            import requests as _req
            resp = _req.post(
                f'{_AUDIO_SVC}/tts-sync',
                json={'text': text, 'language': language},
                timeout=30,
                stream=False,  # short audio, fits comfortably in memory
            )
        except Exception as exc:
            _logger.warning('shadow_tts proxy network error: %s', exc)
            return _json_response({
                'status': 'unavailable',
                'message': 'TTS service unavailable.',
            }, 502)

        if resp.status_code != 200:
            # Pass through the audio service's structured error verbatim
            # so the extension can render it (413 long text, 503 engine
            # timeout, etc.).
            try:
                detail = resp.json()
            except Exception:
                detail = {'detail': (resp.text or '')[:200]}
            return _json_response({
                'status': 'error',
                'http_status': resp.status_code,
                **detail,
            }, resp.status_code)

        # Stream the audio bytes back with the same Content-Type the audio
        # service used (typically audio/mpeg). _cors_headers() adds the
        # extension-friendly CORS reflection.
        headers = list(_cors_headers().items()) + [
            ('Content-Type', resp.headers.get('Content-Type', 'audio/mpeg')),
            ('Cache-Control', 'no-store'),
        ]
        # Forward the X-Lexora-TTS-* diagnostic headers so the extension
        # can show which engine / voice was used.
        for h in ('X-Lexora-TTS-Engine', 'X-Lexora-TTS-Language'):
            if h in resp.headers:
                headers.append((h, resp.headers[h]))
        return request.make_response(resp.content, headers=headers, status=200)

    # ------------------------------------------------------------------
    # POST /lexora_api/shadow_evaluate  (M33 — Webpage Shadowing)
    # ------------------------------------------------------------------
    @http.route('/lexora_api/shadow_evaluate', type='http', auth='none',
                methods=['POST'], csrf=False)
    def shadow_evaluate(self, **kw):
        """Two-stage orchestrator: transcribe user audio, then evaluate.

        Multipart request:
            audio           (file, required)  — user's recording (any
                                                MediaRecorder format).
            reference_text  (str, required)   — sentence the user
                                                practised. Capped at
                                                _MAX_SHADOW_TEXT.
            language        (str, optional)   — en / uk / el / pl
                                                (default 'en').

        Pipeline:
          1. Forward audio to audio_service /transcribe-sync (M30 path).
          2. Forward {reference_text, transcript, language} to
             llm_service /evaluate-pronunciation.
          3. Combine both responses + inject status='ok'.

        Response (combined):
            {"status":"ok",
             "transcript":"...","duration":4.2,"detected_language":"en",
             "score":85,"missed_words":[...],"mispronounced_words":[...],
             "feedback":"..."}
        """
        err = _require_session()
        if err:
            return err

        # Multipart fields land in request.params (audio is a FileStorage,
        # text fields are plain strings).
        audio_file = request.params.get('audio') or request.httprequest.files.get('audio')
        reference  = (request.params.get('reference_text') or '').strip()
        language   = (request.params.get('language') or 'en').strip().lower()

        if not reference:
            return _json_response(
                {'status': 'error', 'message': 'reference_text is required'}, 400)
        if len(reference) > _MAX_SHADOW_TEXT:
            reference = reference[:_MAX_SHADOW_TEXT]
        if language not in _ALLOWED_LANGUAGES:
            language = 'en'
        if not audio_file:
            return _json_response(
                {'status': 'error', 'message': 'audio file is required'}, 400)

        try:
            audio_bytes = audio_file.read()
        except Exception as exc:
            return _json_response(
                {'status': 'error', 'message': f'could not read audio upload: {exc}'},
                400)
        if not audio_bytes:
            return _json_response(
                {'status': 'error', 'message': 'audio upload is empty'}, 400)

        # ── Stage 1 — transcribe ───────────────────────────────────────
        import requests as _req
        try:
            mime = getattr(audio_file, 'content_type', None) or 'audio/webm'
            filename = getattr(audio_file, 'filename', None) or 'recording.webm'
            tx_resp = _req.post(
                f'{_AUDIO_SVC}/transcribe-sync',
                files={'audio': (filename, audio_bytes, mime)},
                data={'language': language},
                timeout=120,
            )
        except Exception as exc:
            _logger.warning('shadow_evaluate transcribe network error: %s', exc)
            return _json_response({
                'status': 'unavailable',
                'message': 'Audio service unavailable during transcription.',
                'transcript': '', 'duration': 0,
                'score': 0, 'missed_words': [], 'mispronounced_words': [],
                'feedback': '',
            }, 502)

        if tx_resp.status_code != 200:
            try:
                tx_detail = tx_resp.json()
            except Exception:
                tx_detail = {'detail': (tx_resp.text or '')[:200]}
            return _json_response({
                'status': 'error',
                'stage': 'transcribe',
                'http_status': tx_resp.status_code,
                **tx_detail,
            }, tx_resp.status_code)

        try:
            tx_payload = tx_resp.json()
        except Exception:
            return _json_response(
                {'status': 'error', 'stage': 'transcribe',
                 'message': 'audio service returned non-JSON'}, 502)

        transcript = (tx_payload.get('transcript') or '').strip()
        duration   = float(tx_payload.get('duration') or 0.0)
        detected   = tx_payload.get('language') or language

        # ── Stage 2 — evaluate ─────────────────────────────────────────
        try:
            ev_resp = _req.post(
                f'{_LLM_SVC}/evaluate-pronunciation',
                json={'reference_text': reference, 'transcript': transcript,
                      'language': language},
                timeout=60,
            )
            ev_resp.raise_for_status()
            ev_payload = json.loads(ev_resp.content.decode('utf-8', errors='replace'))
        except Exception as exc:
            _logger.warning('shadow_evaluate LLM error: %s', exc)
            return _json_response({
                'status': 'unavailable',
                'message': 'LLM unavailable during evaluation.',
                'transcript': transcript,
                'duration': duration,
                'detected_language': detected,
                'score': 0, 'missed_words': [], 'mispronounced_words': [],
                'feedback': '',
            }, 502)

        # ── Merge + return ─────────────────────────────────────────────
        combined = {
            'status':            'ok',
            'transcript':        transcript,
            'duration':          duration,
            'detected_language': detected,
            'score':              int(ev_payload.get('score') or 0),
            'missed_words':       ev_payload.get('missed_words') or [],
            'mispronounced_words': ev_payload.get('mispronounced_words') or [],
            'feedback':           ev_payload.get('feedback') or '',
        }
        return _json_response(combined)

    # ------------------------------------------------------------------
    # GET /lexora_api/my_vocab  (M34 — YouTube Vocab Radar)
    # ------------------------------------------------------------------
    @http.route('/lexora_api/my_vocab', type='http', auth='none',
                methods=['GET'], csrf=False)
    def my_vocab(self, **kw):
        """Lightweight vocabulary projection for the YouTube radar.

        Distinct from /lexora_api/get_learned_words (M27): no SRS state,
        no per-entry days_ago, only entries with at least one completed
        translation (so the radar always has something to show). Capped
        at _MAX_RADAR_VOCAB (env override LEXORA_RADAR_VOCAB_LIMIT).

        Response shape:
            {
              "status": "ok",
              "words": [
                {
                  "id": 1234,
                  "word": "ephemeral",
                  "normalized": "ephemeral",
                  "lang": "en",
                  "translations": {
                    "uk": "короткочасний",
                    "el": "εφήμερος",
                    "pl": "efemeryczny"
                  }
                }
              ],
              "generated_at": 1747094400
            }

        Cached client-side in chrome.storage.local for 15 min (M34-S2).
        Invalidated on /lexora_api/add_word success.
        """
        err = _require_session()
        if err:
            return err

        uid = _resolve_uid()

        if 'language.entry' not in request.env.registry:
            return _json_response({'status': 'ok', 'words': [],
                                   'generated_at': int(time.time())})

        entries = request.env['language.entry'].sudo().search([
            ('owner_id', '=', uid),
            ('status', '=', 'active'),
            ('pvp_eligible', '=', True),
        ], limit=_MAX_RADAR_VOCAB, order='write_date desc')

        # Build translation lookup: entry_id → {lang_code: translated_text}
        # Same shape as M27 so a future shared client helper can consume either.
        trans_map = {}
        if entries and 'language.translation' in request.env.registry:
            translations = request.env['language.translation'].sudo().search([
                ('entry_id', 'in', entries.ids),
                ('status', '=', 'completed'),
            ], order='id asc')
            for t in translations:
                if not t.translated_text:
                    continue
                bucket = trans_map.setdefault(t.entry_id.id, {})
                # Keep first result per language (order='id asc' → earliest job wins).
                if t.target_language not in bucket:
                    bucket[t.target_language] = t.translated_text

        words = []
        for entry in entries:
            words.append({
                'id': entry.id,
                'word': entry.source_text,
                'normalized': entry.normalized_text or (entry.source_text or '').lower(),
                'lang': entry.source_language,
                'translations': trans_map.get(entry.id) or {},
            })

        return _json_response({
            'status': 'ok',
            'words': words,
            'generated_at': int(time.time()),
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
    """Call the translation service synchronously for every supported target.

    M29 (2026-05-03): live translation now covers ALL supported languages
    (en/uk/el/pl) minus the source — not the user's profile preferences —
    so Polish always appears in the Quick Look overlay regardless of
    learning_languages. Results are NOT stored; the caller receives them
    as ephemeral "live" translations and the user can persist via
    Add to Vocabulary.
    """
    import requests as _req

    translate_url = f'{_TRANSLATION_SVC}/translate'
    _logger.error('_live_translate ENTER — word=%r source=%s uid=%s url=%s',
                  word, source_lang, uid, translate_url)

    # Always use the full supported-language set minus source.
    target_langs = [l for l in _ALLOWED_LANGUAGES if l != source_lang]
    _logger.error('_live_translate target_langs=%r', target_langs)

    results = []
    # Cap at 3 (en/uk/el/pl minus source = 3) — keeps latency bounded but
    # ensures Polish is never dropped.
    for tgt in target_langs[:3]:
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
