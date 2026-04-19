"""language.review — SM-2 spaced repetition state per user per entry (M7).

SM-2 algorithm (Wozniak 1987):
  EF  = ease factor (min 1.3, default 2.5)
  n   = repetitions (consecutive correct answers)
  I   = interval in days

  grade 0 — Again: reset n=0, I=1, EF unchanged
  grade 1 — Hard:  n unchanged, I = max(1, round(I * 1.2)), EF -= 0.15
  grade 2 — Good:  n += 1, I = _next_interval(n, EF),       EF unchanged
  grade 3 — Easy:  n += 1, I = _next_interval(n, EF) * 1.3, EF += 0.15

  _next_interval(n, EF):
    n == 1 → 1 day
    n == 2 → 4 days
    n >= 3 → round(prev_I * EF)

State machine:
  new      → card never seen
  learning → seen but grade < 2 within the last cycle (short re-study loop)
  review   → n >= 2 (graduated to spaced review)
"""

import logging
import math
from datetime import date, timedelta

from odoo import api, fields, models
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)

GRADE_AGAIN = 0
GRADE_HARD  = 1
GRADE_GOOD  = 2
GRADE_EASY  = 3

EF_DEFAULT   = 2.5
EF_MIN       = 1.3
EF_MAX       = 3.5
INTERVAL_MAX = 36500  # ~100 years; prevents date overflow on aggressive EF

REVIEW_STATES = [
    ('new',      'New'),
    ('learning', 'Learning'),
    ('review',   'Review'),
]


