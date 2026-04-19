"""Portal controller for vocabulary (learning entries).

Provides:
  GET  /my/vocabulary[/page/<n>]     — paginated list with search/filter/sort
  GET  /my/vocabulary/<id>           — entry detail + edit
  GET/POST /my/vocabulary/new        — add-entry form
  GET  /my/vocabulary/shared         — shared entries from all users
  POST /my/vocabulary/<id>/share     — toggle is_shared
  POST /my/vocabulary/<id>/archive   — archive / restore entry
  JSON /my/vocabulary/detect_language — language detection for AJAX

Search searches source_text + translation_ids.translated_text.
Filter options: all | new | learning | review | unstarted (SRS states).
Sort options: newest (default) | az | difficulty (ease factor asc).
"""

import logging

from odoo import http
from odoo.exceptions import ValidationError
from odoo.http import request

from odoo.addons.portal.controllers.portal import CustomerPortal
from odoo.addons.portal.controllers.portal import pager as portal_pager

_logger = logging.getLogger(__name__)

ITEMS_PER_PAGE = 20

LANG_NAMES = {'en': 'English', 'uk': 'Ukrainian', 'el': 'Greek'}

SUPPORTED_LANGS = [
    {'code': 'en', 'name': 'English'},
    {'code': 'uk', 'name': 'Ukrainian'},
    {'code': 'el', 'name': 'Greek'},
]

# Valid filterby / sortby values — used to reject tampered query params.
_VALID_FILTERS = frozenset({'all', 'new', 'learning', 'review', 'unstarted'})
_VALID_SORTS   = frozenset({'newest', 'az', 'difficulty'})


def _try_detect_language(text: str):
    """Return 'en', 'uk', 'el', or None.

    Uses langdetect with a confidence threshold of 0.7.
    Returns None for short/ambiguous text so the UI falls back to the
    user's default_source_language (SPEC §4.1, ADR-005).

    Known limitation: single-word detection is unreliable for short words
    (especially shared-character scripts like Cyrillic).  The UI allows the
    user to override the pre-fill.
    """
    if not text or len(text.strip()) < 3:
        return None
    try:
        from langdetect import detect_langs  # installed via base-requirements.txt
        results = detect_langs(text)
        if results:
            top = results[0]
            lang_code = top.lang.split('-')[0].lower()  # 'en-US' → 'en'
            if top.prob >= 0.7 and lang_code in ('en', 'uk', 'el'):
                return lang_code
    except Exception:
        _logger.debug('Language detection failed for text=%r', text[:50], exc_info=True)
    return None


