"""Portal controller for PvP Arena (/my/arena).

Routes:
  GET  /my/arena                — lobby: open challenges, active duels, history
  POST /my/arena/new            — create an open challenge
  GET  /my/arena/<id>           — duel detail / play screen
  POST /my/arena/<id>/join      — accept an open challenge
  POST /my/arena/<id>/answer    — submit an answer for one round
"""

import logging

from odoo import http
from odoo.exceptions import UserError
from odoo.http import request

from odoo.addons.portal.controllers.portal import CustomerPortal
from odoo.addons.portal.controllers.portal import pager as portal_pager

_logger = logging.getLogger(__name__)

LANG_NAMES = {'en': 'English', 'uk': 'Ukrainian', 'el': 'Greek'}


class ArenaPortal(CustomerPortal):

    # ------------------------------------------------------------------
    # Portal home widget
    # ------------------------------------------------------------------

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        if 'arena_active_count' in counters:
            uid = request.env.user.id
            Duel = request.env['language.duel']
            values['arena_active_count'] = Duel.search_count([
                ('state', 'in', ['open', 'ongoing']),
                '|',
                ('challenger_id', '=', uid),
                ('opponent_id', '=', uid),
            ])
        return values

    # ------------------------------------------------------------------
    # Lobby  GET /my/arena
    # ------------------------------------------------------------------

    @http.route('/my/arena', type='http', auth='user', website=True)
    def arena_lobby(self, **kwargs):
        uid = request.env.user.id
        Duel = request.env['language.duel']

        # Open challenges from others that match any of user's learning languages
        profile = request.env['language.user.profile'].search(
            [('user_id', '=', uid)], limit=1
        )
        learning_langs = (
            [l.code for l in profile.learning_languages]
            if profile and profile.learning_languages
            else ['en', 'uk', 'el']
        )

        open_challenges = Duel.search([
            ('state', '=', 'open'),
            ('opponent_id', '=', False),
            ('challenger_id', '!=', uid),
            ('practice_language', 'in', learning_langs),
        ], limit=10, order='create_date desc')

        active_duels = Duel.search([
            ('state', 'in', ['open', 'ongoing']),
            '|',
            ('challenger_id', '=', uid),
            ('opponent_id', '=', uid),
        ], order='create_date desc')

        recent_history = Duel.search([
            ('state', '=', 'finished'),
            '|',
            ('challenger_id', '=', uid),
            ('opponent_id', '=', uid),
        ], limit=10, order='end_date desc')

        return request.render('language_pvp.portal_arena_lobby', {
            'page_name': 'arena',
            'open_challenges': open_challenges,
            'active_duels': active_duels,
            'recent_history': recent_history,
            'lang_names': LANG_NAMES,
            'uid': uid,
            'languages': [('en', 'English'), ('uk', 'Ukrainian'), ('el', 'Greek')],
        })

    # ------------------------------------------------------------------
    # Create challenge  POST /my/arena/new
    # ------------------------------------------------------------------

    @http.route('/my/arena/new', type='http', auth='user', website=True,
                methods=['POST'])
    def arena_new(self, **post):
        uid = request.env.user.id
        practice_language = post.get('practice_language', 'en')
        native_language = post.get('native_language', 'uk')
        xp_staked = int(post.get('xp_staked', 10) or 10)
        rounds_total = int(post.get('rounds_total', 10) or 10)

        if practice_language == native_language:
            return request.redirect('/my/arena?error=same_language')

        Duel = request.env['language.duel']

        # Quick eligibility check before creating
        tmp_duel = Duel.new({
            'challenger_id': uid,
            'practice_language': practice_language,
            'native_language': native_language,
        })
        try:
            tmp_duel._check_min_entries(uid)
        except UserError as exc:
            return request.redirect(
                '/my/arena?error=%s' % http.url_quote(str(exc.args[0]))
            )

        duel = Duel.create({
            'challenger_id': uid,
            'practice_language': practice_language,
            'native_language': native_language,
            'xp_staked': max(0, xp_staked),
            'rounds_total': max(1, min(20, rounds_total)),
            'state': 'open',
        })
        return request.redirect('/my/arena/%d' % duel.id)

    # ------------------------------------------------------------------
    # Duel detail  GET /my/arena/<id>
    # ------------------------------------------------------------------

    @http.route('/my/arena/<int:duel_id>', type='http', auth='user', website=True)
    def arena_duel(self, duel_id, **kwargs):
        uid = request.env.user.id
        duel = request.env['language.duel'].browse(duel_id)
        if not duel.exists():
            return request.not_found()
        if (duel.challenger_id.id != uid and
                (not duel.opponent_id or duel.opponent_id.id != uid) and
                duel.state != 'open'):
            return request.not_found()

        current_entry = None
        round_number = None
        if duel.state == 'ongoing':
            submitted = duel._rounds_submitted_by(uid)
            if submitted < duel.rounds_total:
                round_number = submitted + 1
                eligible = duel._get_eligible_entries(uid)
                used_ids = {
                    l.entry_id.id for l in duel.line_ids if l.player_id.id == uid
                }
                remaining = eligible.filtered(lambda e: e.id not in used_ids)
                if remaining:
                    import random
                    current_entry = random.choice(remaining)
                elif eligible:
                    import random
                    current_entry = random.choice(eligible)

        # Check if duel should be auto-finished
        if duel.state == 'ongoing' and duel.opponent_id:
            challenger_done = duel._has_completed_rounds(duel.challenger_id.id)
            opponent_done = duel._has_completed_rounds(duel.opponent_id.id)
            if challenger_done and opponent_done:
                duel.action_finish_duel()
                duel.invalidate_recordset()

        # Compute per-player stats for finished duel
        challenger_lines = []
        opponent_lines = []
        if duel.state == 'finished':
            challenger_lines = duel.line_ids.sudo().filtered(
                lambda l: l.player_id.id == duel.challenger_id.id
            ).sorted('round_number')
            opponent_lines = (
                duel.line_ids.sudo().filtered(
                    lambda l: l.player_id.id == duel.opponent_id.id
                ).sorted('round_number')
                if duel.opponent_id else []
            )

        return request.render('language_pvp.portal_arena_duel', {
            'page_name': 'arena',
            'duel': duel,
            'uid': uid,
            'lang_names': LANG_NAMES,
            'current_entry': current_entry,
            'round_number': round_number,
            'challenger_lines': challenger_lines,
            'opponent_lines': opponent_lines,
        })

    # ------------------------------------------------------------------
    # Join challenge  POST /my/arena/<id>/join
    # ------------------------------------------------------------------

    @http.route('/my/arena/<int:duel_id>/join', type='http', auth='user',
                website=True, methods=['POST'])
    def arena_join(self, duel_id, **post):
        uid = request.env.user.id
        duel = request.env['language.duel'].browse(duel_id)
        if not duel.exists():
            return request.not_found()
        try:
            duel.action_join(uid)
        except UserError as exc:
            return request.redirect(
                '/my/arena?error=%s' % http.url_quote(str(exc.args[0]))
            )
        return request.redirect('/my/arena/%d' % duel_id)

    # ------------------------------------------------------------------
    # Submit answer  POST /my/arena/<id>/answer
    # ------------------------------------------------------------------

    @http.route('/my/arena/<int:duel_id>/answer', type='http', auth='user',
                website=True, methods=['POST'])
    def arena_answer(self, duel_id, **post):
        uid = request.env.user.id
        duel = request.env['language.duel'].browse(duel_id)
        if not duel.exists() or duel.state != 'ongoing':
            return request.not_found()
        if duel.challenger_id.id != uid and (
                not duel.opponent_id or duel.opponent_id.id != uid):
            return request.not_found()

        if duel._has_completed_rounds(uid):
            return request.redirect('/my/arena/%d' % duel_id)

        entry_id = int(post.get('entry_id', 0) or 0)
        answer_given = (post.get('answer_given', '') or '').strip()
        round_number = duel._rounds_submitted_by(uid) + 1

        entry = request.env['language.entry'].sudo().browse(entry_id)
        if not entry.exists():
            return request.redirect('/my/arena/%d' % duel_id)

        # Check correctness: answer matches any completed translation
        correct = any(
            t.translated_text and
            t.translated_text.strip().lower() == answer_given.lower()
            for t in entry.translation_ids
            if t.status == 'completed'
        )

        request.env['language.duel.line'].sudo().create({
            'duel_id': duel_id,
            'player_id': uid,
            'entry_id': entry_id,
            'round_number': round_number,
            'correct': correct,
            'answer_given': answer_given,
        })

        # Invalidate cache so _rounds_submitted_by sees the new line
        duel.invalidate_recordset()

        # Auto-finish when both players done
        if duel.opponent_id:
            challenger_done = duel._has_completed_rounds(duel.challenger_id.id)
            opponent_done = duel._has_completed_rounds(duel.opponent_id.id)
            if challenger_done and opponent_done:
                duel.action_finish_duel()

        return request.redirect('/my/arena/%d' % duel_id)

    # ------------------------------------------------------------------
    # Cancel challenge  POST /my/arena/<id>/cancel
    # ------------------------------------------------------------------

    @http.route('/my/arena/<int:duel_id>/cancel', type='http', auth='user',
                website=True, methods=['POST'])
    def arena_cancel(self, duel_id, **post):
        uid = request.env.user.id
        duel = request.env['language.duel'].browse(duel_id)
        if not duel.exists():
            return request.not_found()
        if duel.challenger_id.id != uid:
            return request.redirect('/my/arena?error=not_your_challenge')
        try:
            duel.action_cancel()
        except UserError as exc:
            return request.redirect(
                '/my/arena?error=%s' % http.url_quote(str(exc.args[0]))
            )
        return request.redirect('/my/arena')

    # ------------------------------------------------------------------
    # Summon bot  POST /my/arena/<id>/summon_bot
    # ------------------------------------------------------------------

    @http.route('/my/arena/<int:duel_id>/summon_bot', type='http', auth='user',
                website=True, methods=['POST'])
    def arena_summon_bot(self, duel_id, **post):
        uid = request.env.user.id
        duel = request.env['language.duel'].browse(duel_id)
        if not duel.exists():
            return request.not_found()
        if duel.challenger_id.id != uid:
            return request.redirect('/my/arena?error=not_your_challenge')
        try:
            duel.action_summon_bot()
        except UserError as exc:
            return request.redirect(
                '/my/arena/%d?error=%s' % (duel_id, http.url_quote(str(exc.args[0])))
            )
        return request.redirect('/my/arena/%d' % duel_id)
