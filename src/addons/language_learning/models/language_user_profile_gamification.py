"""Gamification extension for language.user.profile (M8).

Adds XP, streak, level, and progress tracking to the existing profile model.
Fields are added via _inherit so language_words is never modified.
"""

import math
import logging
from datetime import timedelta

from odoo import api, fields, models

_logger = logging.getLogger(__name__)

# XP awarded per review grade (0=Again, 1=Hard, 2=Good, 3=Easy)
XP_BY_GRADE = {0: 0, 1: 5, 2: 10, 3: 15}

LEVEL_CAP = 20


def _xp_to_level(xp: int) -> int:
    """Return the level for a given XP total.

    Formula: level = floor(sqrt(xp / 50)) + 1, capped at LEVEL_CAP.
    Inflection points: L2@50, L3@200, L4@450, L5@800, L10@4050, L20@18050.
    """
    return min(LEVEL_CAP, 1 + int(math.sqrt(max(0, xp) / 50)))


def _level_xp_floor(level: int) -> int:
    """Minimum XP required to reach `level`."""
    return 50 * (level - 1) ** 2


def _level_progress_pct(xp: int) -> int:
    """Percentage progress within the current level band (0–100)."""
    lvl = _xp_to_level(xp)
    if lvl >= LEVEL_CAP:
        return 100
    floor_xp = _level_xp_floor(lvl)
    ceil_xp  = _level_xp_floor(lvl + 1)
    return round((xp - floor_xp) / max(1, ceil_xp - floor_xp) * 100)


class LanguageUserProfileGamification(models.Model):
    """Gamification fields added to language.user.profile."""

    _inherit = 'language.user.profile'

    xp_total = fields.Integer(
        string='Total XP',
        default=0,
        help='Experience points balance. Increases on practice/wins; decreases on duel losses (floor 0).',
    )
    current_streak = fields.Integer(
        string='Current Streak (days)',
        default=0,
    )
    longest_streak = fields.Integer(
        string='Longest Streak (days)',
        default=0,
    )
    last_practice_date = fields.Date(
        string='Last Practice Date',
        readonly=True,
        help='Date of the most recent review submission.',
    )
    level = fields.Integer(
        string='Level',
        compute='_compute_level',
        store=True,
        compute_sudo=True,
        default=1,
    )
    level_progress_pct = fields.Integer(
        string='Level Progress %',
        compute='_compute_level_progress',
        store=False,
        compute_sudo=True,
    )

    @api.depends('xp_total')
    def _compute_level(self):
        for rec in self:
            rec.level = _xp_to_level(rec.xp_total)

    @api.depends('xp_total')
    def _compute_level_progress(self):
        for rec in self:
            rec.level_progress_pct = _level_progress_pct(rec.xp_total)

    # ------------------------------------------------------------------ #
    # Public API called by language.review.action_register_review
    # ------------------------------------------------------------------ #

    @api.model
    def _update_gamification_for_user(self, user_id: int, grade: int):
        """Award XP and update streak for user_id after a review with grade.

        Safe to call with grade=0 (Again) — awards 0 XP, still updates streak
        so the user's daily practice counts toward the streak.
        """
        xp_delta = XP_BY_GRADE.get(grade, 0)
        today = fields.Date.today()
        profile = self._get_or_create_for_user(user_id)

        lp = profile.last_practice_date

        if lp == today:
            # Already practiced today — only award XP, streak unchanged
            if xp_delta:
                profile.write({'xp_total': profile.xp_total + xp_delta})
                self.env['language.xp.log'].sudo().create({
                    'user_id': user_id,
                    'amount': xp_delta,
                    'reason': 'practice',
                    'date': fields.Datetime.now(),
                })
            return

        new_streak = profile.current_streak
        if lp == today - timedelta(days=1):
            # Consecutive day — extend streak
            new_streak = profile.current_streak + 1
        else:
            # Gap (or first practice ever) — reset to 1
            new_streak = 1

        profile.write({
            'xp_total':          profile.xp_total + xp_delta,
            'current_streak':    new_streak,
            'longest_streak':    max(profile.longest_streak, new_streak),
            'last_practice_date': today,
        })
        _logger.debug(
            'Gamification update: user=%d grade=%d xp_delta=%d '
            'new_xp=%d streak=%d longest=%d',
            user_id, grade, xp_delta,
            profile.xp_total, new_streak, profile.longest_streak,
        )
        if xp_delta:
            self.env['language.xp.log'].sudo().create({
                'user_id': user_id,
                'amount': xp_delta,
                'reason': 'practice',
                'date': fields.Datetime.now(),
            })

    @api.model
    def _record_duel_activity(self, user_id: int):
        """Mark duel participation as daily activity for streak tracking.

        Does NOT award or deduct XP (handled separately by _transfer_xp).
        Called for both players when a duel finishes so that playing a duel
        counts toward the daily streak even if no practice review was done.
        """
        today = fields.Date.today()
        profile = self._get_or_create_for_user(user_id)

        if profile.last_practice_date == today:
            return  # streak already counted for today

        lp = profile.last_practice_date
        if lp == today - timedelta(days=1):
            new_streak = profile.current_streak + 1
        else:
            new_streak = 1

        profile.write({
            'current_streak':     new_streak,
            'longest_streak':     max(profile.longest_streak, new_streak),
            'last_practice_date': today,
        })
        _logger.debug(
            'Duel activity recorded: user=%d streak=%d longest=%d',
            user_id, new_streak, profile.longest_streak,
        )
