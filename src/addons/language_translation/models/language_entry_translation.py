"""Extend language.entry with translation_ids and auto-enqueue logic (M3).

This extension lives in language_translation (which depends on language_words)
so that language_words stays free of any translation-specific imports.
"""

import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)

# M29: every newly created entry auto-translates to all four supported
# languages (minus the source). This replaces the previous behavior of
# translating only to the user's profile.learning_languages, so Polish
# is always covered without requiring users to opt in via their profile.
_DEFAULT_TARGET_LANGUAGES = ('en', 'uk', 'el', 'pl')


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
        """Enqueue translation jobs for every supported target language.

        M29 (2026-05-03): we now translate to ALL supported languages
        (en/uk/el/pl) minus the source — not just the owner's
        profile.learning_languages. Rationale: Polish (and any future
        language) should be covered out of the box, and per-user
        learning_languages can still gate which translations are *shown*
        in the UI later. This guarantees coverage on the data layer.
        """
        translation_model = self.env['language.translation']
        for code in _DEFAULT_TARGET_LANGUAGES:
            if code == self.source_language:
                continue  # don't translate into the source language
            translation_model._enqueue_single(self, code)
