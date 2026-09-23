"""Portal controller for Lesson Import (/my/lessons).

Routes:
  GET  /my/lessons                — list of the user's own lessons
  GET  /my/lessons/new            — paste-a-lesson form
  POST /my/lessons/new            — create + parse + analyze (synchronous)
  GET  /my/lessons/<id>           — lesson detail (New/Seen/Corrections/Grammar/Notes)
  POST /my/lessons/<id>/reparse   — re-run the parser + novelty analysis
"""

import logging

from odoo import http
from odoo.exceptions import AccessError, UserError
from odoo.http import request

from odoo.addons.portal.controllers.portal import CustomerPortal

_logger = logging.getLogger(__name__)

LANG_NAMES = {'en': 'English', 'uk': 'Ukrainian', 'el': 'Greek', 'pl': 'Polish'}


class LessonsPortal(CustomerPortal):

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        if 'lesson_count' in counters:
            values['lesson_count'] = request.env['language.lesson'].search_count([
                ('user_id', '=', request.env.user.id),
            ])
        return values

    def _get_own_lesson(self, lesson_id):
        lesson = request.env['language.lesson'].search([
            ('id', '=', lesson_id),
            ('user_id', '=', request.env.user.id),
        ], limit=1)
        if not lesson:
            raise AccessError('Lesson not found or not owned by the current user.')
        return lesson

    # ------------------------------------------------------------------
    # List
    # ------------------------------------------------------------------

    @http.route('/my/lessons', type='http', auth='user', website=True)
    def lessons_list(self, **kwargs):
        lessons = request.env['language.lesson'].search([
            ('user_id', '=', request.env.user.id),
        ], order='lesson_date desc, id desc')
        return request.render('language_lessons.portal_lessons_list', {
            'lessons': lessons,
            'lang_names': LANG_NAMES,
            'page_name': 'lessons',
        })

    # ------------------------------------------------------------------
    # New lesson  GET/POST /my/lessons/new
    # ------------------------------------------------------------------

    @http.route('/my/lessons/new', type='http', auth='user', website=True, methods=['GET'])
    def lesson_new_form(self, **kwargs):
        return request.render('language_lessons.portal_lesson_new', {
            'lang_names': LANG_NAMES,
            'error': kwargs.get('error'),
            'post': {},
            'page_name': 'lessons',
        })

    @http.route('/my/lessons/new', type='http', auth='user', website=True, methods=['POST'], csrf=True)
    def lesson_new_submit(self, **post):
        raw_payload = (post.get('raw_payload') or '').strip()
        language = post.get('language') or 'en'
        name = (post.get('name') or '').strip() or 'New Lesson'

        if not raw_payload:
            return request.render('language_lessons.portal_lesson_new', {
                'lang_names': LANG_NAMES,
                'error': 'Paste the lesson text before importing.',
                'post': post,
                'page_name': 'lessons',
            })
        if language not in LANG_NAMES:
            language = 'en'

        lesson_vals = {
            'name': name,
            'user_id': request.env.user.id,
            'tutor_name': post.get('tutor_name') or False,
            'language': language,
            'source_type': 'manual_text',
            'raw_payload': raw_payload,
        }
        if post.get('lesson_date'):
            lesson_vals['lesson_date'] = post['lesson_date']

        lesson = request.env['language.lesson'].create(lesson_vals)
        lesson.action_parse()
        if lesson.state == 'parsed':
            try:
                lesson.action_analyze_novelty()
            except UserError as exc:
                _logger.warning('Lesson %s: novelty analysis failed: %s', lesson.id, exc)

        return request.redirect(f'/my/lessons/{lesson.id}')

    # ------------------------------------------------------------------
    # Detail  GET /my/lessons/<id>
    # ------------------------------------------------------------------

    @http.route('/my/lessons/<int:lesson_id>', type='http', auth='user', website=True)
    def lesson_detail(self, lesson_id, **kwargs):
        lesson = self._get_own_lesson(lesson_id)
        items = lesson.item_ids
        return request.render('language_lessons.portal_lesson_detail', {
            'lesson': lesson,
            'lang_names': LANG_NAMES,
            'new_items': items.filtered(lambda i: i.item_type in ('vocab', 'phrase') and i.novelty == 'new'),
            'seen_items': items.filtered(lambda i: i.item_type in ('vocab', 'phrase') and i.novelty in ('seen', 'known')),
            'correction_items': items.filtered(lambda i: i.item_type == 'correction'),
            'grammar_items': items.filtered(lambda i: i.item_type == 'grammar'),
            'note_items': items.filtered(lambda i: i.item_type == 'note'),
            'page_name': 'lessons',
        })

    # ------------------------------------------------------------------
    # Re-parse  POST /my/lessons/<id>/reparse
    # ------------------------------------------------------------------

    @http.route('/my/lessons/<int:lesson_id>/reparse', type='http', auth='user', website=True, methods=['POST'], csrf=True)
    def lesson_reparse(self, lesson_id, **kwargs):
        lesson = self._get_own_lesson(lesson_id)
        lesson.action_reparse()
        if lesson.state == 'parsed':
            try:
                lesson.action_analyze_novelty()
            except UserError as exc:
                _logger.warning('Lesson %s: novelty analysis failed on reparse: %s', lesson.id, exc)
        return request.redirect(f'/my/lessons/{lesson.id}')
