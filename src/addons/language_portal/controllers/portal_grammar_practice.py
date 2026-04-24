import logging
from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)

_EXERCISE_SETS = [
    {
        'icon': '⏱️', 'title': 'Tense Trainer',
        'description': 'Fill in the blanks with the correct verb tense across all 12 English tenses.',
        'level': 'A2–B2', 'questions': 20,
    },
    {
        'icon': '📰', 'title': 'Article Master',
        'description': 'Choose the correct article (a / an / the / zero) for each sentence.',
        'level': 'A1–B1', 'questions': 15,
    },
    {
        'icon': '🔀', 'title': 'Conditional Mix',
        'description': 'Complete the conditional sentences using the correct structure (0–3).',
        'level': 'B1–C1', 'questions': 12,
    },
    {
        'icon': '🎭', 'title': 'Passive Voice',
        'description': 'Transform active sentences to passive voice and vice versa.',
        'level': 'B1–B2', 'questions': 10,
    },
    {
        'icon': '🗣️', 'title': 'Modal Verbs',
        'description': 'Select the right modal verb to express ability, obligation, or possibility.',
        'level': 'A2–B2', 'questions': 15,
    },
    {
        'icon': '📣', 'title': 'Reported Speech',
        'description': 'Convert direct speech into reported speech with correct tense shifts.',
        'level': 'B1–C1', 'questions': 12,
    },
]


class GrammarPracticeController(http.Controller):

    @http.route('/my/grammar-practice', type='http', auth='user', website=True,
                methods=['GET'])
    def grammar_practice_index(self, **kw):
        return request.render('language_portal.portal_grammar_practice_index', {
            'exercise_sets': _EXERCISE_SETS,
        })
