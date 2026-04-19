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

        # Tally from lines
        challenger_correct = sum(
            1 for l in self.line_ids
            if l.player_id.id == self.challenger_id.id and l.correct
        )
        opponent_correct = sum(
            1 for l in self.line_ids
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
        """Transfer XP between winner and loser. No-op if gamification not installed."""
        if not winner_id or not self.xp_staked:
            return
        try:
            Profile = self.env['language.user.profile'].sudo()
            loser_id = (
                self.opponent_id.id
                if winner_id == self.challenger_id.id
                else self.challenger_id.id
            )
            winner_profile = Profile.search([('user_id', '=', winner_id)], limit=1)
            loser_profile = Profile.search([('user_id', '=', loser_id)], limit=1)
            if winner_profile and hasattr(winner_profile, 'xp_total'):
                winner_profile.xp_total += self.xp_staked
            if loser_profile and hasattr(loser_profile, 'xp_total'):
                loser_profile.xp_total = max(0, loser_profile.xp_total - self.xp_staked)
        except Exception:
            _logger.debug('XP transfer skipped (gamification not installed)', exc_info=True)

    def _rounds_submitted_by(self, user_id):
        """Count duel lines already submitted by this user."""
        return sum(1 for l in self.line_ids if l.player_id.id == user_id)

    def _has_completed_rounds(self, user_id):
        return self._rounds_submitted_by(user_id) >= self.rounds_total
