import logging

from odoo import fields, http
from odoo.http import request

from odoo.addons.portal.controllers.portal import CustomerPortal
from odoo.addons.portal.controllers.portal import pager as portal_pager

_logger = logging.getLogger(__name__)

GRADE_LABELS = {0: 'Again', 1: 'Hard', 2: 'Good', 3: 'Easy'}
LEADERBOARD_PAGE_SIZE = 20


class PracticePortal(CustomerPortal):

    # ------------------------------------------------------------------
    # Portal home widget — supplies due-card count for /my
    # ------------------------------------------------------------------

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        if 'practice_due_count' in counters:
            today = fields.Date.today()
            values['practice_due_count'] = request.env['language.review'].search_count([
                ('user_id', '=', request.env.uid),
                ('next_review_date', '<=', today),
            ])
        return values

    # ------------------------------------------------------------------
    # /my/practice — daily practice index
    # ------------------------------------------------------------------

    @http.route('/my/practice', type='http', auth='user', website=True, methods=['GET'])
    def practice_index(self, **kw):
        user = request.env.user
        Review = request.env['language.review'].sudo()

        # Enqueue any new active entries that have no card yet (up to 20)
        Review.enqueue_new_entries(user_id=user.id, batch=20)

        cards = Review.get_due_cards(user_id=user.id, limit=20)

        return request.render('language_learning.portal_practice', {
            'cards': cards,
            'total_due': len(cards),
            'grade_labels': GRADE_LABELS,
        })

    # ------------------------------------------------------------------
    # POST /my/practice/review/<card_id> — apply SM-2 grade
    # ------------------------------------------------------------------

    @http.route('/my/practice/review/<int:card_id>', type='http', auth='user',
                website=True, methods=['POST'])
    def practice_review(self, card_id, grade=None, **kw):
        Review = request.env['language.review'].sudo()
        card = Review.search([
            ('id', '=', card_id),
            ('user_id', '=', request.env.user.id),
        ], limit=1)

        if not card:
            return request.not_found()

        try:
            grade_int = int(grade)
        except (TypeError, ValueError):
            grade_int = 0

        card.action_register_review(grade_int)
        return request.redirect('/my/practice')

    # ------------------------------------------------------------------
    # GET /my/leaderboard — XP leaderboard (paginated)
    # ------------------------------------------------------------------

    @http.route('/my/leaderboard', type='http', auth='user', website=True, methods=['GET'])
    def leaderboard(self, page=1, **kw):
        Profile = request.env['language.user.profile'].sudo()
        uid = request.env.user.id

        domain = [('xp_total', '>', 0)]
        total = Profile.search_count(domain)

        pager = portal_pager(
            url='/my/leaderboard',
            total=total,
            page=int(page),
            step=LEADERBOARD_PAGE_SIZE,
        )

        profiles = Profile.search(
            domain,
            order='xp_total desc, current_streak desc, id asc',
            limit=LEADERBOARD_PAGE_SIZE,
            offset=pager['offset'],
        )

        # Compute global rank for current user
        my_profile = Profile.search([('user_id', '=', uid)], limit=1)
        my_rank = None
        if my_profile and my_profile.xp_total > 0:
            my_rank = Profile.search_count([
                ('xp_total', '>', my_profile.xp_total),
            ]) + 1

        # Build ranked rows (offset + position within page)
        ranked = []
        for pos, p in enumerate(profiles, start=pager['offset'] + 1):
            ranked.append({
                'rank': pos,
                'profile': p,
                'is_me': p.user_id.id == uid,
            })

        return request.render('language_learning.portal_leaderboard', {
            'ranked': ranked,
            'pager': pager,
            'total': total,
            'my_rank': my_rank,
            'my_profile': my_profile,
        })
