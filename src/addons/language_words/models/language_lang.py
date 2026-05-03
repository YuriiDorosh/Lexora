from odoo import fields, models

LANGUAGE_SELECTION = [
    ('en', 'English'),
    ('uk', 'Ukrainian'),
    ('el', 'Greek'),
    ('pl', 'Polish'),
]


class LanguageLang(models.Model):
    """Supported language lookup table.

    Seeded with four records (en/uk/el/pl) via data XML.
    Used for Many2many on language.user.profile.learning_languages
    and as a reusable reference across modules.
    """

    _name = 'language.lang'
    _description = 'Supported Language'
    _rec_name = 'name'
    _order = 'name'

    code = fields.Char(string='Code', required=True, size=10, index=True)
    name = fields.Char(string='Name', required=True)

    _sql_constraints = [
        ('unique_code', 'UNIQUE(code)', 'Language code must be unique.'),
    ]
