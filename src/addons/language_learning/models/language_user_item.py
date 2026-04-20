from odoo import api, fields, models


class LanguageUserItem(models.Model):
    _name = 'language.user.item'
    _description = 'User Owned Shop Item'
    _order = 'id desc'

    user_id = fields.Many2one(
        'res.users', required=True, ondelete='cascade', index=True,
    )
    item_id = fields.Many2one(
        'language.shop.item', required=True, ondelete='restrict', string='Item',
    )
    item_type = fields.Selection(
        related='item_id.item_type', store=True, readonly=True,
    )
    quantity = fields.Integer(default=1)
    activated_at = fields.Datetime()
    expires_at = fields.Datetime()
    is_consumed = fields.Boolean(default=False)

    @api.model
    def _get_active_item(self, user_id, item_type):
        """Return the first non-consumed item of item_type for user_id, or empty."""
        return self.sudo().search([
            ('user_id', '=', user_id),
            ('item_type', '=', item_type),
            ('is_consumed', '=', False),
            ('quantity', '>', 0),
        ], limit=1)

    def _consume(self):
        """Decrement quantity; mark consumed when it hits 0."""
        self.ensure_one()
        if self.quantity > 1:
            self.quantity -= 1
        else:
            self.write({'quantity': 0, 'is_consumed': True})
