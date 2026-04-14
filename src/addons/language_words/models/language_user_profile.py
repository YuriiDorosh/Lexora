from odoo import api, fields, models

from .language_lang import LANGUAGE_SELECTION


class LanguageUserProfile(models.Model):
    """Per-user language learning preferences and PvP statistics (SPEC §3.3)."""

    _name = 'language.user.profile'
    _description = 'Language User Profile'
    _rec_name = 'user_id'

    user_id = fields.Many2one(
        comodel_name='res.users',
        string='User',
        required=True,
        ondelete='cascade',
        index=True,
    )
    native_language = fields.Selection(
        selection=LANGUAGE_SELECTION,
        string='Native Language',
    )
    learning_languages = fields.Many2many(
        comodel_name='language.lang',
        relation='language_user_profile_lang_rel',
        column1='profile_id',
        column2='lang_id',
        string='Learning Languages',
    )
    default_source_language = fields.Selection(
        selection=LANGUAGE_SELECTION,
        string='Default Source Language',
        help='Pre-filled when language detection confidence is low.',
    )

    # PvP statistics (M10 will populate these via battle outcomes)
    pvp_total_battles = fields.Integer(string='Total Battles', default=0)
    pvp_wins = fields.Integer(string='Wins', default=0)
    pvp_losses = fields.Integer(string='Losses', default=0)
    pvp_draws = fields.Integer(string='Draws', default=0)
    pvp_win_rate = fields.Float(
        string='Win Rate',
        compute='_compute_pvp_win_rate',
        store=True,
        digits=(5, 2),
    )

    is_shared_list = fields.Boolean(
        string='Share Vocabulary List',
        default=False,
        help='When True, the whole vocabulary list is visible to other Language Users.',
    )

    _sql_constraints = [
        ('unique_user', 'UNIQUE(user_id)', 'Each user can have only one language profile.'),
    ]

    @api.depends('pvp_wins', 'pvp_total_battles')
    def _compute_pvp_win_rate(self):
        for profile in self:
            if profile.pvp_total_battles:
                profile.pvp_win_rate = profile.pvp_wins / profile.pvp_total_battles * 100.0
            else:
                profile.pvp_win_rate = 0.0

    @api.model
    def _get_or_create_for_user(self, user_id=None):
        """Return (or lazily create) the profile for the given user.

        :param user_id: res.users record, integer user ID, or None (defaults to env.uid)
        """
        from odoo.models import BaseModel  # noqa: PLC0415
        raw = user_id or self.env.uid
        uid = raw.id if isinstance(raw, BaseModel) else raw
        profile = self.search([('user_id', '=', uid)], limit=1)
        if not profile:
            profile = self.create({'user_id': uid})
        return profile
