from odoo import fields, models


class LanguageGrammarSection(models.Model):
    _name = 'language.grammar.section'
    _description = 'Grammar Encyclopedia Section'
    _order = 'category asc, sequence asc'

    title = fields.Char(required=True)
    slug = fields.Char(required=True, index=True,
                       help='URL-friendly identifier, e.g. "tenses" or "irregular-verbs"')
    category = fields.Selection([
        ('tenses', 'Tenses'),
        ('verbs', 'Verbs'),
        ('articles', 'Articles & Determiners'),
        ('conditionals', 'Conditionals'),
        ('modals', 'Modal Verbs'),
        ('voice', 'Voice & Reported Speech'),
    ], required=True, index=True)
    content_html = fields.Html('Content', sanitize=False)
    sequence = fields.Integer(default=10, index=True)
    is_published = fields.Boolean(default=True, index=True)

    _sql_constraints = [
        ('unique_slug', 'UNIQUE(slug)', 'A grammar section with this slug already exists.'),
    ]