class LanguageReview(models.Model):
    """One SRS card per (user, entry) pair.

    Created automatically when a user visits /my/practice with new entries,
    or explicitly via action_enqueue_entry().  Users never create these
    directly — the practice controller manages card creation.
    """

    _name = 'language.review'
    _description = 'SRS Review Card (SM-2)'
    _rec_name = 'entry_id'
    _order = 'next_review_date asc, id asc'

    entry_id = fields.Many2one(
        comodel_name='language.entry',
        string='Entry',
        required=True,
        ondelete='cascade',
        index=True,
    )
    user_id = fields.Many2one(
        comodel_name='res.users',
        string='User',
        required=True,
        default=lambda self: self.env.user,
        index=True,
        ondelete='cascade',
    )
    state = fields.Selection(
        selection=REVIEW_STATES,
        string='State',
        default='new',
        required=True,
        index=True,
    )
    next_review_date = fields.Date(
        string='Next Review',
        default=fields.Date.today,
        required=True,
        index=True,
    )
    last_review_date = fields.Date(
        string='Last Review',
        readonly=True,
    )
    # Number of consecutive successful reviews (grade >= GOOD)
    repetitions = fields.Integer(
        string='Repetitions',
        default=0,
        help='Consecutive correct answers. Resets to 0 on Again.',
    )
    # Interval in days until the next review
    interval = fields.Integer(
        string='Interval (days)',
        default=0,
    )
    # Ease factor — multiplier applied to interval on each Good answer
    ease_factor = fields.Float(
        string='Ease Factor',
        default=EF_DEFAULT,
        digits=(6, 4),
    )
    # Cumulative stats for this card
    total_reviews = fields.Integer(string='Total Reviews', default=0, readonly=True)
    correct_reviews = fields.Integer(string='Correct Reviews', default=0, readonly=True)

    _sql_constraints = [
        (
            'unique_user_entry',
            'UNIQUE(user_id, entry_id)',
            'A review card already exists for this user and entry.',
        ),
    ]

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    @api.model
    def get_due_cards(self, user_id=None, limit=20):
        """Return up to ``limit`` review cards due today for ``user_id``.

        Priority: learning > new > overdue review > review due today.
        New cards are included up to a daily cap of 20 (configurable later).
        """
        uid = user_id or self.env.uid
        today = fields.Date.today()

        domain = [
            ('user_id', '=', uid),
            ('next_review_date', '<=', today),
        ]
        # Stable ordering: learning first, then new, then review
        return self.search(domain, order='state desc, next_review_date asc, id asc', limit=limit)

    @api.model
    def get_or_create_card(self, entry, user_id=None):
        """Fetch the review card for (user, entry), creating it if absent."""
        uid = user_id or self.env.uid
        card = self.search([('user_id', '=', uid), ('entry_id', '=', entry.id)], limit=1)
        if not card:
            card = self.create({'entry_id': entry.id, 'user_id': uid})
        return card

    def action_register_review(self, grade: int):
        """Apply the SM-2 algorithm for ``grade`` ∈ {0, 1, 2, 3}.

        :param grade: 0=Again, 1=Hard, 2=Good, 3=Easy
        :returns: self (updated)
        """
        self.ensure_one()
        if grade not in (GRADE_AGAIN, GRADE_HARD, GRADE_GOOD, GRADE_EASY):
            raise ValidationError(f'Invalid grade {grade!r}. Must be 0 (Again), 1 (Hard), 2 (Good), or 3 (Easy).')

        today = fields.Date.today()
        ef = self.ease_factor
        n  = self.repetitions
        i  = max(self.interval, 1)

        if grade == GRADE_AGAIN:
            n  = 0
            i  = 1
            # No EF change on Again
            new_state = 'learning'

        elif grade == GRADE_HARD:
            # n stays the same — not a successful repetition
            i  = max(1, round(i * 1.2))
            ef = max(EF_MIN, ef - 0.15)
            new_state = 'learning' if n < 2 else 'review'

        elif grade == GRADE_GOOD:
            n  += 1
            i   = self._next_interval(n, ef, i)
            # EF unchanged
            new_state = 'review' if n >= 2 else 'learning'

        else:  # GRADE_EASY
            n  += 1
            i   = max(1, round(self._next_interval(n, ef, i) * 1.3))
            ef  = min(EF_MAX, ef + 0.15)
            new_state = 'review'

        ef = max(EF_MIN, min(EF_MAX, ef))
        i  = min(i, INTERVAL_MAX)
        next_date = today + timedelta(days=i)

        correct_delta = 1 if grade >= GRADE_GOOD else 0
        self.write({
            'state':            new_state,
            'repetitions':      n,
            'interval':         i,
            'ease_factor':      ef,
            'next_review_date': next_date,
            'last_review_date': today,
            'total_reviews':    self.total_reviews + 1,
            'correct_reviews':  self.correct_reviews + correct_delta,
        })
        _logger.debug(
            'SM-2 review: user=%d entry=%d grade=%d → state=%s n=%d I=%d EF=%.2f next=%s',
            self.user_id.id, self.entry_id.id, grade, new_state, n, i, ef, next_date,
        )

        # Award XP and update streak (M8)
        self.env['language.user.profile'].sudo()._update_gamification_for_user(
            self.user_id.id, grade,
        )

        return self

    # ------------------------------------------------------------------ #
    # SM-2 interval helper
    # ------------------------------------------------------------------ #

    @staticmethod
    def _next_interval(n: int, ef: float, prev_interval: int = 1) -> int:
        """Compute the next interval in days.

        n=1 → 1 day, n=2 → 4 days, n>=3 → round(prev_interval * EF).
        """
        if n == 1:
            return 1
        if n == 2:
            return 4
        return max(1, round(prev_interval * ef))

    # ------------------------------------------------------------------ #
    # Bulk enqueue (called by portal on first visit)
    # ------------------------------------------------------------------ #

    @api.model
    def enqueue_new_entries(self, user_id=None, batch=20):
        """Create review cards for up to ``batch`` active entries that
        have no card yet.  Called once per session from the practice portal.
        """
        uid = user_id or self.env.uid
        today = fields.Date.today()

        # Entries that already have a card for this user
        existing_entry_ids = self.search([('user_id', '=', uid)]).mapped('entry_id').ids

        domain = [
            ('owner_id', '=', uid),
            ('status', '=', 'active'),
            ('id', 'not in', existing_entry_ids),
        ]
        new_entries = self.env['language.entry'].sudo().search(domain, limit=batch)
        for entry in new_entries:
            self.sudo().create({
                'entry_id': entry.id,
                'user_id': uid,
                'next_review_date': today,
            })
        if new_entries:
            _logger.info('SRS: enqueued %d new cards for user=%d', len(new_entries), uid)
        return len(new_entries)

    # ------------------------------------------------------------------ #
    # Computed accuracy helper (used in portal template)
    # ------------------------------------------------------------------ #

    @api.depends('total_reviews', 'correct_reviews')
    def _compute_accuracy(self):
        for rec in self:
            rec.accuracy = (
                round(rec.correct_reviews / rec.total_reviews * 100)
                if rec.total_reviews else 0
            )

    accuracy = fields.Integer(
        string='Accuracy %',
        compute='_compute_accuracy',
        store=False,
    )
