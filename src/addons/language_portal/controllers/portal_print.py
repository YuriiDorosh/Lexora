"""PDF print controllers for Lexora cheat sheets (M13).

Routes:
  GET /my/vocabulary/print          — user's active vocabulary as PDF
  GET /useful-words/print           — Gold Vocabulary for a CEFR level as PDF
  GET /grammar/<slug>/print         — Grammar section as PDF
"""

import logging
from datetime import date

from odoo import http
from odoo.http import request, Response

_logger = logging.getLogger(__name__)

_LANG_NAMES = {'en': 'English', 'uk': 'Ukrainian', 'el': 'Greek', 'pl': 'Polish'}

_PAPERFORMAT_ARGS = {
    'data-report-margin-top': 12,
    'data-report-margin-bottom': 16,
    'data-report-margin-left': 14,
    'data-report-margin-right': 14,
    'data-report-dpi': 96,
}


def _render_pdf(template_xmlid, values, filename='cheat_sheet.pdf'):
    """Render a QWeb template to PDF bytes and return a Response."""
    env = request.env
    html_bytes = env['ir.qweb'].sudo()._render(
        template_xmlid, values, minimal_qcontext=True
    )
    html_str = html_bytes if isinstance(html_bytes, str) else html_bytes.decode('utf-8')

    pdf_content = env['ir.actions.report'].sudo()._run_wkhtmltopdf(
        [html_str],
        specific_paperformat_args=_PAPERFORMAT_ARGS,
    )

    return Response(
        pdf_content,
        status=200,
        headers={
            'Content-Type': 'application/pdf',
            'Content-Disposition': f'inline; filename="{filename}"',
            'Content-Length': str(len(pdf_content)),
        },
    )


class PrintController(http.Controller):

    # ------------------------------------------------------------------
    # Personal vocabulary PDF
    # ------------------------------------------------------------------

    @http.route('/my/vocabulary/print', type='http', auth='user',
                website=True, methods=['GET'])
    def vocabulary_print(self, **kw):
        uid = request.env.user.id
        Entry = request.env['language.entry'].sudo()
        entries = Entry.search(
            [('owner_id', '=', uid), ('status', '=', 'active')],
            order='source_language asc, source_text asc',
        )

        # Group by source language
        groups_map = {}
        for e in entries:
            groups_map.setdefault(e.source_language, []).append(e)

        lang_groups = [
            {'lang': lang, 'label': _LANG_NAMES.get(lang, lang.upper()),
             'entries': elist}
            for lang, elist in sorted(groups_map.items())
        ]

        values = {
            'lang_groups': lang_groups,
            'entry_count': len(entries),
            'date_generated': date.today().strftime('%d %b %Y'),
        }

        return _render_pdf(
            'language_portal.report_vocabulary_cheat_sheet_document',
            values,
            filename='lexora_vocabulary.pdf',
        )

    # ------------------------------------------------------------------
    # Gold Vocabulary PDF (by CEFR level)
    # ------------------------------------------------------------------

    @http.route('/useful-words/print', type='http', auth='user',
                website=True, methods=['GET'])
    def gold_vocab_print(self, level='A1', **kw):
        _LEVELS = ['A1', 'A2', 'B1', 'B2', 'C1', 'C2']
        if level not in _LEVELS:
            level = 'A1'

        SW = request.env['language.seeded.word'].sudo()
        words = SW.search(
            [('level', '=', level)],
            order='sort_order asc, word asc',
        )

        values = {
            'words': words,
            'active_level': level,
            'word_count': len(words),
            'date_generated': date.today().strftime('%d %b %Y'),
        }

        return _render_pdf(
            'language_portal.report_gold_vocab_cheat_sheet_document',
            values,
            filename=f'lexora_gold_vocab_{level.lower()}.pdf',
        )

    # ------------------------------------------------------------------
    # Grammar section PDF
    # ------------------------------------------------------------------

    @http.route('/grammar/<string:slug>/print', type='http', auth='user',
                website=True, methods=['GET'])
    def grammar_print(self, slug, **kw):
        GS = request.env['language.grammar.section'].sudo()
        section = GS.search(
            [('slug', '=', slug), ('is_published', '=', True)], limit=1
        )
        if not section:
            return request.not_found()

        values = {
            'section': section,
            'date_generated': date.today().strftime('%d %b %Y'),
        }

        safe_slug = slug.replace('/', '-')
        return _render_pdf(
            'language_portal.report_grammar_cheat_sheet_document',
            values,
            filename=f'lexora_grammar_{safe_slug}.pdf',
        )
