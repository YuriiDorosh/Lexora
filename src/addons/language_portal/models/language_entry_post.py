from odoo import fields, models


class LanguageEntryPost(models.Model):
    """Adds copied_from_post_id to language.entry (M7 extension)."""
    _inherit = 'language.entry'

    copied_from_post_id = fields.Many2one(
        comodel_name='language.post',
        string='Copied From Post',
        ondelete='set null',
    )