class VocabularyPortal(CustomerPortal):
    """Portal pages for vocabulary management."""

    # ------------------------------------------------------------------
    # Portal home widget (shows entry count on /my/home)
    # ------------------------------------------------------------------

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        if 'entry_count' in counters:
            Entry = request.env['language.entry']
            values['entry_count'] = Entry.search_count(
                [('owner_id', '=', request.env.user.id)]
            )
        return values

    # ------------------------------------------------------------------
    # Portal profile  GET/POST /my/profile
    # ------------------------------------------------------------------

    @http.route('/my/profile', type='http', auth='user', website=True,
                methods=['GET', 'POST'])
    def vocabulary_profile(self, **post):
        """Portal page for editing the user's language preferences.

        Needed for M3 auto-translation to work end-to-end without an admin
        touching the backend: users set their own learning_languages here.
        """
        Profile = request.env['language.user.profile'].sudo()
        profile = Profile._get_or_create_for_user(request.env.uid)
        Lang = request.env['language.lang'].sudo()
        all_langs = Lang.search([], order='code')

        error = None
        saved = False
        if request.httprequest.method == 'POST':
            native = post.get('native_language') or False
            default_src = post.get('default_source_language') or False
            learning_codes = request.httprequest.form.getlist('learning_languages')
            is_shared_list = bool(post.get('is_shared_list'))
            valid_codes = {'en', 'uk', 'el'}

            if native and native not in valid_codes:
                error = 'Invalid native language.'
            elif default_src and default_src not in valid_codes:
                error = 'Invalid default source language.'
            else:
                lang_records = Lang.search([('code', 'in', learning_codes)])
                profile.write({
                    'native_language': native,
                    'default_source_language': default_src,
                    'learning_languages': [(6, 0, lang_records.ids)],
                    'is_shared_list': is_shared_list,
                })
                saved = True

        return request.render('language_words.portal_profile', {
            'page_name': 'profile',
            'profile': profile,
            'all_langs': all_langs,
            'lang_names': LANG_NAMES,
            'error': error,
            'saved': saved,
        })

    # ------------------------------------------------------------------
    # Vocabulary list  GET /my/vocabulary[/page/<n>]
    # ------------------------------------------------------------------

    @http.route(['/my/vocabulary', '/my/vocabulary/page/<int:page>'],
                type='http', auth='user', website=True)
    def vocabulary_list(self, page=1, search='', filterby='all', sortby='newest', **kwargs):
        uid   = request.env.user.id
        Entry = request.env['language.entry']
        Review = request.env['language.review'].sudo()

        # Sanitise query params
        search   = (search or '').strip()
        filterby = filterby if filterby in _VALID_FILTERS else 'all'
        sortby   = sortby   if sortby   in _VALID_SORTS   else 'newest'

        # ── Base domain ─────────────────────────────────────────────────
        domain = [('owner_id', '=', uid)]

        # ── Full-text search (source_text OR translation text) ──────────
        if search:
            trans_ids = request.env['language.translation'].sudo().search([
                ('translated_text', 'ilike', search),
                ('entry_id.owner_id', '=', uid),
            ]).mapped('entry_id').ids
            domain += ['|', ('source_text', 'ilike', search), ('id', 'in', trans_ids)]

        # ── SRS state filter ─────────────────────────────────────────────
        if filterby in ('new', 'learning', 'review'):
            srs_ids = Review.search([
                ('user_id', '=', uid),
                ('state', '=', filterby),
            ]).mapped('entry_id').ids
            domain += [('id', 'in', srs_ids)]
        elif filterby == 'unstarted':
            started_ids = Review.search([('user_id', '=', uid)]).mapped('entry_id').ids
            domain += [('id', 'not in', started_ids)]

        # ── Sorting ──────────────────────────────────────────────────────
        url_args = {}
        if search:
            url_args['search'] = search
        if filterby != 'all':
            url_args['filterby'] = filterby
        if sortby != 'newest':
            url_args['sortby'] = sortby

        if sortby == 'difficulty':
            # Sort by ease_factor asc (lowest = hardest words that trip the user).
            # Entries with no review card yet appear after all reviewed entries.
            all_ids    = Entry.search(domain).ids
            all_id_set = set(all_ids)
            reviews    = Review.search(
                [('user_id', '=', uid), ('entry_id', 'in', list(all_id_set))],
                order='ease_factor asc, id asc',
            )
            reviewed_ids   = [r.entry_id.id for r in reviews if r.entry_id.id in all_id_set]
            unreviewed_ids = [eid for eid in all_ids if eid not in set(reviewed_ids)]
            ordered_ids    = reviewed_ids + unreviewed_ids
            total          = len(ordered_ids)

            pager = portal_pager(
                url='/my/vocabulary',
                url_args=url_args,
                total=total,
                page=int(page),
                step=ITEMS_PER_PAGE,
            )
            page_ids = ordered_ids[pager['offset']: pager['offset'] + ITEMS_PER_PAGE]
            entries  = Entry.browse(page_ids)
        else:
            order = 'source_text asc, id asc' if sortby == 'az' else 'create_date desc, id desc'
            total = Entry.search_count(domain)
            pager = portal_pager(
                url='/my/vocabulary',
                url_args=url_args,
                total=total,
                page=int(page),
                step=ITEMS_PER_PAGE,
            )
            entries = Entry.search(domain, limit=ITEMS_PER_PAGE, offset=pager['offset'], order=order)

        # ── SRS state map for the current page (badge display) ───────────
        srs_states = {}
        if entries:
            cards = Review.search([('user_id', '=', uid), ('entry_id', 'in', entries.ids)])
            srs_states = {c.entry_id.id: c.state for c in cards}

        return request.render('language_words.portal_vocabulary_list', {
            'entries':     entries,
            'page_name':   'vocabulary',
            'pager':       pager,
            'entry_count': total,
            'lang_names':  LANG_NAMES,
            'search':      search,
            'filterby':    filterby,
            'sortby':      sortby,
            'srs_states':  srs_states,
        })

    # ------------------------------------------------------------------
    # Entry detail  GET /my/vocabulary/<id>
    # ------------------------------------------------------------------

    @http.route('/my/vocabulary/<int:entry_id>', type='http', auth='user', website=True)
    def vocabulary_detail(self, entry_id, **kwargs):
        entry = request.env['language.entry'].browse(entry_id)
        if not entry.exists() or entry.owner_id.id != request.env.user.id:
            return request.not_found()
        profile = request.env['language.user.profile'].search(
            [('user_id', '=', request.env.uid)], limit=1
        )
        # Languages that have no translation record yet (excluding source language).
        existing_lang_codes = {t.target_language for t in entry.translation_ids}
        missing_translation_langs = [
            lang for lang in SUPPORTED_LANGS
            if lang['code'] != entry.source_language
            and lang['code'] not in existing_lang_codes
        ]
        return request.render('language_words.portal_vocabulary_detail', {
            'entry': entry,
            'page_name': 'vocabulary',
            'lang_names': LANG_NAMES,
            'user_profile': profile,
            'missing_translation_langs': missing_translation_langs,
        })

    # ------------------------------------------------------------------
    # Add entry form  GET/POST /my/vocabulary/new
    # ------------------------------------------------------------------

    @http.route('/my/vocabulary/new', type='http', auth='user', website=True,
                methods=['GET', 'POST'])
    def vocabulary_new(self, **post):
        error = None
        values = {
            'page_name': 'vocabulary',
            'source_text': post.get('source_text', ''),
            'source_language': post.get('source_language', ''),
            'entry_type': post.get('entry_type', 'word'),
        }

        if request.httprequest.method == 'POST':
            source_text = post.get('source_text', '').strip()
            source_language = post.get('source_language', '')
            entry_type = post.get('entry_type', 'word')

            if not source_text:
                error = 'Please enter a word, phrase or sentence.'
            elif not source_language:
                error = 'Please select a source language.'
            else:
                try:
                    entry = request.env['language.entry'].create({
                        'source_text': source_text,
                        'source_language': source_language,
                        'type': entry_type,
                        'owner_id': request.env.user.id,
                        'created_from': 'manual',
                    })
                    return request.redirect('/my/vocabulary/%d' % entry.id)
                except ValidationError as exc:
                    error = exc.args[0]

        values['error'] = error
        return request.render('language_words.portal_vocabulary_new', values)

    # ------------------------------------------------------------------
    # Toggle sharing  POST /my/vocabulary/<id>/share
    # ------------------------------------------------------------------

    @http.route('/my/vocabulary/<int:entry_id>/share', type='http', auth='user',
                website=True, methods=['POST'])
    def vocabulary_share(self, entry_id, **post):
        entry = request.env['language.entry'].browse(entry_id)
        if not entry.exists() or entry.owner_id.id != request.env.user.id:
            return request.not_found()
        entry.is_shared = not entry.is_shared
        return request.redirect('/my/vocabulary/%d' % entry_id)

    # ------------------------------------------------------------------
    # Archive / restore  POST /my/vocabulary/<id>/archive
    # ------------------------------------------------------------------

    @http.route('/my/vocabulary/<int:entry_id>/archive', type='http', auth='user',
                website=True, methods=['POST'])
    def vocabulary_archive(self, entry_id, **post):
        entry = request.env['language.entry'].browse(entry_id)
        if not entry.exists() or entry.owner_id.id != request.env.user.id:
            return request.not_found()
        new_status = 'archived' if entry.status == 'active' else 'active'
        entry.status = new_status
        return request.redirect('/my/vocabulary/%d' % entry_id)

    # ------------------------------------------------------------------
    # Shared vocabulary  GET /my/vocabulary/shared
    # ------------------------------------------------------------------

    @http.route('/my/vocabulary/shared', type='http', auth='user', website=True)
    def vocabulary_shared(self, page=1, **kwargs):
        Entry = request.env['language.entry']
        domain = [
            ('is_shared', '=', True),
            ('owner_id', '!=', request.env.user.id),
        ]
        entry_count = Entry.search_count(domain)
        pager = portal_pager(
            url='/my/vocabulary/shared',
            total=entry_count,
            page=int(page),
            step=ITEMS_PER_PAGE,
        )
        entries = Entry.search(
            domain,
            limit=ITEMS_PER_PAGE,
            offset=pager['offset'],
            order='create_date desc',
        )
        return request.render('language_words.portal_vocabulary_shared', {
            'entries': entries,
            'page_name': 'vocabulary',
            'pager': pager,
            'entry_count': entry_count,
            'lang_names': LANG_NAMES,
        })

    # ------------------------------------------------------------------
    # Copy shared entry  POST /my/vocabulary/<id>/copy
    # ------------------------------------------------------------------

    @http.route('/my/vocabulary/<int:entry_id>/copy', type='http', auth='user',
                website=True, methods=['POST'])
    def vocabulary_copy(self, entry_id, **post):
        entry = request.env['language.entry'].browse(entry_id)
        if not entry.exists() or not entry.is_shared:
            return request.not_found()
        try:
            new_entry = entry.copy_to_user(request.env.user.id)
            return request.redirect('/my/vocabulary/%d' % new_entry.id)
        except ValidationError as exc:
            # Already in vocabulary
            return request.redirect(
                '/my/vocabulary/shared?copy_error=%s' % http.url_quote(exc.args[0])
            )

    # ------------------------------------------------------------------
    # Language detection JSON endpoint  POST /my/vocabulary/detect_language
    # ------------------------------------------------------------------

    @http.route('/my/vocabulary/detect_language', type='json', auth='user')
    def detect_language(self, text=''):
        lang = _try_detect_language(text)
        # Fall back to user's default_source_language from their profile
        if not lang:
            profile = request.env['language.user.profile'].search(
                [('user_id', '=', request.env.user.id)], limit=1
            )
            lang = profile.default_source_language if profile else None
        return {'lang': lang}
