"""Extend language.entry's provenance selection with 'lesson_import'.

Canonical-extension pattern (ADR-029 § 29b, ADR-038 § 38e) — append to
the base CREATED_FROM_SELECTION list rather than writing a bare string
value that was never declared on the field (the mistake this same ADR
flags in ``language_portal/controllers/portal_library.py``).
"""

from odoo import fields, models
from odoo.addons.language_words.models.language_entry import CREATED_FROM_SELECTION

LESSON_CREATED_FROM_SELECTION = CREATED_FROM_SELECTION + [
    ('lesson_import', 'Lesson Import'),
]


class LanguageEntry(models.Model):
    _inherit = 'language.entry'

    created_from = fields.Selection(
        selection=LESSON_CREATED_FROM_SELECTION,
        string='Created From',
        default='manual',
    )
