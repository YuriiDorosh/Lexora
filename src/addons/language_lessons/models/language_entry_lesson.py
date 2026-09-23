"""Extend language.entry's provenance selection with 'lesson_import'.

Canonical-extension pattern (ADR-029 § 29b, ADR-038 § 38e) — append to
the base CREATED_FROM_SELECTION set rather than writing a bare string
value that was never declared on the field (the mistake this same ADR
flags in ``language_portal/controllers/portal_library.py``).

Uses Odoo's ``selection_add`` mechanism (not a full re-declaration of
``selection=``) so this module composes safely with any other module
that also extends ``created_from`` in the future, regardless of load
order. A full ``selection=[...]`` override here would silently clobber
whatever another such module added — Odoo logs exactly this as a
"overrides existing selection; use selection_add instead" warning,
which is what caught this during the M39 production install.
"""

from odoo import fields, models


class LanguageEntry(models.Model):
    _inherit = 'language.entry'

    created_from = fields.Selection(
        selection_add=[('lesson_import', 'Lesson Import')],
        ondelete={'lesson_import': 'set default'},
    )
