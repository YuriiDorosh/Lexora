import random
import logging
from datetime import datetime

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)

MIN_ENTRIES_PARAM = 'language.pvp.min_entries'
_DEFAULT_MIN_ENTRIES = 10


class LanguageDuel(models.Model):
    _name = 'language.duel'
    _description = 'PvP Word Duel'
    _order = 'create_date desc'

    challenger_id = fields.Many2one('res.users', string='Challenger', required=True,
                                    ondelete='restrict')
    opponent_id = fields.Many2one('res.users', string='Opponent', ondelete='restrict')
    state = fields.Selection([
        ('open', 'Open'),
        ('ongoing', 'Ongoing'),
        ('finished', 'Finished'),
        ('cancel', 'Cancelled'),
    ], default='open', required=True, index=True)
    winner_id = fields.Many2one('res.users', string='Winner', ondelete='set null')

    practice_language = fields.Selection([
        ('en', 'English'), ('uk', 'Ukrainian'), ('el', 'Greek'),
    ], required=True, string='Practice Language')
    native_language = fields.Selection([
        ('en', 'English'), ('uk', 'Ukrainian'), ('el', 'Greek'),
    ], required=True, string='Native Language')

    xp_staked = fields.Integer(default=10, string='XP Staked')
    rounds_total = fields.Integer(default=10, string='Total Rounds')
    challenger_score = fields.Integer(default=0)
    opponent_score = fields.Integer(default=0)

    start_date = fields.Datetime(string='Started')
    end_date = fields.Datetime(string='Ended')

    line_ids = fields.One2many('language.duel.line', 'duel_id', string='Round Lines')

    # ------------------------------------------------------------------
    # Computed helpers
    # ------------------------------------------------------------------

    def _get_min_entries(self):
        param = self.env['ir.config_parameter'].sudo().get_param(MIN_ENTRIES_PARAM)
        try:
            return int(param or _DEFAULT_MIN_ENTRIES)
        except (TypeError, ValueError):
            return _DEFAULT_MIN_ENTRIES

    def _get_eligible_entries(self, user_id):
        """Return pvp_eligible=True entries in practice_language owned by user_id."""
        Entry = self.env['language.entry']
        return Entry.sudo().search([
            ('owner_id', '=', user_id),
            ('source_language', '=', self.practice_language),
            ('pvp_eligible', '=', True),
            ('status', '=', 'active'),
        ])

    def _check_min_entries(self, user_id):
        min_e = self._get_min_entries()
        entries = self._get_eligible_entries(user_id)
        if len(entries) < min_e:
            raise UserError(
                f'You need at least {min_e} PvP-eligible entries in '
                f'{self.practice_language.upper()} to participate in a duel. '
                f'You currently have {len(entries)}.'
            )

    def _select_round_entries(self, user_id, n):
        """Return a random sample of n eligible entries for user_id."""
        entries = self._get_eligible_entries(user_id)
        if not entries:
            return entries.browse([])
        ids = entries.ids
        sample_ids = random.sample(ids, min(n, len(ids)))
        return entries.browse(sample_ids)

    # ------------------------------------------------------------------
    # State transitions
    # ------------------------------------------------------------------

    def action_join(self, user_id):
        """Opponent joins an open challenge."""
        self.ensure_one()
        if self.state != 'open':
            raise UserError('This challenge is no longer open.')
        if self.challenger_id.id == user_id:
            raise UserError('You cannot join your own challenge.')
        self._check_min_entries(user_id)
        self.write({
            'opponent_id': user_id,
            'state': 'ongoing',
            'start_date': fields.Datetime.now(),
        })
        return self

    def action_finish_duel(self):
        """Tally scores, determine winner, transfer XP."""
        self.ensure_one()
        if self.state != 'ongoing':
            return

        # Use sudo so record-rule filtering on duel.line does not distort tallies
        Line = self.env['language.duel.line'].sudo()
        all_lines = Line.search([('duel_id', '=', self.id)])
        challenger_correct = sum(
            1 for l in all_lines
            if l.player_id.id == self.challenger_id.id and l.correct
        )
        opponent_correct = sum(
            1 for l in all_lines
            if self.opponent_id and l.player_id.id == self.opponent_id.id and l.correct
        )

        if challenger_correct > opponent_correct:
            winner_id = self.challenger_id.id
        elif opponent_correct > challenger_correct:
            winner_id = self.opponent_id.id if self.opponent_id else False
        else:
            winner_id = False  # draw

        vals = {
            'state': 'finished',
            'end_date': fields.Datetime.now(),
            'challenger_score': challenger_correct,
            'opponent_score': opponent_correct,
            'winner_id': winner_id,
        }
        self.write(vals)

        # XP transfer (requires M8 gamification fields on language.user.profile)
        self._transfer_xp(winner_id)

        return self

    # ------------------------------------------------------------------
    # Convenience
    # ------------------------------------------------------------------

    def _transfer_xp(self, winner_id):
        """Transfer XP and record streak activity for both players.

        winner_id=False means draw — no XP moves but both players still get
        streak credit and a duel_draw log entry.
        """
        challenger_id = self.challenger_id.id
        opponent_id   = self.opponent_id.id if self.opponent_id else None
        try:
            Profile = self.env['language.user.profile'].sudo()
            has_gamification = hasattr(
                Profile.search([('user_id', '=', challenger_id)], limit=1),
                'xp_total',
            )

            if winner_id and self.xp_staked and has_gamification:
                loser_id = opponent_id if winner_id == challenger_id else challenger_id
                winner_profile = Profile.search([('user_id', '=', winner_id)], limit=1)
                loser_profile  = Profile.search([('user_id', '=', loser_id)],  limit=1)

                if winner_profile:
                    winner_profile.xp_total += self.xp_staked
                if loser_profile:
                    # Floor at 0; log the amount actually deducted
                    actual_loss = min(loser_profile.xp_total, self.xp_staked)
                    loser_profile.xp_total -= actual_loss

                if 'language.xp.log' in self.env.registry:
                    Log = self.env['language.xp.log'].sudo()
                    Log.create({
                        'user_id': winner_id,
                        'amount':  self.xp_staked,
                        'reason':  'duel_win',
                        'duel_id': self.id,
                    })
                    Log.create({
                        'user_id': loser_id,
                        'amount':  -actual_loss,
                        'reason':  'duel_loss',
                        'duel_id': self.id,
                    })
            elif not winner_id:
                # Draw — log activity for both, no XP movement
                if 'language.xp.log' in self.env.registry:
                    Log = self.env['language.xp.log'].sudo()
                    for uid in filter(None, [challenger_id, opponent_id]):
                        Log.create({
                            'user_id': uid,
                            'amount':  0,
                            'reason':  'duel_draw',
                            'duel_id': self.id,
                        })

        except Exception:
            _logger.debug('XP transfer skipped (gamification not installed)', exc_info=True)

        # Record duel participation toward daily streak — runs unconditionally
        # so a gamification failure above never silently blocks streak tracking.
        try:
            Profile = self.env['language.user.profile'].sudo()
            if hasattr(Profile, '_record_duel_activity'):
                for uid in filter(None, [challenger_id, opponent_id]):
                    Profile._record_duel_activity(uid)
        except Exception:
            _logger.warning('Streak update failed after duel %d', self.id, exc_info=True)

    def _rounds_submitted_by(self, user_id):
        """Count duel lines submitted by this user (sudo bypasses record rules)."""
        return self.env['language.duel.line'].sudo().search_count([
            ('duel_id', '=', self.id),
            ('player_id', '=', user_id),
        ])

    def _has_completed_rounds(self, user_id):
        return self._rounds_submitted_by(user_id) >= self.rounds_total

    def action_cancel(self):
        """Cancel an open challenge (challenger only)."""
        self.ensure_one()
        if self.state != 'open':
            raise UserError('Only open challenges can be cancelled.')
        self.write({'state': 'cancel'})
        return self

    # ------------------------------------------------------------------
    # Bot support
    # ------------------------------------------------------------------

    def _get_or_create_bot_user(self):
        """Return the Lexora Bot system user, creating it if absent.

        Must be active=True so Odoo allows it as a Many2one target.
        active_test=False ensures we find it even if it was previously archived.
        """
        User = self.env['res.users'].sudo().with_context(active_test=False)
        bot = User.search([('login', '=', 'lexora_bot@system')], limit=1)
        if bot:
            if not bot.active:
                bot.write({'active': True})
            return bot
        return User.create({
            'name': 'Lexora Bot',
            'login': 'lexora_bot@system',
            'email': 'lexora_bot@system',
            'active': True,
        })

    def action_summon_bot(self):
        """Fill opponent slot with the Lexora Bot and pre-generate its answers."""
        self.ensure_one()
        if self.state != 'open':
            raise UserError('Only open challenges can summon the bot.')
        if self.challenger_id.id != self.env.user.id:
            raise UserError('Only the challenger can summon the bot.')

        bot = self._get_or_create_bot_user()
        self.write({
            'opponent_id': bot.id,
            'state': 'ongoing',
            'start_date': fields.Datetime.now(),
        })

        # Generate bot answers (70 % accuracy)
        entries = self._select_round_entries(self.challenger_id.id, self.rounds_total)
        Line = self.env['language.duel.line'].sudo()
        for i, entry in enumerate(entries):
            correct = random.random() < 0.70
            Line.create({
                'duel_id': self.id,
                'player_id': bot.id,
                'entry_id': entry.id,
                'round_number': i + 1,
                'correct': correct,
                'answer_given': '[bot]',
            })
        return self
