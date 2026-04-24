import logging
from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)

_LEVEL_COLORS = {
    'A1': 'success', 'A2': 'info',
    'B1': 'primary', 'B2': 'warning',
    'C1': 'danger', 'C2': 'dark',
}

_CATEGORY_LABELS = {
    'daily_life': 'Daily Life',
    'work': 'Work & Career',
    'emotions': 'Emotions',
    'relationships': 'Relationships',
    'learning': 'Learning',
    'communication': 'Communication',
}

_LANG_LABELS = {'en': 'English', 'uk': 'Ukrainian', 'el': 'Greek'}


class IdiomsController(http.Controller):

    @http.route('/idioms', type='http', auth='user', website=True, methods=['GET'])
    def idioms_index(self, lang=None, category=None, level=None, q=None, **kw):
        Idiom = request.env['language.idiom'].sudo()

        domain = []
        lang = lang if lang in ('en', 'uk', 'el') else 'en'
        domain.append(('language', '=', lang))

        if category and category in _CATEGORY_LABELS:
            domain.append(('category', '=', category))
        if level and level in ('A1', 'A2', 'B1', 'B2', 'C1', 'C2'):
            domain.append(('level', '=', level))
        if q:
            q = q.strip()
            domain.append(('expression', 'ilike', q))

        idioms = Idiom.search(domain, order='level asc, expression asc')

        available_langs = ['en', 'uk', 'el']
        lang_counts = {lc: Idiom.search_count([('language', '=', lc)]) for lc in available_langs}

        return request.render('language_portal.portal_idioms_index', {
            'idioms': idioms,
            'active_lang': lang,
            'active_category': category or '',
            'active_level': level or '',
            'search_q': q or '',
            'lang_labels': _LANG_LABELS,
            'lang_counts': lang_counts,
            'category_labels': _CATEGORY_LABELS,
            'level_colors': _LEVEL_COLORS,
            'levels': ['A1', 'A2', 'B1', 'B2', 'C1', 'C2'],
        })
