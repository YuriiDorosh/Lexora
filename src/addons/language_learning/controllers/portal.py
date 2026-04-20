import logging

from odoo import fields, http
from odoo.http import request

from odoo.addons.portal.controllers.portal import CustomerPortal
from odoo.addons.portal.controllers.portal import pager as portal_pager

_logger = logging.getLogger(__name__)

GRADE_LABELS = {0: 'Again', 1: 'Hard', 2: 'Good', 3: 'Easy'}
LEADERBOARD_PAGE_SIZE = 20

LANG_NAMES = {'en': 'English', 'uk': 'Ukrainian', 'el': 'Greek'}

REASON_LABELS = {
    'duel_win':      'Duel Win',
    'duel_loss':     'Duel Loss',
    'duel_draw':     'Duel Draw',
    'practice':      'Practice',
    'bonus':         'Bonus',
    'initial':       'Initial Balance',
    'shop_purchase': 'Shop Purchase',
}


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

        domain = ['|', ('xp_total', '>', 0), ('current_streak', '>', 0)]
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
        if my_profile and (my_profile.xp_total > 0 or my_profile.current_streak > 0):
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

    # ------------------------------------------------------------------
    # GET /my/dashboard — XP command centre
    # ------------------------------------------------------------------

    @http.route('/my/dashboard', type='http', auth='user', website=True, methods=['GET'])
    def user_dashboard(self, **kw):
        uid = request.env.user.id
        Profile = request.env['language.user.profile'].sudo()

        profile = Profile.search([('user_id', '=', uid)], limit=1)

        # XP history — last 20 entries for this user
        xp_logs = request.env['language.xp.log'].sudo().search(
            [('user_id', '=', uid)], limit=20,
        )

        # Global rank
        my_rank = None
        if profile and (profile.xp_total > 0 or profile.current_streak > 0):
            my_rank = Profile.search_count([('xp_total', '>', profile.xp_total)]) + 1

        # Duel stats — graceful if language_pvp not installed
        duel_wins = duel_losses = duel_draws = duel_total = 0
        recent_duels = []
        if 'language.duel' in request.env.registry:
            Duel = request.env['language.duel'].sudo()
            finished = [
                ('state', '=', 'finished'),
                '|',
                ('challenger_id', '=', uid),
                ('opponent_id', '=', uid),
            ]
            duel_wins    = Duel.search_count(finished + [('winner_id', '=', uid)])
            duel_losses  = Duel.search_count(
                finished + [('winner_id', '!=', False), ('winner_id', '!=', uid)]
            )
            duel_draws   = Duel.search_count(finished + [('winner_id', '=', False)])
            duel_total   = duel_wins + duel_losses + duel_draws
            recent_duels = Duel.search(finished, limit=5, order='end_date desc')

        win_rate_pct = round(duel_wins / duel_total * 100) if duel_total else 0

        return request.render('language_learning.portal_user_dashboard', {
            'page_name':    'dashboard',
            'profile':      profile,
            'xp_logs':      xp_logs,
            'my_rank':      my_rank,
            'reason_labels': REASON_LABELS,
            'duel_wins':    duel_wins,
            'duel_losses':  duel_losses,
            'duel_draws':   duel_draws,
            'duel_total':   duel_total,
            'win_rate_pct': win_rate_pct,
            'recent_duels': recent_duels,
            'lang_names':   LANG_NAMES,
            'uid':          uid,
        })

    # ------------------------------------------------------------------
    # GET /my/shop — XP shop
    # ------------------------------------------------------------------

    @http.route('/my/shop', type='http', auth='user', website=True, methods=['GET'])
    def xp_shop(self, **kw):
        uid = request.env.user.id
        ShopItem = request.env['language.shop.item'].sudo()
        UserItem = request.env['language.user.item'].sudo()
        Profile = request.env['language.user.profile'].sudo()

        items = ShopItem.search([('is_active', '=', True)])
        profile = Profile.search([('user_id', '=', uid)], limit=1)
        xp_balance = profile.xp_total if profile else 0

        # Build owned counts per item type for the UI
        owned = {}
        for item in items:
            owned[item.id] = UserItem.search_count([
                ('user_id', '=', uid),
                ('item_id', '=', item.id),
                ('is_consumed', '=', False),
            ])

        flash = kw.get('flash')
        return request.render('language_learning.portal_xp_shop', {
            'page_name':   'shop',
            'items':       items,
            'xp_balance':  xp_balance,
            'owned':       owned,
            'flash':       flash,
        })

    # ------------------------------------------------------------------
    # POST /my/shop/buy/<item_id> — purchase item
    # ------------------------------------------------------------------

    @http.route('/my/shop/buy/<int:item_id>', type='http', auth='user',
                website=True, methods=['POST'])
    def xp_shop_buy(self, item_id, **kw):
        uid = request.env.user.id
        ShopItem = request.env['language.shop.item'].sudo()
        item = ShopItem.search([('id', '=', item_id), ('is_active', '=', True)], limit=1)
        if not item:
            return request.not_found()

        try:
            item.action_buy(uid)
            return request.redirect(f'/my/shop?flash=bought&item={item.name}')
        except Exception as exc:
            _logger.warning('Shop purchase failed for user %d item %d: %s', uid, item_id, exc)
            return request.redirect(f'/my/shop?flash=error&msg={request.env._(str(exc))}')

    # ------------------------------------------------------------------
    # GET /my/inventory — owned items
    # ------------------------------------------------------------------

    @http.route('/my/inventory', type='http', auth='user', website=True, methods=['GET'])
    def xp_inventory(self, **kw):
        uid = request.env.user.id
        UserItem = request.env['language.user.item'].sudo()
        user_items = UserItem.search([
            ('user_id', '=', uid),
            ('is_consumed', '=', False),
        ])
        return request.render('language_learning.portal_xp_inventory', {
            'page_name':  'inventory',
            'user_items': user_items,
        })
