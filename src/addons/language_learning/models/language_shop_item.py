import logging

from odoo import api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

ITEM_TYPES = [
    ('streak_freeze', 'Streak Freeze'),
    ('profile_frame', 'Profile Frame'),
    ('double_xp',     'Double XP Booster'),
]


class LanguageShopItem(models.Model):
    _name = 'language.shop.item'
    _description = 'XP Shop Item'
    _order = 'xp_cost asc, name asc'

    name = fields.Char(required=True)
    description = fields.Text()
    xp_cost = fields.Integer(required=True, string='XP Cost')
    item_type = fields.Selection(ITEM_TYPES, required=True, string='Type')
    icon = fields.Char(default='🎁', help='Emoji or short icon text shown in the shop.')
    is_active = fields.Boolean(default=True, string='Available in Shop')

    def action_buy(self, user_id):
        """Purchase this item for user_id.

        Deducts xp_cost from the user's XP balance via a shop_purchase log entry,
        creates a language.user.item record, and returns the new user-item.
        Raises UserError if the user's balance is insufficient.
        """
        self.ensure_one()
        Profile = self.env['language.user.profile'].sudo()
        profile = Profile.search([('user_id', '=', user_id)], limit=1)
        if not profile:
            raise UserError('User profile not found.')

        if profile.xp_total < self.xp_cost:
            raise UserError(
                f'Insufficient XP. You need {self.xp_cost} XP but have {profile.xp_total}.'
            )

        # Deduct XP (floor at 0 is guaranteed by the check above)
        profile.xp_total -= self.xp_cost
        self.env['language.xp.log'].sudo().create({
            'user_id': user_id,
            'amount':  -self.xp_cost,
            'reason':  'shop_purchase',
            'note':    self.name,
        })

        user_item = self.env['language.user.item'].sudo().create({
            'user_id': user_id,
            'item_id': self.id,
            'quantity': 1,
        })
        _logger.info('User %d purchased shop item %s (%d XP)', user_id, self.name, self.xp_cost)
        return user_item
