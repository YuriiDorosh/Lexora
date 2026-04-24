import logging
from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)

_SCENARIOS = [
    {
        'icon': '🛒', 'title': 'Shopping Trip',
        'description': 'Practice asking for prices, sizes, and making purchases.',
        'level': 'A2', 'duration': '5–10 min',
    },
    {
        'icon': '🍽️', 'title': 'At the Restaurant',
        'description': 'Order food, ask about the menu, handle dietary restrictions.',
        'level': 'A2', 'duration': '5–10 min',
    },
    {
        'icon': '🏥', 'title': 'Doctor Visit',
        'description': 'Describe symptoms, understand medical instructions.',
        'level': 'B1', 'duration': '10–15 min',
    },
    {
        'icon': '✈️', 'title': 'Airport & Travel',
        'description': 'Check in, navigate the airport, ask for assistance.',
        'level': 'B1', 'duration': '10–15 min',
    },
    {
        'icon': '💼', 'title': 'Job Interview',
        'description': 'Discuss your experience, strengths, and career goals.',
        'level': 'B2', 'duration': '15–20 min',
    },
    {
        'icon': '📞', 'title': 'Phone Call',
        'description': 'Make appointments, handle service calls, leave messages.',
        'level': 'B2', 'duration': '10–15 min',
    },
]


class RoleplayController(http.Controller):

    @http.route('/my/roleplay', type='http', auth='user', website=True, methods=['GET'])
    def roleplay_index(self, **kw):
        return request.render('language_portal.portal_roleplay_index', {
            'scenarios': _SCENARIOS,
        })
