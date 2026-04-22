"""Portal controllers for the Knowledge Hub (M12).

Routes:
  GET  /useful-words                — Gold vocabulary, tabbed by CEFR level
  GET  /useful-words/page/<int:p>   — Pagination
  POST /useful-words/add            — Add word to user's vocabulary list
  GET  /grammar                     — Grammar encyclopedia index
  GET  /grammar/<slug>              — Grammar section detail
"""

import logging
from odoo import http
from odoo.exceptions import ValidationError
from odoo.http import request

_logger = logging.getLogger(__name__)

_LEVELS = ['A1', 'A2', 'B1', 'B2', 'C1', 'C2']
_PER_PAGE = 50

_LEVEL_COLORS = {
    'A1': 'success', 'A2': 'info',
    'B1': 'primary', 'B2': 'warning',
    'C1': 'danger', 'C2': 'dark',
}

_CATEGORY_LABELS = {
    'tenses': 'Tenses',
    'verbs': 'Verbs',
    'articles': 'Articles & Determiners',
    'conditionals': 'Conditionals',
    'modals': 'Modal Verbs',
    'voice': 'Voice & Reported Speech',
}


class LibraryController(http.Controller):

    # ------------------------------------------------------------------
    # Useful Words
    # ------------------------------------------------------------------

    @http.route(['/useful-words', '/useful-words/page/<int:page>'],
                type='http', auth='user', website=True, methods=['GET'])
    def useful_words(self, page=1, level=None, q=None, **kw):
        SW = request.env['language.seeded.word'].sudo()
        q = (q or '').strip()

        if q:
            # Search mode: find word across all levels; highlight its level tab.
            domain = [('word', 'ilike', q)]
            match = SW.search(domain, limit=1, order='sort_order asc, word asc')
            active_level = match.level if match else (level if level in _LEVELS else _LEVELS[0])
        else:
            active_level = level if level in _LEVELS else _LEVELS[0]
            domain = [('level', '=', active_level)]

        total = SW.search_count(domain)
        offset = (int(page) - 1) * _PER_PAGE
        words = SW.search(domain, limit=_PER_PAGE, offset=offset,
                          order='sort_order asc, word asc')
        total_pages = max(1, (total + _PER_PAGE - 1) // _PER_PAGE)

        level_counts = {lvl: SW.search_count([('level', '=', lvl)]) for lvl in _LEVELS}

        return request.render('language_portal.portal_useful_words', {
            'words': words,
            'active_level': active_level,
            'levels': _LEVELS,
            'level_colors': _LEVEL_COLORS,
            'level_counts': level_counts,
            'page': int(page),
            'total_pages': total_pages,
            'total': total,
            'search_q': q,
        })

    @http.route('/useful-words/add', type='http', auth='user', website=True,
                methods=['POST'])
    def useful_words_add(self, word_id=None, **kw):
        if not word_id:
            return request.redirect('/useful-words')
        try:
            word_id = int(word_id)
        except (ValueError, TypeError):
            return request.redirect('/useful-words')

        sw = request.env['language.seeded.word'].sudo().browse(word_id).exists()
        if not sw:
            return request.redirect('/useful-words')

        uid = request.env.user.id
        Entry = request.env['language.entry'].sudo()
        try:
            Entry.create({
                'source_text': sw.word,
                'source_language': 'en',
                'owner_id': uid,
                'type': 'word',
                'created_from': 'seeded_content',
                'status': 'active',
            })
            result = 'added'
        except ValidationError:
            result = 'duplicate'
        except Exception as exc:
            _logger.warning('useful_words_add failed: %s', exc)
            result = 'error'

        active_level = sw.level
        return request.redirect(f'/useful-words?level={active_level}&result={result}')

    # ------------------------------------------------------------------
    # Grammar Encyclopedia
    # ------------------------------------------------------------------

    @http.route('/grammar', type='http', auth='user', website=True, methods=['GET'])
    def grammar_index(self, **kw):
        GS = request.env['language.grammar.section'].sudo()
        sections = GS.search([('is_published', '=', True)], order='category asc, sequence asc')

        grouped = {}
        for s in sections:
            grouped.setdefault(s.category, []).append(s)

        return request.render('language_portal.portal_grammar_index', {
            'grouped': grouped,
            'category_labels': _CATEGORY_LABELS,
            'category_order': list(_CATEGORY_LABELS.keys()),
        })

    @http.route('/grammar/<string:slug>', type='http', auth='user', website=True,
                methods=['GET'])
    def grammar_section(self, slug, **kw):
        GS = request.env['language.grammar.section'].sudo()
        section = GS.search([('slug', '=', slug), ('is_published', '=', True)], limit=1)
        if not section:
            return request.not_found()

        all_sections = GS.search([('is_published', '=', True)],
                                  order='category asc, sequence asc')
        grouped = {}
        for s in all_sections:
            grouped.setdefault(s.category, []).append(s)

        return request.render('language_portal.portal_grammar_section', {
            'section': section,
            'grouped': grouped,
            'category_labels': _CATEGORY_LABELS,
            'category_order': list(_CATEGORY_LABELS.keys()),
        })
