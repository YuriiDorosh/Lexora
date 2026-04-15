"""Extends language.entry with enrichment_ids One2many."""

from odoo import fields, models


class LanguageEntryEnrichment(models.Model):
    _inherit = 'language.entry'

    enrichment_ids = fields.One2many(
        comodel_name='language.enrichment',
        inverse_name='entry_id',
        string='Enrichments',
        readonly=True,
    )
