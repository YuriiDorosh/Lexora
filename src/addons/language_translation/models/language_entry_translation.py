"""Extend language.entry with translation_ids and auto-enqueue logic (M3).

This extension lives in language_translation (which depends on language_words)
so that language_words stays free of any translation-specific imports.
"""

import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class LanguageEntryTranslation(models.Model):
    """Adds translation_ids and post-save enqueue to language.entry."""

    _inherit = 'language.entry'

    translation_ids = fields.One2many(
        comodel_name='language.translation',
        inverse_name='entry_id',
        string='Translations',
        readonly=True,
    )

    # Override pvp_eligible: True when at least one translation is completed.
    pvp_eligible = fields.Boolean(
        string='PvP Eligible',
        compute='_compute_pvp_eligible',
        store=True,
        help='True if the entry has at least one completed translation (SPEC §3.1).',
    )

    @api.depends('translation_ids.status')
    def _compute_pvp_eligible(self):
        for entry in self:
            entry.pvp_eligible = any(
                t.status == 'completed' for t in entry.translation_ids
            )

    # ------------------------------------------------------------------ #
    # Override create to auto-enqueue translations (SPEC §4.1, §4.7)
    # ------------------------------------------------------------------ #

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for record in records:
            record._enqueue_translations()
        return records

    def _enqueue_translations(self):
        """Enqueue translation jobs for each of the owner's learning languages.

        Skips languages that match the entry's source language.
        If the user has no learning languages set, does nothing.
        """
        profile = self.env['language.user.profile']._get_or_create_for_user(self.owner_id)
        if not profile:
            return

        translation_model = self.env['language.translation']
        for lang in profile.learning_languages:
            if lang.code == self.source_language:
                continue  # don't translate into the source language
            translation_model._enqueue_single(self, lang.code)
