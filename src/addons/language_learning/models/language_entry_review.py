from odoo import api, fields, models


class LanguageEntryReview(models.Model):
    """Extend language.entry with SRS review card count + stat button action."""

    _inherit = 'language.entry'

    review_card_count = fields.Integer(
        string='SRS Cards',
        compute='_compute_review_card_count',
        store=False,
    )

    @api.depends()
    def _compute_review_card_count(self):
        Review = self.env['language.review']
        for entry in self:
            entry.review_card_count = Review.search_count([('entry_id', '=', entry.id)])

    def action_open_review_cards(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'SRS Review Cards',
            'res_model': 'language.review',
            'view_mode': 'list,form',
            'domain': [('entry_id', '=', self.id)],
            'context': {'default_entry_id': self.id},
        }
