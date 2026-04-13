"""Portal controller for vocabulary (learning entries).

Provides:
  GET  /my/vocabulary               — paginated list of own entries
  GET  /my/vocabulary/<id>          — entry detail + edit
  GET/POST /my/vocabulary/new       — add-entry form
  GET  /my/vocabulary/shared        — shared entries from all users
  POST /my/vocabulary/<id>/share    — toggle is_shared
  POST /my/vocabulary/<id>/archive  — archive / restore entry
  JSON /my/vocabulary/detect_language — language detection for AJAX
"""

import logging

from odoo import http
from odoo.exceptions import ValidationError
from odoo.http import request

from odoo.addons.portal.controllers.portal import CustomerPortal
from odoo.addons.portal.controllers.portal import pager as portal_pager

_logger = logging.getLogger(__name__)

ITEMS_PER_PAGE = 20


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
    # Vocabulary list  GET /my/vocabulary
    # ------------------------------------------------------------------

    @http.route('/my/vocabulary', type='http', auth='user', website=True)
    def vocabulary_list(self, page=1, **kwargs):
        Entry = request.env['language.entry']
        domain = [('owner_id', '=', request.env.user.id)]
        entry_count = Entry.search_count(domain)

        pager = portal_pager(
            url='/my/vocabulary',
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

        return request.render('language_words.portal_vocabulary_list', {
            'entries': entries,
            'page_name': 'vocabulary',
            'pager': pager,
            'entry_count': entry_count,
        })

    # ------------------------------------------------------------------
    # Entry detail  GET /my/vocabulary/<id>
    # ------------------------------------------------------------------

    @http.route('/my/vocabulary/<int:entry_id>', type='http', auth='user', website=True)
    def vocabulary_detail(self, entry_id, **kwargs):
        entry = request.env['language.entry'].browse(entry_id)
        if not entry.exists() or entry.owner_id.id != request.env.user.id:
            return request.not_found()
        return request.render('language_words.portal_vocabulary_detail', {
            'entry': entry,
            'page_name': 'vocabulary',
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
