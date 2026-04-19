"""Extend language.entry with audio_ids One2many (M6).

Lives in language_audio (not language_words) so that language_words
stays free of audio-specific imports — same layering pattern as
language_entry_translation.py in language_translation.
"""

from odoo import fields, models


class LanguageEntryAudio(models.Model):
    """Adds audio_ids relation to language.entry."""

    _inherit = 'language.entry'

    audio_ids = fields.One2many(
        comodel_name='language.audio',
        inverse_name='entry_id',
        string='Audio',
        readonly=True,
    )
